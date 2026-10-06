# V252: retained information-axis diagnosis

V251's **10/11 stage result and actual return count of 48/72 remain unchanged**.
V252 diagnoses the 24 failed SHORT-versus-RETRY return endpoints in each of
UNIFORM_SHARED and QUERY_SHARED, using three frozen candidate rules per endpoint.
All 48 endpoints and 144 classifications complete without new observations.

| Arm | Retained full-region bad endpoints | R-centered full-region bad endpoints | S/D-centered full-region bad endpoints | Distinct bad endpoints | Same-region certificate ceiling |
|---|---:|---:|---:|---:|---:|
| UNIFORM_SHARED | 24 | 24 | 0 | 24 | 48/72 |
| QUERY_SHARED | 19 | 6 | 0 | 19 | 53/72 |

QUERY_SHARED still admits strict bad kernels at **19 distinct endpoints** through
all eight original query regions and all nine original execution events. Thus
proof improvements at these terminal evidence prefixes, within these original
regions, cannot reach the frozen requirement of 54/72. The ceiling of 53 is an
upper bound, not an achieved certificate count.

With R fixed at its empirical frequency, six QUERY_SHARED endpoints remain bad:
S/D uncertainty still matters. All 48 analytic candidates with S/D fixed at their
empirical rows are rejected by the canonical query region and the source/pool
R events. This fixed candidate test does not establish that acquiring R alone
would resolve the remaining failures.

Twenty focused tests pass once. Independent audit is valid with zero failures
(17,702 checks); producer and auditor both exit 0 with zero-byte stderr.
Actual wall times are 1,851.07 s and 850.16 s. See [verification](v252_runtime_tmp/verification_summary.json)
and [independent analysis](information_axes_v252/analysis.json).

Next freeze all 72 return targets per arm at their own chronological endpoints,
and compare ONE_WAY with the existing TWO_WAY evidence view. V251 retained
compatible native B evidence; QUERY_SHARED life1's failed type has 1,648 paid
R observations available. Reuse adds no sampling fee. The changed life2 R row
is incompatible and cannot transfer. This tests whether existing information
can complete certificates before another acquisition change.

Limits: rejecting individual candidates does not prove the bad-kernel space empty.
The ceiling applies only to the retained evidence, regions and decision times.
A snapshot comparison cannot establish a new adaptive policy's stopping or cost
benefit. No query certificates are added; the original scientific Gate remains
FAIL and U006 remains unstarted.
