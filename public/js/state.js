// @ts-check
/**
 * @fileoverview Application state management and safe localStorage adapter.
 */

/**
 * Valid vendor checklist progress statuses.
 * @type {readonly ["to do", "contacted", "quote received", "booked", "confirmed"]}
 */
export const ALLOWED_STATUSES = [
  "to do",
  "contacted",
  "quote received",
  "booked",
  "confirmed",
];

/**
 * Validate whether a string is an allowed vendor status.
 * @param {unknown} status
 * @returns {status is typeof ALLOWED_STATUSES[number]}
 */
export function isValidStatus(status) {
  return typeof status === "string" && ALLOWED_STATUSES.includes(
    /** @type {typeof ALLOWED_STATUSES[number]} */ (status)
  );
}

/**
 * Safely load vendor statuses for a specific plan key from storage.
 * @param {Storage | null | undefined} storage
 * @param {string} planKey
 * @returns {Record<string, string>}
 */
export function loadVendorStatuses(storage, planKey) {
  if (!storage || !planKey) return {};
  try {
    const raw = storage.getItem(`eventcraft_vendors_${planKey}`);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};

    /** @type {Record<string, string>} */
    const cleaned = {};
    for (const [id, status] of Object.entries(parsed)) {
      if (typeof id === "string" && isValidStatus(status)) {
        cleaned[id] = status;
      }
    }
    return cleaned;
  } catch {
    return {};
  }
}

/**
 * Safely persist a single vendor item's status to storage.
 * @param {Storage | null | undefined} storage
 * @param {string} planKey
 * @param {string} itemId
 * @param {string} status
 * @returns {boolean}
 */
export function saveVendorStatus(storage, planKey, itemId, status) {
  if (!storage || !planKey || !itemId || !isValidStatus(status)) return false;
  try {
    const current = loadVendorStatuses(storage, planKey);
    current[itemId] = status;
    storage.setItem(`eventcraft_vendors_${planKey}`, JSON.stringify(current));
    return true;
  } catch {
    return false;
  }
}

/**
 * Recalculate progress counts and percentage for checklist items.
 * @param {Array<{ id: string, status: string }>} items
 * @param {Record<string, string>} overrides
 * @returns {{ total: number, completed: number, inProgress: number, pending: number, percent: number }}
 */
export function calculateProgress(items, overrides = {}) {
  const total = items.length;
  if (total === 0) {
    return { total: 0, completed: 0, inProgress: 0, pending: 0, percent: 0 };
  }

  let completed = 0;
  let inProgress = 0;
  let pending = 0;

  for (const item of items) {
    const status = overrides[item.id] || item.status || "to do";
    if (status === "booked" || status === "confirmed") {
      completed += 1;
    } else if (status === "contacted" || status === "quote received") {
      inProgress += 1;
    } else {
      pending += 1;
    }
  }

  const percent = Math.round((completed / total) * 100);
  return { total, completed, inProgress, pending, percent };
}

/**
 * Create initial clean application state.
 * @returns {{ currentPlan: any, currentBrief: any, chatHistory: Array<[string, string]>, vendorStatuses: Record<string, string> }}
 */
export function createInitialState() {
  return {
    currentPlan: null,
    currentBrief: null,
    chatHistory: [],
    vendorStatuses: {},
  };
}
