## 1. Public error normalization

- [ ] 1.1 Classify final balancer exhaustion into canonical public transient errors without exposing `no_accounts` on public API surfaces.
- [ ] 1.2 Map waitable cooldown/reset conditions to HTTP `429` with `rate_limit_exceeded` and retry metadata.
- [ ] 1.3 Map generic temporary capacity exhaustion to HTTP `503` with `service_unavailable`.

## 2. Regression coverage

- [ ] 2.1 Update proxy integration coverage to assert canonical public transient codes instead of `no_accounts`.
- [ ] 2.2 Add focused unit coverage for balancer public error classification.

## 3. Verification

- [ ] 3.1 Run focused proxy unit/integration tests covering responses and bridge startup errors.
- [ ] 3.2 Run diagnostics on changed files and confirm no new issues.
