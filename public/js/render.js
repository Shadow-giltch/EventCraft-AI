// @ts-check
/**
 * @fileoverview DOM rendering engine using strict createElement/textContent (no innerHTML).
 */
import { formatCurrency, formatDate, formatPercent } from "./format.js";
import { ALLOWED_STATUSES } from "./state.js";

/**
 * @param {string} tag
 * @param {Record<string, any>} [attrs={}]
 * @param {Array<Node | string | null | undefined>} [children=[]]
 * @returns {HTMLElement}
 */
export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null) continue;
    if (k === "className") node.className = String(v);
    else if (k === "textContent") node.textContent = String(v);
    else if (k.startsWith("on")) node.addEventListener(k.slice(2).toLowerCase(), v);
    else node.setAttribute(k, String(v));
  }
  for (const c of children) {
    if (typeof c === "string") node.appendChild(document.createTextNode(c));
    else if (c instanceof Node) node.appendChild(c);
  }
  return node;
}

export function createBadge(source) {
  const isAi = source.toLowerCase() === "ai";
  return el("span", {
    className: `badge ${isAi ? "badge-ai" : "badge-template"}`,
    textContent: isAi ? "AI-generated" : "Template",
  });
}

export function renderBudget(root, budget) {
  root.textContent = "";
  const header = el("div", { className: "section-meta-row" }, [
    createBadge(budget.meta.source),
    el("span", { className: "cost-per-guest", textContent: `Cost/guest: ${formatCurrency(budget.cost_per_guest, budget.currency)}` }),
    el("span", { className: "contingency-note", textContent: `Contingency: ${formatCurrency(budget.contingency_amount, budget.currency)}` }),
  ]);
  const rows = budget.lines.map((l) => el("tr", {}, [
    el("th", { scope: "row", textContent: l.category }),
    el("td", { textContent: formatPercent(l.percent) }),
    el("td", { textContent: formatCurrency(l.amount, budget.currency) }),
    el("td", { textContent: l.rationale }),
    el("td", { textContent: l.saving_tip }),
  ]));
  const table = el("table", { className: "budget-table" }, [
    el("caption", { textContent: `Budget Breakdown (Total: ${formatCurrency(budget.total_amount, budget.currency)})` }),
    el("thead", {}, [el("tr", {}, ["Category", "Share", "Amount", "Rationale", "Saving Tip"].map((h) => el("th", { scope: "col", textContent: h })))]),
    el("tbody", {}, rows),
  ]);
  root.append(header, table);
}

export function renderTimeline(root, timeline) {
  root.textContent = "";
  const header = el("div", { className: "section-meta-row" }, [
    createBadge(timeline.meta.source),
    el("span", { textContent: `Lead time: ${timeline.total_lead_days}d | Date: ${formatDate(timeline.event_date)}` }),
  ]);
  const mList = el("ol", { className: "milestone-list" }, timeline.milestones.map((m) => el("li", { className: `milestone-item ${m.is_rush ? "rush-item" : ""}` }, [
    el("div", { className: "milestone-header" }, [
      el("strong", { textContent: m.title }),
      el("span", { className: "due-date", textContent: `Due: ${formatDate(m.due_date)}` }),
      m.is_rush ? el("span", { className: "badge-rush", textContent: "Rush" }) : null,
    ]),
    el("div", { className: "milestone-meta" }, [el("span", { textContent: `Phase: ${m.phase}` })]),
    el("p", { className: "milestone-notes", textContent: m.notes }),
  ])));
  const rList = el("ol", { className: "run-of-show-list" }, timeline.run_of_show.map((r) => el("li", { className: "ros-item" }, [
    el("strong", { className: "ros-time", textContent: r.time }),
    el("span", { className: "ros-activity", textContent: ` ${r.activity} (${r.responsible})` }),
    el("p", { className: "ros-notes", textContent: r.notes }),
  ])));
  root.append(header, el("h3", { textContent: "Milestones Schedule" }), mList, el("h3", { textContent: "Day-of Run of Show" }), rList);
}

export function renderVendors(root, checklist, savedStatuses, onStatusChange) {
  root.textContent = "";
  const header = el("div", { className: "section-meta-row" }, [createBadge(checklist.meta.source)]);
  const cards = checklist.items.map((item) => {
    const curr = savedStatuses[item.id] || item.status;
    const select = el("select", {
      id: `vendor-status-${item.id}`,
      "aria-label": `Status for ${item.title}`,
      onchange: (e) => onStatusChange(item.id, /** @type {HTMLSelectElement} */ (e.target).value),
    }, ALLOWED_STATUSES.map((st) => el("option", { value: st, textContent: st, ...(st === curr ? { selected: "selected" } : {}) })));
    return el("li", { className: "vendor-card" }, [
      el("div", { className: "vendor-card-header" }, [
        el("h4", { textContent: item.title }),
        el("span", { className: "vendor-book-by", textContent: `Book by: ${formatDate(item.book_by_date)}` }),
        el("div", { className: "status-control" }, [el("label", { htmlFor: `vendor-status-${item.id}`, textContent: "Status: " }), select]),
      ]),
      el("div", { className: "vetting-details" }, [
        el("div", { className: "vetting-col" }, [el("strong", { textContent: "Questions:" }), el("ul", {}, item.questions_to_ask.map((q) => el("li", { textContent: q })))]),
        el("div", { className: "vetting-col" }, [el("strong", { textContent: "Verify:" }), el("ul", {}, item.documents_to_verify.map((d) => el("li", { textContent: d })))]),
        el("div", { className: "vetting-col warning" }, [el("strong", { textContent: "Red Flags:" }), el("ul", {}, item.red_flags.map((rf) => el("li", { textContent: rf })))]),
      ]),
    ]);
  });
  root.append(header, el("ul", { className: "vendor-list" }, cards));
}

export function renderIdeas(root, ideasData) {
  root.textContent = "";
  const header = el("div", { className: "section-meta-row" }, [
    createBadge(ideasData.meta.source),
    ideasData.steer ? el("span", { className: "active-steer", textContent: `Steer: "${ideasData.steer}"` }) : null,
  ]);
  const cards = ideasData.ideas.map((i) => el("div", { className: "idea-card" }, [
    el("div", { className: "idea-facet-tag", textContent: i.facet.toUpperCase() }),
    el("h4", { textContent: i.title }),
    el("p", { className: "idea-desc", textContent: i.description }),
    el("p", { className: "why-it-fits" }, [el("strong", { textContent: "Why it fits: " }), i.why_it_fits]),
    el("span", { className: "tier-tag", textContent: `Tier: ${i.budget_tier}` }),
  ]));
  root.append(header, el("div", { className: "ideas-grid" }, cards));
}

export function renderAssistantLog(root, chatHistory) {
  root.textContent = "";
  if (!chatHistory.length) {
    root.append(el("p", { className: "empty-log", textContent: "Ask any planning or logistical question grounded in your plan." }));
    return;
  }
  for (const [q, a] of chatHistory) {
    root.append(
      el("div", { className: "chat-entry user" }, [el("strong", { textContent: "You: " }), q]),
      el("div", { className: "chat-entry assistant" }, [el("strong", { textContent: "Assistant: " }), a])
    );
  }
}
