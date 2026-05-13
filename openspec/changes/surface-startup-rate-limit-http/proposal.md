## Why

OpenCode and similar OpenAI-compatible clients detect throttling primarily from an HTTP `429` response plus retry hints. The current `/v1/responses` streaming path can surface an immediate upstream `response.failed` rate-limit event on an HTTP `200` SSE stream, which prevents those clients from recognizing the condition as a retryable rate limit.

## What Changes

- Treat an immediate startup `response.failed` or `error` event carrying a rate-limit error as a pre-stream HTTP error on public Responses routes.
- Preserve the existing streamed `response.failed` contract for non-rate-limit startup failures and for failures that occur after the stream is already established.
- Add regression coverage for startup rate-limit conversion and retry header synthesis.

## Impact

- Affected code: `app/modules/proxy/api.py`, `tests/unit/test_proxy_api_responses_contract.py`, `tests/integration/test_proxy_responses.py`.
- Affected APIs: HTTP `/v1/responses` and HTTP `/backend-api/codex/responses` startup error handling.
- Compatibility impact: improves OpenCode/OpenAI-style rate-limit detection without changing the established streamed error contract for non-429 failures.
