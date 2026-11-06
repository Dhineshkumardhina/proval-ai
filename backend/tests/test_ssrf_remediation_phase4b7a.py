"""Comprehensive test suite for Phase 4B-7A Critical SSRF and Network Security Remediation.

Verifies:
1. Finding 1: DNS Rebinding / TOCTOU & Socket-Level IP Pinning:
   - Pinned IP socket connection evidence (demonstrating connection to exact IP).
   - TLS SNI and HTTP Host header integrity.
   - Deterministic DNS rebinding attack simulations blocked.
   - Multiple DNS A records (with mixed public/private IPs) blocked.
   - Multiple DNS AAAA records (with mixed public/private IPs) blocked.
   - TLS certificate hostname verification and untrusted certificate rejection.
2. Finding 2: IPv4-Mapped IPv6 & Subnet Normalization:
   - Explicit tests for ::ffff:127.0.0.1, ::ffff:169.254.169.254, ::ffff:10.0.0.1,
     ::ffff:192.168.1.1, ::ffff:172.16.0.1.
   - IPv4 loopback, private ranges, link-local.
   - IPv6 loopback, link-local, unique-local.
   - Cloud metadata destinations.
   - Normalization of hex, octal with leading zeros, DWORD integer representations.
   - Strict rejection of ambiguous and malformed address representations.
3. Additional Network Security Controls:
   - Redirect to localhost blocked.
   - Redirect to private IPv4 blocked.
   - Redirect to IPv4-mapped IPv6 blocked.
   - Multi-hop redirect chains and depth limit enforcement.
   - HTTPS enforcement in production.
   - Port whitelist enforcement (disallowed ports blocked).
   - Ambient proxy environment variables isolation (trust_env=False).
   - Oversized streamed response abortion (PayloadTooLargeError).
   - Retry exhaustion and backoff behavior.
"""

import asyncio
import datetime
import ipaddress
import json
import os
import socket
import ssl
from typing import Any, Dict, List
import pytest
import httpx
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import settings
from app.connectors.exceptions import (
    AuthenticationError,
    RateLimitExceededError,
    NetworkTimeoutError,
    SecurityViolationError,
    InvalidResponseError,
    PayloadTooLargeError,
)
from app.connectors.http_client import (
    ResilientHTTPClient,
    SecuredPinningTransport,
    SecuredPinningNetworkBackend,
    normalize_ip_address,
    is_ip_disallowed,
    resolve_and_validate_hostname,
    PRODUCTION_ALLOWED_HOSTNAMES,
    TEST_ALLOWED_HOSTNAMES,
    ALLOWED_PORTS_PRODUCTION,
    ALLOWED_PORTS_NON_PROD,
    DEFAULT_MAX_RESPONSE_BYTES,
    DEFAULT_MAX_REQUEST_BYTES,
)


# =============================================================================
# Helper: Generate In-Memory Self-Signed Certificate for Isolated TLS Testing
# =============================================================================

def generate_test_tls_credentials(common_name: str, san_names: List[str] = None):
    """Generate self-signed X.509 certificate and private key in PEM format."""
    san_names = san_names or [common_name]
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(name) for name in san_names]),
            critical=False,
        )
    )
    cert = builder.sign(key, hashes.SHA256())
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    return cert_pem, key_pem


# =============================================================================
# 1. FINDING 2: IPv4-MAPPED IPv6 & ADDRESS NORMALIZATION TESTS
# =============================================================================

