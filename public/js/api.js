// @ts-check
/**
 * @fileoverview Network API client for communicating with EventCraft endpoints.
 */

/**
 * Handle HTTP response and parse JSON or extract RFC 7807 problem details.
 * @param {Response} response
 * @returns {Promise<any>}
 */
async function handleResponse(response) {
  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errorJson = await response.json();
      if (errorJson && typeof errorJson === "object") {
        errorDetail = errorJson.detail || errorJson.title || errorDetail;
      }
    } catch {
      // Fallback to text status
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

/**
 * Generate full multi-deliverable event plan.
 * @param {object} brief
 * @returns {Promise<any>}
 */
export async function fetchPlan(brief) {
  const response = await fetch("/api/v1/plans/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(brief),
  });
  return handleResponse(response);
}

/**
 * Rebalance budget lines with zero LLM calls.
 * @param {object} payload
 * @returns {Promise<any>}
 */
export async function rebalanceBudget(payload) {
  const response = await fetch("/api/v1/budget/rebalance", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

/**
 * Regenerate personalized ideas with optional steer.
 * @param {object} brief
 * @param {string | null} [steer=null]
 * @returns {Promise<any>}
 */
export async function regenerateIdeas(brief, steer = null) {
  const response = await fetch("/api/v1/plans/ideas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ brief, steer }),
  });
  return handleResponse(response);
}

/**
 * Ask the grounded event planning assistant.
 * @param {object} brief
 * @param {string} question
 * @param {Array<[string, string]>} chatHistory
 * @returns {Promise<any>}
 */
export async function askAssistant(brief, question, chatHistory = []) {
  const response = await fetch("/api/v1/assistant/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ brief, question, chat_history: chatHistory }),
  });
  return handleResponse(response);
}

/**
 * Fetch one of the three verified sample briefs.
 * @param {"wedding" | "birthday" | "community"} eventType
 * @returns {Promise<any>}
 */
export async function fetchSampleBrief(eventType) {
  const fileMap = {
    wedding: "/examples/wedding_sample.json",
    birthday: "/examples/birthday_sample.json",
    community: "/examples/community_sample.json",
  };
  const url = fileMap[eventType] || fileMap.wedding;
  const response = await fetch(url);
  return handleResponse(response);
}
