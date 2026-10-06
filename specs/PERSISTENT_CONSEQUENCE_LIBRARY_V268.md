# V268 two-step composable consequence protocol

V267 held-out weights stayed inside the same exact action regions. V268 tests
the route graph's only genuine two-stage branch: a fixed-index pair of one
`DETOUR_PASS` draw and one `RECOVERY_RETRY` draw. A pair is recorded as
`DETOUR_DELIVERY`, `DETOUR_LOST`, `RECOVERY_RETRY_DELIVERY` or
`RECOVERY_RETRY_LOST`; Jeffreys posteriors over those four joint categories
directly produce the `DETOUR_RETRY` consequence vector. `SHORT_PASS` remains a
separate marginal row. This avoids multiplying two separately estimated
marginals while keeping the route semantics explicit.

The paired V267 streams, seeds, and `48 fit + 16 audit` rows per operator are
unchanged. `RESET_MARGINAL` is the V266 reset control. `LOCKED_MARGINAL` uses the V266
action-agreement assignment. `LOCKED_COMPOSED` uses exactly the same module IDs
and assignment reasons while learning the joint pair representation in
parallel. The audit suffix is never merged. Pair counts, policy correctness,
action-set agreement and exact regret are retained.

The simulator's retry law is independent of the preceding detour outcome, so
this is a diagnostic of finite-sample representation noise, not a claim that
the joint pair contains new environmental structure. If it does not improve
the matched marginal control, the joint-pair route closes.

This is an exploratory representation diagnostic. It does not reopen the
original Gate or start U006.
