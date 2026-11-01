# Accessibility & WCAG 2.2 AA Compliance

EventCraft AI is designed from the ground up to achieve full compliance with the W3C Web Content Accessibility Guidelines (WCAG) 2.2 Level AA.

---

## WCAG 2.2 AA Criterion Mapping

| Criterion | Level | Implementation File | Verification Test | Description & Enforcement |
| :--- | :--- | :--- | :--- | :--- |
| **1.1.1 Non-text Content** | A | `index.html`, `js/render.js` | `test_static_accessibility.py` | All informative visual indicators have accessible text alternatives. Purely decorative elements use `aria-hidden="true"`. |
| **1.3.1 Info and Relationships** | A | `index.html`, `css/style.css` | `test_static_accessibility.py` | Semantic landmarks (`<header>`, `<nav>`, `<main>`, `<footer>`), single top-level `<h1>`, logical heading hierarchy, and data table captions with `scope="col"` / `scope="row"`. |
| **1.3.5 Identify Input Purpose** | AA | `index.html` | `test_static_accessibility.py` | Standard form fields use appropriate input types (`date`, `number`, `select`) and autocomplete-friendly identifiers. |
| **1.4.3 Contrast (Minimum)** | AA | `css/style.css` | `test_css_wcag_contrast_ratios` | Body text achieves >= 4.5:1 contrast against light (`#ffffff`, `#f8fafc`) and dark (`#1e293b`, `#0b1120`) backgrounds. Primary action buttons exceed 10:1 contrast. |
| **1.4.11 Non-text Contrast** | AA | `css/style.css` | `test_css_wcag_contrast_ratios` | Focus rings, form input borders, and badge outlines maintain >= 3:1 contrast against adjacent background colors. |
| **1.4.12 Text Spacing** | AA | `css/style.css` | Manual Review | Layout uses relative units (`rem`), line heights >= 1.6, and fluid grid containers that withstand user text spacing adjustments without overflow. |
| **2.1.1 Keyboard** | A | `index.html`, `js/render.js` | `test_no_positive_tabindex` | Every interactive button, link, and form input is operable via standard keyboard tab and enter/space keys. Zero mouse-only traps. |
| **2.4.1 Bypass Blocks** | A | `index.html`, `css/style.css` | `test_skip_link_present_and_targets_main` | Prominent skip navigation link positioned at the top of the DOM directly transfers keyboard focus to `<main id="main-content">`. |
| **2.4.7 Focus Visible** | AA | `css/style.css` | Manual Review | High-visibility 3px solid focus ring with 2px offset (`:focus-visible`) across all interactive elements. |
| **2.5.8 Target Size (Minimum)** | AA | `css/style.css` | Manual Review | Interactive touch targets (buttons, links, inputs) enforce minimum dimensions of 44x44px. |
| **3.3.1 Error Identification** | A | `index.html`, `js/form.js` | `test_static_accessibility.py` | Form validation failures populate an accessible error summary box with `role="alert"` and anchor links directly focusing invalid fields. |
| **3.3.2 Labels or Instructions** | A | `index.html` | `test_all_form_controls_have_associated_labels` | 100% of form inputs have visible, associated `<label for="...">` tags and descriptive hint text linked via `aria-describedby`. |
| **4.1.3 Status Messages** | AA | `index.html`, `js/a11y.js` | `test_static_accessibility.py` | Screen reader announcements for loading, plan generation, rebalancing, and errors are dispatched through `aria-live="polite"` and `aria-live="assertive"` regions. |

---

## Manual Keyboard Verification Checklist

Perform this 6-step manual keyboard verification using standard browser controls:

1. **Skip Navigation**:
   - Open `http://localhost:3000`.
   - Press `Tab`. Verify the "Skip to main content" link becomes visible in the top-left corner with a distinct focus ring.
   - Press `Enter`. Verify keyboard focus shifts directly to `#main-content`.

2. **Sample Brief Selection**:
   - Press `Shift+Tab` or navigate to the sample brief buttons.
   - Press `Enter` on "Wedding Sample (Punjabi Sangeet)".
   - Verify all form fields are instantly populated with North Indian Punjabi sample data.

3. **Form Error Handling**:
   - Clear the "Event Date" field.
   - Tab to the "Generate Event Plan" button and press `Enter`.
   - Verify the browser focuses the `#form-error-summary` alert box.
   - Press `Enter` on the error link. Verify focus moves directly to the invalid "Event Date" input with `aria-invalid="true"`.

4. **In-Page Anchor Navigation**:
   - Re-enter a valid future date and press `Enter` on "Generate Event Plan".
   - When the plan renders, navigate to the in-page navigation links (`#budget-section`, `#timeline-section`, etc.).
   - Press `Enter` on each link and verify the browser smoothly scrolls and moves focus to each respective section without keyboard traps.

5. **Vendor Checklist Interaction**:
   - Tab to a vendor checklist item's status dropdown (e.g. Venue status).
   - Use `Up`/`Down` arrow keys to change status from `to do` to `booked`.
   - Verify the live region announces the status update and the selection persists upon page reload.

6. **Assistant Chat Box**:
   - Tab to the "Ask the assistant" input field.
   - Type a question (e.g. "What should I book first?") and press `Enter`.
   - Verify the loading indicator displays and the assistant's answer appears in the polite chat log region.
