import test from "node:test";
import assert from "node:assert/strict";
import {
  ALLOWED_STATUSES,
  isValidStatus,
  loadVendorStatuses,
  saveVendorStatus,
  calculateProgress,
  createInitialState,
} from "../state.js";

/**
 * Mock localStorage implementation for tests.
 */
class MockStorage {
  constructor() {
    /** @type {Record<string, string>} */
    this.store = {};
  }
  getItem(key) {
    return this.store[key] || null;
  }
  setItem(key, value) {
    this.store[key] = String(value);
  }
  removeItem(key) {
    delete this.store[key];
  }
  clear() {
    this.store = {};
  }
}

test("isValidStatus correctly validates allowed vendor workflow stages", () => {
  for (const status of ALLOWED_STATUSES) {
    assert.equal(isValidStatus(status), true);
  }
  assert.equal(isValidStatus("unknown_status"), false);
  assert.equal(isValidStatus(123), false);
  assert.equal(isValidStatus(null), false);
});

test("loadVendorStatuses and saveVendorStatus interact safely with storage", () => {
  const storage = new MockStorage();
  const planKey = "wedding_2027-04-18_1800000";

  assert.deepEqual(loadVendorStatuses(storage, planKey), {});

  const saved = saveVendorStatus(storage, planKey, "venue_1", "booked");
  assert.equal(saved, true);

  const reloaded = loadVendorStatuses(storage, planKey);
  assert.deepEqual(reloaded, { venue_1: "booked" });

  // Invalid status rejection
  assert.equal(saveVendorStatus(storage, planKey, "venue_1", "invalid_stage"), false);

  // Corrupt data handling
  storage.setItem(`eventcraft_vendors_${planKey}`, "not-valid-json");
  assert.deepEqual(loadVendorStatuses(storage, planKey), {});
});

test("calculateProgress tallies item status counts and percentages", () => {
  const items = [
    { id: "v1", status: "to do" },
    { id: "v2", status: "contacted" },
    { id: "v3", status: "booked" },
    { id: "v4", status: "confirmed" },
  ];

  const p1 = calculateProgress(items);
  assert.equal(p1.total, 4);
  assert.equal(p1.completed, 2);
  assert.equal(p1.inProgress, 1);
  assert.equal(p1.pending, 1);
  assert.equal(p1.percent, 50);

  // With override
  const p2 = calculateProgress(items, { v1: "booked" });
  assert.equal(p2.completed, 3);
  assert.equal(p2.percent, 75);

  // Empty items
  assert.deepEqual(calculateProgress([]), {
    total: 0,
    completed: 0,
    inProgress: 0,
    pending: 0,
    percent: 0,
  });
});

test("createInitialState returns pristine state model", () => {
  const state = createInitialState();
  assert.equal(state.currentPlan, null);
  assert.equal(state.currentBrief, null);
  assert.deepEqual(state.chatHistory, []);
  assert.deepEqual(state.vendorStatuses, {});
});
