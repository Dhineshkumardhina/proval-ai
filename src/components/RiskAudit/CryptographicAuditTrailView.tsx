/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import {
  Link2,
  ShieldCheck,
  AlertOctagon,
  RefreshCw,
  Search,
  Filter,
  CheckCircle2,
  Lock,
  FileCode,
  Info,
  Clock,
  UserCheck,
  X,
  ExternalLink,
} from 'lucide-react';
import {
  AuditEvent,
  AuditVerificationReport,
  AuditSummary,
  fetchAuditEvents,
  verifyAuditChain,
  fetchAuditSummary,
} from '../../services/apiClient';

interface CryptographicAuditTrailViewProps {
  onSelectCase?: (caseId: string) => void;
}

export const CryptographicAuditTrailView: React.FC<CryptographicAuditTrailViewProps> = ({
  onSelectCase,
}) => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [verification, setVerification] = useState<AuditVerificationReport | null>(null);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const loadAuditData = async () => {
    setIsLoading(true);
    try {
      const [sumRes, evtsRes] = await Promise.all([
        fetchAuditSummary(),
        fetchAuditEvents({ limit: 100 }),
      ]);
      if (sumRes) setSummary(sumRes);
      if (evtsRes && evtsRes.items) setEvents(evtsRes.items);
    } catch {
      // Offline fallback retaining empty or existing state
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAuditData();
  }, []);

  const handleRunVerification = async () => {
    setIsVerifying(true);
    try {
      const rep = await verifyAuditChain();
      if (rep) {
        setVerification(rep);
        // Refresh summary
        const sum = await fetchAuditSummary();
        if (sum) setSummary(sum);
      }
    } catch {
      // Handle gracefully
    } finally {
      setIsVerifying(false);
    }
  };

  const filteredEvents = events.filter((e) => {
    if (eventTypeFilter !== 'ALL' && e.event_type !== eventTypeFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchActor = e.actor_id.toLowerCase().includes(q);
      const matchCase = (e.case_id || '').toLowerCase().includes(q);
      const matchType = e.event_type.toLowerCase().includes(q);
      const matchHash = e.current_hash.toLowerCase().includes(q);
      return matchActor || matchCase || matchType || matchHash;
    }
    return true;
  });

  const getEventBadgeColor = (type: string) => {
    if (type.includes('APPROVED')) return 'bg-[#DCFCE7] text-[#15803D] border-[#BBF7D0]';
    if (type.includes('REJECTED') || type.includes('FAILED')) return 'bg-[#FEE2E2] text-[#B91C1C] border-[#FECACA]';
    if (type.includes('VALUATION')) return 'bg-[#EFF6FF] text-[#1D4ED8] border-[#BFDBFE]';
    if (type.includes('AI_')) return 'bg-[#F5F3FF] text-[#6D28D9] border-[#DDD6FE]';
    if (type.includes('CASE_CREATED')) return 'bg-[#FEF3C7] text-[#B45309] border-[#FDE68A]';
    return 'bg-[#F1F5F9] text-[#475569] border-[#CBD5E1]';
  };

  return (
    <div className="space-y-4">
      {/* Verification Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        {/* Card 1: Chain Integrity Status */}
        <div className="bg-white p-3.5 rounded-md border border-[#E2E8F0] shadow-sm flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748B] block">
              Hash Chain Integrity
            </span>
            <div className="flex items-center gap-2 mt-1">
              {summary?.is_chain_intact || verification?.is_valid ? (
                <>
                  <ShieldCheck className="w-5 h-5 text-[#15803D]" />
                  <span className="text-sm font-bold text-[#15803D]">Intact & Verified</span>
                </>
              ) : summary ? (
                <>
                  <AlertOctagon className="w-5 h-5 text-[#DC2626]" />
                  <span className="text-sm font-bold text-[#DC2626]">Tampering Flagged</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-5 h-5 text-[#64748B]" />
                  <span className="text-sm font-bold text-[#64748B]">Ready for Audit</span>
                </>
              )}
            </div>
          </div>
          <p className="text-[10px] text-[#64748B] mt-2">
            SHA-256 block hash & predecessor continuity
          </p>
        </div>

        {/* Card 2: Total Recorded Blocks */}
        <div className="bg-white p-3.5 rounded-md border border-[#E2E8F0] shadow-sm">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748B] block">
            Recorded Ledger Blocks
          </span>
          <p className="text-xl font-bold font-mono text-[#142B4A] mt-1 tabular-nums">
            {summary ? summary.total_events : events.length}
          </p>
          <p className="text-[10px] text-[#64748B] mt-1">
            Latest Sequence: #{summary?.latest_sequence_number || events[0]?.sequence_number || 0}
          </p>
        </div>

        {/* Card 3: Cryptographic Anchors */}
        <div className="bg-white p-3.5 rounded-md border border-[#E2E8F0] shadow-sm">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748B] block">
            Current Block Hash
          </span>
          <p className="text-xs font-mono text-[#142B4A] mt-1 break-all select-all font-semibold" title={summary?.latest_hash}>
            {summary?.latest_hash ? `${summary.latest_hash.substring(0, 16)}...` : 'Genesis Block'}
          </p>
          <p className="text-[10px] text-[#64748B] mt-1">
            Genesis: 00000000...
          </p>
        </div>

        {/* Card 4: Action Button */}
        <div className="bg-white p-3.5 rounded-md border border-[#E2E8F0] shadow-sm flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748B] block">
              Cryptographic Audit
            </span>
            <p className="text-[11px] text-[#64748B] mt-0.5">
              Recalculate SHA-256 for all blocks
            </p>
          </div>
          <button
            onClick={handleRunVerification}
            disabled={isVerifying}
            className="w-full mt-2 py-1.5 px-3 rounded text-xs font-semibold bg-[#142B4A] hover:bg-[#1E3A5F] text-white flex items-center justify-center gap-1.5 shadow-xs transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isVerifying ? 'animate-spin' : ''}`} />
            {isVerifying ? 'Verifying Chain...' : 'Verify Hash Chain'}
          </button>
        </div>
      </div>

      {/* Verification Detailed Report Banner (if verified) */}
      {verification && (
        <div
          className={`p-3.5 rounded-md border text-xs space-y-1.5 ${
            verification.is_valid
              ? 'bg-[#F0FDF4] border-[#BBF7D0] text-[#166534]'
              : 'bg-[#FEF2F2] border-[#FECACA] text-[#991B1B]'
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 font-bold">
              {verification.is_valid ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-[#15803D]" />
                  <span>Audit Verification Passed: {verification.details}</span>
                </>
              ) : (
                <>
                  <AlertOctagon className="w-4 h-4 text-[#DC2626]" />
                  <span>Audit Verification Failed: {verification.details}</span>
                </>
              )}
            </div>
            <span className="text-[10px] font-mono text-slate-500">
              Verified at: {new Date(verification.verified_at).toLocaleTimeString()} UTC
            </span>
          </div>

          {!verification.is_valid && (
            <div className="p-2 bg-white rounded border border-[#FECACA] text-[11px] space-y-1 text-slate-800">
              <p>
                <strong>Error Taxonomy:</strong> <span className="font-mono text-red-600 font-bold">{verification.error_type}</span>
              </p>
              <p>
                <strong>Failed Sequence:</strong> Block #{verification.broken_index} (Event ID: {verification.broken_event_id})
              </p>
            </div>
          )}
        </div>
      )}

      {/* Security Boundary & DBA Notice (Mandatory Institutional Governance) */}
      <div className="bg-[#F8FAFC] border border-[#CBD5E1] p-3 rounded-md text-[11px] flex items-start gap-2.5 text-[#334155]">
        <Lock className="w-4 h-4 text-[#2563EB] shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-bold text-[#142B4A]">
            Institutional Security Boundary & Immutability Notice:
          </span>
          <p className="leading-relaxed text-[#475569]">
            This cryptographic hash chain guarantees immediate mathematical detection of unauthorized modifications,
            insertions, or deletions within the application layer. However, a database-level hash chain alone cannot prevent
            a privileged database administrator (DBA) with direct database write credentials from rewriting the entire history.
            Architected for periodic external anchoring (e.g., RFC 3161 certified timestamping or public ledger checkpointing).
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-3 rounded-md border border-[#E2E8F0] shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1.5 text-xs text-[#64748B]">
            <Filter className="w-3.5 h-3.5 text-[#142B4A]" />
            <span className="font-semibold">Filter Type:</span>
          </div>
          <select
            value={eventTypeFilter}
            onChange={(e) => setEventTypeFilter(e.target.value)}
            className="text-xs py-1 px-2.5 rounded border border-[#CBD5E1] bg-[#F8FAFC] text-[#142B4A] focus:outline-none focus:border-[#2563EB]"
          >
            <option value="ALL">All Event Types</option>
            <option value="CASE_CREATED">Case Created</option>
            <option value="VALUATION_CALCULATED">Valuation Calculated</option>
            <option value="UNDERWRITER_PARAM_CHANGED">Underwriter Param Changed</option>
            <option value="AI_EXPLANATION_GENERATED">AI Explanation Generated</option>
            <option value="CASE_APPROVED">Case Approved</option>
            <option value="CASE_REJECTED">Case Rejected</option>
            <option value="CASE_STATUS_CHANGED">Case Status Changed</option>
            <option value="AUTH_LOGIN_SUCCESS">Auth Login Success</option>
            <option value="AUTH_LOGIN_FAILED">Auth Login Failed</option>
            <option value="ADMIN_ACTION">Admin Genesis Action</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-[#94A3B8]" />
            <input
              type="text"
              placeholder="Search actor, case ID, or hash..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1 text-xs rounded border border-[#CBD5E1] bg-[#F8FAFC] text-[#142B4A] focus:outline-none focus:border-[#2563EB] w-56 sm:w-72"
            />
          </div>
          <button
            onClick={loadAuditData}
            title="Refresh events"
            className="p-1.5 rounded hover:bg-[#F1F5F9] text-[#64748B] hover:text-[#142B4A] transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Audit Events Ledger Table */}
      <div className="bg-white rounded-md border border-[#E2E8F0] shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-[#F8FAFC] border-b border-[#E2E8F0] text-[#64748B] font-semibold text-[10.5px] uppercase tracking-wider">
                <th className="py-2.5 px-3 w-16">Seq #</th>
                <th className="py-2.5 px-3">Event Type</th>
                <th className="py-2.5 px-3">Actor & Role</th>
                <th className="py-2.5 px-3">Case Reference</th>
                <th className="py-2.5 px-3">Timestamp (UTC)</th>
                <th className="py-2.5 px-3">Previous Hash</th>
                <th className="py-2.5 px-3">Current Hash</th>
                <th className="py-2.5 px-3 text-right">Payload</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E2E8F0]">
              {filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-xs text-[#94A3B8]">
                    {isLoading ? 'Loading audit ledger...' : 'No audit events found matching query.'}
                  </td>
                </tr>
              ) : (
                filteredEvents.map((evt) => (
                  <tr
                    key={evt.event_id}
                    className="hover:bg-[#F8FAFC] transition-colors cursor-pointer group"
                    onClick={() => setSelectedEvent(evt)}
                  >
                    <td className="py-2.5 px-3 font-mono font-bold text-[#142B4A]">
                      #{evt.sequence_number}
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold border ${getEventBadgeColor(
                          evt.event_type
                        )}`}
                      >
                        {evt.event_type}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-[#172033]">{evt.actor_id}</div>
                      <div className="text-[10px] text-[#64748B]">{evt.actor_role}</div>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      {evt.case_id ? (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (onSelectCase && evt.case_id) onSelectCase(evt.case_id);
                          }}
                          className="text-[#2563EB] hover:underline"
                        >
                          {evt.case_id}
                        </button>
                      ) : (
                        <span className="text-[#94A3B8]">—</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-[#475569] font-mono text-[11px] whitespace-nowrap">
                      {new Date(evt.timestamp).toISOString().replace('.000', '')}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[10.5px] text-[#64748B]" title={evt.prev_hash}>
                      {evt.prev_hash.substring(0, 10)}...
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[10.5px] font-semibold text-[#142B4A]" title={evt.current_hash}>
                      {evt.current_hash.substring(0, 10)}...
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedEvent(evt);
                        }}
                        className="px-2 py-1 text-[11px] font-semibold rounded bg-[#F1F5F9] hover:bg-[#E2E8F0] text-[#142B4A] transition-colors"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Block Payload Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-lg border border-[#CBD5E1] shadow-2xl max-w-2xl w-full max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in duration-150">
            {/* Modal Header */}
            <div className="px-4 py-3 bg-[#142B4A] text-white flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-[#38BDF8]" />
                <span className="font-bold text-xs uppercase tracking-wide">
                  Audit Block #{selectedEvent.sequence_number} Payload ({selectedEvent.event_id})
                </span>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="text-slate-300 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-4 overflow-y-auto space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2 bg-[#F8FAFC] p-3 rounded border border-[#E2E8F0] text-[11px]">
                <div>
                  <span className="text-[#64748B] block font-semibold">Event Type:</span>
                  <span className="font-bold text-[#142B4A]">{selectedEvent.event_type}</span>
                </div>
                <div>
                  <span className="text-[#64748B] block font-semibold">Actor:</span>
                  <span className="font-bold text-[#142B4A]">{selectedEvent.actor_id} ({selectedEvent.actor_role})</span>
                </div>
                <div>
                  <span className="text-[#64748B] block font-semibold">Case Reference:</span>
                  <span className="font-mono text-[#142B4A]">{selectedEvent.case_id || 'Global'}</span>
                </div>
                <div>
                  <span className="text-[#64748B] block font-semibold">Recorded Timestamp (UTC):</span>
                  <span className="font-mono text-[#142B4A]">{selectedEvent.timestamp}</span>
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748B] block">
                  Cryptographic Hash Linkages
                </span>
                <div className="p-2 bg-[#F1F5F9] rounded border border-[#CBD5E1] font-mono text-[11px] space-y-1">
                  <div>
                    <span className="text-[#64748B]">Predecessor Hash: </span>
                    <span className="break-all text-slate-800">{selectedEvent.prev_hash}</span>
                  </div>
                  <div>
                    <span className="text-[#64748B]">Current Block Hash: </span>
                    <span className="break-all font-bold text-[#142B4A]">{selectedEvent.current_hash}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748B] block">
                  Canonically Serialized Payload
                </span>
                <pre className="p-3 bg-[#0F172A] text-[#38BDF8] rounded text-[11px] font-mono overflow-x-auto max-h-60">
                  {JSON.stringify(selectedEvent.payload, null, 2)}
                </pre>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-4 py-2.5 bg-[#F8FAFC] border-t border-[#E2E8F0] flex justify-end">
              <button
                onClick={() => setSelectedEvent(null)}
                className="px-3 py-1.5 rounded text-xs font-semibold bg-[#142B4A] text-white hover:bg-[#1E3A5F] transition-colors"
              >
                Close Block Detail
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

