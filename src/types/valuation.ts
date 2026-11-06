/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export type RiskTier = 'LOW_RISK' | 'MODERATE_RISK' | 'HIGH_ALERT';
export type CaseStatus = 'READY_FOR_APPROVAL' | 'REVIEW_REQUIRED' | 'HIGH_ALERT' | 'APPROVED' | 'REJECTED';
export type PropertyType = 'High-Rise Apartment' | 'Gated Villa' | 'Independent Floor' | 'Commercial SCO';
export type DataSourceType = 'synthetic-demo' | 'verified-registry' | 'pending-verification';

export const CREDIBILITY_LABELS = {
  ENGINE_TYPE: 'provisional rule-based estimation',
  ENGINE_BADGE: 'Provisional Rule-Based Estimation',
  ENGINE_TITLE: 'Provisional Rule-Based Valuation Engine',
  DATA_SOURCE_SYNTHETIC: 'Synthetic demonstration data',
  COMPARABLE_SYNTHETIC: 'Synthetic sample comparable, not verified transaction evidence',
  UNCERTAINTY_NOTE: 'Rule-based indicative range, not a statistical interval',
  CALIBRATION_STATUS: 'Not available: no calibrated model',
  CONSISTENCY_SCORE: 'Rule Consistency Score (Heuristic, Uncalibrated)',
  GOVERNANCE_UNVERIFIED: 'Pending verification',
  GOVERNANCE_NOT_AVAILABLE: 'Not available',
  LEDGER_STATUS: 'Not implemented (Local prototype state)',
  AI_STATUS: 'Not connected (Demo prototype)',
} as const;

export interface ComparableDeed {
  id: string;
  dataSource?: DataSourceType;
  sroRegNo: string;
  regDate: string;
  propertyName: string;
  unitNo: string;
  carpetAreaSqFt: number;
  superBuiltUpAreaSqFt: number;
  registeredPrice: number;
  ratePerSqFt: number;
  distanceMeters: number;
  similarityScorePct: number;
  weightInEstimate: number;
  floor: number;
  coordinates: { x: number; y: number }; // Relative coordinates for GIS map
}

export interface DocumentVerificationField {
  label: string;
  applicantDeclared: string;
  sroIndexExtract: string;
  matchStatus: 'MATCHED' | 'DISCREPANCY' | 'PENDING';
  notes?: string;
}

export interface FieldInspectionPhoto {
  id: string;
  title: string;
  category: 'Exterior' | 'Interior' | 'Surroundings' | 'Structural';
  latLong: string;
  capturedAt: string;
  surveyor: string;
  surveyorId: string;
  status: 'VERIFIED' | 'CAUTION_NOTED';
  description: string;
  imageUrl: string;
}

export interface ValuationCase {
  id: string;
  dataSource?: DataSourceType;
  applicationNo: string;
  borrowerName: string;
  coBorrowerName?: string;
  cibilScore: number;
  loanRequested: number;
  declaredAgreementValue: number;
  propertyType: PropertyType;
  unitAddress: string;
  projectName: string;
  locality: string;
  city: 'Bengaluru' | 'Mumbai' | 'Delhi-NCR' | 'Hyderabad' | 'Pune' | 'Chennai';
  pincode: string;
  branch: string;
  carpetAreaSqFt: number;
  superBuiltUpAreaSqFt: number;
  floorNo: number;
  totalFloors: number;
  ageYears: number;
  roadWidthFt: number;
  circleRatePerSqFt: number;
  baseMarketRatePerSqFt: number;
  floorRiseFactor: number;
  roadWidthFactor: number;
  amenitiesPremium: number;
  structuralDepreciation: number;
  status: CaseStatus;
  statusLabel: string;
  underwriterHaircutPct: number;
  distressDiscountPct: number;
  ltvRatioPct: number;
  legalRiskPenaltyPct: number;
  assignedUnderwriter: string;
  createdAt: string;
  lastUpdated: string;
  reraRegistration: string;
  bbmpPlanApprovalNo: string;
  titleChainYears: number;
  encumbranceStatus: 'NIL_ENCUMBRANCE' | 'ACTIVE_CHARGE' | 'MORTGAGE_NOTED';
  comparables: ComparableDeed[];
  documentFields: DocumentVerificationField[];
  surveyPhotos: FieldInspectionPhoto[];
  auditNotes: string[];
}
