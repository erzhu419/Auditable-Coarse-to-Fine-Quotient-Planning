# V136: policy-conditioned Bellman consequences from frozen H2 teachers

V135 establishes a positive planning contribution with frozen scalar values.
The next object is reusable reward and terminal-event knowledge, conditioned
on an explicit subsequent policy. Keep all four histories, both SINGLE and
CAPACITY representations, and each representation's risk1/risk8 H2 teachers.
Evaluate each teacher separately; there is no cross-teacher selector or GPI.

## Fixed policy and joint learning

Each of16 teachers is the unchanged V135 H2 planner on the V134 final524288
leaf. Its identified spawn law remains the frozen empirical distribution;
the actual environment has p4=.1, two initial spawns and goal rank11. The
teacher's parameters, query and behavior do not learn or receive evaluation
query weights. Neither V135 evaluation outcomes nor its trajectories enter
training. Source checkpoints are referenced in place.

For every non-goal afterstate y, learn future normalized score R(y) and
success S(y)=sigmoid(z(y)); failure is 1-S. Both use the original32 feature
occurrences (including CAPACITY's existing local bank selection). Copy the
teacher's raw scalar table into the reward table; initialize the logit table
to zero, so S0=.5. Set bR=teacher.offset+[f0-(f0+g0)/2]. Here f0=g0, so the
bracket is exactly zero. R=Rraw+bR. This is an initial assumption, not an
estimated H2 success rate. Each student has twice its teacher leaf's table
parameters. Source acquisition and copying costs remain explicit.

At a newly observed decision state, choose the frozen teacher action ONCE.
Read both student predictions at that chosen afterstate before updating the
previous pending afterstate. For its actual score r, the joint target is:

    target_R = r/2048 + R(chosen_afterstate)
    target_S = S(chosen_afterstate)

Winning afterstates are analytic (R,S)=(0,1); the preceding pending update
still includes the winning action's score. A terminal loss settles the last
pending item to (0,0). Goal afterstates are never indexed or trained. Use one
pre-update error per head, alpha=.0025 and occurrence multiplicities m:

    raw_target_R = target_R - bR
    reward_weight[i] += alpha * (raw_target_R - Rraw_before) * m[i]
    logit_weight[i]  += alpha * (target_S - S_before) * m[i]

The event update is the soft-label Bernoulli cross-entropy semigradient;
predictions remain bounded through the sigmoid. Neither head selects its own
continuation action. Retain budget pauses with the same board, RNG and
pending item. A true2000-action cutoff remains censored and drops its pending
update, without constructing a terminal-failure label.

Every teacher supplies524288 new actual transitions, for8,388,608 total.
Checkpoints are0 and524288 only, with no intermediate evaluation or selection.
All training finishes and freezes before any evaluation or diagnostics.
BASE=136*100000000. Training seed is BASE+10000000+life*2000000+
representation_index*1000000+teacher_query_index*500000+episode. The order is
SINGLE/CAPACITY and risk1/risk8. The algorithm is fixed for every episode.

## Query recomposition and unchanged H2 planning

For query q=(1,fq,gq), combine the same policy's joint vector as
score/2048+R-fq+(fq+gq)S. Preserve the original source addition order:

    A = ((score/2048 + Rraw) + failure_shift0) + success_shift0
    Qq = A + (f0+g0)*(S-.5) + (f0-fq) + ((fq+gq)-(f0+g0))*S

Thus the zero-training own-query readout exactly recovers the teacher leaf's
action values and lexical ties. Analytic goals use score/2048+gq. Use the
same H2 structure and frozen learned spawn probabilities as V135; at every
candidate, select by the joint scalarized vector, then accumulate reward and
success from that same selected branch. The root score is included once.
Retain Q using the source arithmetic, along with its numerically equivalent
joint vector. Clamp only the reported H2 success expectation to[0,1] to
remove summation roundoff at the probability boundary; the independently
accumulated Q, chosen branches and training targets are unchanged. Replanning
does not change the policy label of a learned head.

Each teacher is evaluated on its own original query plus two queries absent
from this training: risk2=(1,2,2) and risk6=(1,6,6). Methods are TEACHER (the
fixed original H2 behavior, scored using evaluation weights), INITIAL_H2
(frozen initialized joint heads), and LEARNED_H2 (final joint heads). Original
scalar teachers remain tied to their original queries.

## Evaluation roster and evidence

Use16 fresh games per history/representation/teacher/query/method, with seed
BASE+90000000+life*100000+replica shared across methods and queries. Run each
teacher's actual behavior once and rescore the same trace for its three
queries. On those games, verify every root legal value and selected action
of the zero-training own-query readout against TEACHER, then alias that
INITIAL_H2 comparison. All other student games run physically.

This gives256 physical teacher games,512 INITIAL_H2 new-query games and768
LEARNED_H2 games:1536 physical games and2304 logical records. Keep every
terminal and cutoff. A cutoff retains costs and suppresses its affected
terminal-return comparison. No replacement games or favorable-seed selection.

For each representation/teacher/query separately, compare LEARNED_H2 with
INITIAL_H2 and with that fixed TEACHER. Own-query comparisons measure retained
control; new queries measure reuse. Pair by evaluation seed, average within
each history and then equally over all four histories. Never pool teacher
identities or form an ex-post best-teacher controller.

Reuse the same256 held-out teacher trajectories for consequence diagnostics:
predict with initial and final joint heads on each non-goal afterstate, then
compare R with its recorded future-score suffix and S with its actual final
success. Report reward MSE, success Brier and original-query recomposed error,
first per game and then per history. Censored trajectories do not supply
terminal labels. Diagnostics run after training, incur prediction costs and
never feed back into learning. No extra environment sampling is needed.

## Validation and accounting

Finite tests cover joint Bellman target timing, terminal reward/event
boundaries, multiplicity updates, bounded success, exact zero own-query
recovery, contextual features, save/load, budget continuation and native H2
agreement with independent enumeration. Runner tests use mocked games.
Independent analysis reconciles numeric targets, frozen teachers, actual
budgets, source probability binding, query/method rosters and full-game
returns. It reads diagnostic predictions and labels without retraining.

Charge teacher planning, student prediction/update, initialization/copy/save/
load, zero equivalence checks and diagnostics separately. Enumerated model
outcomes are model work, not new real observations or stochastic samples.
All attempts, logs, builds and intermediate files stay inside this research
worktree. Preserve previous negative results; U005 remains FAIL and U006
remains unstarted.

## Limitations

These heads estimate consequences of fixed H2 teachers, while executing a
recomposed controller can change the visited states and continuation policy.
One-step bootstrapping, shared features and frozen spawn estimates can still
introduce errors. Bounded complementary probabilities do not establish
accurate consequences or improved control. This tests query reuse within the
existing fixed dynamics, not autonomous structure revision or compression.