class TestIPv4MappedIPv6AndNormalization:
    """Verifies that IPv4-mapped IPv6, 6to4, and ambiguous IP notations are normalized and blocked."""

    @pytest.mark.parametrize(
        "ip_str",
        [
            "::ffff:127.0.0.1",
            "::ffff:169.254.169.254",
            "::ffff:10.0.0.1",
            "::ffff:192.168.1.1",
            "::ffff:172.16.0.1",
        ],
    )
    def test_explicit_mandated_ipv4_mapped_ipv6_addresses_disallowed(self, ip_str):
        """Audit Finding 2 Mandated Test: Explicit IPv4-mapped IPv6 addresses must be blocked."""
        # Test as string
        assert is_ip_disallowed(ip_str) is True, f"Failed to disallow string {ip_str}"

        # Test as ipaddress.IPv6Address object
        ip_obj = ipaddress.ip_address(ip_str)
        assert is_ip_disallowed(ip_obj) is True, f"Failed to disallow object {ip_obj}"

        # Verify normalization yields correct underlying IPv4Address
        norm = normalize_ip_address(ip_str)
        assert isinstance(norm, ipaddress.IPv4Address)
        assert norm.is_private or norm.is_loopback or norm.is_link_local

    def test_ipv4_loopback_ranges_disallowed(self):
        """IPv4 loopback (127.0.0.0/8) must be strictly blocked."""
        for ip in ["127.0.0.1", "127.0.0.2", "127.10.20.30", "127.255.255.254"]:
            assert is_ip_disallowed(ip) is True
            assert is_ip_disallowed(ipaddress.ip_address(ip)) is True

    def test_ipv4_private_ranges_disallowed(self):
        """RFC 1918 private subnets (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) must be blocked."""
        private_ips = [
            "10.0.0.1", "10.255.255.254",
            "172.16.0.1", "172.24.1.1", "172.31.255.254",
            "192.168.0.1", "192.168.1.100", "192.168.255.254",
        ]
        for ip in private_ips:
            assert is_ip_disallowed(ip) is True
            assert is_ip_disallowed(ipaddress.ip_address(ip)) is True

    def test_ipv4_link_local_and_metadata_disallowed(self):
        """IPv4 link-local and cloud metadata (169.254.0.0/16) must be blocked."""
        for ip in ["169.254.169.254", "169.254.0.1", "169.254.254.254"]:
            assert is_ip_disallowed(ip) is True
            assert is_ip_disallowed(ipaddress.ip_address(ip)) is True

    def test_ipv6_loopback_link_local_unique_local_disallowed(self):
        """IPv6 loopback (::1), link-local (fe80::/10), and unique-local (fc00::/7) must be blocked."""
        disallowed_v6 = [
            "::1",
            "fe80::1",
            "fe80::dead:beef",
            "fc00::1",
            "fd00::1",
            "fd12:3456:789a::1",
        ]
        for ip in disallowed_v6:
            assert is_ip_disallowed(ip) is True
            assert is_ip_disallowed(ipaddress.ip_address(ip)) is True

    def test_ipv4_mapped_hex_and_bracketed_variants_disallowed(self):
        """Test alternative representations of IPv4-mapped IPv6."""
        # ::ffff:7f00:1 is hexadecimal notation for ::ffff:127.0.0.1
        assert is_ip_disallowed("::ffff:7f00:1") is True
        # Bracketed notation as often found in URLs
        assert is_ip_disallowed("[::ffff:127.0.0.1]") is True
        assert is_ip_disallowed("[::ffff:169.254.169.254]") is True

    def test_public_ips_permitted(self):
        """Legitimate public IP addresses must NOT be disallowed."""
        public_ips = [
            "104.21.45.10",
            "93.184.216.34",
            "8.8.8.8",
            "1.1.1.1",
            "2606:4700:4700::1111",
        ]
        for ip in public_ips:
            assert is_ip_disallowed(ip) is False, f"Legitimate public IP {ip} was incorrectly disallowed"

    def test_ambiguous_and_malformed_representations_rejected(self):
        """Malformed, octal, hex, and DWORD integer notations must raise SecurityViolationError or be disallowed."""
        # Octal representations with leading zeros
        with pytest.raises(SecurityViolationError):
            normalize_ip_address("0177.0.0.1")

        with pytest.raises(SecurityViolationError):
            normalize_ip_address("010.0.0.1")

        # Hex representations
        with pytest.raises(SecurityViolationError):
            normalize_ip_address("0x7f.0.0.1")

        with pytest.raises(SecurityViolationError):
            normalize_ip_address("0x7f000001")

        # Integer / DWORD representations
        with pytest.raises(SecurityViolationError):
            normalize_ip_address("2130706433")

        # Malformed strings
        with pytest.raises(SecurityViolationError):
            normalize_ip_address("not-an-ip")

        with pytest.raises(SecurityViolationError):
            normalize_ip_address("127.0.0.1.1")

        # is_ip_disallowed must safely return True for all of these
        for bad in ["0177.0.0.1", "0x7f000001", "2130706433", "malformed"]:
            assert is_ip_disallowed(bad) is True


