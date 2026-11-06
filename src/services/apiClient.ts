/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * 
 * PropVal AI Backend Client Integration Layer
 */

import { ValuationInputParams, ValuationResult } from '../utils/valuationEngine';
import { ValuationCase, CaseStatus, ComparableDeed } from '../types/valuation';

const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

let _inMemoryToken: string | null = null;

// Lightweight in-flight deduplication and short-TTL caching for static metadata
const inFlightRequests = new Map<string, Promise<any>>();
const cacheStore = new Map<string, { data: any; expiry: number }>();

export function clearClientCache(pattern?: string): void {
  if (!pattern) {
    cacheStore.clear();
    return;
  }
  for (const key of cacheStore.keys()) {
    if (key.includes(pattern)) {
      cacheStore.delete(key);
    }
  }
}

async function cachedFetch<T>(key: string, ttlMs: number, fetcher: () => Promise<T>): Promise<T> {
  const cached = cacheStore.get(key);
  const now = Date.now();
  if (cached && cached.expiry > now) {
    return cached.data;
  }
  if (inFlightRequests.has(key)) {
    return inFlightRequests.get(key)!;
  }
  const promise = fetcher()
    .then((data) => {
      inFlightRequests.delete(key);
      if (data !== null && data !== undefined) {
        cacheStore.set(key, { data, expiry: Date.now() + ttlMs });
      }
      return data;
    })
    .catch((err) => {
      inFlightRequests.delete(key);
      throw err;
    });
  inFlightRequests.set(key, promise);
  return promise;
}

export function getAuthToken(): string | null {
  if (_inMemoryToken) return _inMemoryToken;
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      _inMemoryToken = window.localStorage.getItem('propval_auth_token');
    }
  } catch {
    // localStorage restricted or not available
  }
  return _inMemoryToken;
}

export function setAuthToken(token: string | null): void {
  _inMemoryToken = token;
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      if (token) {
        window.localStorage.setItem('propval_auth_token', token);
      } else {
        window.localStorage.removeItem('propval_auth_token');
      }
    }
  } catch {
    // localStorage restricted or not available
  }
}

export async function loginUser(username = 'v.sundaram', password = 'SrUnderwriter@2026!'): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    throw new Error(`Authentication failed (${response.status})`);
  }
  const data = await response.json();
  setAuthToken(data.access_token);
  return data.access_token;
}

export async function logoutUser(): Promise<void> {
  const token = getAuthToken();
  if (token) {
    try {
      await fetch(`${API_BASE_URL}/api/v1/auth/revoke`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/json',
        },
      });
    } catch {
      // ignore
    }
  }
  setAuthToken(null);
}

export async function ensureAuthenticated(): Promise<string | null> {
  const existing = getAuthToken();
  if (existing) return existing;
  try {
    return await loginUser();
  } catch (err) {
    console.warn('Authentication negotiation failed:', err);
    return null;
  }
}

function getHeaders(extraHeaders: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = { ...extraHeaders };
  const token = getAuthToken();
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function authenticatedFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  let token = getAuthToken();
  if (!token) {
    token = await ensureAuthenticated();
  }
  const headers = getHeaders((init.headers as Record<string, string>) || {});
  let response = await fetch(input, { ...init, headers });
  if (response.status === 401 && token) {
    setAuthToken(null);
    const newToken = await ensureAuthenticated();
    if (newToken) {
      const retryHeaders = getHeaders((init.headers as Record<string, string>) || {});
      response = await fetch(input, { ...init, headers: retryHeaders });
    }
  }
  return response;
}

export interface BackendHealthResponse {
  status: string;
  environment: string;
  version: string;
  engineType: string;
  database: string;
  timestamp: string;
}

export interface BackendValuationEstimateResponse extends ValuationResult {
  engineVersion?: string;
  engineType?: string;
  dataSource?: string;
  isProvisional?: boolean;
  calculatedAt?: string;
}

