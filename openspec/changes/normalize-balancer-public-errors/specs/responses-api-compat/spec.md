## ADDED Requirements

### Requirement: Public balancer exhaustion uses canonical transient error codes
When the proxy cannot select an upstream account for a public Responses request because capacity is temporarily unavailable, it MUST expose a canonical public transient error instead of the internal `no_accounts` code.

#### Scenario: generic temporary exhaustion
- **WHEN** account selection fails without a concrete retry window
- **THEN** the public response uses HTTP `503`
- **AND** the error code is `service_unavailable`

#### Scenario: cooldown-backed exhaustion
- **WHEN** account selection fails with a concrete retry delay or reset window
- **THEN** the public response uses HTTP `429`
- **AND** the error code is `rate_limit_exceeded`
- **AND** the error metadata preserves the retry delay
