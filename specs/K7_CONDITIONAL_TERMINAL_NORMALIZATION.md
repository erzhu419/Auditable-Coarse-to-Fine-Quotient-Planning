# K7 conditional terminal normalization

Contract `2.0.40` / V0-110B-2E-29 consumes the exact Contract-2.0.33
all-path profile and closes the semantic ambiguity of its 14
`PROFILE_EXTENSION_REQUIRED` V075 rows. It is a conditional normalization
profile, not a terminal authority.

## Exact source partition

| Family | Rows | Rule |
|---|---:|---|
| successful total lift | 2 | Retained route provenance selects only the candidate `ABSTRACT_CERTIFIED`, `LOCAL_GROUND_RECOVERY` or `FULL_GROUND_FALLBACK` target. |
| route continuation | 7 | Risk/regret/statistical miss, no-frontier, policy-abort and construction-control statuses remain nonterminal until later evidence. |
| process failure | 2 | `PROTOCOL_FAILURE` is a candidate only when both process-failure and protocol evidence are retained. |
| timeout | 2 | Preregistered cap plus trusted replay selects the candidate attempt- or fallback-cap code; without that pair the candidate is `PROTOCOL_FAILURE`. |
| generic total-lift noncertificate | 1 | One typed cause-evidence binding must select an exact FQ9 noncertificate code. |

Every rule binds the original source module, enum class, member name, member
value and Contract-2.0.33 reason code. The source all-path profile ID and its
exact V075 inventory ID are also bound. A new or changed member has no class
default and requires a profile revision.

## Authority boundary

A normalization result may identify a candidate FQ9 class/code, but always
records:

```text
normalization_only = true
terminal_artifact_issued = false
downstream_semantic_terminal_authority_required = true
```

The referenced provenance, process/protocol, cap/replay or typed-cause
evidence must still be verified by the appropriate downstream semantic
authority. The profile cannot issue a terminal, certificate, CounterRecord,
WorkVector, ComparisonVector or occurrence closure.

The producer returns a fresh authority object on every freeze; independent
document replay reconstructs the exact 14-row table and its central
domain-separated identities. Unknown members, changed values, row reordering,
cross-family evidence, incomplete evidence and re-signed target mutations fail
closed.

All locks remain unchanged:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```
