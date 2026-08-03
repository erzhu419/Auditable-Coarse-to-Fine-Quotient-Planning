# K7 protocol-failure accounting negative control

Contract `2.0.37` / V0-110B-2E-26 exercises the FQ13 failure semantics with
the same `ProtocolSequenceProfileV1`, `AccessEventLogV1` and semantic replay as
the production runner. The canonical negative control requests `KERNEL_STEP`
before route-decision freeze. The controller rejects it, so detection work is
charged while the rejected operation is not counted as a kernel transition.

The fixture retains all 202 observed V6 CounterRecords, an
`ABSTRACT_FAILED_PREFIX` WorkVector and exact eight-axis ComparisonVector. Its
only terminal is:

```text
ROUTE_ATTEMPT
ATTEMPT_CLOSURE_NONCERTIFICATE
PROTOCOL_FAILURE
```

The independent byte verifier reconstructs the production protocol profile,
first semantic violation, event sequence, complete accounting and terminal.
Fully re-signed event, sequence, counter and classification attacks fail, and
the result cannot become integrity failure, cap exhaustion, infeasibility or a
plan certificate.

The correct production runner has not emitted this violation. Therefore every
artifact carries `NO_PRODUCTION_PREDECISION_VIOLATION_OBSERVED` and
`production_violation_claimed=false`; the negative control cannot be used as a
production occurrence. This validates the failure mechanism but leaves real
all-path production coverage open.
