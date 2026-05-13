## ADDED Requirements

### Requirement: Public Responses startup rate limits surface as HTTP 429
When a public HTTP `/v1/responses` or `/backend-api/codex/responses` request encounters an upstream rate-limit failure before the first public stream event is committed, the proxy MUST surface the failure as an HTTP `429` OpenAI-style error response instead of opening an HTTP `200` SSE stream with an in-band `response.failed` rate-limit event.

#### Scenario: immediate upstream rate limit before public stream commit
- **WHEN** the startup probe observes the first upstream event is `response.failed` or `error`
- **AND** the normalized OpenAI error maps to `429`
- **THEN** the public route returns HTTP `429`
- **AND** the response body preserves the OpenAI-style rate-limit error payload

#### Scenario: non-rate-limit startup failures keep streamed contract
- **WHEN** the startup probe observes the first upstream event is `response.failed`
- **AND** the normalized OpenAI error does not map to `429`
- **THEN** the route keeps the existing streamed `response.failed` contract

### Requirement: Public Responses 429 errors include retry hints when available
When a public Responses route returns HTTP `429` and the normalized upstream OpenAI error payload includes `resets_in_seconds` or `resets_at`, the proxy MUST include a `Retry-After` header unless one is already present.

#### Scenario: reset seconds become Retry-After
- **WHEN** a public Responses error response has HTTP `429`
- **AND** the normalized OpenAI error includes `resets_in_seconds`
- **AND** no `Retry-After` header is already set
- **THEN** the response includes `Retry-After` with the corresponding positive whole-second delay
