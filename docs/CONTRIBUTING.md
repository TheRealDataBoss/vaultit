# Contributing to VaultIt

## Protocol Versioning

The protocol schema uses semantic versioning (`vaultit-v<major>.<minor>`):
- **Minor** bumps add optional fields. Existing consumers continue to work.
- **Major** bumps change required fields, remove fields, or alter types. Existing consumers must update.

All schema changes require a PR that updates:
1. `protocol/vaultit.schema.json`
2. `protocol/STATE_VECTOR.template.json`
3. `docs/SPEC.md`
4. Both CLI implementations (npm and Python)

## Proposing Schema Changes

1. Open an issue titled `[Schema] <description>` with:
   - The field(s) to add, change, or remove
   - Justification: what use case does this serve?
   - Migration path for existing STATE_VECTOR.json files
2. Discussion happens in the issue before any PR is opened
3. Schema changes require approval from the project owner

## Adding a New Delivery Mechanism

VaultIt is designed for thin wrappers around an identical protocol. To add a new delivery mechanism (e.g., a Rust CLI, a Homebrew formula, a Docker image):

1. Open an issue titled `[Delivery] <mechanism>`
2. The new mechanism must:
   - Validate STATE_VECTOR.json against the canonical schema
   - Implement all four commands: init, sync, status, bootstrap
   - Produce identical output for identical input (cross-implementation parity)
   - Include a test suite that runs against the shared test fixtures
3. Place the implementation under `packages/<name>/`

## Code Style

### JavaScript (npm package)
- ESLint with the project config
- No semicolons (StandardJS convention)
- ES modules (`import`/`export`)
- Node.js 18+ features allowed

### Python (Python package)
- Black formatter, default settings
- isort for import ordering
- Type hints on all public functions
- Python 3.10+ features allowed (match statements, union types with `|`)

## Testing Requirements

- Every new feature or bug fix must include tests
- npm package: Vitest
- Python package: pytest
- Schema changes: add validation test cases to both implementations
- GitHub Action: test with act (local Action runner)

## PR Process

1. Fork the repo and create a feature branch
2. Make your changes with tests
3. Run the full test suite locally
4. Open a PR against `main` with:
   - Clear title (imperative mood, under 72 chars)
   - Description of what and why
   - Link to related issue
5. All CI checks must pass
6. Project owner reviews and merges
