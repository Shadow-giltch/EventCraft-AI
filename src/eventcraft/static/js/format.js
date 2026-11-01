// @ts-check
/**
 * @fileoverview Pure formatting functions for numbers, currency, dates, and percentages.
 */

/**
 * Currency locale map for accurate regional formatting.
 * @type {Record<string, string>}
 */
const CURRENCY_LOCALES = {
  INR: "en-IN",
  USD: "en-US",
  EUR: "de-DE",
  GBP: "en-GB",
};

/**
 * Format a numeric amount or string into localized currency display.
 * @param {number | string} amount
 * @param {string} [currency="INR"]
 * @returns {string}
 */
export function formatCurrency(amount, currency = "INR") {
  const numericVal = typeof amount === "string" ? parseFloat(amount) : amount;
  if (Number.isNaN(numericVal)) {
    return "0.00";
  }
  const curr = (currency || "INR").toUpperCase();
  const locale = CURRENCY_LOCALES[curr] || "en-US";
  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency: curr,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(numericVal);
  } catch {
    return `${curr} ${numericVal.toFixed(2)}`;
  }
}

/**
 * Format ISO date string (YYYY-MM-DD) into readable localized format.
 * @param {string} isoDate
 * @returns {string}
 */
export function formatDate(isoDate) {
  if (!isoDate || typeof isoDate !== "string") {
    return "";
  }
  const parts = isoDate.split("-");
  if (parts.length !== 3) {
    return isoDate;
  }
  const year = parseInt(parts[0], 10);
  const month = parseInt(parts[1], 10) - 1;
  const day = parseInt(parts[2], 10);
  const dateObj = new Date(year, month, day);
  if (Number.isNaN(dateObj.getTime())) {
    return isoDate;
  }
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(dateObj);
}

/**
 * Format decimal percentage into display string.
 * @param {number | string} percent
 * @returns {string}
 */
export function formatPercent(percent) {
  const val = typeof percent === "string" ? parseFloat(percent) : percent;
  if (Number.isNaN(val)) {
    return "0.0%";
  }
  return `${val.toFixed(1)}%`;
}

/**
 * Format lead time in days into human readable representation.
 * @param {number} days
 * @returns {string}
 */
export function formatLeadDays(days) {
  if (days < 0) return "Past due";
  if (days === 0) return "Today";
  if (days === 1) return "1 day";
  if (days < 30) return `${days} days`;
  const months = Math.floor(days / 30);
  const remDays = days % 30;
  if (remDays === 0) return `${months} mo`;
  return `${months} mo ${remDays} d (${days} d)`;
}
