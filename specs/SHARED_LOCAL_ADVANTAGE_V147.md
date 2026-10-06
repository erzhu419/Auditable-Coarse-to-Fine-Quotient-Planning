# V147: one shared local representation under fixed learning and control

V146 found unstable eight-suffix labels and weak training-feature support.
Test one predetermined representation change using the existing experience.
No feature search, additional labels, changed target or gate tuning occurs.

For each cell, c is the number of boundary coordinates:0 interior,1 edge,
2 corner. Emit unary address11*c+rank, including rank0 (16 occurrences).
For each of the24 horizontal/vertical adjacent pairs, let u=11*c_i+rank_i
and v=11*c_j+rank_j. Emit33+33*min(u,v)+max(u,v). This ties undirected
pair parameters across positions while retaining endpoint boundary classes.
There are40 feature occurrences per board. Keep multiplicities and subtract
the H2 afterstate features from the H1 afterstate features. There are no
diagonals, longer tuples, rank clipping, hand-set utility weights or bias.

SHARED reuses zero-initialized three-component normalized LMS with alpha=.1.
For each of four histories and two queries, execute32 ordered passes through
old16 TRAIN roots then new16 TRAIN roots, exactly the V145 UPDATED schedule.
Keep the same averaged eight-suffix targets and exact immediate-score
subtraction. Replicas0..3 train;4..7 remain diagnostic validation. Load the
retained V145 UPDATED model unchanged as the six-cell representation control.
Each SHARED model attempts1,024 updates; all eight fits finish and freeze
before new control. Zero-feature examples remain counted, with no update.

ZERO uses the same shared-feature selector with frozen zero weights, without
training. It separates learned-weight benefits from the immediate-reward gate.
Run H2, ZERO, UPDATED and SHARED on256 fresh games, four histories × two queries ×
eight replicas × four methods. Reuse unchanged H2/H1_CONT candidates and the
V144 strict-positive recomposed advantage gate. Ties, same actions and pairs
with an immediate-goal afterstate retain H2. Charge both candidate planners
even on fallback. BASE=147*100000000. Environment seed=BASE+90000000+
life*100000+replica; H1 seed=BASE+80000000+life*1000000+replica*10000+step.
Use p_four=.1, two initial spawns, goal rank11 and the V115 2,000-action cap.
Retain cutoff costs and utility=None; do not replace games or refit models.

Compare SHARED−H2, SHARED−ZERO, SHARED−UPDATED, UPDATED−H2 and ZERO−H2 by paired replicas, then
history means and four-history mean/signs. Preserve complete game traces.
Report OLD/NEW training and validation errors, zero-feature differences,
training support/projection and lost distinctions relative to UPDATED.
Geometry improvement alone is not strategic improvement. The inspected
validation sets cannot select a representation; new games assess its effect.

Keep inherited interaction and analysis costs by explicit artifact references.
New training-label interaction is zero. Charge the8,192 new update attempts,
effective updates, feature work, storage, loads, both planners, actual game
transitions and independent analysis separately. Per board, feature work is
16 unary and48 edge endpoint rank accesses,40 emitted occurrences; charge
the initial16-rank board conversion separately. Freeze protocol and executable
sources before fitting, retain all final models before control, and verify
features/weights/gate/trajectories with independent calculations. Four histories
support an exploratory comparison, not a significance or generality claim.
U005 stays FAIL and U006 stays unstarted.
