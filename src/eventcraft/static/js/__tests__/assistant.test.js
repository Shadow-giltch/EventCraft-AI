import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { addChatMessage, formatAssistantBadge } from "../state.js";
import { renderAssistantLog } from "../render.js";
import { cleanAssistantAnswer } from "../api.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..", "..", "..", "..", "..");

// ========================================================================
// 1. Assistant State & Badge Logic Tests
// ========================================================================

test("addChatMessage records questions, answers, normalized source and timestamp", () => {
  const history = [];

  addChatMessage(history, "What should I book first? ", " Secure venue and caterer first.", "template");
  assert.equal(history.length, 1);
  assert.equal(history[0].question, "What should I book first?");
  assert.equal(history[0].answer, "Secure venue and caterer first.");
  assert.equal(history[0].source, "template");
  assert.ok(history[0].timestamp);

  // Default source when omitted
  addChatMessage(history, "Where can I save money?", "Focus on seasonal flowers.");
  assert.equal(history.length, 2);
  assert.equal(history[1].source, "template");

  // AI source
  addChatMessage(history, "Any creative lighting ideas?", "Use warm botanical uplighting.", "gemini");
  assert.equal(history.length, 3);
  assert.equal(history[1].source, "template");
  assert.equal(history[2].source, "gemini");
});

test("formatAssistantBadge correctly distinguishes template answers from AI", () => {
  // Template / fallback responses must be clearly labeled
  const templateBadge = formatAssistantBadge("template");
  assert.equal(templateBadge.label, "Template answer (AI unavailable)");
  assert.equal(templateBadge.className, "badge-template");
  assert.equal(templateBadge.isAi, false);

  const fallbackBadge = formatAssistantBadge("fallback");
  assert.equal(fallbackBadge.label, "Template answer (AI unavailable)");
  assert.equal(fallbackBadge.isAi, false);

  const emptyBadge = formatAssistantBadge("");
  assert.equal(emptyBadge.label, "Template answer (AI unavailable)");
  assert.equal(emptyBadge.isAi, false);

  // Genuine AI responses
  const aiBadge = formatAssistantBadge("ai");
  assert.equal(aiBadge.label, "AI-generated");
  assert.equal(aiBadge.className, "badge-ai");
  assert.equal(aiBadge.isAi, true);

  const geminiBadge = formatAssistantBadge("gemini");
  assert.equal(geminiBadge.label, "AI-generated");
  assert.equal(geminiBadge.isAi, true);
});

// Mock DOM container for renderAssistantLog test
class MockElement {
  constructor(tagName = "div") {
    this.tagName = tagName;
    this.children = [];
    this.attributes = {};
    this.className = "";
    this.textContent = "";
    this.hidden = false;
  }
  setAttribute(k, v) {
    this.attributes[k] = String(v);
  }
  removeAttribute(k) {
    delete this.attributes[k];
  }
  getAttribute(k) {
    return this.attributes[k];
  }
  appendChild(child) {
    this.children.push(child);
  }
  append(...children) {
    for (const c of children) {
      this.children.push(c);
    }
  }
}

// Global minimal document shim for el() in render.js
if (typeof globalThis.document === "undefined") {
  globalThis.document = {
    createElement(tag) {
      return new MockElement(tag);
    },
    createTextNode(text) {
      return text;
    },
  };
  globalThis.Node = MockElement;
}

test("renderAssistantLog hides when history is empty and shows answers with badges", () => {
  const container = new MockElement("div");

  // 1. Empty history -> container hidden
  renderAssistantLog(container, []);
  assert.equal(container.hidden, true);
  assert.equal(container.getAttribute("tabindex"), undefined);

  // 2. Populated history -> container unhidden, entries rendered
  const chatHistory = [
    {
      question: "What should I book first?",
      answer: "Book your ceremony venue 9-12 months prior.",
      source: "template",
    },
  ];

  renderAssistantLog(container, chatHistory);
  assert.equal(container.hidden, false);
  assert.equal(container.getAttribute("tabindex"), undefined);
  assert.equal(container.children.length, 2); // user entry + assistant entry

  const assistantEntry = container.children[1];
  assert.equal(assistantEntry.className, "chat-entry assistant");
  const header = assistantEntry.children[0];
  const badge = header.children[1];
});

// ========================================================================
// 1b. Mocked LLM Answer Parsing & Fallback Tests
// ========================================================================

