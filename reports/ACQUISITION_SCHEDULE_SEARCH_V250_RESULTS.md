# V250: no feasible witness among eight acquisition schedules

**Complete: 1,728 decisions; independent audit valid=true, zero failures.** No candidate reaches both frozen quality targets (late-B27/36, return54/72). No schedule is adopted.

| Candidate | Late-B queries /36 | Return queries /72 | Joint /216 | Full charged observations |
| --- | ---: | ---: | ---: | ---: |
| SD128_B0 | 23 | 48 | 131 | 47,824 |
| SD128_B384 | 23 | 48 | 134 | 47,904 |
| SD512_B0 | 23 | 48 | 132 | 48,384 |
| SD512_B384 | 27 | 48 | 140 | 48,384 |
| SD1024_B0 | 25 | 48 | 127 | 48,384 |
| SD1024_B384 | 21 | 48 | 122 | 48,384 |
| ALL512_B0 | 23 | 48 | 132 | 48,384 |
| ALL512_B384 | 27 | 48 | 141 | 48,384 |

The [protocol](../specs/ACQUISITION_SCHEDULE_SEARCH_V250.md) moves shared A evidence before its B snapshot and optionally supplements B's changed row, with unchanged certifiers and budgets. Two plans reach late-B27 at 592 more observations than V249.

The [diagnosis](v250_runtime_tmp/schedule_diagnosis.json) finds **zero true regret for uncertified queries in all 192 failed returns**, concentrated in one type/life. Twenty SD128_B0 failures reach member caps with life budget remaining; larger quotas exhaust budgets. Next allocate shared evidence jointly to unresolved current/future queries and stop at certification. Uniform quota increases stop here.

**16 tests passed once**, with full independent replay. Search pays 275,440 new observations plus fully charged reused sources and uses 12,205.64 model CPU seconds. Producer/audit exit0; producer clipping warnings retained, audit stderr0. [Summary](acquisition_schedule_search_v250/summary.json), [audit](acquisition_schedule_search_v250/analysis.json), [verification](v250_runtime_tmp/verification_summary.json).

Limitations: eight plans on three previously seen layouts, not a global impossibility result or general learning evidence. Zero regret is posthoc truth evaluation; uncertified targets still fall back to WAIT. Original Gate and U006 remain unchanged.