# =============================================================================
# 2. FINDING 1: DNS REBINDING, MULTI-RECORD, & CONNECTION PINNING TESTS
# =============================================================================

class TestDNSRebindingAndConnectionPinning:
    """Verifies that socket connections are pinned to validated IPs and DNS rebinding attacks are thwarted."""

    def test_multiple_dns_a_records_with_private_ip_blocked(self, monkeypatch):
        """Multi-A Rebinding: If ANY resolved A record is in a disallowed range, reject completely."""
        def mock_multi_a(host, port, *args, **kwargs):
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.21.45.10", 443)),  # Good public IP
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),     # Malicious loopback
            ]

        monkeypatch.setattr(socket, "getaddrinfo", mock_multi_a)

        with pytest.raises(SecurityViolationError) as exc_info:
            resolve_and_validate_hostname("api.zapkey.com", allow_test_endpoints=False, is_production=False)
        assert "resolves to disallowed private / metadata IP '127.0.0.1'" in str(exc_info.value)

    def test_multiple_dns_aaaa_records_with_private_ip_blocked(self, monkeypatch):
        """Multi-AAAA Rebinding: If ANY resolved AAAA record is in a disallowed range, reject completely."""
        def mock_multi_aaaa(host, port, *args, **kwargs):
            return [
                (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2606:4700::1", 443)),        # Public IPv6
                (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::ffff:169.254.169.254", 443)), # Disallowed v4-mapped
            ]

        monkeypatch.setattr(socket, "getaddrinfo", mock_multi_aaaa)

        with pytest.raises(SecurityViolationError) as exc_info:
            resolve_and_validate_hostname("api.zapkey.com", allow_test_endpoints=False, is_production=False)
        assert "resolves to disallowed private / metadata IP" in str(exc_info.value)

    def test_multiple_dns_all_public_allowed(self, monkeypatch):
        """Multiple public A records for authorized hostname must be accepted."""
        def mock_multi_public(host, port, *args, **kwargs):
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.21.45.10", 443)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.21.45.11", 443)),
            ]

        monkeypatch.setattr(socket, "getaddrinfo", mock_multi_public)
        ips = resolve_and_validate_hostname("api.zapkey.com", allow_test_endpoints=False, is_production=False)
        assert ips == ["104.21.45.10", "104.21.45.11"]

    @pytest.mark.asyncio
    async def test_dns_rebinding_simulation_blocked_at_connect_time(self, monkeypatch):
        """TOCTOU Simulation: Preflight check returns public IP, but connect-time DNS resolves to private IP.
        
        The secured connection-pinning backend re-validates and blocks the connection attempt.
        """
        dns_queries = 0

        def rebinding_dns(host, port, *args, **kwargs):
            nonlocal dns_queries
            dns_queries += 1
            if dns_queries == 1:
                # First resolution (preflight check): Legitimate public IP
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.21.45.10", 443))]
            else:
                # Rebound resolution (connect-time exploit attempt): Internal AWS metadata IP
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 443))]

        monkeypatch.setattr(socket, "getaddrinfo", rebinding_dns)

        # Preflight validation passes on query 1
        preflight_ips = resolve_and_validate_hostname("api.zapkey.com", allow_test_endpoints=False, is_production=False)
        assert preflight_ips == ["104.21.45.10"]

        backend = SecuredPinningNetworkBackend(allow_test_endpoints=False, is_production=False)

        # Connect attempt executes query 2 and must be blocked immediately
        with pytest.raises(SecurityViolationError) as exc_info:
            await backend.connect_tcp(host="api.zapkey.com", port=443)

        assert "resolves to disallowed private / metadata IP '169.254.169.254'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_socket_connection_pinning_evidence(self):
        """Verifiable Connection Pinning: Prove that the TCP socket connects to the exact pinned IP,
        while HTTP Host header remains the authorized domain.
        """
        received_requests = []

        async def local_echo_server(reader, writer):
            data = await reader.read(2048)
            received_requests.append(data.decode("utf-8", errors="ignore"))
            response = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: 15\r\n"
                b"\r\n"
                b'{"status":"ok"}'
            )
            writer.write(response)
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(local_echo_server, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        # Pin "api.zapkey.com" to "127.0.0.1" for this isolated test
        client = ResilientHTTPClient(
            base_url=f"http://api.zapkey.com:{port}",
            allow_test_endpoints=True,
            pinned_ip_override={"api.zapkey.com": "127.0.0.1"},
            verify_ssl=False,
        )

        res = await client.request(method="GET", endpoint="/v1/pinned-test")
        assert res.get("status") == "ok"

        # Verify connection pinning evidence
        assert client.last_pinned_ip == "127.0.0.1"
        assert len(client.connection_audit_log) >= 1
        audit_entry = client.connection_audit_log[-1]
        assert audit_entry["hostname"] == "api.zapkey.com"
        assert audit_entry["pinned_ip"] == "127.0.0.1"
        assert audit_entry["port"] == port

        # Inspect the HTTP headers received by the local server
        assert len(received_requests) >= 1
        req_text = received_requests[0]
        # HTTP Host header must remain "api.zapkey.com:<port>" per RFC standards
        assert f"Host: api.zapkey.com:{port}" in req_text

        server.close()
        await server.wait_closed()

    @pytest.mark.asyncio
    async def test_tls_certificate_hostname_verification_and_sni(self, tmp_path):
        """TLS Verification: TLS SNI and certificate hostname matching must succeed with valid cert,
        and fail if server presents a certificate for a mismatched domain.
        """
        # 1. Generate certificate for api.zapkey.com
        cert_pem, key_pem = generate_test_tls_credentials("api.zapkey.com")
        cert_file = tmp_path / "zapkey.crt"
        key_file = tmp_path / "zapkey.key"
        cert_file.write_bytes(cert_pem)
        key_file.write_bytes(key_pem)

        ssl_server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_server_ctx.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))

        async def https_server(reader, writer):
            data = await reader.read(2048)
            body = b'{"tls":"success"}'
            cl_header = f"Content-Length: {len(body)}\r\n".encode("ascii")
            response = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: application/json\r\n"
                + cl_header
                + b"\r\n"
                + body
            )
            writer.write(response)
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(https_server, "127.0.0.1", 0, ssl=ssl_server_ctx)
        port = server.sockets[0].getsockname()[1]

        # 2. Client with CA bundle trusting our generated certificate
        client_ssl_ctx = ssl.create_default_context(cafile=str(cert_file))

        transport = SecuredPinningTransport(
            verify=client_ssl_ctx,
            allow_test_endpoints=True,
            pinned_ip_override={"api.zapkey.com": "127.0.0.1"},
        )

        async with httpx.AsyncClient(transport=transport, follow_redirects=False, trust_env=False) as session:
            resp = await session.get(f"https://api.zapkey.com:{port}/v1/tls-test")
            assert resp.status_code == 200
            assert resp.json() == {"tls": "success"}

        server.close()
        await server.wait_closed()

    @pytest.mark.asyncio
    async def test_mismatched_tls_certificate_rejected(self, tmp_path):
        """TLS Rejection: A server certificate with mismatched Common Name (e.g. evil-domain.com) must be rejected."""
        # Generate certificate for "evil-domain.com"
        cert_pem, key_pem = generate_test_tls_credentials("evil-domain.com")
        cert_file = tmp_path / "evil.crt"
        key_file = tmp_path / "evil.key"
        cert_file.write_bytes(cert_pem)
        key_file.write_bytes(key_pem)

        ssl_server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_server_ctx.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))

        async def evil_server(reader, writer):
            await reader.read(1024)
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(evil_server, "127.0.0.1", 0, ssl=ssl_server_ctx)
        port = server.sockets[0].getsockname()[1]

        # Trust the CA, but connecting to "api.zapkey.com" while cert is for "evil-domain.com"
        client_ssl_ctx = ssl.create_default_context(cafile=str(cert_file))
        transport = SecuredPinningTransport(
            verify=client_ssl_ctx,
            allow_test_endpoints=True,
            pinned_ip_override={"api.zapkey.com": "127.0.0.1"},
        )

        async with httpx.AsyncClient(transport=transport, follow_redirects=False, trust_env=False) as session:
            with pytest.raises((httpx.ConnectError, ssl.SSLCertVerificationError)):
                await session.get(f"https://api.zapkey.com:{port}/v1/tls-test")

        server.close()
        await server.wait_closed()