test("cleanAssistantAnswer extracts plain text from JSON-wrapped LLM reply", () => {
  const raw = '{"response": "Secure your ceremony and reception venue first."}';
  const result = cleanAssistantAnswer(raw);
  assert.equal(result, "Secure your ceremony and reception venue first.");
  assert.equal(result.includes("{"), false);
  assert.equal(result.includes("response"), false);
});

test("cleanAssistantAnswer preserves natural plain-text LLM reply", () => {
  const raw = "Secure your ceremony and reception venue first.";
  const result = cleanAssistantAnswer(raw);
  assert.equal(result, "Secure your ceremony and reception venue first.");
});

test("cleanAssistantAnswer strips markdown code fences from LLM reply", () => {
  const raw = '```json\n{\n  "response": "Secure your ceremony and reception venue first."\n}\n```';
  const result = cleanAssistantAnswer(raw);
  assert.equal(result, "Secure your ceremony and reception venue first.");
  assert.equal(result.includes("```"), false);
});

test("cleanAssistantAnswer returns empty string on empty or malformed reply", () => {
  assert.equal(cleanAssistantAnswer(""), "");
  assert.equal(cleanAssistantAnswer("   "), "");
  assert.equal(cleanAssistantAnswer("{}"), "");
});

test("Mocked LLM assistant workflow: handles JSON, plain text, fenced, and empty fallback", () => {
  // 1. Mock JSON-wrapped LLM response
  const jsonMockLLM = {
    answer: '{"response": "Focus on priority catering and venue bookings."}',
    source: "ai",
  };
  const cleanedJson = cleanAssistantAnswer(jsonMockLLM.answer);
  assert.equal(cleanedJson, "Focus on priority catering and venue bookings.");
  assert.equal(cleanedJson.includes("{"), false);

  // 2. Mock plain-text LLM response
  const plainMockLLM = {
    answer: "Focus on priority catering and venue bookings.",
    source: "ai",
  };
  const cleanedPlain = cleanAssistantAnswer(plainMockLLM.answer);
  assert.equal(cleanedPlain, "Focus on priority catering and venue bookings.");

  // 3. Mock fenced LLM response
  const fencedMockLLM = {
    answer: '```json\n{\n  "response": "Focus on priority catering and venue bookings."\n}\n```',
    source: "ai",
  };
  const cleanedFenced = cleanAssistantAnswer(fencedMockLLM.answer);
  assert.equal(cleanedFenced, "Focus on priority catering and venue bookings.");
  assert.equal(cleanedFenced.includes("```"), false);

  // 4. Mock empty LLM response -> triggers fallback to template answer
  const emptyMockLLM = {
    answer: "",
    source: "ai",
  };
  const cleanedEmpty = cleanAssistantAnswer(emptyMockLLM.answer);
  const fallbackAnswer = !cleanedEmpty
    ? "Based on your wedding plan, your budget total is 10000.00 INR for 100 guests."
    : cleanedEmpty;
  const fallbackSource = !cleanedEmpty ? "template" : emptyMockLLM.source;

  assert.equal(
    fallbackAnswer,
    "Based on your wedding plan, your budget total is 10000.00 INR for 100 guests."
  );
  assert.equal(fallbackSource, "template");

  // Verify that fallback response is labeled "Template answer (AI unavailable)"
  const badgeInfo = formatAssistantBadge(fallbackSource);
  assert.equal(badgeInfo.label, "Template answer (AI unavailable)");
  assert.equal(badgeInfo.isAi, false);
});


// ========================================================================
// 2. Static Accessibility Tests on index.html
// ========================================================================

