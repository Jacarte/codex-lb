## Why

The proxy currently exposes balancer exhaustion as the internal code `no_accounts`, which does not align with standard public OpenAI-compatible transient failure semantics. Main-session fallback logic in downstream clients is more likely to react correctly to canonical transient errors such as `service_unavailable` and `rate_limit_exceeded`.

## What Changes

- Classify final balancer selection failures into canonical public errors before they leave the proxy.
- Expose waitable cooldown/reset conditions as HTTP `429` with `rate_limit_exceeded` and retry metadata.
- Expose generic temporary capacity exhaustion as HTTP `503` with `service_unavailable`.
- Keep internal selection state and logs free to retain more specific internal reasons if needed.

## Impact

- Affected code: `app/modules/proxy/load_balancer.py`, `app/modules/proxy/service.py`
- Affected APIs: `/v1/responses`, `/backend-api/codex/responses`, bridge startup errors, websocket connect failures, and adjacent non-streaming proxy surfaces that depend on account selection.
- Compatibility impact: public transient balancer errors become standard retryable API contracts instead of `no_accounts`.
