# Contributing to EventCraft AI

Thank you for your interest in contributing to EventCraft AI! We welcome community contributions, bug fixes, and documentation improvements.

## Code of Conduct

Please maintain a respectful, inclusive, and professional environment across all interactions.

## Development Workflow

1. Fork and clone the repository.
2. Install Python 3.11+ and Node.js 22+.
3. Install development dependencies:
   ```bash
   make install
   ```
4. Run the full verification suite before submitting PRs:
   ```bash
   make check
   ```

## Architectural Guidelines

- **One-way dependencies**: `api` -> `services` -> `domain` / `llm`.
- **Pure domain logic**: Code in `src/eventcraft/domain/` must be 100% pure Python with zero I/O, framework, or network imports.
- **Decimals for money**: Always use `decimal.Decimal` with 2 decimal places for financial calculations. Never use floats.
- **File & Function limits**: Source files <= 250 lines; functions <= 30 lines; arguments <= 5.
- **Security & A11y**: Zero raw `innerHTML`, strict CSP compliance, and WCAG 2.2 AA accessibility standards.
