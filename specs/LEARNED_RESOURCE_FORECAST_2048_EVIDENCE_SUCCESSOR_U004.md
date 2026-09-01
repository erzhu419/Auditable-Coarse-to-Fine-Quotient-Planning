# Learned Resource Forecast 2048 Evidence Successor U004

## Purpose

U002 completed 144/144 policy-training jobs and materialized all 432 registered
snapshots.  Its evidence launcher then consumed the U002 evidence-dispatch
identity but failed before worker 0 was dispatched.  No U002 evidence job,
status stream, log, or lane artifact exists.

U003 prepared and deployed a protocol and manifest but stopped before its
history scan and before dispatch identity consumption.  It is ineligible
because it declared a fresh model-evaluation tape that its evidence-only path
would never execute or read.  No U003 evidence job or artifact exists, and
U003 remains untouched as abandoned design evidence.

U004 is therefore a fresh fixed-policy evidence successor.  It is not a
retry of U002 evidence and it is not a new training campaign.  It conditions on
the complete U002 policy population.  Its trajectory, label, and exact-eight-
action probe tapes are fresh.  Its model-evaluation tape and measurements are
explicitly inherited read-only from U002; U004 neither re-runs nor reads that
tape in its evidence phase.

## Two authorities

The read-only predecessor authority is fixed to:

- U002 source commit `84b021304712cfa7db9e81b4a5e42e541704ba7f`;
- U002 protocol `399e7af3e69d7b39189cd82d428a1d339ff6fe6be86d189410b113c3a320858f`;
- 144 completed U002 training IDs, 144 training JSON documents, 432 model
  snapshots, six completed training streams, six training logs, and the
  completed U002 training dispatch;
- the U002 model-evaluation tape prefix and the measurements already recorded
  in those U002 training documents, as read-only predecessor evidence;
- the original six-worker seed, host, GPU, arm, and checkpoint ownership.

The fresh successor authority contains:

- ordinal 4, attempt 1 identity
  `acfqp-learned-resource-forecast-2048-pilot-u004-ordinal4-attempt1`;
- 432 new evidence execution IDs;
- 432 label JSON, 432 probe JSON, 288 trajectory JSON, and 288 trajectory NPZ
  artifacts under a separate U004 output root;
- six new evidence status streams, six evidence logs, and one new dispatch;
- U004 analysis, independent verification, and retention outputs.

Every U004 evidence lane document records its U004 measurement protocol, source and
execution ID and, separately, the U002 protocol, source, training execution ID,
pilot identity, and original snapshot path.  U002 artifacts are never renamed,
rewritten, or described as U004 training.  Model-evaluation provenance remains
U002; trajectory, label, probe, encoder, analysis, and retention provenance is
U004.

The failed U002 evidence dispatch and abandoned pre-dispatch U003 design remain
retained history.  They are explicitly ineligible for prerequisites and
contribute no job or artifact to the Gate.

## Frozen scientific contract

The 32/16 train/test split, all 432 policy players, three representations,
encoder architecture and epochs, player-shuffled control, logistic classifier,
20,000 paired base-seed cluster bootstrap, and all six Gate components are
unchanged from U002.  No player is selected by training reward or any observed
measurement outcome.

A PASS is an exploratory feasibility signal conditional on the fixed U002
policy population.  It does not establish robustness to new training seeds.
Only a later full successor with new training randomness may make that stronger
claim.

## Execution boundary

All six global preflights must validate the exact U002 training and model-
evaluation authority, the
clean U004 source/runtime, CPU Adam construction, absent U004 output roots, and
the exact zero-hit U004 history receipt for 432 evidence IDs, three fresh tape
roots, and five fresh artifact roots before the U004 dispatch file is
created.  SSH preflight and dispatch disable `ControlMaster` and `ControlPath`.
No consumed dispatch, worker, job, analysis, verification, or retention
identity may be retried.

Gathering is server-to-server transport, not job execution.  It copies remote
U002 training artifacts into the same central U002 provenance tree and remote
U004 evidence artifacts into the separate central U004 tree.  Postprocessing
validates the two trees independently before fitting encoders, encoding probes,
opening labels, evaluating the unchanged Gate, independently replaying the
result, and retaining the exact inventory.
