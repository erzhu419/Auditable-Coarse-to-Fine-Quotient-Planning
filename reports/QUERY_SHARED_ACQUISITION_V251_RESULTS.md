# V251: focused evidence gives a small saving; return certification remains unresolved

**Complete: 648 targets and 4,680 auxiliary queries; independent audit valid=true, zero failures. The frozen stage passes 10/11 conditions.** Return quality remains below 54/72.

| Arm | Late-B queries /36 | Return queries /72 | Joint /216 | Full charged observations | Model CPU seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| UNIFORM_SHARED | 33 | 48 | 141 | 48,384 | 2,344.02 |
| QUERY_FIXED | 34 | 48 | 142 | 48,112 | 4,260.68 |
| QUERY_SHARED | 34 | 48 | 142 | 48,112 | 4,257.54 |

Under the [frozen protocol](../specs/QUERY_SHARED_ACQUISITION_V251.md), allocation saves **272 observations (0.56%)**, with four B gains and three losses. Model CPU increases **81.63%**. Stopping never activates: all A phases consume 3,072 samples, release zero, and both QUERY arms have identical216-target histories.

The [diagnosis](v251_runtime_tmp/shared_acquisition_diagnosis.json) finds zero true query regret and resolved execution certificates in all24 failed returns/arm; they still execute WAIT. All24 SHORT-to-RETRY goal blockers persist despite2,864–3,072 focused samples versus uniform1,024. QUERY failures stop at the whole budget in16 cases and the member cap in eight.

**Next:** end quota tuning. Compare complete SHORT-to-RETRY regions with R fixed/free at these frozen endpoints to separate row information from joint uncertainty and proof conservatism before choosing acquisition/model changes.

**17 tests passed**, including one repaired audit interface test. Independent replay checks40,037 profiles. Producer/audit exit0; clipping warnings retained, audit stderr0. [Summary](query_shared_acquisition_v251/summary.json), [audit](query_shared_acquisition_v251/analysis.json), [verification](v251_runtime_tmp/verification_summary.json).

Limitations: one fresh cohort on three known layouts with declared type/change/correspondence information; a fixed acquisition rule, not general strategic learning. Original Gate and U006 remain unchanged.
