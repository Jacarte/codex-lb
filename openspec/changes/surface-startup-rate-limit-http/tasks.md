## 1. Startup rate-limit surfacing

- [ ] 1.1 Update the public Responses startup probe so an immediate rate-limit `response.failed`/`error` event becomes an HTTP 429 instead of an HTTP 200 SSE stream.
- [ ] 1.2 Preserve existing streamed `response.failed` behavior for non-rate-limit startup events and post-start failures.
- [ ] 1.3 Synthesize `Retry-After` from upstream rate-limit metadata when the public response is 429 and no retry header is already present.

## 2. Regression coverage

- [ ] 2.1 Add unit coverage for startup rate-limit event detection and retry-header synthesis.
- [ ] 2.2 Add integration coverage showing `/v1/responses` returns HTTP 429 for an immediate upstream rate-limit event.

## 3. Verification

- [ ] 3.1 Run focused unit and integration tests covering Responses startup error handling.
- [ ] 3.2 Run changed-file diagnostics and confirm clean results.
