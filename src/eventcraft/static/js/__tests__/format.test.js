import test from "node:test";
import assert from "node:assert/strict";
import { formatCurrency, formatDate, formatPercent, formatLeadDays } from "../format.js";

test("formatCurrency handles INR, USD, EUR, GBP and edge values", () => {
  const inr = formatCurrency("1800000.00", "INR");
  assert.match(inr, /₹|INR/);
  assert.ok(inr.includes("18,00,000") || inr.includes("1,800,000"));

  const usd = formatCurrency(2500, "USD");
  assert.match(usd, /\$|USD/);
  assert.ok(usd.includes("2,500.00"));

  const eur = formatCurrency(7500.5, "EUR");
  assert.match(eur, /€|EUR/);

  const fallback = formatCurrency("invalid", "INR");
  assert.equal(fallback, "0.00");
});

test("formatDate parses valid ISO strings and gracefully falls back", () => {
  const formatted = formatDate("2027-04-18");
  assert.match(formatted, /Apr(il)?\s+18,\s+2027/);

  assert.equal(formatDate(""), "");
  assert.equal(formatDate("invalid-date-string"), "invalid-date-string");
});

test("formatPercent converts decimal weights to single-decimal display", () => {
  assert.equal(formatPercent(12.34), "12.3%");
  assert.equal(formatPercent("5.0"), "5.0%");
  assert.equal(formatPercent("invalid"), "0.0%");
});

test("formatLeadDays formats human readable lead timelines", () => {
  assert.equal(formatLeadDays(-5), "Past due");
  assert.equal(formatLeadDays(0), "Today");
  assert.equal(formatLeadDays(1), "1 day");
  assert.equal(formatLeadDays(20), "20 days");
  assert.equal(formatLeadDays(60), "2 mo");
  assert.ok(formatLeadDays(65).includes("2 mo 5 d"));
});
