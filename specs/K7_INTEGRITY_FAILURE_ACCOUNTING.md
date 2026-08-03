# K7 integrity-failure accounting

Contract `2.0.35` / V0-110B-2E-24 closes the FQ9 integrity-failure recipe
without constructing an invalid WorkVector. An externally anchored expected
artifact identity is compared with the canonical bytes actually read. The
read receipt retains exact bytes, byte count, SHA-256, content domain and the
typed mismatch reasons.

All 202 V6 required leaves are emitted as observed CounterRecords through the
failure cutoff, including explicit native zeros. The actual read and hash
work are charged once through `io.read_bytes` and
`common.hash_invocations`; diagnostic `integrity.bytes_hashed` remains outside
the cost vector. The resulting WorkVector and eight-axis ComparisonVector are
valid last-prefix accounting artifacts.

The only terminal is:

```text
ROUTE_ATTEMPT
ATTEMPT_CLOSURE_NONCERTIFICATE
INTEGRITY_FAILURE
```

Non-contiguous protocol events, post-cutoff activity, counter metadata errors,
route-family violations and reconciliation failures are protocol errors and
cannot be relabelled as integrity failures. Matched bytes cannot issue the
terminal. The independent byte verifier reconstructs the expected/actual
identity violation, cutoff, all records, projection and terminal without
calling the producer; fully re-signed anchor, counter and terminal mutations
fail.

This contract closes one attempt-terminal family only. It does not issue a
plan or infeasibility certificate, close a logical occurrence, establish
campaign coverage or unlock a Gate.
