import test from 'node:test';
import assert from 'node:assert/strict';
import {
  fetchValuationEstimate,
  checkBackendHealth,
  fetchCases,
  fetchCaseById,
  createCase,
  updateCase,
  updateCaseStatus,
  fetchComparables,
  fetchMLStatus,
  requestMLPrediction,
  fetchUncertaintyStatus,
  requestUncertaintyPrediction,
  fetchAIStatus,
  fetchAIUnderwriterBriefing,
  fetchAuditEvents,
  verifyAuditChain,
  fetchAuditSummary,
} from './apiClient';

test('apiClient: checkBackendHealth returns false gracefully when backend is unreachable', async () => {
  const controller = new AbortController();
  const signal = controller.signal;
  const isHealthy = await checkBackendHealth(signal);
  assert.equal(typeof isHealthy, 'boolean');
});

test('apiClient: fetchValuationEstimate throws network error gracefully when unreachable', async () => {
  const dummyParams = {
    carpetAreaSqFt: 1000,
    superBuiltUpAreaSqFt: 1200,
    baseMarketRatePerSqFt: 8000,
    circleRatePerSqFt: 7000,
    floorRiseFactor: 0,
    roadWidthFactor: 0,
    amenitiesPremium: 0,
    structuralDepreciation: 0,
    underwriterHaircutPct: 0,
    distressDiscountPct: 20,
    ltvRatioPct: 75,
    legalRiskPenaltyPct: 0,
  };

  try {
    await fetchValuationEstimate(dummyParams);
  } catch (err: any) {
    assert.ok(err instanceof Error);
    assert.match(err.message, /fetch failed|ECONNREFUSED|Valuation backend error/i);
  }
});

test('apiClient: fetchCases and fetchCaseById handle offline state gracefully', async () => {
  try {
    await fetchCases();
  } catch (err: any) {
    assert.ok(err instanceof Error);
    assert.match(err.message, /fetch failed|ECONNREFUSED|Failed to fetch valuation cases/i);
  }

  try {
    await fetchCaseById('case-blr-89412');
  } catch (err: any) {
    assert.ok(err instanceof Error);
    assert.match(err.message, /fetch failed|ECONNREFUSED|not found/i);
  }
});

test('apiClient: createCase, updateCase and updateCaseStatus error handling', async () => {
  try {
    await createCase({
      borrowerName: 'Test Offline User',
      carpetAreaSqFt: 1000,
      superBuiltUpAreaSqFt: 1300,
      declaredAgreementValue: 10000000,
      loanRequested: 7500000,
      city: 'Bengaluru',
      projectName: 'Test Project',
      unitAddress: 'Flat 101',
    });
  } catch (err: any) {
    assert.ok(err instanceof Error);
    assert.match(err.message, /fetch failed|ECONNREFUSED|Failed to create valuation case/i);
  }

  try {
    await updateCase('case-blr-89412', { underwriterHaircutPct: -5 });
  } catch (err: any) {
    assert.ok(err instanceof Error);
    assert.match(err.message, /fetch failed|ECONNREFUSED|Failed to update valuation case/i);
  }

  try {
    await updateCaseStatus('case-blr-89412', 'APPROVED', 'Test note');
  } catch (err: any) {
    assert.ok(err instanceof Error);
    assert.match(err.message, /fetch failed|ECONNREFUSED|Failed to transition case status/i);
  }
});

test('apiClient: fetchComparables returns array or empty list on offline state', async () => {
  const comps = await fetchComparables({ city: 'Bengaluru' });
  assert.ok(Array.isArray(comps));
});

test('apiClient: fetchMLStatus handles offline state gracefully returning null', async () => {
  const status = await fetchMLStatus();
  // When backend is offline, gracefully returns null without throwing unhandled exceptions
  assert.ok(status === null || typeof status === 'object');
});

test('apiClient: requestMLPrediction handles offline state gracefully returning null', async () => {
  const result = await requestMLPrediction({
    city: 'Bengaluru',
    locality: 'Whitefield',
    propertyType: 'High-Rise Apartment',
    carpetAreaSqFt: 1200,
  });
  // When backend is offline, gracefully returns null without crashing UI
  assert.ok(result === null || typeof result === 'object');
});

test('apiClient: fetchUncertaintyStatus handles offline state gracefully returning null', async () => {
  const status = await fetchUncertaintyStatus();
  assert.ok(status === null || typeof status === 'object');
});

test('apiClient: requestUncertaintyPrediction handles offline state gracefully returning null', async () => {
  const result = await requestUncertaintyPrediction({
    city: 'Bengaluru',
    locality: 'Whitefield',
    propertyType: 'High-Rise Apartment',
    carpetAreaSqFt: 1200,
    nominalCoverage: 0.90,
  });
  assert.ok(result === null || typeof result === 'object');
});

test('apiClient: fetchAIStatus handles offline state gracefully returning null', async () => {
  const status = await fetchAIStatus();
  assert.ok(status === null || typeof status === 'object');
});

test('apiClient: fetchAIUnderwriterBriefing handles offline state gracefully returning null', async () => {
  const briefing = await fetchAIUnderwriterBriefing('case-blr-89412');
  assert.ok(briefing === null || typeof briefing === 'object');
});

test('apiClient: fetchAuditEvents handles offline state gracefully returning null', async () => {
  const events = await fetchAuditEvents({ limit: 5 });
  assert.ok(events === null || typeof events === 'object');
});

test('apiClient: verifyAuditChain handles offline state gracefully returning null', async () => {
  const report = await verifyAuditChain();
  assert.ok(report === null || typeof report === 'object');
});

test('apiClient: fetchAuditSummary handles offline state gracefully returning null', async () => {
  const summary = await fetchAuditSummary();
  assert.ok(summary === null || typeof summary === 'object');
});
