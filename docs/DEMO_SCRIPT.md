# 2-Minute Demonstration Script

This timestamped demonstration script guides evaluators through the core capabilities of EventCraft AI in 120 seconds.

---

## Script Overview

| Timestamp | Phase / Feature | Key Actions & Narrative |
| :--- | :--- | :--- |
| **0:00 - 0:20** | **Introduction & Problem Statement** | - State verbatim problem statement: *"Create a GenAI-powered planning assistant that helps users organize weddings, birthdays, and community events with budgets, timelines, vendor checklists, and personalized ideas."*<br>- Highlight architectural highlights: Zero client frameworks, WCAG 2.2 AA accessibility, exact largest-remainder Decimal budgets, and offline fallback. |
| **0:20 - 0:45** | **Wedding Planning (North Indian Punjabi)** | - Click **"Try Wedding Sample (Punjabi Sangeet)"** button.<br>- Click **"Generate Event Plan"**.<br>- Walk through the **Budget deliverable**: notice INR currency (`₹`), exact cent precision, cost per guest, and contingency reserve.<br>- Walk through the **Timeline deliverable**: backwards scheduled milestones from April 2027, dependency ordering, and day-of run-of-show.<br>- Walk through **Vendor checklist**: vetting questions, required docs, and red flags. |
| **0:45 - 1:05** | **Instant Budget Rebalance (Zero AI Calls)** | - Scroll to the Budget section.<br>- In the rebalance sub-form, adjust total budget from `1,800,000` to `2,200,000` and guest count from `220` to `250`.<br>- Click **"Rebalance Budget (Zero AI calls)"**.<br>- Demonstrate instant recalculation (< 1ms latency) with no LLM calls and exact dollar/cent allocation. |
| **1:05 - 1:25** | **Birthday & Community Events + Steering** | - Click **"Try Birthday Sample (Retro Arcade Neon)"**.<br>- Show age-appropriate timeline milestones and arcade theme suggestions.<br>- Click **"Try Community Sample (Solar Green Festival)"**.<br>- Note community-specific checklist categories (city permits, volunteer safety, sound/stage power).<br>- In **Personalized Ideas**, enter a steer: *"Focus on native tree planting and youth volunteer workshops"*, and click **"Regenerate Ideas with Steer"**. |
| **1:25 - 1:45** | **Grounded Planning Assistant** | - Scroll to **"Ask the assistant"**.<br>- Type: *"What is the most critical item to secure first for this community festival?"*<br>- Assistant provides grounded logistical advice citing the city permit deadline from the generated timeline.<br>- Type off-topic query: *"Who won the 1998 World Cup?"*<br>- Demonstrate graceful polite refusal keeping conversation focused strictly on event planning. |
| **1:45 - 2:00** | **Accessibility & Quality Proof** | - Demonstrate keyboard-only navigation: reload page, press `Tab` to reveal the skip link, press `Enter` to skip to `#main-content`.<br>- Trigger form error: clear event date, submit, show `#form-error-summary` alert and focus shifting.<br>- Conclude with quality metrics: `make check` passing 100%, 95.81% branch coverage, zero security issues in Bandit. |

---

## Preparation Checklist

1. Ensure the development server is running: `make run` (or `npm start` / `uvicorn eventcraft.main:create_app --port 3000`).
2. Verify browser viewport is set to 1920x1080 (or standard 1080p).
3. If demonstrating Gemini live generation, set `GEMINI_API_KEY="your-key"`; otherwise, verify that `OfflineClient` executes deterministically.
