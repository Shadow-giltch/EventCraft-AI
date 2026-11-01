// @ts-check
/**
 * @fileoverview Form extraction, validation, error summary presentation, and sample brief loading.
 */

import { focusElement } from "./a11y.js";

/**
 * Extract structured brief object from form inputs.
 * @param {HTMLFormElement} form
 * @returns {object}
 */
export function getBriefFormData(form) {
  const fd = new FormData(form);
  const eventType = String(fd.get("event_type") || "wedding");
  const eventDate = String(fd.get("event_date") || "");
  const guestCount = parseInt(String(fd.get("guest_count") || "100"), 10);
  const budgetTotal = String(fd.get("budget_total") || "10000.00").trim();
  const currency = String(fd.get("currency") || "INR");
  const culture = String(fd.get("culture_or_tradition") || "").trim();
  const style = String(fd.get("style") || "").trim();
  const steer = String(fd.get("steer") || "").trim();

  /**
   * Split comma-separated string into cleaned list.
   * @param {string} raw
   * @returns {string[]}
   */
  const splitList = (raw) =>
    raw
      ? raw
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
      : [];

  const priorities = splitList(String(fd.get("priorities") || ""));
  const dietary = splitList(String(fd.get("dietary_needs") || ""));
  const accessibility = splitList(String(fd.get("accessibility_needs") || ""));
  const interests = splitList(String(fd.get("interests") || ""));

  return {
    event_type: eventType,
    event_date: eventDate,
    guest_count: guestCount,
    budget_total: budgetTotal,
    currency,
    culture_or_tradition: culture,
    style,
    priorities,
    dietary_needs: dietary,
    accessibility_needs: accessibility,
    interests,
    steer: steer || null,
  };
}

/**
 * Populate form inputs from a structured brief object.
 * @param {HTMLFormElement} form
 * @param {any} brief
 */
export function populateBriefForm(form, brief) {
  if (!form || !brief) return;
  const setVal = (/** @type {string} */ name, /** @type {any} */ val) => {
    const el = /** @type {HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement | null} */ (
      form.elements.namedItem(name)
    );
    if (el) el.value = val != null ? String(val) : "";
  };

  setVal("event_type", brief.event_type);
  setVal("event_date", brief.event_date);
  setVal("guest_count", brief.guest_count);
  setVal("budget_total", brief.budget_total);
  setVal("currency", brief.currency || "INR");
  setVal("culture_or_tradition", brief.culture_or_tradition || "");
  setVal("style", brief.style || "");
  setVal("steer", brief.steer || "");

  const joinList = (/** @type {any} */ val) => (Array.isArray(val) ? val.join(", ") : "");
  setVal("priorities", joinList(brief.priorities));
  setVal("dietary_needs", joinList(brief.dietary_needs));
  setVal("accessibility_needs", joinList(brief.accessibility_needs));
  setVal("interests", joinList(brief.interests));
}

/**
 * Validate event brief inputs on the client before submission.
 * @param {any} brief
 * @returns {Array<{ field: string, message: string }>}
 */
export function validateBrief(brief) {
  /** @type {Array<{ field: string, message: string }>} */
  const errors = [];

  if (!brief.event_date) {
    errors.push({ field: "event_date", message: "Event date is required." });
  } else {
    const parsed = new Date(brief.event_date);
    if (Number.isNaN(parsed.getTime())) {
      errors.push({ field: "event_date", message: "Valid date format (YYYY-MM-DD) is required." });
    }
  }

  if (Number.isNaN(brief.guest_count) || brief.guest_count < 1 || brief.guest_count > 10000) {
    errors.push({ field: "guest_count", message: "Guest count must be between 1 and 10,000." });
  }

  const budgetNum = parseFloat(brief.budget_total);
  if (Number.isNaN(budgetNum) || budgetNum <= 0) {
    errors.push({ field: "budget_total", message: "Total budget must be a positive number." });
  }

  return errors;
}

/**
 * Display errors in the accessible error summary box.
 * @param {HTMLElement} errorSummaryEl
 * @param {Array<{ field: string, message: string }>} errors
 */
export function showFormErrors(errorSummaryEl, errors) {
  errorSummaryEl.hidden = false;
  const listEl = errorSummaryEl.querySelector("ul");
  if (!listEl) return;
  listEl.textContent = "";

  for (const err of errors) {
    const li = document.createElement("li");
    const link = document.createElement("a");
    link.href = `#${err.field}`;
    link.textContent = err.message;
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const target = document.getElementById(err.field);
      if (target) focusElement(target);
    });
    li.appendChild(link);
    listEl.appendChild(li);

    const input = document.getElementById(err.field);
    if (input) {
      input.setAttribute("aria-invalid", "true");
    }
  }

  focusElement(errorSummaryEl);
}

/**
 * Clear the error summary box and remove invalid markings.
 * @param {HTMLElement} errorSummaryEl
 */
export function clearFormErrors(errorSummaryEl) {
  errorSummaryEl.hidden = true;
  const listEl = errorSummaryEl.querySelector("ul");
  if (listEl) listEl.textContent = "";

  const invalids = document.querySelectorAll('[aria-invalid="true"]');
  for (const el of invalids) {
    el.removeAttribute("aria-invalid");
  }
}
