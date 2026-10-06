# V123: persistence in observed-context routing

V122's free reactivation of old modules allowed short noisy blocks to change
their identity. Freeze one routing change before replaying its retained data.
The original V122 outcome and U005 FAIL remain; U006 remains unstarted.

## One fixed change

Keep V115's Beta(1,1) initialization, 256 source observations, 64-observation
blocks, predictive likelihoods, tie handling and chosen-module updates.
Subtract log(64) from each INACTIVE existing module's block score. The active
module is unpenalized. NEW keeps its original, single log(64) penalty. These
are relative transition weights 64 for staying and 1 for each alternative;
they are not a fixed global switch probability when alternatives multiply.
There is no parameter search, confirmation buffer, module pruning, oracle
boundary signal or posterior-statistics freeze. A wrong assignment can still
update the wrong module; this experiment measures whether persistence suffices.

## Fixed data and causal comparison

Replay all four V122 histories and both separately trained queries. Initialize
each algorithm from that stream's exact 256 V120 ranks in the V122 source
capsule. Then consume its retained BANK training ranks in recorded order:
524288 observations in B, followed by 524288 in A_RETURN. No evaluation data,
new environment samples, value weights, TD updates or generated model samples.
Keep memory across games and the phase boundary. Methods are unchanged V115
LIBRARY (BASELINE) and the single new rule (PERSISTENT). The router receives
only each rank, never phase, probability, query or life. Predictions and active
IDs are measured BEFORE consuming the next rank.

Require baseline events, pre-action bank IDs and both final router payloads
to equal the retained V122 records exactly. A failure means this replay is
invalid, not evidence about the persistence rule. Store paired 64-rank block
sufficient statistics and events rather than copying boards or model files.
Both probabilities are constant within a completed block, so block counts
give the exact prequential Bernoulli log loss and Brier score.

## Outcomes and decision

Primary: original source module's posterior change during B, source-module
action fraction in each phase, number of modules and switches, and delay to
first non-source activation in B / source reactivation on return. Also report
the last incorrectly routed action index and later switches: an early lucky
activation is not stable recovery. For this diagnostic only, source ID0 is the
desired identity on return; any nonzero ID is new-context use in B. This does
not assign a true regime to a new module inside the learner.
Activation delay counts consumed observations. Last wrong action uses a
one-based phase-local action index; zero means no incorrectly routed action.

Report mean prequential log loss, Brier score and absolute error to the harness
p4 (.5 in B, .1 on return), plus every life/query result. Phase names and true
p4 are used by the evaluator only. The two queries are not eight independent
source histories. Judge whether old-identity preservation and return recovery
improve consistently without sacrificing change detection; no significance or
new scientific Gate is defined. If the mechanism is still unstable, retain
that result and diagnose the first remaining wrong assignment rather than tune
this replay. If stable enough to proceed, the next experiment must separately
test value learning: router stability alone cannot establish score improvement.

Charge the 8388608 retained training ranks and 2048 retained warmup ranks as
reused data, with two algorithms' processing work separately. Count block
predictive scores, source read bytes, output bytes and execution seconds. The
original acquisition costs remain inherited; do not count reading a rank as
acquiring a new transition. No model weight load/copy/save. Save source and
protocol before one main execution; tests use synthetic ranks and project-local
temporary files. No reruns or outcome-dependent extensions.

## Limitations

These are fixed behavior traces collected by V122, not trajectories generated
by the new router's policy. Boundaries align with 64-observation blocks. There
is one large change and return, not general nonstationarity. Even correct
eventual routing leaves actions and possible TD updates before detection in
the previous bank; a later value-learning test must account for that delay.
