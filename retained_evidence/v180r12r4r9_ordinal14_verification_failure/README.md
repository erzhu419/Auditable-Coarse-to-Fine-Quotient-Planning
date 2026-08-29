# V180r12r4r9 Ordinal 14 verification failure freeze

This directory retains the exact Ordinal 14 production artifacts copied from
`jtl110gpu2` after its one-shot verification identity was consumed.

The measurement itself completed successfully: nine `CounterRecord` objects,
nine path receipts, one `WorkVector`, one eight-axis `ComparisonVector`, and one
native-zero attestation were published.  The producer-free verifier then wrote
byte-identical verification and replay payloads with counter completeness
`PASS`.

The encompassing verification launch nevertheless failed after the verifier
returned.  The shared bootstrap required the six Git processes used by the
measurement authority replay. Static control-flow diagnosis shows that the
verification runner has no subprocess path, but the private observed-process
count was not serialized in a formal artifact.
Consequently the bootstrap raised the exact secondary observation
`V180r12r4 six-process Git contract was incomplete`, no inner or outer
verification success receipt was issued, and the identity cannot be retried.

`raw/post_failure_runner_git_contract_observation.json` separates:

- successful measurement and producer-free payload properties;
- verification systemd-unit ownership at T1;
- the failed full runner/launcher conformance;
- the one formal completeness mismatch and the exact cause;
- a separately labelled seven-row static control-flow inference.

The successor repair makes the audit target-aware: measurement still requires
the six-process source replay, verification requires zero subprocesses, and any
verification subprocess remains a rejected foreign launch.
