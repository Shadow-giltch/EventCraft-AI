// @ts-check
/**
 * @fileoverview Main orchestrator wiring user interactions, state, and rendering.
 */
import { announce, focusElement, setBusy } from "./a11y.js";
import { askAssistant, fetchPlan, fetchSampleBrief, rebalanceBudget, regenerateIdeas } from "./api.js";
import { clearFormErrors, getBriefFormData, populateBriefForm, showFormErrors, validateBrief } from "./form.js";
import { renderAssistantLog, renderBudget, renderIdeas, renderTimeline, renderVendors } from "./render.js";
import { addChatMessage, createInitialState, loadVendorStatuses, saveVendorStatus } from "./state.js";

const state = createInitialState();

function updateDeliverables(plan, brief) {
  state.currentPlan = plan;
  state.currentBrief = brief;
  const planKey = `${brief.event_type}_${brief.event_date}_${brief.budget_total}`;
  state.vendorStatuses = loadVendorStatuses(window.localStorage, planKey);

  const sec = document.getElementById("deliverables-container");
  if (sec) sec.hidden = false;

  const bRoot = document.getElementById("budget-content");
  if (bRoot) renderBudget(bRoot, plan.budget);

  const tRoot = document.getElementById("timeline-content");
  if (tRoot) renderTimeline(tRoot, plan.timeline);

  const vRoot = document.getElementById("vendors-content");
  const checklist = plan.vendor_checklist || plan.vendors;
  if (vRoot && checklist) {
    renderVendors(vRoot, checklist, state.vendorStatuses, (id, newSt) => {
      saveVendorStatus(window.localStorage, planKey, id, newSt);
      state.vendorStatuses[id] = newSt;
      announce(`Updated vendor status to ${newSt}`, "polite");
    });
  }

  const iRoot = document.getElementById("ideas-content");
  const ideasData = plan.personalized_ideas || plan.ideas;
  if (iRoot && ideasData) renderIdeas(iRoot, ideasData);

  const nav = document.getElementById("deliverables-nav");
  if (nav) nav.hidden = false;
}

