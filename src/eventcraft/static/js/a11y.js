// @ts-check
/**
 * @fileoverview Accessibility utilities for announcements, live regions, and focus management.
 */

/**
 * Announce a status message to screen readers via polite or assertive live regions.
 * @param {string} message
 * @param {"polite" | "assertive"} [priority="polite"]
 */
export function announce(message, priority = "polite") {
  const regionId = priority === "assertive" ? "assertive-announcer" : "status-announcer";
  let announcer = document.getElementById(regionId);

  if (!announcer) {
    announcer = document.createElement("div");
    announcer.id = regionId;
    announcer.setAttribute("aria-live", priority);
    announcer.setAttribute("aria-atomic", "true");
    announcer.className = "sr-only";
    document.body.appendChild(announcer);
  }

  // Clear and update to ensure screen readers re-read duplicate announcements
  announcer.textContent = "";
  setTimeout(() => {
    if (announcer) {
      announcer.textContent = message;
    }
  }, 50);
}

/**
 * Set aria-busy attribute on main landmark and update loading indicator state.
 * @param {boolean} isBusy
 * @param {string} [busyMessage="Generating your event plan..."]
 */
export function setBusy(isBusy, busyMessage = "Loading...") {
  const main = document.getElementById("main-content");
  if (main) {
    main.setAttribute("aria-busy", isBusy ? "true" : "false");
  }

  const indicator = document.getElementById("loading-indicator");
  if (indicator) {
    indicator.hidden = !isBusy;
    if (isBusy) {
      const msgSpan = indicator.querySelector(".loading-text");
      if (msgSpan) msgSpan.textContent = busyMessage;
      announce(busyMessage, "polite");
    }
  }
}

/**
 * Focus an element reliably, setting tabindex=-1 temporarily if not naturally focusable.
 * @param {HTMLElement | null | undefined} element
 */
export function focusElement(element) {
  if (!element) return;
  const isFocusable = ["A", "BUTTON", "INPUT", "SELECT", "TEXTAREA"].includes(element.tagName)
    || element.hasAttribute("tabindex");

  if (!isFocusable) {
    element.setAttribute("tabindex", "-1");
  }

  element.focus();
  element.scrollIntoView({ behavior: "smooth", block: "start" });
}