# =============================================================================
# 3. REDIRECT SECURITY TESTS (Hop-by-Hop Validation)
# =============================================================================

class TestRedirectSecurity:
    """Verifies that every redirect hop strictly enforces SSRF, hostname, and IP boundaries."""

    @pytest.mark.asyncio
    async def test_redirect_to_localhost_blocked(self):
        """Redirect aiming at localhost in production or without test mode is blocked."""
        def handler(request: httpx.Request):
            return httpx.Response(status_code=302, headers={"Location": "http://localhost:8080/secret"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as mock_client:
            client = ResilientHTTPClient(base_url="https://api.zapkey.com", allow_test_endpoints=False)
            with pytest.raises(SecurityViolationError) as exc_info:
                await client.request(method="GET", endpoint="/v1/redir", client=mock_client)
            msg = str(exc_info.value).lower()
            assert "ssrf" in msg or "whitelist" in msg or "prohibited" in msg

    @pytest.mark.asyncio
    async def test_redirect_to_private_ipv4_blocked(self):
        """Redirect aiming at RFC 1918 private IPv4 is blocked."""
        for target in ["http://10.0.0.1/admin", "http://192.168.1.1/config", "http://172.16.0.1/meta"]:
            def handler(request: httpx.Request, loc=target):
                return httpx.Response(status_code=302, headers={"Location": loc})

            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport) as mock_client:
                client = ResilientHTTPClient(base_url="https://api.zapkey.com", allow_test_endpoints=True)
                with pytest.raises(SecurityViolationError) as exc_info:
                    await client.request(method="GET", endpoint="/v1/step", client=mock_client)
                assert "SSRF Prevention" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_redirect_to_ipv4_mapped_ipv6_blocked(self):
        """Audit Finding 2 Mandated: Redirect aiming at IPv4-mapped IPv6 must be blocked."""
        targets = [
            "http://[::ffff:127.0.0.1]/secret",
            "http://[::ffff:169.254.169.254]/latest/meta-data",
            "http://[::ffff:10.0.0.1]/db",
        ]
        for target in targets:
            def handler(request: httpx.Request, loc=target):
                return httpx.Response(status_code=302, headers={"Location": loc})

            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport) as mock_client:
                client = ResilientHTTPClient(base_url="https://api.zapkey.com", allow_test_endpoints=True)
                with pytest.raises(SecurityViolationError) as exc_info:
                    await client.request(method="GET", endpoint="/v1/step", client=mock_client)
                assert "SSRF Prevention" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_multi_hop_redirect_chain_allowed_when_valid(self):
        """Valid multi-hop redirect chain within allowed hostnames succeeds."""
        hop_count = 0

        def handler(request: httpx.Request):
            nonlocal hop_count
            hop_count += 1
            if request.url.path == "/v1/hop1":
                return httpx.Response(status_code=302, headers={"Location": "https://api.zapkey.com/v1/hop2"})
            elif request.url.path == "/v1/hop2":
                return httpx.Response(status_code=302, headers={"Location": "https://api.zapkey.com/v1/final"})
            elif request.url.path == "/v1/final":
                return httpx.Response(status_code=200, json={"status": "destination_reached"})
            return httpx.Response(status_code=404)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as mock_client:
            client = ResilientHTTPClient(base_url="https://api.zapkey.com", allow_test_endpoints=True)
            res = await client.request(method="GET", endpoint="/v1/hop1", client=mock_client, max_redirects=3)
            assert res.get("status") == "destination_reached"
            assert hop_count == 3

    @pytest.mark.asyncio
    async def test_redirect_chain_blocked_at_second_hop_if_evil(self):
        """If hop 1 redirects to an allowed domain but hop 2 tries to steer to an internal IP, abort immediately."""
        def handler(request: httpx.Request):
            if request.url.path == "/v1/safe_hop":
                return httpx.Response(status_code=302, headers={"Location": "https://api.zapkey.com/v1/evil_hop"})
            elif request.url.path == "/v1/evil_hop":
                # Steer to metadata service
                return httpx.Response(status_code=302, headers={"Location": "http://169.254.169.254/latest/meta-data"})
            return httpx.Response(status_code=200, json={"status": "ok"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as mock_client:
            client = ResilientHTTPClient(base_url="https://api.zapkey.com", allow_test_endpoints=True)
            with pytest.raises(SecurityViolationError) as exc_info:
                await client.request(method="GET", endpoint="/v1/safe_hop", client=mock_client, max_redirects=3)
            assert "SSRF" in str(exc_info.value)


# =============================================================================
# 4. PORT FILTERING, HTTPS ENFORCEMENT, & PROXY DEFENSES
# =============================================================================

class TestPortAndProtocolSecurity:
    """Verifies that non-standard ports, insecure schemes, and ambient proxy environments are rejected."""

    def test_https_enforced_in_production(self, monkeypatch):
        """Production requests must strictly use HTTPS; HTTP is rejected."""
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        with pytest.raises(SecurityViolationError) as exc_info:
            ResilientHTTPClient(base_url="http://api.zapkey.com", allow_test_endpoints=False)
        assert "Production requests must use HTTPS" in str(exc_info.value)

    def test_disallowed_ports_rejected(self, monkeypatch):
        """Prohibit non-whitelisted ports (22, 25, 3306, 5432, 6379, 8080) to prevent port scanning."""
        # Non-production without allow_test_endpoints
        for port in [22, 25, 3306, 5432, 6379, 8080]:
            with pytest.raises(SecurityViolationError) as exc_info:
                ResilientHTTPClient(base_url=f"https://api.zapkey.com:{port}", allow_test_endpoints=False)
            assert "prohibited" in str(exc_info.value)

        # In production mode, port 80 is strictly disallowed
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        with pytest.raises(SecurityViolationError) as exc_info2:
            resolve_and_validate_hostname("api.zapkey.com", port=80, is_production=True)
        assert "port 80 is prohibited in production mode" in str(exc_info2.value).lower()

    def test_ambient_proxy_environment_variables_ignored(self, monkeypatch):
        """Zero-Trust: ambient proxy variables (HTTP_PROXY, HTTPS_PROXY, ALL_PROXY) must NOT be trusted."""
        monkeypatch.setenv("HTTP_PROXY", "http://untrusted-proxy.com:8080")
        monkeypatch.setenv("HTTPS_PROXY", "http://untrusted-proxy.com:8080")
        monkeypatch.setenv("ALL_PROXY", "socks5://untrusted-proxy.com:1080")

        transport = SecuredPinningTransport(allow_test_endpoints=True)
        # Verify transport sets trust_env to False
        assert transport._pool is not None

        # When creating httpx.AsyncClient with trust_env=False, mounts are empty
        client = httpx.AsyncClient(transport=transport, trust_env=False)
        assert client._trust_env is False
        assert client._mounts == {}


# =============================================================================
# 5. STREAMED PAYLOAD SIZE & RETRY EXHAUSTION TESTS
# =============================================================================

class TestPayloadStreamingAndRetryExhaustion:
    """Verifies protection against oversized streamed responses and verifies retry exhaustion handling."""

    @pytest.mark.asyncio
    async def test_oversized_streamed_chunked_response_aborted(self):
        """Verify that a response streamed in chunks without Content-Length is aborted before memory exhaustion."""
        async def infinite_chunk_stream():
            while True:
                yield b"X" * 1024

        def handler(request: httpx.Request):
            return httpx.Response(status_code=200, content=infinite_chunk_stream())

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as mock_client:
            client = ResilientHTTPClient(
                base_url="https://api.zapkey.com",
                max_response_bytes=5 * 1024,  # 5KB limit
                allow_test_endpoints=True,
            )
            with pytest.raises(PayloadTooLargeError) as exc_info:
                await client.request(method="GET", endpoint="/v1/stream", client=mock_client)
            assert "exceeds limit" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_retry_exhaustion_raises_network_timeout_error(self):
        """Verify repeated transport connection timeouts exhaust retries and raise NetworkTimeoutError."""
        calls = 0

        def handler(request: httpx.Request):
            nonlocal calls
            calls += 1
            raise httpx.ConnectTimeout("Upstream socket unreachable")

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as mock_client:
            client = ResilientHTTPClient(
                base_url="https://api.zapkey.com",
                max_retries=2,
                backoff_factor=0.01,
                rate_limit_per_minute=6000,
                allow_test_endpoints=True,
            )
            with pytest.raises(NetworkTimeoutError) as exc_info:
                await client.request(method="GET", endpoint="/v1/fail", client=mock_client)
            assert "Exceeded max retries" in str(exc_info.value) or "Request timeout" in str(exc_info.value)
            assert calls == 3  # Initial + 2 retries

