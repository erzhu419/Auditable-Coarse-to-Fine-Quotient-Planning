# K7 direct-fallback exact-infeasibility readiness

Contract `2.0.39` / V0-110B-2E-28 tests the genuine canonical G2048 H1 direct
fallback against the durable exact proof. The fallback returns
`INFEASIBLE_CERTIFIED`, and its query identity exactly matches the independently
verified proof. This is still insufficient for a formal K7 occurrence.

The current fallback retains only a 42-leaf V1 WorkVector. It lacks the 202
production-native CounterRecords, nine shared-resource receipts, route decision
and upper chain, route-specific materializer, independent complete-bundle
verifier, exact terminal authority and denominator-preserving occurrence
closure. The durable proof is evaluation-lane evidence and cannot replace the
operational search/accounting chain.

The domain-separated readiness artifact therefore has only `BLOCKED` outcome
and cannot mint a vector, terminal or certificate. Missing execution, identity
mismatch, invalid proof, non-infeasible result and `CAP_EXHAUSTED` have separate
blockers; cap exhaustion remains a noncertificate.
