import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatIndianCurrency,
  formatIndianNumber,
  calculateValuation,
} from './valuationEngine';

test('formatIndianNumber groups digits using Indian numeral system', () => {
  assert.equal(formatIndianNumber(14250000), '1,42,50,000');
  assert.equal(formatIndianNumber(850000), '8,50,000');
  assert.equal(formatIndianNumber(12500), '12,500');
  assert.equal(formatIndianNumber(450), '450');
});

test('formatIndianCurrency formats full and short (Lakh / Crore) modes', () => {
  assert.equal(formatIndianCurrency(14250000, 'full'), '₹1,42,50,000');
  assert.equal(formatIndianCurrency(14250000, 'short'), '₹1.43 Cr');
  assert.equal(formatIndianCurrency(8850000, 'short'), '₹88.50 L');
  assert.equal(formatIndianCurrency(75000, 'short'), '₹75,000');
});

test('calculateValuation computes correct gross, haircut, liquidation and sanction values', () => {
  const result = calculateValuation({
    carpetAreaSqFt: 1250,
    superBuiltUpAreaSqFt: 1650,
    baseMarketRatePerSqFt: 9800,
    circleRatePerSqFt: 7800,
    floorRiseFactor: 350,
    roadWidthFactor: 250,
    amenitiesPremium: 400,
    structuralDepreciation: 150,
    underwriterHaircutPct: -5,
    distressDiscountPct: 20,
    ltvRatioPct: 75,
    legalRiskPenaltyPct: 0,
  });

  // net adjustment = 350 + 250 + 400 - 150 = 850
  // ai adjusted rate = 9800 + 850 = 10650
  assert.equal(result.aiAdjustedRatePerSqFt, 10650);

  // gross market value = 10650 * 1250 = 1,33,12,500
  assert.equal(result.grossMarketValue, 13312500);

  // haircut -5% => 13312500 * 0.95 = 12646875
  assert.equal(result.netAssessedValue, 12646875);

  // distress 20% discount => 12646875 * 0.8 = 10117500
  assert.equal(result.distressLiquidationValue, 10117500);

  // max loan sanction at 75% LTV => 12646875 * 0.75 = 9485156
  assert.equal(result.maxSanctionAmount, 9485156);

  // deviation from circle rate: ((10650 - 7800) / 7800) * 100 = 36.5%
  assert.ok(result.deviationFromCircleRatePct > 36 && result.deviationFromCircleRatePct < 37);

  // Attribution breakdown has expected 5 factors
  assert.equal(result.attributionBreakdown.length, 5);
});

test('calculateValuation handles edge cases: zero area and zero circle rate safely', () => {
  const result = calculateValuation({
    carpetAreaSqFt: 0,
    superBuiltUpAreaSqFt: 0,
    baseMarketRatePerSqFt: 10000,
    circleRatePerSqFt: 0,
    floorRiseFactor: 0,
    roadWidthFactor: 0,
    amenitiesPremium: 0,
    structuralDepreciation: 0,
    underwriterHaircutPct: 0,
    distressDiscountPct: 20,
    ltvRatioPct: 75,
    legalRiskPenaltyPct: 0,
  });

  assert.equal(result.grossMarketValue, 0);
  assert.equal(result.netAssessedValue, 0);
  assert.equal(result.distressLiquidationValue, 0);
  assert.equal(result.maxSanctionAmount, 0);
  assert.equal(result.deviationFromCircleRatePct, 0);
  assert.equal(result.confidenceScorePct, 95.5);
  assert.equal(result.riskTier, 'LOW_RISK');
});

test('calculateValuation applies confidence penalties and assigns HIGH_ALERT risk tier', () => {
  const result = calculateValuation({
    carpetAreaSqFt: 1000,
    superBuiltUpAreaSqFt: 1300,
    baseMarketRatePerSqFt: 12000,
    circleRatePerSqFt: 6000, // +100% deviation triggers circle rate penalty
    floorRiseFactor: 0,
    roadWidthFactor: 0,
    amenitiesPremium: 0,
    structuralDepreciation: 0,
    underwriterHaircutPct: 0,
    distressDiscountPct: 20,
    ltvRatioPct: 75,
    legalRiskPenaltyPct: 10, // legal penalty triggers -8.5 confidence deduction and HIGH_ALERT
  });

  // Deviation = 100% (>35% => -10 confidence)
  // Legal penalty = 10% (>0 => -8.5 confidence)
  // Base 95.5 - 10 - 8.5 = 77.0
  assert.equal(result.confidenceScorePct, 77.0);
  assert.equal(result.riskTier, 'HIGH_ALERT');
});
