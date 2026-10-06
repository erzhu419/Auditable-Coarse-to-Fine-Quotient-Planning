# V248: retained evidence contains bad kernels

**Diagnosis complete; independent audit valid=true, zero failures.** All 48 frozen endpoints and 96 candidate states are retained. The original SHORT decisions cannot reach 54/72 using their unchanged terminal regions alone.

| Arm | RETAINED full-region bad kernels /24 | R_CENTERED full-region bad kernels /24 | Original-decision certificate ceiling /72 |
| --- | ---: | ---: | ---: |
| ONE_WAY | 23 | 21 | 49 |
| JOINT_PREDICTION | 24 | 24 | 48 |

The [frozen protocol](../specs/ENDPOINT_REGIONS_V248.md) checks all eight query families and nine original source/pool/member events. There are 92 full-region bad kernels, four rejected points and zero unknowns. All rejections occur in ONE_WAY, life 1: RETAINED at target 70; R_CENTERED at 66, 67 and 70.

The [mechanism diagnosis](v248_runtime_tmp/mechanism_diagnosis.json) finds 45 full-region bad kernels with RETRY TV exactly zero. Mean SHORT/DETOUR TV is 0.02388/0.01576 in ONE_WAY and 0.02327/0.01783 in JOINT_PREDICTION. Lower SHORT delivery and higher DETOUR delivery retain a strict 0.050001 bad gap: S/D ambiguity remains inside the complete regions.

Next compare shared S/D acquisition before return, delayed acquisition of the **same quota and cost**, and strong REBUILD on fresh complete lifecycles. Charge probes within the full budget; retain source anchors, confidence events and target caps. Measure timing benefits and total acquisition/model cost.

Validation: **17 tests passed**; producer/audit each ran once (1,114.63/373.88 s), with 9,711 checks and 24 captured sources. Both stderr files are empty. New observations/optimizations/certificates/truth scoring are zero; retained charges remain 46,672 per arm. [Summary](endpoint_regions_v248/summary.json), [audit](endpoint_regions_v248/analysis.json), [verification](v248_runtime_tmp/verification_summary.json).

Limitations: ceilings concern original SHORT decisions, regions and terminal times. Rejected points do not prove an empty bad null; empirical RETRY is not truth. New evidence or decisions may change results. The next experiment qualifies known structure, not general strategic learning. Original Gate/U006 status is unchanged.