document.addEventListener("DOMContentLoaded", () => {
  const briefForm = /** @type {HTMLFormElement | null} */ (document.getElementById("brief-form"));
  const errorSummary = document.getElementById("form-error-summary");

  // Sample Brief loaders
  for (const type of ["wedding", "birthday", "community"]) {
    document.getElementById(`sample-btn-${type}`)?.addEventListener("click", async () => {
      try {
        setBusy(true, `Loading sample ${type}...`);
        const sample = await fetchSampleBrief(/** @type {any} */ (type));
        if (briefForm) populateBriefForm(briefForm, sample);
        announce(`Loaded sample ${type} brief into form.`, "polite");
      } catch (err) {
        announce(`Error loading sample: ${/** @type {Error} */ (err).message}`, "assertive");
      } finally {
        setBusy(false);
      }
    });
  }

  // Plan generation
  briefForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!errorSummary) return;
    clearFormErrors(errorSummary);
    const brief = getBriefFormData(briefForm);
    const errors = validateBrief(brief);
    if (errors.length) {
      showFormErrors(errorSummary, errors);
      announce("Please correct the errors in the event brief form.", "assertive");
      return;
    }
    try {
      setBusy(true, "Crafting your multi-deliverable event plan with Gemini...");
      const plan = await fetchPlan(brief);
      updateDeliverables(plan, brief);
      announce("Event plan successfully generated across all four deliverables.", "polite");
      const firstSection = document.getElementById("budget-section");
      if (firstSection) focusElement(firstSection);
    } catch (err) {
      showFormErrors(errorSummary, [{ field: "budget_total", message: /** @type {Error} */ (err).message }]);
      announce(`Generation error: ${/** @type {Error} */ (err).message}`, "assertive");
    } finally {
      setBusy(false);
    }
  });

  // Budget rebalance
  const rebalForm = /** @type {HTMLFormElement | null} */ (document.getElementById("rebalance-form"));
  rebalForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!state.currentBrief) return;
    const fd = new FormData(rebalForm);
    const total = String(fd.get("rebalance_total") || state.currentBrief.budget_total);
    const guests = parseInt(String(fd.get("rebalance_guests") || state.currentBrief.guest_count), 10);
    const cont = parseFloat(String(fd.get("rebalance_contingency") || "5.0"));
    try {
      setBusy(true, "Recalculating budget allocation...");
      const updated = await rebalanceBudget({
        event_type: state.currentBrief.event_type,
        budget_total: total,
        currency: state.currentBrief.currency,
        guest_count: guests,
        priorities: state.currentBrief.priorities,
        contingency_percent: cont,
      });
      state.currentPlan.budget = updated;
      const bRoot = document.getElementById("budget-content");
      if (bRoot) renderBudget(bRoot, updated);
      announce("Budget rebalanced successfully.", "polite");
    } catch (err) {
      announce(`Rebalance error: ${/** @type {Error} */ (err).message}`, "assertive");
    } finally {
      setBusy(false);
    }
  });

  // Ideas regeneration
  const steerForm = /** @type {HTMLFormElement | null} */ (document.getElementById("steer-form"));
  steerForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!state.currentBrief) return;
    const steerVal = String(new FormData(steerForm).get("steer_input") || "").trim();
    try {
      setBusy(true, "Regenerating personalized ideas with your steer...");
      const updatedIdeas = await regenerateIdeas(state.currentBrief, steerVal || null);
      state.currentPlan.personalized_ideas = updatedIdeas;
      const iRoot = document.getElementById("ideas-content");
      if (iRoot) renderIdeas(iRoot, updatedIdeas);
      announce("Personalized ideas updated.", "polite");
    } catch (err) {
      announce(`Ideas error: ${/** @type {Error} */ (err).message}`, "assertive");
    } finally {
      setBusy(false);
    }
  });

  // Assistant suggested question chips
  const chips = document.querySelectorAll(".chip-btn");
  const qTextarea = /** @type {HTMLTextAreaElement | null} */ (document.getElementById("assistant-question"));
  for (const chip of chips) {
    chip.addEventListener("click", () => {
      const q = chip.getAttribute("data-question") || chip.textContent || "";
      if (qTextarea) {
        qTextarea.value = q;
        qTextarea.focus();
        announce(`Selected suggested question: ${q}`, "polite");
      }
    });
  }

  const askForm = /** @type {HTMLFormElement | null} */ (document.getElementById("assistant-form"));
  const chatLog = document.getElementById("chat-log");
  const submitBtn = /** @type {HTMLButtonElement | null} */ (document.getElementById("assistant-submit-btn"));
  const assistantStatus = document.getElementById("assistant-status");

  // Support Enter to submit in textarea (Shift+Enter inserts a new line)
  qTextarea?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      askForm?.requestSubmit();
    }
  });

  // Assistant ask form submission
  askForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!state.currentBrief) {
      announce("Please generate an event plan first before asking questions.", "assertive");
      return;
    }
    const question = qTextarea?.value.trim() || "";
    if (!question) return;

    // Show Thinking... status and disable submit button
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Thinking...";
    }
    if (assistantStatus) {
      assistantStatus.textContent = "Thinking... Consulting EventCraft planning assistant...";
    }

    try {
      setBusy(true, "Consulting EventCraft planning assistant...");
      const res = await askAssistant(state.currentBrief, question, state.chatHistory);
      const answerSource = res.source || (res.grounded ? "template" : "fallback");
      addChatMessage(state.chatHistory, question, res.answer, answerSource);

      if (qTextarea) {
        qTextarea.value = "";
        qTextarea.focus();
      }
      if (chatLog) {
        renderAssistantLog(chatLog, state.chatHistory);
      }
      announce(`Assistant answered: ${res.answer}`, "polite");
    } catch (err) {
      announce(`Assistant error: ${/** @type {Error} */ (err).message}`, "assertive");
      if (qTextarea) qTextarea.focus();
    } finally {
      setBusy(false);
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Ask Assistant";
      }
      if (assistantStatus) {
        assistantStatus.textContent = "";
      }
    }
  });
});
