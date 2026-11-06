"""Connector registry, authentication provider, and factory."""

import os
from typing import Dict, Optional, Type
from app.connectors.base import BaseDataConnector, ConnectorConfig
from app.connectors.exceptions import ConnectorError
from app.connectors.zapkey_connector import ZapkeyB2BConnector
from app.connectors.propequity_connector import PropEquityConnector
from app.connectors.propstack_connector import PropStackConnector
from app.connectors.hfc_connector import HFCBankingPortfolioConnector
from app.connectors.rera_developer_connector import RERADeveloperConnector
from app.connectors.ogd_connector import OpenGovernmentDataConnector
from app.connectors.state_igr_connector import StateRegistrationDepartmentConnector
from app.connectors.mock_connector import MockDeedConnector


class ConnectorRegistry:
    """Registry maintaining available data connector implementations and instances."""

    _connectors: Dict[str, Type[BaseDataConnector]] = {
        "zapkey_b2b": ZapkeyB2BConnector,
        "propequity": PropEquityConnector,
        "propstack": PropStackConnector,
        "hfc_banking": HFCBankingPortfolioConnector,
        "rera_developer": RERADeveloperConnector,
        "ogd_india": OpenGovernmentDataConnector,
        "state_igr": StateRegistrationDepartmentConnector,
        "mock_deed": MockDeedConnector,
    }

    @classmethod
    def register(cls, source_type: str, connector_cls: Type[BaseDataConnector]) -> None:
        cls._connectors[source_type.lower()] = connector_cls

    @classmethod
    def create(cls, source_type: str, config: ConnectorConfig) -> BaseDataConnector:
        key = source_type.lower()
        if key not in cls._connectors:
            raise ConnectorError(
                f"Unknown connector type '{source_type}'. Registered types: {list(cls._connectors.keys())}"
            )
        return cls._connectors[key](config)

    @classmethod
    def list_available(cls) -> Dict[str, str]:
        return {
            "zapkey_b2b": "Zapkey B2B Indian Property Transaction API (Class C / Institutional)",
            "propequity": "PropEquity National Transaction & Absorption Intelligence (Class C / Institutional)",
            "propstack": "PropStack Commercial & Residential Deed Aggregation API (Class C / Institutional)",
            "hfc_banking": "Institutional HFC & Banking Collateral Transaction Portfolio (Class C / Institutional)",
            "rera_developer": "RERA-Registered Developer Project Primary Allotment Feed (Class B / Bulk)",
            "ogd_india": "National Open Government Data Platform India (data.gov.in) (Class E / Public)",
            "state_igr": "State Registration & Stamps Department (IGR) SRO Gateway (Class A / API)",
            "mock_deed": "Mock / Test Deed Connector for Simulation & Testing (Class F / Mock)",
        }

