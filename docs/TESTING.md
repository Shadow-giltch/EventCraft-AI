# Testing Strategy & Test Inventory

EventCraft AI employs a multi-tiered test suite ensuring algorithmic correctness, security hardening, strict input validation, and high accessibility compliance.

---

## Test Inventory Summary

| Test Category | Directory / Files | Framework | Count | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Unit Tests** | `tests/unit/` | `pytest` | 42 | Pure domain logic: largest-remainder budget calculations, backwards timeline scheduling, five-facet ideas generation, clock abstractions, and guardrails. |
| **Integration Tests** | `tests/integration/` | `pytest` + `httpx.ASGITransport` | 14 | API endpoint contracts, ASGI lifespan lifecycles, and OpenAPI schema drift detection. |
| **Security Tests** | `tests/security/` | `pytest` + `httpx.ASGITransport` | 11 | Injection payloads, rate limiting sliding window, body size limits, CSP header enforcement, and secret key leak prevention. |
| **Property Tests** | `tests/property/` | `hypothesis` | 10 | Invariant validation: budget allocations sum identically to total across random currencies and guest counts; timeline dependencies never invert. |
| **Accessibility Tests** | `tests/accessibility/` | `pytest` + `BeautifulSoup4` | 8 | Static HTML validation: single h1, semantic landmarks, skip link presence, 100% input-to-label mapping, and CSS contrast ratios >= 4.5:1. |
| **Frontend Unit Tests** | `static/js/__tests__/` | `node:test` | 8 | Pure client-side JavaScript functions: currency formatting, ISO date parsing, localStorage adapters, and progress calculation. |
| **Total Automated Tests** | — | — | **93** | Comprehensive test coverage across all layers. |

---

## Coverage Gate Verification

The project enforces a strict branch coverage gate: `--cov-fail-under=95`.

Current execution metrics:
- **Total Statements**: 1,274
- **Branch Points**: 182
- **Total Coverage**: **95.81%**

Run the coverage report locally:

```bash
pytest --cov=src/eventcraft --cov-branch --cov-report=term-missing
```

---

## Hypothesis Property Testing Invariants

Property-based testing is implemented in `tests/property/` via the `hypothesis` library:

1. **Budget Invariant (`test_budget_properties.py`)**:
   - For *any* arbitrary total budget $T \in [10.00, 10{,}000{,}000.00]$ and guest count $G \in [1, 5000]$:
     $$\sum_{i} \text{amount}_i + \text{contingency} = T \quad (\text{exact Decimal cent precision})$$
   - Category percentages sum to $100.00\% \pm 0.01\%$.
   - Cost per guest is always positive and equals $T / G$ rounded to 2 decimal places.

2. **Timeline Invariant (`test_timeline_properties.py`)**:
   - For *any* valid lead time horizon $L \in [1, 1095]$ days:
     - No milestone is scheduled in the past ($\text{due\_date} \ge \text{reference\_date}$).
     - Milestone due dates monotonically advance according to lead days.
     - Dependent milestones are never scheduled prior to their prerequisite tasks.

3. **Sanitization Invariant (`test_sanitize_properties.py`)**:
   - For *any* generated unicode string containing arbitrary control codes or ANSI escape sequences:
     - `sanitize_string()` produces output guaranteed to be free of control characters.
     - Valid printable text and alphanumeric content is preserved without data loss.

---

## Reproducing All Tests

Execute the entire test battery using the Makefile:

```bash
# Run Python pytest suite (including coverage gate)
make test-python

# Run pure JavaScript node:test suite
make test-frontend

# Run full unified test suite
make test
```
