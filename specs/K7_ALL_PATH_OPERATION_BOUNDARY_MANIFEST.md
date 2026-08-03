# K7 all-path operation-boundary manifest

Contract `2.0.36` / V0-110B-2E-25 freezes where future native accounting must
attach to the existing production code. Ten real AST call sites cover all six
required families:

```text
PREOPEN/common
ABSTRACT
LOCAL
FALLBACK
REBUILD
VERIFICATION/terminal
```

Each site binds complete module bytes and SHA-256, the enclosing qualified
symbol and AST digest, exact call target/cardinality/location/AST digest,
stage, route and terminal applicability, accounting families and required
evidence roles. The manifest consumes the contract-2.0.33 all-path profile and
uses centrally registered role-separated content domains.

Independent replay accepts only the exact six-member source archive. Missing,
extra, non-byte, syntax-invalid or changed source and every symbol/call-site or
manifest mutation return a typed blocker. A blocker cannot be interpreted as
zero, an executed route or an accounting record.

This is a catalogue only: `execution_performed=false` and zero CounterRecords,
WorkVectors and ComparisonVectors are issued. The successor must instrument
these frozen boundaries and produce route-native evidence before Counter
Completeness can run.
