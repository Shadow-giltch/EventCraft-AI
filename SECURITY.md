# Security Policy & Threat Model

EventCraft AI is engineered with defense-in-depth principles across the entire application stack.

## Reporting a Vulnerability

If you discover a security vulnerability, please report it via private disclosure by emailing `security@eventcraft.ai` or through GitHub Security Advisories. We will respond within 48 hours.

## Threat Model Matrix

| Threat | Risk / Impact | Mitigation Strategy | Implementation File | Verification Test |
| :--- | :--- | :--- | :--- | :--- |
| **Prompt Injection** | Jailbreak, data exfiltration, system manipulation | Delimiter wrapping, control-char stripping, system instruction isolation, strict schema output | `src/eventcraft/llm/guardrails.py`<br>`src/eventcraft/security/sanitize.py` | `tests/security/test_injection_payloads.py`<br>`tests/unit/test_guardrails.py` |
| **Cross-Site Scripting (XSS)** | Script execution in user browser, token theft | Strict CSP (`script-src 'self'`), zero `innerHTML`, DOM manipulation via `textContent` only | `src/eventcraft/security/headers.py`<br>`src/eventcraft/static/js/render.js` | `tests/security/test_security_headers.py`<br>`tests/accessibility/test_static_accessibility.py` |
| **Denial of Service (DoS)** | Exhaustion of server CPU/memory and Gemini quota | Strict 32 KB request body limit, in-memory rate limiting, bounded LLM concurrency semaphore | `src/eventcraft/security/body_limit.py`<br>`src/eventcraft/security/rate_limit.py`<br>`src/eventcraft/services/planner.py` | `tests/security/test_rate_limiting.py`<br>`tests/integration/test_endpoints.py` |
| **API Secret Leakage** | Compromised credentials, unauthorized billing | `pydantic.SecretStr` for API keys, excluded from serialization/repr, never logged or sent to browser | `src/eventcraft/config.py`<br>`src/eventcraft/llm/gemini.py` | `tests/unit/test_config.py`<br>`tests/security/test_security_headers.py` |
| **Information Disclosure** | Stack traces, server runtime leak on error | RFC 7807 `ProblemDetails` with unique correlation ID; generic fallback messages on 500/502/504 | `src/eventcraft/errors.py`<br>`src/eventcraft/main.py` | `tests/integration/test_endpoints.py` |
| **Cross-Origin Abuse** | Unauthorized third-party site invocation | Strict CORS allow-list via environment configuration; rejects wildcard (`*`) origins | `src/eventcraft/main.py`<br>`src/eventcraft/config.py` | `tests/security/test_security_headers.py` |
| **Supply Chain Poisoning** | Vulnerable or tampered dependencies | Pinned/semver dependencies, automated scanning via Bandit and Pip-Audit in CI | `requirements.txt`<br>`pyproject.toml`<br>`.github/workflows/ci.yml` | `make security-audit` |
| **Client Data Tampering** | Fake server-side plan fed to assistant | Server-side deterministic reconstruction of grounded context before LLM query | `src/eventcraft/services/assistant.py` | `tests/integration/test_endpoints.py` |
