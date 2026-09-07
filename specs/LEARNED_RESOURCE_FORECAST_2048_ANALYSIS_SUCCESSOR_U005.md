# Learned Resource Forecast 2048 Analysis Successor U005

## Purpose and authority

U004 completed and gathered all 432 registered player-evidence jobs. Its
one-shot postprocess identity was then consumed at `FIT_ENCODERS` by exactly
one missing import: `aligned_forecast_examples_v1`. The U004 status stream and
empty analysis directory remain immutable failure evidence; U004 is never
retried.

U005 ordinal 5 attempt 1 is analysis-only. It reads the completed U002 training
population and gathered U004 trajectory, probe, and label artifacts. It creates
no policy-training ID, evidence ID, tape root, trajectory, probe, label, or new
game measurement. Exact transition replay of existing U004 trajectories is
validation, not a new measurement. The U004 split, representation arms,
encoder, classifier, bootstrap, and provisional Gate are unchanged.
The only numeric-program repair is the one missing import; the remaining
shared analyzer/verifier changes record and validate dual-source provenance.
U005 remains a provisional fixed-policy analysis and authorizes neither a
confirmatory claim nor a new-training-randomness claim.

Every encoder receipt, matrix metadata document, pilot result, independent
verification result, status start row, and successor receipt separates:

- U004 measurement protocol and source; and
- U005 analysis-runtime protocol, source, and execution ID.

Legacy U002/U004 calls that do not supply an explicit analysis runtime retain
their original one-source behavior. The base analyzer and verifier never fake
their clean checkout commit.

## One-shot boundary

Preparation creates only the U005 protocol and manifest. Before analysis, a
three-host zero-hit scan must cover the U005 protocol ID, analysis execution ID,
and fixed analysis/status/retained roots, excluding only the current U005 source
and launch roots. Any existing U005 analysis, status, or retained root consumes
the identity. A partial retained root after a copy failure also consumes it.

The U004 failure boundary is admissible only on `jtl110gpu2` when its exact
four-row failure status exists, its U004 analysis directory exists and is
strictly empty, and its U004 retained directory is absent. Formal U005 analysis
and retention run only on `jtl110gpu2` (`erzhu419-Super-Server`, `cuda:0`).

The history coordinator is WSL because `jtl110gpu2` cannot resolve all three
SSH aliases. The same clean U005 commit must nevertheless be deployed at the
fixed U005 source path on WSL, `jtl110gpu2`, `jtl110gpu`, and `jtl311linux`.
The protocol and manifest are prepared once on `jtl110gpu2`, copied as small
JSON files to WSL and the other two servers, and the WSL-generated small
authority receipt is copied back to `jtl110gpu2`. Remote server copies execute
only the read-only host-scan code; scientific analysis remains gpu2-only.

## Stages and retention

The formal postprocess executes once, in order: fit the two frozen encoders;
encode all probes; evaluate the unchanged provisional Gate; independently
replay evidence, matrices, and statistics; then retain the closure. The
independent-verification document deliberately keeps the unchanged U004 numeric
replay schema, while its embedded runtime fields, successor receipt, and
inventory make it an unambiguous U005-derived artifact.

Retention contains exactly 2,064 entries before its inventory and 2,065
physical files after it:

- 591 U002 training-authority files;
- 1,456 U004 evidence-authority files;
- 2 U004 gather files;
- 1 failed-U002 history file;
- 1 failed-U004 postprocess status;
- 3 U005 authority files;
- 9 U005 analysis files; and
- 1 U005 status file.

The ninth analysis file is `analysis-successor-receipt.json`. A successful
retention claim requires the exclusive inventory with the exact 2,064-entry
set and exact 2,065-file physical tree; the final status row alone is only
`RETENTION_READY` and is not a retention-complete claim.

## Formal workflow

Let `U005_COMMIT` be the final clean implementation commit. First deploy that
same commit to the fixed source path on WSL and all three servers. On gpu2 only,
run:

```bash
env PYTHONPATH=/home/erzhu419/mine_code/acfqp-learned-resource-forecast-2048-pilot-u005-source/src \
  /home/erzhu419/.venvs/scheduleurm-torch-bench/bin/python \
  /home/erzhu419/mine_code/acfqp-learned-resource-forecast-2048-pilot-u005-source/scripts/prepare_learned_resource_forecast_analysis_successor_u005.py \
  --output-root /home/erzhu419/mine_code/acfqp-learned-resource-forecast-2048-pilot-u005-launch
```

Copy only `protocol.json` and `launch-manifest.json` to the identical launch
path on WSL, gpu1, and jtl311. Then run the coordinator on WSL:

```bash
env PYTHONPATH=/home/erzhu419/mine_code/acfqp-learned-resource-forecast-2048-pilot-u005-source/src \
  python3 \
  /home/erzhu419/mine_code/acfqp-learned-resource-forecast-2048-pilot-u005-source/scripts/scan_learned_resource_forecast_analysis_history_u005.py \
  --protocol /home/erzhu419/mine_code/acfqp-learned-resource-forecast-2048-pilot-u005-launch/protocol.json \
  --manifest /home/erzhu419/mine_code/acfqp-learned-resource-forecast-2048-pilot-u005-launch/launch-manifest.json \
  --output /home/erzhu419/mine_code/acfqp-learned-resource-forecast-2048-pilot-u005-launch/authority-scan-receipt.json
```

After copying only that receipt back to gpu2, run the one-shot postprocess there
using the exact paths printed by `--help`. Do not run it until all three fresh
U005 output roots are confirmed absent and the zero-hit receipt validates.