export interface CaseListFilters {
  city?: string;
  status?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface CaseListResponse {
  items: ValuationCase[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Check connectivity to the FastAPI backend health endpoint.
 */
export async function checkBackendHealth(signal?: AbortSignal): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/health`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      signal,
    });
    if (!response.ok) return false;
    const data: BackendHealthResponse = await response.json();
    return data.status === 'healthy';
  } catch {
    return false;
  }
}

/**
 * Dispatch valuation calculation request to FastAPI backend.
 * Throws on network failure or non-200 HTTP response.
 */
export async function fetchValuationEstimate(
  params: ValuationInputParams,
  signal?: AbortSignal
): Promise<BackendValuationEstimateResponse> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/valuation/estimate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(params),
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown server error');
    throw new Error(`Valuation backend error (${response.status}): ${errorText}`);
  }

  const data = await response.json();

  return {
    carpetAreaSqFt: data.carpetAreaSqFt,
    superBuiltUpAreaSqFt: data.superBuiltUpAreaSqFt,
    unadjustedRatePerSqFt: data.unadjustedRatePerSqFt,
    ruleAdjustedRatePerSqFt: data.ruleAdjustedRatePerSqFt,
    aiAdjustedRatePerSqFt: data.aiAdjustedRatePerSqFt ?? data.ruleAdjustedRatePerSqFt,
    circleRatePerSqFt: data.circleRatePerSqFt,
    grossMarketValue: data.grossMarketValue,
    netAssessedValue: data.netAssessedValue,
    distressLiquidationValue: data.distressLiquidationValue,
    maxSanctionAmount: data.maxSanctionAmount,
    deviationFromCircleRatePct: data.deviationFromCircleRatePct,
    confidenceScorePct: data.confidenceScorePct,
    riskTier: data.riskTier,
    attributionBreakdown: data.attributionBreakdown || [],
    engineVersion: data.engineVersion,
    engineType: data.engineType,
    dataSource: data.dataSource,
    isProvisional: data.isProvisional,
    calculatedAt: data.calculatedAt,
  };
}

/**
 * Fetch list of valuation cases from backend API with optional filtering.
 */
export async function fetchCases(
  filters: CaseListFilters = {},
  signal?: AbortSignal
): Promise<CaseListResponse> {
  const queryParams = new URLSearchParams();
  if (filters.city) queryParams.append('city', filters.city);
  if (filters.status) queryParams.append('status', filters.status);
  if (filters.search) queryParams.append('search', filters.search);
  if (filters.limit) queryParams.append('limit', filters.limit.toString());
  if (filters.offset) queryParams.append('offset', filters.offset.toString());

  const url = `${API_BASE_URL}/api/v1/cases${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
  const response = await authenticatedFetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown server error');
    throw new Error(`Failed to fetch valuation cases (${response.status}): ${errorText}`);
  }

  return response.json();
}

/**
 * Fetch a single valuation case by ID.
 */
export async function fetchCaseById(caseId: string, signal?: AbortSignal): Promise<ValuationCase> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/cases/${encodeURIComponent(caseId)}`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown server error');
    throw new Error(`Case ${caseId} not found (${response.status}): ${errorText}`);
  }

  return response.json();
}

/**
 * Create a new valuation case in the backend.
 */
export async function createCase(
  caseData: Partial<ValuationCase>,
  signal?: AbortSignal
): Promise<ValuationCase> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/cases`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(caseData),
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown server error');
    throw new Error(`Failed to create valuation case (${response.status}): ${errorText}`);
  }

  return response.json();
}

/**
 * Update case parameters in the backend.
 */
export async function updateCase(
  caseId: string,
  updates: Partial<ValuationCase>,
  signal?: AbortSignal
): Promise<ValuationCase> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/cases/${encodeURIComponent(caseId)}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(updates),
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown server error');
    throw new Error(`Failed to update valuation case ${caseId} (${response.status}): ${errorText}`);
  }

  return response.json();
}

/**
 * Transition case status and append an audit note.
 */
export async function updateCaseStatus(
  caseId: string,
  status: CaseStatus,
  auditNote?: string,
  signal?: AbortSignal
): Promise<ValuationCase> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/cases/${encodeURIComponent(caseId)}/status`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ status, auditNote }),
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown server error');
    throw new Error(`Failed to transition case status (${response.status}): ${errorText}`);
  }

  return response.json();
}

/**
 * Search comparable deeds from backend.
 */
export async function fetchComparables(
  params: { city?: string; caseId?: string; limit?: number } = {},
  signal?: AbortSignal
): Promise<ComparableDeed[]> {
  try {
    const queryParams = new URLSearchParams();
    if (params.city) queryParams.append('city', params.city);
    if (params.caseId) queryParams.append('case_id', params.caseId);
    if (params.limit) queryParams.append('limit', params.limit.toString());

    const url = `${API_BASE_URL}/api/v1/comparables${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    const response = await authenticatedFetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      signal,
    });

    if (!response.ok) return [];
    return response.json();
  } catch {
    return [];
  }
}