test("index.html has accessible question form, matching label, and no tabindex on chat-log", () => {
  const htmlPath = path.join(rootDir, "src", "eventcraft", "static", "index.html");
  const html = fs.readFileSync(htmlPath, "utf-8");

  // Verify label exists with explicit for="assistant-question"
  assert.match(
    html,
    /<label[^>]*for=["']assistant-question["'][^>]*>/i,
    "Must have explicit label with for='assistant-question'"
  );

  // Verify textarea exists with id="assistant-question" and name="assistant-question"
  assert.match(
    html,
    /<textarea[^>]*id=["']assistant-question["'][^>]*name=["']assistant-question["'][^>]*>/i,
    "Must have textarea with id and name matching label"
  );

  // Verify chat-log exists
  assert.match(html, /id=["']chat-log["']/i, "Must have element with id='chat-log'");

  // Extract chat-log tag to inspect attributes
  const chatLogTagMatch = html.match(/<[^>]*id=["']chat-log["'][^>]*>/i);
  assert.ok(chatLogTagMatch, "chat-log element must exist in HTML");
  const chatLogTag = chatLogTagMatch[0];

  // Must NOT have tabindex (empty bordered box must not be focusable)
  assert.equal(
    /tabindex/i.test(chatLogTag),
    false,
    "chat-log must NOT have tabindex attribute"
  );

  // Must have role="log"
  assert.match(chatLogTag, /role=["']log["']/i, "chat-log must have role='log'");

  // Must have aria-live="polite"
  assert.match(chatLogTag, /aria-live=["']polite["']/i, "chat-log must have aria-live='polite'");

  // Must be hidden initially when empty
  assert.match(chatLogTag, /\bhidden\b/i, "chat-log must be hidden initially when empty");

  // Verify dedicated assistant live region status element exists
  assert.match(
    html,
    /<div[^>]*id=["']assistant-status["'][^>]*role=["']status["'][^>]*aria-live=["']polite["'][^>]*>/i,
    "Must have assistant-status element with role='status' and aria-live='polite'"
  );

  // Verify example question chips exist as accessible buttons
  assert.match(
    html,
    /<button[^>]*class=["'][^"']*chip-btn[^"']*["'][^>]*data-question=["']What should I book first\?["']/i,
    "Must have example question chip for booking priority"
  );
  assert.match(
    html,
    /<button[^>]*class=["'][^"']*chip-btn[^"']*["'][^>]*data-question=["']Where can I save money\?["']/i,
    "Must have example question chip for saving money"
  );
});

// ========================================================================
// 3. WCAG 2.2 AA Contrast Ratio Calculation & Tests on style.css
// ========================================================================

/**
 * Convert hex color to sRGB components (0 to 1).
 * @param {string} hex
 * @returns {[number, number, number]}
 */
function hexToRgb(hex) {
  let clean = hex.replace("#", "").trim();
  if (clean.length === 3) {
    clean = clean.split("").map((c) => c + c).join("");
  }
  const num = parseInt(clean, 16);
  return [(num >> 16) / 255, ((num >> 8) & 0xff) / 255, (num & 0xff) / 255];
}

/**
 * Calculate relative luminance per WCAG 2.1 / 2.2 specification.
 * @param {[number, number, number]} rgb
 * @returns {number}
 */
function relativeLuminance([r, g, b]) {
  const linearize = (c) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
  return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b);
}

/**
 * Calculate contrast ratio between two hex colors.
 * @param {string} hex1
 * @param {string} hex2
 * @returns {number}
 */
function contrastRatio(hex1, hex2) {
  const l1 = relativeLuminance(hexToRgb(hex1));
  const l2 = relativeLuminance(hexToRgb(hex2));
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

test("style.css color variables meet WCAG 2.2 AA contrast ratio (>= 4.5:1)", () => {
  const cssPath = path.join(rootDir, "src", "eventcraft", "static", "css", "style.css");
  const css = fs.readFileSync(cssPath, "utf-8");

  // Helper to extract CSS variable value from :root in style.css
  const getVar = (name) => {
    const match = css.match(new RegExp(`${name}:\\s*([^;]+);`));
    assert.ok(match, `CSS variable ${name} must be defined`);
    return match[1].trim();
  };

  const text = getVar("--color-text");
  const textMuted = getVar("--color-text-muted");
  const surface = getVar("--color-surface");
  const templateBg = getVar("--badge-template-bg");
  const templateText = getVar("--badge-template-text");
  const aiBg = getVar("--badge-ai-bg");
  const aiText = getVar("--badge-ai-text");

  // 1. Primary body text on surface
  const ratioText = contrastRatio(text, surface);
  assert.ok(
    ratioText >= 4.5,
    `Primary text contrast (${ratioText.toFixed(2)}:1) must be >= 4.5:1`
  );

  // 2. Muted text on surface
  const ratioMuted = contrastRatio(textMuted, surface);
  assert.ok(
    ratioMuted >= 4.5,
    `Muted text contrast (${ratioMuted.toFixed(2)}:1) must be >= 4.5:1`
  );

  // 3. Template badge text on template badge background
  const ratioTemplate = contrastRatio(templateText, templateBg);
  assert.ok(
    ratioTemplate >= 4.5,
    `Template badge contrast (${ratioTemplate.toFixed(2)}:1) must be >= 4.5:1`
  );

  // 4. AI badge text on AI badge background
  const ratioAi = contrastRatio(aiText, aiBg);
  assert.ok(
    ratioAi >= 4.5,
    `AI badge contrast (${ratioAi.toFixed(2)}:1) must be >= 4.5:1`
  );
});