export interface MLModelStatus {
  isMlActive: boolean;
  activeModelVersion: string | null;
  engineType: string;
  trainingGateStatus: string;
  totalVerifiedRecordsAvailable: number;
  requiredRecordsThreshold: number;
  datasetReadinessSummary: string;
  governanceNotice: string;
}

export interface SHAPContribution {
  feature: string;
  featureValue: any;
  shapValue: number;
  impactDirection: string;
  impactDescription: string;
}

export interface MLPredictionResponse {
  engineType: string;
  modelVersion: string | null;
  estimatedPrice: number;
  estimatedPricePerSqFt: number;
  confidenceScore: number;
  isMlPrediction: boolean;
  fallbackReason: string | null;
  shapBaseValue: number | null;
  shapContributions: SHAPContribution[] | null;
  governanceDisclaimer: string;
}

export interface MLPredictionRequest {
  city: string;
  locality: string;
  propertyType: string;
  carpetAreaSqFt: number;
  superBuiltUpAreaSqFt?: number;
  floorNo?: number;
  totalFloors?: number;
  guidelineRatePerSqFt?: number;
  ageYears?: number;
  transactionQuarter?: string;
}

/**
 * Query real-time ML subsystem status and readiness gate state.
 */
export async function fetchMLStatus(signal?: AbortSignal): Promise<MLModelStatus | null> {
  return cachedFetch('ml_status', 15000, async () => {
    try {
      const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/ml/status`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        signal,
      });
      if (!response.ok) return null;
      return response.json();
    } catch {
      return null;
    }
  });
}

/**
 * Request valuation prediction from ML service (with transparent fallback).
 */
export async function requestMLPrediction(
  req: MLPredictionRequest,
  signal?: AbortSignal
): Promise<MLPredictionResponse | null> {
  try {
    const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/ml/predict`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(req),
      signal,
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

export interface UncertaintyStatus {
  isCalibrated: boolean;
  calibrationStatus: string;
  activeModelVersion: string | null;
  supportedCoverageLevels: number[];
  calibrationRecordsCount: number;
  blockingReasons: string[];
  governanceNotice: string;
  conceptualTaxonomy: Record<string, string>;
}

export interface UncertaintyPredictionRequest {
  city: string;
  locality: string;
  propertyType: string;
  carpetAreaSqFt: number;
  superBuiltUpAreaSqFt?: number;
  floorNo?: number;
  totalFloors?: number;
  guidelineRatePerSqFt?: number;
  ageYears?: number;
  transactionQuarter?: string;
  nominalCoverage?: number;
}

export interface UncertaintyPredictionResponse {
  status: string;
  isCalibrated: boolean;
  pointEstimate: number;
  pointEstimatePerSqFt: number;
  nominalCoverage: number;
  lowerBound: number | null;
  upperBound: number | null;
  intervalWidth: number | null;
  relativeIntervalWidthPct: number | null;
  empiricalCoverage: number | null;
  modelVersion: string | null;
  calibrationVersion: string | null;
  ruleConsistencyScore: number;
  dataCompletenessScore: number;
  evidenceCoverageTier: string;
  governanceDisclaimer: string;
  blockingReasons: string[] | null;
}

/**
 * Query real-time uncertainty calibration status and taxonomy.
 */
export async function fetchUncertaintyStatus(signal?: AbortSignal): Promise<UncertaintyStatus | null> {
  return cachedFetch('uncertainty_status', 15000, async () => {
    try {
      const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/ml/uncertainty/status`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        signal,
      });
      if (!response.ok) return null;
      return response.json();
    } catch {
      return null;
    }
  });
}

/**
 * Request valuation point estimate with conformal prediction intervals (or honest uncalibrated fallback).
 */
export async function requestUncertaintyPrediction(
  req: UncertaintyPredictionRequest,
  signal?: AbortSignal
): Promise<UncertaintyPredictionResponse | null> {
  try {
    const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/ml/uncertainty/predict`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(req),
      signal,
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// AI Underwriter Assistant & Gemini Integration Types (Phase 2G)
// ---------------------------------------------------------------------------

export interface AIStatus {
  configured: boolean;
  model: string;
  provider: 'gemini' | 'deterministic_fallback';
  cloud_processing_enabled: boolean;
  privacy_guard_active: boolean;
  rate_limit_per_minute: number;
  regulatory_framework: string;
  disclaimer: string;
}

export interface AIUnderwriterFactor {
  factor_name: string;
  impact: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL';
  details: string;
}

export interface AIUnderwriterReport {
  valuation_summary: string;
  major_valuation_factors: AIUnderwriterFactor[];
  comparable_evidence_analysis: string;
  location_considerations: string;
  data_quality_concerns: string[];
  legal_regulatory_risks: string[];
  valuation_limitations: string[];
  underwriter_recommendations: string[];
  recommendation_decision_role: string;
}

export interface AIExplainCaseResponse {
  case_id: string;
  provider: 'gemini' | 'deterministic_fallback';
  model_name: string;
  status: string;
  pii_redacted_count: number;
  report: AIUnderwriterReport;
  disclaimer: string;
  generated_at: string;
}

/**
 * Check AI Underwriter Assistant & Gemini service status.
 */
export async function fetchAIStatus(signal?: AbortSignal): Promise<AIStatus | null> {
  return cachedFetch('ai_status', 15000, async () => {
    try {
      const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/ai/status`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        signal,
      });
      if (!response.ok) return null;
      return response.json();
    } catch {
      return null;
    }
  });
}

/**
 * Request an evidence-grounded AI Underwriter Briefing for a specific valuation case.
 */
export async function fetchAIUnderwriterBriefing(
  caseId: string,
  signal?: AbortSignal
): Promise<AIExplainCaseResponse | null> {
  try {
    const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/ai/explain-case/${encodeURIComponent(caseId)}`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
      },
      signal,
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Tamper-Evident SHA-256 Audit Trail Types (Phase 2H)
// ---------------------------------------------------------------------------

export interface AuditEvent {
  id: number;
  event_id: string;
  sequence_number: number;
  event_type: string;
  actor_id: string;
  actor_role: string;
  case_id?: string | null;
  timestamp: string;
  payload: Record<string, any>;
  prev_hash: string;
  current_hash: string;
}

export interface AuditVerificationReport {
  is_valid: boolean;
  total_events: number;
  verified_events: number;
  genesis_hash: string;
  latest_hash: string;
  broken_index?: number | null;
  broken_event_id?: string | null;
  error_type?: string | null;
  details: string;
  security_boundary_notice: string;
  verified_at: string;
}

export interface AuditSummary {
  total_events: number;
  latest_sequence_number: number;
  latest_event_id?: string | null;
  latest_event_type?: string | null;
  latest_timestamp?: string | null;
  latest_hash: string;
  is_chain_intact: boolean;
  event_counts_by_type: Record<string, number>;
}

/**
 * Fetch paginated audit trail events.
 */
export async function fetchAuditEvents(
  params?: { case_id?: string; event_type?: string; limit?: number; offset?: number },
  signal?: AbortSignal
): Promise<{ items: AuditEvent[]; total: number } | null> {
  try {
    const query = new URLSearchParams();
    if (params?.case_id) query.append('case_id', params.case_id);
    if (params?.event_type) query.append('event_type', params.event_type);
    if (params?.limit) query.append('limit', String(params.limit));
    if (params?.offset) query.append('offset', String(params.offset));

    const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/audit/events?${query.toString()}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      signal,
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

/**
 * Execute cryptographic verification of the complete SHA-256 hash chain.
 */
export async function verifyAuditChain(signal?: AbortSignal): Promise<AuditVerificationReport | null> {
  try {
    const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/audit/verify`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
      },
      signal,
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

/**
 * Fetch high-level audit summary metrics.
 */
export async function fetchAuditSummary(signal?: AbortSignal): Promise<AuditSummary | null> {
  try {
    const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/audit/summary`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      signal,
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

// =========================================================================
// Institutional Data Quality & Governance Surveillance (Phase 4B-5)
// =========================================================================

export interface SourceDistributionItem {
  source_id: string;
  source_name: string;
  provider_name: string;
  authorization_status: string;
  total_records: number;
  verified_empirical_count: number;
  is_active: boolean;
}

export interface GeographicDistributionItem {
  state: string;
  city_count: number;
  record_count: number;
  percentage: number;
}

export interface CityDistributionItem {
  city: string;
  record_count: number;
  percentage: number;
  locality_count: number;
}

export interface MissingDataStatisticItem {
  field_name: string;
  missing_count: number;
  missing_percentage: number;
  impact_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface IngestionJobStatusItem {
  job_id: string;
  source_id: string;
  status: string;
  trigger_mode: string;
  records_fetched: number;
  records_normalized: number;
  records_rejected: number;
  records_duplicate: number;
  started_at: string;
  completed_at?: string | null;
}

export interface QuarantinedRecordReviewItem {
  id: string;
  dataset_id: string;
  row_index: number;
  quarantine_code: string;
  quarantine_reason: string;
  anomaly_score: number;
  anomalous_fields: string[];
  resolution_status: string;
  created_at: string;
}

export interface DataQualityMethodology {
  overall_score: number;
  completeness_score: number;
  validity_score: number;
  uniqueness_score: number;
  consistency_score: number;
  formula_description: string;
  weights: Record<string, number>;
}

export interface MLReadinessGateSummary {
  is_gated: boolean;
  empirical_records_count: number;
  empirical_records_threshold: number;
  calibration_holdout_count: number;
  calibration_holdout_threshold: number;
  status_label: string;
  gate_reason: string;
}

export interface InstitutionalGovernanceDashboard {
  total_ingested_transactions: number;
  successfully_normalized_records: number;
  validated_records: number;
  verified_empirical_deeds: number;
  synthetic_and_mock_records: number;
  duplicate_records: number;
  rejected_records: number;
  quarantined_records: number;
  records_awaiting_verification: number;
  verification_rate_pct?: number;
  total_localities_covered?: number;
  data_quality_score: number;
  quality_methodology: DataQualityMethodology;
  source_wise_distribution: SourceDistributionItem[];
  geographic_distribution: GeographicDistributionItem[];
  city_wise_distribution?: CityDistributionItem[];
  missing_data_statistics: MissingDataStatisticItem[];
  latest_ingestion_jobs: IngestionJobStatusItem[];
  data_freshness_timestamp?: string | null;
  latest_acquisition_date?: string | null;
  ml_readiness_gate: MLReadinessGateSummary;
  active_dataset_count: number;
  approved_dataset_count: number;
  dataset_version_history_count: number;
  user_role: string;
  can_approve_datasets: boolean;
  can_export_ml: boolean;
}

/**
 * Fetch aggregated institutional data quality & governance dashboard metrics.
 */
export async function fetchGovernanceMetrics(signal?: AbortSignal): Promise<InstitutionalGovernanceDashboard | null> {
  try {
    const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/governance/metrics`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      signal,
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

/**
 * Fetch isolated anomalous records held in quarantine for underwriter review.
 */
export async function fetchQuarantinedRecords(
  params?: { limit?: number; offset?: number },
  signal?: AbortSignal
): Promise<QuarantinedRecordReviewItem[] | null> {
  try {
    const query = new URLSearchParams();
    if (params?.limit) query.append('limit', String(params.limit));
    if (params?.offset) query.append('offset', String(params.offset));

    const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/governance/quarantine?${query.toString()}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      signal,
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

/**
 * Phase 7B: Institutional Pilot Dashboard metrics.
 */
export interface InstitutionalPilotDashboard {
  totalRegisteredInstitutions: number;
  institutionsApprovedForPilot: number;
  pendingOnboardingApprovals: number;
  activePilotUsers: number;
  totalValuationCasesProcessed: number;
  pendingHumanReviews: number;
  highAlertCases: number;
  valuationDivergenceStats: {
    meanDivergencePct: number;
    casesExceeding15Pct: number;
    maxDivergencePct: number;
  };
  auditChainVerificationStatus: {
    isValid: boolean;
    totalEvents: number;
    latestHash: string;
  };
  dataProvenanceStatus: {
    certifiedDeeds: number;
    verifiedDeeds: number;
    mlGateStatus: string;
    activeValuationEngine: string;
  };
}

export async function fetchPilotDashboard(signal?: AbortSignal): Promise<InstitutionalPilotDashboard | null> {
  try {
    const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/institutions/pilot-dashboard`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      signal,
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}











