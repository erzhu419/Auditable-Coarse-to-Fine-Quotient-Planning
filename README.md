# Auditable Coarse-to-Fine Quotient Planning

This repository turns the Laplace-semi-MDP follow-on discussion into a finite,
auditable world-model planning prototype. V0 deliberately targets finite-state,
finite-horizon, fully observable symbolic kernels. Its central objective is to compile
a coverage-bounded ground process once into a reusable abstract planning model (RAPM),
perform repeated multi-step contingent planning primarily in that model, and recover
ground distinctions locally only when an independent value/risk certificate cannot
certify the current plan. Quotients, predicates, CEGAR, and ground solvers are the
construction, repair, audit, and fallback machinery; they are not the endpoint.

Phase 0.5 builds are explicitly coverage-limited. `rho0` belongs to `QuerySpec`; the
builder closes its declared positive-mass support under every legal action and outcome,
records the coverage mode/support hash/state count in `build_id`, and forbids RAPM or
certificate reuse outside that closure. This is an auditable scoped-build contract, not
a claim of unrestricted reuse across arbitrary initial distributions.

Research source, frozen protocols, reports and small execution/audit records are
published through V327. Large new JSON results retain their complete content in
the [compressed report snapshot](reports/publication/v327_snapshot/README.md),
which includes instructions to restore their original paths. Raw trajectories,
NPZ heads, native builds and local environments remain outside this source package.

## Current multi-episode learning research (2026-10-06)

[V327 paired terminal reward/WIN intervention](reports/JOINT_TERMINAL_V327_RESULTS.md)
fails decisively: sole final JOINT_RETURN-minus-own-FIRST is -6.662609,
95% CI [-6.989917, -6.351002]; all sixteen lives decline and both tasks
lose retained ability. JOINT-minus-WIN_ONLY is -5.416848 with a wholly
negative nominal interval. Complete WIN tables are bit-exact between arms;
only JOINT also learns the same suffix reward. Held-out reward MSE and WIN
Brier improve while whole-game utility declines. Fixed-FIRST prediction
improvement has not supplied a policy-improvement mechanism.
FIRST-minus-SOURCE remains positive (+0.965274). Reused V326 FIRST/targets,
two actual FIT and two validation members, 16 passes at alpha .0025,
zero new training raw; all 12,288 new evaluation games terminate naturally.
Forty finite cases and independent verification PASS. Full new CPU is
403.10 seconds, or 6,128.48 with actual SOURCE/V326 once; audit CPU 20.22
is separate. The frozen route is STOP_FIXED_FIRST_TERMINAL_REGRESSION.
This stage closes without another quota/replay/alpha variant. Previous
action-advantage, four-parameter direct strategy and closed-loop value
updates also failed their respective tests. General strategic learning and
equal-budget efficiency remain unestablished. A future structural-learning
proposal must address a concrete decision defect before new experiments;
development version count is not learner capability growth.

[V326 terminal-grounded WIN learning intervention](reports/TERMINAL_WIN_V326_RESULTS.md)
fails its sole whole-game primary: TERMINAL_WIN-minus-own-FIRST is
-0.716429, 95% CI [-0.998638, -0.417674]; thirteen of sixteen new target
learning histories decline. The same-root TERMINAL-minus-BOOTSTRAP contrast
is -0.506544, nominal CI wholly negative. A retention fails, B remains
unresolved; win rate and normalized score both decline. FIRST-minus-SOURCE
remains positive (+1.081489), so the first adaptation is retained.
Both WIN learners share 1,024 query roots/four start members per task/round,
16 fixed-order passes and alpha .0025; complete FIRST reward stays unchanged.
All 262,144 suffixes and 12,288 evaluation games terminate naturally.
New training raw is 114,848,929, including 106,177,627 additional suffix tiles;
terminal and bootstrap economic training raw are 126,183,273 and 20,005,646.
Thirty-six finite cases pass; independent verification PASS checks all new
physical traces, labels, actual heads, effects and costs. Full new CPU is
4,023.55 seconds, or 5,725.39 with SOURCE once; audit CPU 1,384.79 is separate.
Prospective phase seed ranges were widened to avoid actual cross-role reuse
found in V324; its frozen results remain and its interval limitation is
recorded. The retained-suffix joint reward/WIN intervention is completed
in V327 above and yields further supported utility loss; its frozen route
stops fixed-FIRST terminal regression. General strategic learning and
equal-total-raw efficiency remain unestablished.

[V325 fixed-snapshot WIN terminal diagnosis](reports/WIN_TERMINAL_V325_RESULTS.md)
supports a small prediction improvement: sole FINAL_QUERY_WIN-minus-FIRST
Brier change on QUERY roots is -0.00085428, 95% CI
[-0.00092637, -0.00078072], negative in all sixteen lives. Brier improves
about 0.35%; V324's added whole-game utility remains unconfirmed.
Conditional teacher WIN bias on QUERY members is -0.084638 in A and
+0.083722 in B, nominal intervals wholly negative/positive; the pooled
bias nearly cancels. Most root probability bias remains after WIN updates.
All 32,768 new suffixes terminate naturally and pay 13,453,015 new tiles;
no fits, head files or whole-game evaluations are added. Sixty-five finite
cases pass; independent verification PASS checks every new physical trace,
actual probabilities/logits and unchanged reward tables, effects and costs.
Full new CPU is 442.75 seconds, or 3,160.89 with SOURCE/V324 once; audit
CPU 205.85 seconds is separate. This is a fixed-FIRST-policy diagnostic
on existing training roots. Its terminal-grounded learning intervention
is completed in V326 above and yields a supported utility loss; the
equal-total-raw efficiency comparison remains unestablished.

[V324 fresh target WIN-learning histories](reports/WIN_LEARNING_V324_RESULTS.md)
do not confirm added learning gain: sole QUERY_WIN-minus-FIRST primary
+0.108914, 95% CI [-0.116499, +0.325697]. A/B retention and matched-budget
QUERY_WIN-minus-FACTUAL_WIN (+0.047632, CI [-0.270030, +0.377136]) remain
unresolved. FIRST-minus-SOURCE is +0.778752, nominal CI wholly positive.
All sixteen FIRST histories and post batches are newly collected; reward
stays exact across both WIN-only learners and rounds. About 99% of teacher
labels still bootstrap the frozen FIRST probability. All 12,288 new games
terminate naturally; new training raw is 16,797,830 and evaluation raw
10,073,878. Sixty-seven finite cases pass; independent verification PASS
checks new facts, every target/path, actual head chains, effects and costs.
Full new CPU is 1,016.31 seconds, or 2,718.15 with successful V312 SOURCE
once; audit CPU 253.21 seconds is separate. These are new target learning
histories under four fixed sources. Its terminal prediction diagnosis is
completed in V325 above; its added learning utility remains unresolved.
Cross-role seed reuse in V324 limits the independence interpretation of
its intervals; details are retained in its report.

[V323 frozen WIN-only new-stream validation](reports/WIN_CONFIRMATION_V323_RESULTS.md)
supports its sole WIN_ONLY-minus-FIRST primary: +0.276123, 95% CI
[+0.015834, +0.539142]. A retention passes; B remains unresolved
(-0.044676, CI [-0.399903, +0.280746]), so retained execution gain is false.
All 6,144 new games terminate naturally and pay 5,030,852 evaluation tiles,
with no new fitting, training acquisition, parameter files or reused games.
Sixty-two finite cases pass; independent verification PASS checks actual
restored parameters, all game summaries, paired effects and costs.
Full new CPU is 175.93 seconds, or 4,442.42 with successful inherited
SOURCE/V317/V319/V321/V322 once; audit CPU 9.28 seconds is separate.
This validates new execution streams on the existing learned cohort.
Its fresh target-learning comparison is completed in V324 above; V323's
B retention remains unresolved.

[V322 saved reward/WIN component crossover](reports/COMPONENT_HEADS_V322_RESULTS.md)
locates policy degradation in the current query reward update. Its sole
REWARD_ONLY-minus-BOTH primary is -0.696301, 95% CI [-1.090645, -0.305826].
Reward updates reduce utility with either WIN head: REWARD_ONLY minus FIRST
is -2.411015 and BOTH minus WIN_ONLY -2.239206, nominal intervals wholly
negative and both contrasts negative in all sixteen lives. WIN_ONLY minus
FIRST is +0.524492, nominal CI [+0.074172, +0.994993], a development candidate;
A retention remains unresolved. All 2,048 new games terminate and pay
1,620,910 evaluation tiles; 2,048 control games are reused, with zero fitting
or new training tiles. Forty-eight finite cases pass. Independent verification
PASS checks complete saved hybrid tables, exact component separation and
all natural-game summaries, paired effects and costs. Full new CPU is
93.52 seconds, or 4,266.49 with inherited successful SOURCE/V317/V319/V321;
audit CPU 21.93 seconds and V320 diagnosis are separate.
Its frozen-candidate new execution-stream validation is completed in V323
above; these component results are not independent learning confirmation.

[V321 paired reward-target intervention](reports/REWARD_TARGETS_V321_RESULTS.md)
does not establish query repair: its sole NSTEP_QUERY-minus-OLD_QUERY primary
is +0.134449, 95% CI [-0.139427, +0.417099]. NSTEP_QUERY minus own FIRST
is -1.714714, nominal CI [-2.188809, -1.239140], with loss in both A and B.
All 128 old-label versions exactly reproduce V319 before new acquisition;
WIN labels and corresponding risk parameters stay exact across reward targets.
The fixed four-action returns still bootstrap 98.84% of members, so this
does not establish removal of the diagnosed reward bias. All 6,144 fresh
natural evaluation games terminate; 24,978,516 new target tiles are paid.
Fifty-four distinct finite cases pass and independent verification PASS
checks every new target physics/RNG/reward tail and 3,308 FIRST H2 probes.
Full new CPU is 1,160.00 seconds, or 4,172.97 with inherited SOURCE/V317/V319;
audit CPU 599.47 seconds and the earlier V320 diagnostic are separate.
Its saved-head component mechanism diagnostic is completed in V322 above.

[V320 fixed-root teacher terminal calibration](reports/TEACHER_CALIBRATION_V320_RESULTS.md)
finds a more pessimistic combined QUERY-minus-FACTUAL teacher error:
-0.433145, 95% CI [-0.528076, -0.330458], with fifteen negative lives
and all four parent means negative. The nominal reward component is
-0.833492; the WIN component +0.050043 partly offsets it. QUERY reward
targets underestimate actual prescribed-DIRECT-then-FIRST-H2 returns by
1.262176 on average. This establishes target calibration differences,
without establishing learning gains or the cause of V319 behavior loss.
All 32,768 continuations end naturally and pay 13,606,558 new tiles;
saved initial spawns are reused. Forty-one new finite cases pass.
Independent verification PASS checks all new physics/RNG/returns and
3,442 frozen FIRST H2 probes. Execution and audit exit 0 with empty stderr.
Full new CPU is 425.58 seconds, or 3,438.55 with successful inherited
SOURCE/V317/V319 once; audit CPU is 170.35 seconds separately.
Its paired reward-target intervention is completed in V321 above.

[V319 matched query-state supervision](reports/QUERY_SUPERVISION_V319_RESULTS.md)
supports loss on its sole own-FIRST primary: -1.533998, 95% CI
[-1.950912, -1.112646]. QUERY minus same-budget FACTUAL is -1.622478,
CI [-2.031787, -1.220476], negative in all sixteen lives and four parent
means. A and B own-FIRST contrasts both support loss; FACTUAL's further
growth remains unresolved. Both arms use 4,194,304 fresh tiles and
1,048,576 rootgroups, with the same frozen FIRST teacher and paired RNG.
All 6,144 new evaluations end naturally. Forty-two distinct new finite
checks ultimately pass; independent verification PASS checks every new
spawn/target, all census paths/draws and 128 private head versions.
Execution and audit exit 0 with empty stderr. Full measured experiment
CPU is 445.88 seconds, or 3,012.97 with successful SOURCE/V317 once;
audit CPU is 184.10 seconds separately. This uniform query-supervision
recipe closes. Its fixed-root terminal calibration is completed in V320 above.

[V318 frozen A target/propagation interventions](reports/RETENTION_MECHANISM_V318_RESULTS.md)
exactly reproduces every V317 GREEDY v2 head and native target before the
counterfactuals. All four prespecified Bonferroni 98.75% mechanism intervals
cross zero: freezing FIRST bootstrap (-0.278866), exact-FIT localization
(-0.248638), their interaction (+0.208817), and first-round localization
(-0.173534). All secondary own-FIRST intervals also cross zero. The new
2,048 paired-seed games end naturally, with no new training acquisition.
Localized H2 leaf queries use the updated head only about 0.34% of the time;
this is exact-board coverage, not tuple-feature coverage or proof that
generalization is harmful. New CPU is 173.99 seconds; 32 distinct new finite
checks ultimately pass. Independent verification PASS checks 32 exact support
sets, 16 new heads, 384 literal H2 views and all new target/action rows.
Execution and audit exit 0 with empty stderr; audit CPU is 56.01 seconds.
The target-freeze/local-fallback route closes without a supported repair.
The direct query-state supervision trial is completed in V319 above.

[V317 sampled joint greedy backup](reports/GREEDY_TARGETS_V317_RESULTS.md)
supports its sole own-FIRST primary: +0.633261, 95% CI [0.086755, 1.195742],
with all four parent means positive. B own-FIRST growth is +1.024849,
CI [0.247683, 1.835102]; A preservation remains unresolved at +0.241673,
CI [-0.517769, 1.039594]. GREEDY minus recorded-action SARSA is +0.275824,
CI [-0.214608, 0.811544], so an operator advantage is not established.
Net SOURCE gain is +1.501001, including first adaptation. Retained growth
and the operator-mechanism endpoint remain unconfirmed. Both arms process
3,313,217 shared states and 97,000,522 actual writes; extra greedy search
is paid. All 6,144 evaluations terminate naturally. The 29 new finite
checks ultimately pass. Successful target CPU is 865.25 seconds, or
2,567.09 with SOURCE once; a failed serialization attempt is preserved
with 2,102,096 additional raw and unmeasured CPU. Independent audit PASS
replays 82,305 new records, reconstructs 160 heads and checks both arms'
complete saved targets, including every greedy action. Audit CPU is 153.90
seconds, separately recorded. Execution and audit exit 0 with empty stderr.
The frozen A mechanism interventions are completed in V318 above.

[V316 fresh target-training confirmation](reports/LOCAL_TARGETS_V316_RESULTS.md)
reproduces the unchanged full TD method's advantage over MC: +0.731802,
95% CI [0.352879, 1.124543]. The sole own-FIRST primary remains unresolved:
+0.072336, CI [-0.189859, 0.383456]. B own-FIRST growth is supported at
+0.353905, CI [0.029206, 0.678600]; A preservation remains unresolved.
Net SOURCE gain is +1.403883, including the +1.331547 first-adaptation gain.
MC own-FIRST loss is supported. These sixteen fresh training lives use
8,409,055 new raw and 6,144 natural-terminal evaluations; the arms' states
and writes match exactly. All 19 new finite checks pass. Independent audit
PASS replays 82,304 new records, reconstructs 160 heads and checks every saved
native TD target. New CPU is 816.23 seconds, or 2,518.07 with SOURCE once.
Retained growth remains unconfirmed under the four reused SOURCE parents.
This fixed-behavior recipe is now closed after its new training confirmation.
The sampled greedy joint-backup comparison is completed in V317 above.

[V315 frozen reward/WIN target decomposition](reports/COMPONENT_TARGETS_V315_RESULTS.md)
identifies positive reward-recurrence contributions under either fixed WIN table:
+0.747181, Bonferroni 99% CI [0.323909, 1.119718], and +0.844563,
CI [0.368731, 1.321903]. All four parent means are positive for both effects.
WIN contributions and interaction remain unresolved in the five-effect family.
Fresh-evaluation secondary TD_TD minus FIRST is +0.417721, 95% CI
[0.090163, 0.757989], but A preservation remains unresolved; no combination
establishes both-task preservation. All 5,120 new games terminate naturally,
with no extra training or mixed-table weight copies. The 36 distinct finite
checks pass; independent audit PASS reconstructs 96 heads and verifies 160
native initial-state action probes, endpoint pairing, signed effects and costs.
New CPU is 185.42 seconds, or 2,752.16 seconds carrying SOURCE/V314 once.
This is new evaluation of the same frozen V314 training instances, not a new
training confirmation; it does not revise the V314 own-FIRST primary.
The fresh-training confirmation is completed in V316 above.

[V314 fixed-policy local targets versus complete MC](reports/LOCAL_TARGETS_V314_RESULTS.md)
supports the target intervention: TD_LOCAL minus MC_LOCAL is +0.712212,
CI [0.321978, 1.115246], with all four parent means positive and 14/16 positive
lifecycles. The own-FIRST primary remains unresolved: +0.274527,
CI [-0.069239, 0.592469]; A/B preservation is also unresolved. Net SOURCE gain
is +0.988779, CI [0.562536, 1.424599], including first-adaptation value.
The relative advantage concentrates in B, where MC has supported own-FIRST loss.
All sixteen new lives share each fresh factual batch from the frozen FIRST_LOCAL
collector; states and actual writes match exactly at 3,314,014 and 97,815,922
per arm. TD alone uses actual recorded successors and its frozen batch-start
reward/WIN snapshot, with all native targets retained. The new acquisition is
8,409,732 raw, with 6,144 natural-terminal H2 evaluations. All 48 distinct new
finite checks pass; the independent 82,305-record audit PASS reconstructs 160
heads and checks every native TD target, including unused winning rows. New target CPU
is 864.90 seconds, or 2,566.74 seconds including reused SOURCE economically once.
This is conditional development under four V312 sources, fixed boundaries and
shared dynamics; continued own-first growth and structural learning remain open.
The frozen component decomposition is completed in V315 above.

[V313 actual-policy collection and periodic consolidation](reports/CLOSED_LOOP_V313_RESULTS.md)
rejects the frozen own-first growth endpoint: final CLOSED_LOCAL minus its own
FIRST_LOCAL is -0.625786, CI [-0.924988, -0.300769], with all four parent means
negative and 13/16 adverse lifecycles. The first shared LOCAL/FIXED cohort already
loses B capability; final B loss is -1.538433, while A preservation is unresolved.
Feedback versus the fixed first collector and net SOURCE gain are both unresolved.
LOCAL exceeds the more severely degraded LINEAR, which does not establish growth.
Four same-head H2-minus-DIRECT contrasts are strongly positive; DIRECT already
uses learned long-term value. All actual actor-change premises hold. The 16 new
lifecycles use 14,700,915 new training raw and 13,312 natural-terminal evaluations;
three updating arms each process 3,281,841 additional states, with differing writes.
All 73 distinct new finite cases pass, and the independent 107,043-record audit
PASS reconstructs 256 actual heads and checks 2,560 action probes. New target CPU
is 1,463.97 seconds; SOURCE plus target economic CPU is 3,165.81 seconds, with no
physical SOURCE retraining or double-added contained costs. Evidence is conditional
on four V312 sources and shared dynamics under supplied subsequent boundaries.
V314 above compares complete-game MC and local consequence-recursion targets under
the same facts, fixed continuation policy and supervised-state quota. Continued growth
and structural strategic learning remain unestablished; additional rounds are not
used to chase a positive interval.

[V312 fresh SOURCE value-training confirmation](reports/FRESH_CONFIRMATION_V312_RESULTS.md)
supports the frozen LOCAL-over-LINEAR_WIN primary: +1.270267, CI
[1.087410, 1.447666], and net SOURCE gain +0.864663, CI [0.632183, 1.094708].
Four new zero-initialized value parents each train on 4,096 fresh games;
their actual source acquisition is 11,285,275 raw. All four parent means
are positive for the primary and net gain. Final A/B gains are separately
supported, and all seven raw retention contrasts reproduce exactly at zero.
MC and LINEAR_WIN both lose to SOURCE; LINEAR_WIN versus MC is unresolved.
The 64 new five-stage sequences retain 128 banks with routes 0/1/0/1/0;
one additional detector game costs 573 raw and resolves reuse. All 73,728
new evaluations end naturally. All 51 new finite cases pass; independent
SOURCE and target audits both PASS, checking 16,384 source games and
263,375 target records. New source plus target CPU is 4,631.74 seconds,
without double adding contained setup, fit or save work. The target uses
16,997,255 new training raw; each arm's economic training input including
source and inherited dynamics is 28,331,599 raw. Intervals remain conditional
on four new value parents under shared identified deterministic dynamics;
historical dynamics CPU is unknown. V313 above completes closed-loop natural-game
collection by each updated policy and periodic consolidation, testing gains
over its own first adaptation, retention and a DIRECT/H2 planning control;
it finds supported own-first loss despite valid actual policy feedback.
Same-context continued improvement and general strategic learning remain open.

[V311 active two-table contribution control](reports/LINEAR_CONTRIBUTION_V311_RESULTS.md)
supports LOCAL over LINEAR_WIN: +1.026154, CI [0.801412, 1.253604], with
identical two-table storage, factual supervision and parameter writes. Net
SOURCE gain is +0.987542, CI [0.731918, 1.231938]; A and B individually
benefit in this cohort, and all seven raw retention contrasts reproduce at zero.
All 59 new finite cases and the independent 263,420-record audit pass;
73,728 new checkpoint games end naturally. The 64 new sequences retain 128
banks; 19 confirmation games cost 8,802 raw, including one unresolved B2 cap
that reuses without a prototype commit. LINEAR and LOCAL each process
13,300,774 states and write 390,074,254 parameters; LOCAL evaluation CPU is
12.7% higher. Real-arithmetic LINEAR/MC equivalence does not imply identical
numerical trajectories; their recorded final difference is +0.171480.
This establishes the joint sigmoid-link/update contribution under the four
original sources, supplied boundaries and historical probes. V312 above
confirms the frozen four-arm comparison under four newly trained risk_goal
SOURCE value parents and measures source CPU. Deterministic learned dynamics
remain shared; general strategic learning and same-context improvement are open.

[V310 selected banks own their planning beliefs](reports/BANK_BELIEF_V310_RESULTS.md)
supports the controlled final average LOCAL advantage over same-context MC:
+1.033409, CI [0.757074, 1.307830], and net SOURCE gain +0.771455,
CI [0.513819, 1.030265]. All seven raw retention contrasts reproduce at zero;
B alone remains unresolved: +0.247062, CI [-0.102080, 0.591136]. Execution
uses each actually selected bank's immutable first-FIT belief for all three
arms, removing task-name probability lookup. All 64 new five-stage sequences
route 0/1/0/1/0 with 128 banks; four confirmation games cost 2,969 raw.
New training costs 16,998,431 raw and 55,296 checkpoint games end naturally.
All 51 new finite cases and the independent 263,388-record audit pass.
LOCAL still uses twice MC's capacity and writes, with about 35% more evaluation
CPU. V311 above implements the two active reward/linear-WIN table control;
newly trained SOURCE parents remain the next confirmation. Supplied
stage boundaries, four fixed parents and readonly historical probes still
limit this evidence; same-context improvement and general strategic learning
remain unestablished.

[V309 confirmed context creation and repeated reuse](reports/CONFIRMED_CONTEXT_V309_RESULTS.md)
supports the frozen controlled five-stage retained-gain endpoint: final LOCAL
versus identically contextual MC +1.190736, CI [0.944169, 1.446879], and versus
SOURCE +0.568004, CI [0.315067, 0.824242]. All seven strict retention contrasts
reproduce exactly at zero across 64 new A/B/A/B/A sequences. Final A benefits;
B alone remains unresolved: -0.055604, CI [-0.410031, 0.297758]. All 146 new
finite cases and the independent 263,392-record audit pass, with 17,004,790
new training raw and 55,296 natural-terminal checkpoint games. Two ambiguous
returns use six paid confirmation games (4,815 raw); one resolves reuse and
one reaches the cap, reusing without committing its prototype. All actual
routes are 0/1/0/1/0 with 128 banks, and no repeated fit. New sequence compute
is closed; LOCAL still has twice MC's capacity and writes. Planning beliefs
remain indexed by measurement task, so this is a controlled checkpoint result,
conditional on four frozen sources. V310 above implements each selected bank's
own stored planning belief and supports controlled average net gain and retention;
contribution controls and newly trained SOURCE confirmation remain next.
Same-context continued improvement,
general strategic learning and historical total CPU remain unestablished.

[V308 fresh first-context adaptation and parameter reuse](reports/FIRST_ADAPT_V308_RESULTS.md)
supports the frozen primary LOCAL versus identically contextual MC: +1.355414,
CI [1.139532, 1.575205], and final equal-weight A/B net gain over SOURCE:
+1.017131, CI [0.815111, 1.210337]. Final A and B individually benefit.
All 60 new finite cases and the independent 266,895-record physical/data/endpoint
audit pass; 17,173,154 new training raw and 30,720 new natural-terminal
checkpoint games are retained. Strict complete retention remains HOLD:
A after B and B after A2 reproduce exactly, but final A versus A1 is
+0.004377, CI [-0.030819, 0.043951]. Actual A2 detection creates a third bank
in 2/64 sequences; old A parameters survive, but switching to the new bank
improves one return and harms the other. All 130 actual acquisitions and their
tails are paid. New sequence compute is closed; source-parent generalization,
historical total CPU and equal-capacity contribution remain open. LOCAL uses
twice MC's capacity and fit writes. V309 above implements confirmed creation
with paid observations and tests new longer sequences under a frozen rule;
it establishes controlled retention while B's individual net gain is unresolved.
Same-context continued improvement
and general strategic learning remain unestablished.

[V307 budget-matched old/new experience replay](reports/EXPERIENCE_REPLAY_V307_RESULTS.md)
fails the frozen replay endpoint: MIXED_REPLAY versus NEW_ONLY -0.484641,
CI [-0.806737, -0.157462], with all four parent means negative. Replay also
loses A1 capability: -0.401468, CI [-0.743454, -0.058890]. Frozen A1 still
exceeds SOURCE by +1.323419, CI [0.948786, 1.713071]; NEW_ONLY's incremental
gain over A1 remains unresolved. All 60 new finite cases and the independent
source-score/selection/target audit pass, with 8,192 new natural-terminal
evaluation games and zero new training acquisition. Both updating arms process
exactly 6,641,342 supervised states; replay changes complete-game/address
commits and costs, and no heldout or cutoff facts enter fits. This frozen
50/50 replay branch stops. V308 above completes fresh observed-context first
adaptation and later parameter reuse for new A/B/A sequences, with SOURCE
and a conventional MC baseline sharing the same context organization; it
establishes net gains while leaving actual-return retention unresolved.
Same-context continuous improvement and general continual strategy learning
remain unresolved; historical total CPU remains unclosed.

[V306 current-policy data for repeated A adaptation](reports/POLICY_DATA_V306_RESULTS.md)
does not establish the frozen actor intervention: CURRENT_DATA versus
SOURCE_DATA +0.276347, CI [-0.031848, 0.578623]. Relative to frozen A1,
CURRENT_DATA +0.311343, CI [-0.027504, 0.642393], leaves retention unresolved;
the new SOURCE_DATA cohort also does not reproduce the old A2 loss.
Frozen A1 itself exceeds SOURCE by +1.205367, CI [0.871271, 1.540228].
Both updating arms start from identical A1 reward/risk parameters and acquire
131,072 new raw per life with paired continuous streams and fixed beliefs.
All 56 new finite cases and the independent 65,664-record audit pass;
16,777,216 physical training raw and 8,192 new natural-terminal evaluation
games are retained. Each updating arm pays 8,388,608 additional raw without
an established incremental gain over A1. Actor choice changes coverage and
factual targets together; retained A1 histories and four parents remain fixed.
V307 above completes the matched-supervision replay control and rejects that
frozen intervention. Historical total CPU is unclosed.

[V305 observed-context persistent reward/risk parameters](reports/CONTEXT_CONTINUAL_V305_RESULTS.md)
passes the frozen structural repair endpoint: final equal-weight A/B utility
versus SHARED_LOCAL +0.279710, CI [0.086740, 0.469176], and versus SOURCE
+0.689903, CI [0.463018, 0.920355]. Both final tasks benefit: A +1.005117,
B +0.374689. Observed FIT-prefix statistics select two persistent contexts
without task labels; unchanged A after B and B after A2 reproduce exactly.
All 50 new finite cases and the independent audit pass, with 10,240 natural
new evaluation games and no new training acquisition. Full retention still
fails: continuing A training reduces A by 0.396635, CI [-0.693646, -0.097343].
Parameter capacity doubles, and the result remains a retained-cohort batch
diagnosis. V306 above tests matched new SOURCE and learned-policy cohorts
from identical A1 parameters; the actor intervention remains unsupported,
and policy/target mismatch remains a hypothesis.

[V304 same-B parameter-history control](reports/HISTORY_CONTROL_V304_RESULTS.md)
isolates the V303 B-stage failure: LOCAL from original SOURCE exceeds the
same method inheriting A1 by +1.546751, CI [1.235445, 1.849899], on identical
B facts, targets, order and evaluation seeds. Fresh LOCAL also exceeds SOURCE
by +0.374689, CI [0.060634, 0.684168], with 630 versus 529 wins; inherited
LOCAL remains below SOURCE. MC suffers the same history penalty but still
fails from a fresh initialization. All inherited numerical controls reproduce
V303 exactly; 45 new finite cases and the independent audit pass. No new
training acquisition was made; 8,192 new evaluation games terminate naturally.
This is a retained-cohort diagnosis, not independent confirmation or equal
total-history budgeting. V305 above implements the observed-context repair;
continuous learning and historical total compute remain unresolved.

[V303 retained-parameter A/B/A sequence](reports/CONTINUAL_V303_RESULTS.md)
passes final equal-weight A/B utility versus SOURCE: +0.410193, CI
[0.133242, 0.678271], on 64 fresh sequences and 30,720 natural-terminal
checkpoint games. All 46 new finite cases and the final independent audit
pass. Continuous adaptation and preservation remain unresolved:
B fitting reduces A by 2.141278 and B itself is below SOURCE; returning to A
improves both tasks, but final A remains below its first-stage level and final
B has no established gain. Fixed task beliefs/seeds and identical SOURCE
replays isolate the critic changes. The interrupted execution was recovered
under the original freeze, reusing 148 complete acquisition stages and
exactly reproducing 448 retained arm receipts. Historical total CPU was not
fully retained and is not claimed closed. V304 above subsequently isolates
the parameter-history effect on exactly the same B facts and controls.

[V302 independent B confirmation of frozen LOCAL_RISK](reports/LOCAL_RISK_V302_RESULTS.md)
passes its prespecified primary endpoint on 64 fresh target training histories:
LOCAL minus SOURCE utility +0.387252, CI [0.011185, 0.762719], with 649 versus
554 wins in 2,048 paired games per arm. All 6,144 evaluation games terminate
naturally; 43 new finite cases and the once-read independent canonical audit
pass. The interval is conditional on four original SOURCE parents and its
lower bound is close to zero. Old B data and V301 evaluations do not enter the
new fits or intervals. MC is worse than SOURCE; LOCAL pays twice MC's parameter
writes. This confirms a modest independent target-cohort benefit, with
continual adaptation, retention and contribution/cost comparisons still open.
The next stage freezes an A-to-B-to-A sequence with retained parameters and
separate A/B evaluations instead of further tuning this B cohort.

[V301 split reward and bounded terminal risk](reports/SPLIT_RISK_V301_RESULTS.md)
implements two distinct representations with exactly SOURCE-matching initial
values on all retained B histories. GLOBAL_RISK fails the primary comparison:
utility -0.700419 versus SOURCE, CI [-1.026942, -0.370467]. The prespecified
LOCAL_RISK control has a promising secondary gain of +0.389858, CI
[0.075359, 0.706092], positive in all four source groups, with 633 wins versus
SOURCE's 543 in 2,048 games. Both new methods share identical reward fits;
similar heldout risk calibration and worse scalar utility errors do not
substitute for complete-game outcomes. All 8,192 games terminate naturally;
66 finite cases and the independent audit pass. LOCAL pays twice MC's
parameter writes, so shared observations are not equal compute. The next
step freezes the current LOCAL method for primary confirmation on a new B
training cohort at the same acquisition budget; this secondary retained-data
signal does not promote V301's failed primary or establish continual transfer.

[V300 retained-B control-target comparison](reports/B_CONTROL_V300_RESULTS.md)
changes only MC targets to game-start H2 expected-control targets on the same
64 retained B histories, original SOURCE copies and normalized single-table
updates. New complete-game control utility exceeds MC by +1.491047, CI
[1.119523, 1.882097], but exceeds SOURCE by only +0.103975, CI
[-0.214316, 0.413317]; the primary gain remains unsupported. MC again
degrades versus SOURCE by -1.387072. All 6,144 new games terminate naturally;
40 finite cases and the independent audit pass. Both learners process the
same 6,670,464 samples and 106,964,712 writes, while control target fitting
uses 75.34 CPU seconds versus MC's 19.91. This retained-training development
comparison ends the current target branch under its frozen stop rule. The
proposed separate reward and bounded nonlinear terminal-risk intervention is
completed in V301, with both local and additional global board feature controls.

[V299 retained-B update and H2 diagnosis](reports/B_MECHANISM_V299_RESULTS.md)
exactly reproduces V298 fit counts/examples and complete SOURCE/MEAN heldout
scores. None of the 10,401 local game updates increases its own squared loss; complete
FIT MSE decreases 2.821557, while complete heldout MSE has no improvement and
MAE worsens. Won-game heldout MSE improves 14.711256 and lost-game MSE worsens
4.774808 as both outcome strata's predictions rise about 0.9. Signed donor
prediction/loss changes and fixed-second-action H2 decompositions close exactly.
The 30.957% root recommendation drift has no counterfactual Q labels and does
not establish a cause of game loss. No new world samples or evaluation games;
35 finite cases and the independent audit pass. Its proposed target-only
control intervention is completed in V300 with SOURCE as the primary comparator.

[V298 independent stable-B learning](reports/STABLE_B_V298_RESULTS.md) uses
the frozen V291 whole-game learner on 64 fresh B-only histories, initialized
from original SOURCE without intervening A-stage updates. MEAN versus SOURCE
utility is -1.221845, CI [-1.586042, -0.855672], with 13 improved and 51 adverse
histories; normalized sequential learning also degrades significantly.
All 6,144 independent evaluation games terminate naturally. New acquisition
costs 8,418,915 raw including warmup, and evaluation costs 3,723,305 raw;
39 focused/regression cases and the independent 131,269-row audit pass.
Stable-B learning remains unsupported. The next core step diagnoses MC targets,
shared features and H2 action rankings on the retained B data before returning
to continual transfer and retention. V291's stable-A result remains intact.

[V297 direct stateful strategy search](reports/DIRECT_STRATEGY_V297_RESULTS.md)
optimizes BUILD/rescue action preferences using complete-game returns while
keeping SOURCE values frozen. Independent stable-A gain is -0.126400, CI
[-0.799927, 0.630618], with four improved, two unchanged and ten adverse
histories. The optimizer contrast against random search also crosses zero.
Fourteen histories choose nonzero programs, changing 64,910 science actions;
the execution framework works, but whole-game benefit remains unsupported.
All 3,336 physical training games and 1,408 science games terminate naturally,
at 3,142,559 and 1,354,306 raw observations respectively; the independent
958-row audit passes. This frozen grammar stops. The next core control tests
the confirmed V291 learner directly in stable B, without intervening A updates,
before attributing failures to continuous transfer or adding a strategy library.

[V296 independent long-continuation action validation](reports/LONG_HORIZON_ADVANTAGE_V296_RESULTS.md)
freezes all 144 V294 natural anchors and the old SOURCE, Bellman and sampled
choices before new acquisition. The old sampled advantage of +0.577684 becomes
-0.081829, CI [-0.248832, 0.086533], on fresh paired continuations; six histories
improve and ten worsen. Bellman differs from SOURCE by +0.002753 with an interval
crossing zero. All 7,552 physical continuations terminate naturally, at a new
cost of 3,373,840 raw tile observations; old discovery and source/input costs
are retained. All 24 focused cases and the independent compact audit pass.
This fixed-SOURCE continuation target branch stops. The next core direction
directly optimizes executable policies using whole-game returns, with V292's
already-tested on-policy MC value regression retained as a control. Whole-game
gain, correction and retention must precede a persistent strategy or skill library.
Whole-algorithm net gain remains unconfirmed.

[V295 observed-module Bellman experts](reports/ROUTED_BELLMAN_V295_RESULTS.md)
isolates residual writes using the original observed LIBRARY routes, retaining
the same targets, samples and whole-game normalization. Independent cycle gain
against frozen SOURCE is -0.028006, CI [-0.391001, 0.335315], so the complete
learning algorithm still has no confirmed net gain. Returning-A performance
improves relative to smooth sharing by +0.548389, CI [0.037209, 1.045821],
but B correction is uncertain and the earlier positive V294 correction does
not persist in the fresh science streams of the unchanged smooth control.
All 16 histories reactivate the original observed A module; known-A capability
is unchanged in 14 histories after B, while final capability remains uncertain.
All 8,704 physical science games terminate naturally; 31 focused cases and
the 11,976-row independent audit pass. New science costs 7,579,163 raw tiles;
expert allocation, copies and inherited source costs are retained. The next
core experiment tests independent long-continuation action improvement before
adding further storage mechanisms or adopting another value target.

[V294 conditional Bellman residuals](reports/CONDITIONAL_BELLMAN_V294_RESULTS.md)
compares MC/control targets and board-only/observed-p values on identical retained
SOURCE carrier games, with no new training acquisition. The conditional Bellman
head improves on its own saved A parameters in B by +0.776047, CI
[0.234970, 1.311102], under identical current B belief and paired games.
Its independent cycle gain against frozen SOURCE is -0.130005, CI
[-0.586510, 0.318783]; net gain remains unsupported. Fixed-A capability falls
by 0.849388 at the end, with a negative interval. All 14,848 science games and
16,096 SOURCE continuation references finish naturally; 43 focused tests and
the independent compact audit pass. New evaluation/reference acquisition costs
19,929,882 raw tile observations and is accounted separately from the reused training data.
The next core comparison isolates residual writes by existing observed LIBRARY
modules while keeping the Bellman target fixed, testing useful B correction,
actual A reactivation and net control gain together.

[V293 shared-shadow deployment](reports/SHADOW_DEPLOYMENT_V293_RESULTS.md)
uses one frozen-source acquisition stream and one persistent episode-mean
candidate for three deployment rules on 16 fresh A→B→A′ histories. Validation
is charged inside each arm's raw budget. Validated deployment accepts only
one of 48 candidates; its independent cycle gain is +0.028714 versus frozen
H2, CI [0, 0.086143], so the frozen positive-lower-bound criterion fails.
Unconditional deployment gains in A but loses in B; its current B head is
worse than its saved A head under identical B belief and games, and fixed-A
capability remains lower at the end. Stable acquisition and conservative
submission have not established continuous learning or B correction.
All 9,216 science games and 2,304 paid validation games terminate naturally;
33 focused test cases and the independent canonical audit pass.
The next core step studies source-anchored Bellman control residuals and
observed-law-conditioned values on the same factual carrier data, separating
target construction from conditional representation before new confirmation.

[V292 continuous natural episode learning](reports/NATURAL_EPISODE_V292_RESULTS.md)
tests the frozen learning methods on 16 new A→B→A′ lifecycles with five
matched-observation controls. Episode-mean H2 learning has a small initial-A
gain, but its whole-cycle utility falls by 6.510362 versus frozen H2 values,
CI [-6.740301, -6.292126], with all 16 histories worse. Under identical B
belief and paired B games, the updated B head loses 7.380081 against the
saved A head; fixed-A capability also collapses and does not recover after
returning to A. All 13,312 evaluations terminate naturally, 53 focused tests
and independent canonical audit pass. Source H2 planning remains beneficial.
This identifies harmful cross-regime value updates and failed retention;
context storage alone cannot repair the observed B learning damage. The next
core step separates stable reference acquisition, shadow fitting and
validated policy deployment, with an unconditional periodic-deployment
control and all validation costs charged. V291's offline A gain remains valid;
continuous strategic learning remains unconfirmed.

[V291 independent training-history confirmation](reports/INDEPENDENT_EPISODE_V291_RESULTS.md)
freezes V290 methods on 64 fresh histories under the same four source parents.
Episode-mean learning improves new complete H2-game utility by 1.211015 over
frozen values, CI [0.888291, 1.529658], with 55 improvements and nine adverse
histories. All 6,144 evaluations terminate naturally. Full heldout MSE falls
from 42.279736 to 30.879864. Normalized sequential learning also gains;
the episode-mean versus sequential utility interval crosses zero, so the
pilot's extra aggregation benefit does not replicate. Both learners process
6,658,122 identical samples; economic training costs are 19,719,069 raw per
arm, with physical fresh acquisition shared once and old target data excluded.
Thirty-two focused tests and independent canonical audit pass.
This confirms offline learning gains against static frozen H2 values,
conditional on old sources. The next core stage tests continuous A→B→A′
learning, correction and retention with natural-execution and same-budget
learning controls. General strategic and structural learning remain open.

[V290 episode consolidation](reports/EPISODE_CONSOLIDATION_V290_RESULTS.md)
keeps the original factual dataset and compares frozen, ordinary MC,
address-normalized sequential MC and game-start-residual episode means.
Both normalized methods improve full heldout MSE on all 16 lifecycles;
episode-mean MSE falls from 45.213894 to 29.486606. Fresh complete-game utility
improves by 0.687813 over frozen values, but CI [-0.283584, 1.673882] crosses
zero and six lifecycles worsen. Episode means outperform the similarly
normalized sequential control by 0.617668 in the predefined secondary
utility contrast; their prediction MSE is almost identical and slightly
worse. Actual parameter writes fall by 57.49%, while fitting CPU exceeds
ordinary MC. All 1,024 games terminate naturally; 30 focused tests and
independent audit pass. The next stage freezes these methods and tests new
independent training histories plus new paired complete-game evaluations.
Net learning and natural long-episode transfer remain unconfirmed.

[V289 cumulative MC replay](reports/CUMULATIVE_CRITIC_V289_RESULTS.md)
preserves all 1,655,968 V287 updates and exactly reproduces its complete heldout
scores. A fixed, label-independent 1,756-anchor panel worsens after the first
complete training game in all 16 lifecycles. Final anchor MSE increases by
103.683593, CI [62.605741, 147.911720]; complete heldout MSE also worsens.
A descriptive decomposition places 95.4% of the anchor increase at the first
time position. Fixed-board H2 recommendations change on 33/64 boards, but old
continuation reference utility does not establish a change. All 28 focused
tests and independent audit pass, with zero new environment observations.
The next core intervention consolidates each complete game's shared-address
evidence, retaining a similarly normalized sequential control to separate
normalization from frozen-residual aggregation. Full heldout prediction and
fresh complete-game utility must improve before calling learning repaired.

[V288 isolated n-tuple update diagnostic](reports/NTUPLE_INTERFERENCE_V288_RESULTS.md)
reuses V285's two independent suffix batches on 128 fixed A boards. All 470
trainable afterstates and 6,934 directed pairs are included, retaining repeated
feature addresses and zero-overlap pairs. The primary cross-board mean-label
MSE difference is -0.187544, CI [-0.246865, -0.132421], with 16/16 lifecycles
improving. Single-label updates also improve on average; their empirical
fluctuation penalty does not cancel that benefit. Some individual pairs worsen
and remain retained. No new environment observations or actual weight updates
occur; 22 focused tests and independent receipt audit pass. This local result
does not establish a learning or control gain and does not explain V287's
accumulated fitting failure. The next core diagnostic replays V287's original
MC update sequence on a fixed heldout panel, tracking prediction errors and H2
recommendation changes before choosing a learning modification.

[V287 fixed-behavior critic comparison](reports/RETAINED_CRITIC_V287_RESULTS.md)
fits factual TD and episodic-return critics on the same retained natural A
prefix, holding out complete later games. Each trainable critic updates the
same 1,655,968 afterstates; all arms inherit 13,391,491 acquisition observations,
and no new training observations are collected. MC reduces fresh static-H2
utility by 6.618736 relative to frozen values, with a negative paired interval
and 16/16 adverse lifecycles. Its heldout MSE and MAE also worsen despite a
smaller aggregate signed bias. TD does not establish a utility gain. All 768
evaluations terminate naturally and independent audit passes. The next core
diagnostic reuses V285's independent suffix batches to separate noisy-target
updates from shared-feature interference, before choosing a new representation
or consolidation method. These results do not yet identify the dominant cause.

[V286 matched-budget natural value learning](reports/NATURAL_ONLINE_VALUE_V286_RESULTS.md)
compares frozen, ordinary TD and persistent context TD across 16 new natural
lifecycles. All arms receive the same 17,585,795 economic training observations,
including source and shared warmup costs. Ordinary and persistent TD reduce
independent complete-game utility by 1.328972 and 0.999840 relative to frozen
values; both paired intervals exclude zero. Persistent versus ordinary TD does
not establish an overall or restoration-stage gain. Deterioration already occurs
in A, before the spawn-law change. Same-head H2 planning still improves all 16
lifecycles. Independent receipt audit passes; all 2,560 evaluation games reach
natural terminal states, and adverse lifecycles are retained. The next core
step fits shadow TD and complete-return critics on
fixed retained A histories, then tests fresh complete-game decision utility.
The three paper evidence gaps remain open; U005 remains FAIL and U006 unstarted.

[V285 independent continuation validation](reports/NATURAL_CONTINUATION_VALUE_V285_RESULTS.md)
evaluates every legal first action on 384 fixed natural boards with separate
discovery and validation batches. The 90,752 complete continuations consume
50,341,737 environment transitions. Discovery-selected actions do not establish
a validation gain in either the uniform or competition cohort; all adverse
lifecycles are retained. Absolute tail underprediction also includes a mismatch
between the source greedy TD policy and the H2 continuation policy. The next
core experiment compares frozen, ordinary online TD and persistent context TD
with the same learned spawn memory, H2 authority and total observation budget.
The three paper evidence gaps remain open; U005 remains FAIL and U006 unstarted.

[V283–V284 model-to-decision diagnostic](reports/NATURAL_MODEL_DECISION_V283_V284_RESULTS.md)
restores every decision on 16 retained library lifecycles using the same observed
prefix for all spawn memories. Library estimates improve H2 reference ranking
on all 16 lifecycles; shifted-phase action disagreement falls from 9.015% to
0.842%. Yet 384 complete known-law reference games do not establish a gain over
the library, and the restoration-phase reference is worse. Better model estimates
and internal ranking are insufficient evidence of full-game learning gains.
The next core step is independent continuation evaluation of competing actions
to guide target-feedback value learning, retaining ordinary TD and frozen-value
controls. The old value table's causal responsibility remains unproved.

[V280–V282 three-stage paper evidence](reports/PAPER_EVIDENCE_STAGES_V280_V282_RESULTS.md)
tests the unchanged relevance controller on 128 fresh source/target lifecycles,
natural model revision on 16 new memory lifecycles, and contributions on retained
execution prefixes. Both route net-gain comparisons support improvement, including
sampled returns; natural library revision does not establish an extra full-game
gain. Same-leaf H2 planning improves all 16 lifecycles. Library spawn estimates
are markedly more accurate than pooled updates in the shifted regime, but that
accuracy has not translated into demonstrated strategic utility. Parameter updates
contribute; passive structure revision remains unsupported. Full costs are retained,
and total source-plus-online observation budgets remain unequal. The next main
question is the interface between model estimates, action ranking and long-term
value. The original U005 scientific Gate remains FAIL; U006 is unstarted.

[V279 evidence-weighted prefix diagnostic](reports/EVIDENCE_WEIGHTED_PREFIX_V279_RESULTS.md)
replays all 64 V278 sources on passive and relevance-controller histories.
Evidence-weighted candidate predictions slightly lower recommendation regret,
but each history cohort has seven source improvements and five degradations.
Only one of the known adverse history's five later wrong RETRY choices is
fixed, with two new B-stage errors. These fixed-history results do not justify
promoting model averaging or claiming an online gain. The next core question
is the expected effect of acquiring feedback on later learning and decisions.

[V278 query-relevant coverage](reports/QUERY_RELEVANT_COVERAGE_V278_RESULTS.md)
tests a decision-relevance controller on 64 fresh paired lifecycles. Mean
executed-route regret is 0.729659 versus the unchanged quota controller's
2.277302; the primary paired interval [-3.522542, -0.138984] excludes zero,
with four improved, 60 equal and none worse. Relative to natural execution,
the interval [-8.473422, 0.020366] still crosses zero and one history worsens.
The extra cost filter changes no outcomes. The adverse case improves immediate
probe decisions but delays factor revision and causes later wrong choices.
The next bottleneck is acquisition's expected effect on future learning and
decisions; its worst-case support envelope does not establish that benefit.

[V277 independent-source confirmation](reports/ONLINE_FACTOR_CONFIRMATION_V277_RESULTS.md)
keeps V276 unchanged on 32 fresh source/target lifecycles with disjoint source
RNG sets. Mean executed regret falls from 7.250056 to 1.915053, but the primary
paired interval [-14.371478, 0.916275] crosses zero: two improved, 29 equal,
one worse. Confirmation fails. The adverse history pays for 53 coverage
attempts to obtain 16 retry outcomes, including costly detours where the
recommended SHORT is already optimal. The next mechanism must consider
decision relevance and operator reachability before buying coverage.

[V276 online factor repair](reports/ONLINE_FACTOR_REPAIR_V276_RESULTS.md)
tests bounded source-gap coverage and episode-start factor revision in a 2×2
design, preserving the 288-opportunity lifecycle. Mean actual regret including
coverage costs falls from 27.35720 to 3.29365; the paired result is one improved
known source history and three equal histories. Reselection alone remains
self-locked; coverage plus reselection unlocks SHORT. The independent-source
follow-up is reported in V277 above; natural full-game transfer remains open.

[V275 execution-only online lifecycle](reports/ONLINE_SUPPORT_CONTINUAL_V275_RESULTS.md)
keeps one learner across four target contexts for 12 episodes × 8 actual
START opportunities in each A→B→A_prime phase. Only reached operators produce
feedback. The factor arms (frozen, continual support expansion, and legacy
coercion) are identical in this cohort. A retained-data decomposition attributes
98.94% of B regret to one source partition error combined with zero SHORT
execution; DELAYED affects only one small-margin query cell. V276 tests bounded
coverage and online factor revision. This remains a finite route diagnostic.

[V274 continual successor support](reports/CROSSED_FACTOR_SUPPORT_CONTINUAL_V274_RESULTS.md)
adds a predeclared `DELAYED` outcome to B while keeping `RECOVERY_RETRY`
available. The expanding arm discovers the new category from fit prefixes and
returns to 12/12 after A_prime; the static arm abstains when the old support is
contradicted. This is the first support-expansion diagnostic, not a Gate rerun.

[V273 continual action-support structure](reports/CROSSED_FACTOR_STRUCTURE_CONTINUAL_V273_RESULTS.md)
keeps the V270 law and query bank fixed while B removes the RETRY branch from
the available action set. Aware arms remain legal and CONTINUAL_FACTOR_AWARE
reaches 12/12 at B prefix 0; the legacy unmasked control produces 3.75 invalid
actions per seed. This tests structural applicability and masking, not new
successor-category learning; the original Gate remains FAIL.

[V272 continual query shift](reports/CROSSED_FACTOR_QUERY_CONTINUAL_V272_RESULTS.md)
keeps the V271 dynamics and factor learner fixed while changing only the B
phase risk preference. The frozen factor model changes its risk action without
new target rows and restores the A action in A_prime; continual updating starts
at 11.25/12 B queries and ends at 12/12 after restoration. This separates
query adaptation from relearning dynamics; the original Gate remains FAIL.

[V271 continual crossed-factor flow](reports/CROSSED_FACTOR_CONTINUAL_V271_RESULTS.md)
keeps V270's source factor selector fixed and tests each unseen target through
`A→B→A_prime`, where only the retry law changes in B and then returns to A.
CONTINUAL_FACTOR lowers B regret from 2.75175 to 0.501125 relative to the
frozen source by prefix 48, then reaches zero regret by prefix 32 after the law
is restored. This is synthetic amortized transfer evidence; source and target
costs remain separate, and the original Gate remains FAIL.

[V270 crossed observable-factor transfer](reports/CROSSED_FACTOR_TRANSFER_V270_RESULTS.md)
introduces a synthetic crossed task flow with an L-shaped source and four
unseen target combinations. The learned operator-factor selector reaches
11/12 queries before target data and 12/12 after four target rows per operator;
RESET/FULL_CONTEXT start at 6/12 and 10.5/12. GLOBAL pooling is worse. The
learner paid a fixed 720 source-fit rows per seed, so this is transfer evidence
after source amortization, not a total-cost claim.

[V269 factorized residual](reports/PERSISTENT_CONSEQUENCE_LIBRARY_V269_RESULTS.md)
keeps V266 module assignment fixed and adds a predeclared one-context baseline
to the current local fit. `FACTORIZED_MODULE` matches RESET at 11.5/12 and
regret 0.105; `GLOBAL_SHRINK` falls to 10.75/12 and regret 0.54425. Module
history supplies no measurable gain, while unconditioned global sharing causes
wrong transfer. Baseline-weight tuning on these streams is closed; a future
factorization needs a longer-lived observable context variable.

[V268 paired two-step consequence](reports/PERSISTENT_CONSEQUENCE_LIBRARY_V268_RESULTS.md)
keeps the V266 module assignment fixed and replaces marginal detour/retry
estimation with fixed-index joint outcome fragments. The composed arm drops to
10.25/12 versus 11.5/12 for the marginal control and raises exact regret from
0.105 to 0.475. The joint estimator also changes the prior and effective
evidence, so this is a negative frozen estimator diagnostic. The route is
closed; any factorization follow-up must predeclare its shared and varying
context factors.

[V267 held-out query transfer](reports/PERSISTENT_CONSEQUENCE_LIBRARY_V267_RESULTS.md)
keeps three utility weights out of the reuse rule and scores them separately.
The held-out bank lies in the same exact action regions as the primary queries,
so `PRIMARY_AGREEMENT` and `ALL_QUERY_AGREEMENT` make identical assignments:
11.5/12 primary policies and 10.75/12 held-out policies, with held-out exact
regret 0.357 versus RESET 0.31. Set-action metrics agree with these counts.
This is a finite negative diagnostic, not evidence of a new generalization
gain; the next substantive route is a genuinely new action region or longer
composable outcomes.

[V266 query-action agreement](reports/PERSISTENT_CONSEQUENCE_LIBRARY_V266_RESULTS.md)
replaces Brier applicability thresholds with direct agreement on all three
queries. It prevents harmful module transfer but matches RESET at 11.5/12 and
exact regret 0.105, with no cost gain. The current assignment-rule route is
closed; further progress requires richer held-out queries or longer composable
consequences.

[V265 fair-prefix applicability diagnostic](reports/PERSISTENT_CONSEQUENCE_LIBRARY_V265_RESULTS.md)
corrects the V263/V264 arm accounting. The guarded persistent library matches
RESET at 11.5/12 query policies and exact regret 0.105, while the legacy
splitter reaches 11.0/12 and GLOBAL 9.5/12. Abstention prevents bad transfer
but has not produced a gain; applicability remains the main bottleneck.

[V264 fresh-stream replication](reports/PERSISTENT_CONSEQUENCE_LIBRARY_V264_RESULTS.md)
exposed an arm-accounting flaw inherited by V263: GLOBAL used 64 observations
while RESET used 48, and LIBRARY committed its validation suffix before scoring.
Those tables are retained but are not fair evidence. V265 corrects the shared
prefix before testing applicability uncertainty.

[V263 persistent consequence library](reports/PERSISTENT_CONSEQUENCE_LIBRARY_V263_RESULTS.md)
is the first small implementation of the revised multi-episode direction. A
held-out predictive split creates a reusable consequence module, preserves all
12 query policies across a fixed `A0→B→A_prime→C` lifecycle, and beats both
per-phase reset (11/12) and one-module pooling (10/12) on this finite diagnostic.
The run is exploratory only; module applicability, generalization and the
original scientific Gate remain unresolved.

[V262 targeted operator-row acquisition](reports/TARGETED_ROWS_V262_RESULTS.md)
is independently valid but scientifically negative. Under one unified native
joint row-confidence proof, direct unresolved-row reuse, full declared-unit
sampling, and continuous reuse all produce 144/216 query-certified, 128/216
joint-complete, and 192/216 execution-certified targets, with 8 goal-impossible
targets. DIRECT saves only 26/27/30 samples per life against FULL and changes
no readiness outcome; it costs the same as CONTINUOUS. Science exits 0 with
stderr 0, the independent audit is valid over 648 targets and 5,400 previews,
and 36 focused tests pass. The scientific Gate remains FAIL and U006 remains
unstarted. The targeted-row route is closed; the next method must change the
representation or query-state construction substantially.

[V261 native partial-path point learning](reports/PARTIAL_PATH_POINT_V261_RESULTS.md)
fails its frozen stage (7/8) and is not adopted. Joint completion is 200/216,
late-B queries 32/36 and return 72/72, but the matched required-row control has
identical completion and fees (44,703). New point learning changes 80 terminal
vector sets and 8 valid candidates, yet changes no acquisition stop or execution.
Both required-row arms beat complete reuse by 3 joint targets and 266 observations;
those gains do not establish an effect of the new estimator. The remaining 8
query-only targets lack RETURN/RETRY comparison power; another 8 execution-only
targets cannot yet prove true goal impossibility. Next freeze a sole row-CS query
proof, then isolate paid acquisition of unresolved operator rows against full
units using that proof. Direct R resets are supported and fully charged; their
observations do not become D/R units. Fifty-eight tests pass after one retained
fixture repair; once-only science/audit exit0/stderr0, independent audit valid
over 648 targets, 4,692 previews and 652 intermediate plans. Known interfaces and
H2 remain; original scientific Gate FAIL, U006 unstarted.

[V260 required-row acquisition](reports/REQUIRED_ROW_UNITS_V260_RESULTS.md)
fails its frozen stage5/8 and is not adopted. Required joint completion176/216
loses8 versus complete continuous reuse184/216; late-B25/36 misses27/36 and
control28/36. All arms spend34,201 shared observations. Lower full fees come
from fewer executions, with0 acquisition saving. Partial units supply more
comparison evidence while query point estimates stay frozen at full history;
a retained candidate has true regret.43 and is correctly refused a certificate.
Next isolate native policy-path point learning from predeclared partial units,
keeping acquisition, thresholds/caps and execution fixed. Thirty-eight tests
pass first attempt; once-only science/audit exit0/stderr0, independent audit
valid over648 targets/5,184 previews/658 intermediate decisions/5,274 partial units.
Known interfaces and H2 remain; original scientific Gate FAIL, U006 unstarted.

[V259 continuous compatible row confidence](reports/CONTINUOUS_ROW_CS_V259_RESULTS.md)
fails one frozen condition (7/8): late-B queries21/36 miss27/36. Same-paid-prefix
continuous D evidence adds8 valid impossibility decisions; joint completion
162→170/216 versus separate reuse, with0 paired losses. Rebuilding gives160/216.
Full observations48,237 versus48,251/48,246 save only14/9; query readiness stays
178/216 versus separate reuse. Shared costs remain34,216: all B phases exhaust
budget, and life1 A leaves B only32 draws. Next acquire rows required by each
unresolved query comparison as well as execution declarations, with fixed
thresholds/point choices/caps; isolate any cross-phase budget policy later.
Thirty tests pass first attempt; once-only science/audit exit0/stderr0, independent
audit valid over648 targets/5,256 previews/656 intermediate decisions.
Known interfaces and H2 remain; original scientific Gate FAIL, U006 unstarted.

[V258 full goal-feasibility lifecycle](reports/GOAL_FEASIBILITY_V258_RESULTS.md)
fails two frozen conditions: late-B queries23/36 miss27/36, and reuse observations
48,248 exceed rebuilding48,241. Joint completion improves160→176/216 with16
paired gains/no losses, but the new dual search adds0 impossibility certificates.
A query qualification consumes22,528 of34,200 shared observations; all B phases
then exhaust budget. All16 execution-unresolved regions still admit risk-feasible
goal>2 kernels, independently checked over208 original constraints. Next predeclare
continuous row evidence for legally identical A/B parameters, then acquire units
according to unresolved query/feasibility declarations.
Twenty-two tests pass after a retained fixture repair; once-only science/audit
exit0/stderr0, independent audit valid over432 targets/3,456 full previews/439
intermediate plans. V256 stays passed and immutable; V257 stays negative.
Original scientific Gate FAIL; U006 unstarted.

[V257 same-evidence impossibility bounds](reports/COUPLED_IMPOSSIBILITY_V257_RESULTS.md)
fails its primary method condition:0/16 new certificates, despite valid execution
and independent audit. All949 paid snapshots/432 terminal targets are retained;
160 nonprimary bounds tighten, no false claims or new observations occur.
Eight primary targets are blocked by the frozen old risk-dual parameter; for the
other eight, exact independently verified feasible kernels remain inside all104
original CS constraints with risk1/20 and goal>2. Certificate tightening alone
cannot resolve that group. Next combine a complete-region risk dual with shared
acquisition directed at goal feasibility, then test a fresh full lifecycle.
Seventeen focused tests pass; science/audit run once, exit0/stderr0. V256 stays
passed and immutable; original scientific Gate FAIL, U006 unstarted.

[V256 complete direct-trajectory lifecycle](reports/TRAJECTORY_LIFECYCLE_V256_RESULTS.md)
passes its frozen A/B/A stage and independent audit with actual execution.
Against strong history-retaining rebuilding, reuse raises joint completion
173→189/216 with16 paired gains and no losses; late-B queries28→31/36,
return queries72/72 in both arms. Full paid observations47,227→46,898,
a329 (0.70%) saving; model CPU rises15.76%. All27 remaining reuse fallbacks
are in B:16 execution-only and11 query-only. Independently matched posthoc
truth finds the16 execution-only goals infeasible under the original risk
limit, but their acquired upper bounds still exceed2. Next test coupled
risk-constrained impossibility certificates on these paid snapshots, then
changed-R-dependent query evidence. Twenty producer/nine audit tests pass;
science/audit run once, exit0/stderr0,432 targets and2,940 auxiliary decisions
retained. Known-type/change/equality interfaces and H2 policies remain;
the original scientific Gate remains FAIL and U006 remains unstarted.

[V255 joint-unresolved type acquisition](reports/JOINT_UNRESOLVED_TRAJECTORY_V255_RESULTS.md)
passes its frozen qualification: combined terminal projections72/72 versus
fresh fixed-RR56/72, sixteen paired gains and no losses or false certificates.
Full paid observations, including source, fall48,112→30,208 (37.21%);
all three treatment lives stop early. Nineteen focused tests and independent
audit pass once; 360 public projections and 2,460 intermediate decisions are
checked. Science/audit exit0, stderr0. Next integrate the frozen direct/filter
mechanism into fresh full A/B/A against strong history-retaining rebuilding,
including execution risk and every fee. This remains a stationary known-type
qualification; projections are not independent episodes. V251 remains10/11;
the original scientific Gate remains FAIL and U006 remains unstarted.

[V254 direct executable-trajectory evidence](reports/EXECUTABLE_TRAJECTORY_V254_RESULTS.md)
passes its frozen qualification on the same 48,384 fresh observations:
goal certificates 50→59/72, risk 48→56/72, zero paired losses or false
certificates; combined readiness remains 48/72. Certificate CPU falls
73.31→10.81 s. Independent audit is valid for 180 decision pairs; 22 initial
tests and one repair regression pass. A cost-string normalization error caused
the first audit failure, retained before repair and successful re-audit;
science runs once. Next compare fixed round-robin with current joint-unresolved
type sampling, then qualify complete A/B/A integration. This is stationary
known-type evidence, with no interaction-saving claim. V251 remains 10/11;
the original scientific Gate remains FAIL and U006 remains unstarted.

[V253 compatible paid return evidence](reports/PAID_RETURN_VIEWS_V253_RESULTS.md)
completes 144 frozen endpoint pairs and 144 new TWO_WAY plans; independent
audit valid, zero failures and 16 focused tests pass once. Both acquisition
arms retain query/combined readiness 48/72 and execution certificates 72/72.
All point choices and 24 SHORT-to-RETRY blockers per arm remain unchanged;
UNIFORM loses two risk-query certificates. Reuse adds zero observations,
but provides no readiness or cost benefit. Stop quota/TWO_WAY refinement.
Next test directly observed executable-continuation consequences and action
value differences against row inference under a frozen full primitive budget.
This is a new, untested exploratory mechanism. V251 remains 10/11; the original
scientific Gate remains FAIL and U006 remains unstarted. Producer/audit exit 0;
producer retains seven SLSQP clipping warnings, audit stderr 0.

[V252 retained information-axis diagnosis](reports/INFORMATION_AXES_V252_RESULTS.md)
completes 48 endpoints and 144 candidate states; independent audit valid,
zero failures and 20 focused tests pass once. QUERY_SHARED retains 19 distinct
full-region bad endpoints, giving a same-evidence, original-region certificate
ceiling of 53/72, below the required 54. Actual V251 returns remain 48/72 and
its stage remains 10/11. Six endpoints remain bad at empirical R; all fixed
S/D-centered candidates are rejected, without proving the full bad space empty.
Next compare existing ONE_WAY and TWO_WAY evidence on all return targets at
their own chronological snapshots, using compatible paid native B observations.
No new samples or query certificates; producer/audit exit 0, stderr 0.
The original scientific Gate remains FAIL; U006 remains unstarted.

[V251 query-driven shared acquisition](reports/QUERY_SHARED_ACQUISITION_V251_RESULTS.md)
completes 648 targets and 4,680 auxiliary queries; independent audit valid,
zero failures and 17 focused tests pass. The stage passes10/11: focused arms
reach late-B34/36 versus uniform33/36 and save272 observations (0.56%),
but all arms retain return48/72. Model CPU rises81.63%. No A phase stops
early or releases budget; both QUERY arms have identical216-target histories.
All24 SHORT-to-RETRY return blockers remain despite concentrated S/D evidence.
Next end quota tuning and isolate R information versus complete joint-region
uncertainty at these frozen endpoints before choosing acquisition/model changes.
Producer/audit exit0; original Gate unchanged. This is exploratory evidence on seen layouts.

[V250 acquisition schedule reachability](reports/ACQUISITION_SCHEDULE_SEARCH_V250_RESULTS.md)
completes eight plans and 1,728 decisions, with independent audit valid,
zero failures and 16 tests passing once. Two plans reach late-B27/36,
but all eight retain return48/72; none is a budget-quality witness.
Those late-B plans charge48,384, 592 above V249. All 192 failed return
queries have zero true terminal regret; certification remains unresolved.
Next allocate shared evidence to unresolved current/future type queries and
stop at certification, rather than increasing uniform quotas. Producer/audit
exit0; original Gate unchanged. This is exploratory evidence on seen layouts.

[V249 fixed shared-probe timing](reports/SHARED_PROBE_TIMING_V249_RESULTS.md)
completes 648 fresh lifecycle decisions and fails 2/11 frozen conditions,
with independent audit valid, zero failures and 17 tests passing once.
BEFORE/DEFERRED tie all 72 paired returns: 48/72 queries and 47,792 full charged
observations. REBUILD charges 48,256; the net 464 saving does not identify an
early-probe timing benefit. All 24 failed returns retain SHORT-to-RETRY blockers.
Next diagnose information requirements under the complete budget before learning
allocation across queries and episodes. Complete artifacts were retained, but the
producer tool reported exit143; that status remains recorded. Original Gate unchanged.

[V248 retained endpoint region diagnosis](reports/ENDPOINT_REGIONS_V248_RESULTS.md)
completes 48 endpoints and 96 candidate states, with independent audit valid,
zero failures and 17 targeted tests passing. Complete regions contain bad kernels
at 23/24 ONE_WAY and 24/24 JOINT_PREDICTION endpoints; with RETRY at its empirical
center, 21/24 and 24/24 remain bad. Original-decision, same-region certificate
ceilings are 49/72 and 48/72, below 54. Next test earlier shared S/D acquisition
against equal-quota delayed acquisition and strong REBUILD over complete lifecycles.
No new observations were acquired; the original Gate is unchanged.

[V247 joint predicted query acquisition](reports/JOINT_PREDICTION_RETURN_V247_RESULTS.md)
completes 144 fresh return targets and fails the frozen conditions (4/5),
with independent audit valid and 24 focused tests passing. Both arms certify
and jointly complete the same 48/72 targets and charge 46,672 observations.
All 557 new choices select RETRY; 472 even predict a larger joint deficit.
Matched histograms expose loose fixed-tangent predictions. The failed one-batch
proxy is retained without adoption. Next distinguish true region obstructions,
then test shared mechanism acquisition before return within a complete matched
lifecycle budget. The original Gate is unchanged.

[V246 common-inheritance return isolation](reports/COMMON_INHERITANCE_RETURN_V246_RESULTS.md)
completes 144 fresh return targets and fails the frozen stage conditions (4/5),
with independent audit valid and 18 focused tests passing. Both arms certify
and jointly complete the same 48/72 targets and charge 46,672 observations;
every paired outcome and cost ties. All 24 SHORT-versus-RETRY query blockers
remain despite 557 active choices. The failed single-candidate KL rule is not
adopted. Next target the joint evidence needs of all unresolved goal/risk
comparisons, then qualify acquisition before another complete lifecycle.
The original Gate is unchanged.

[V245 query-directed acquisition](reports/QUERY_ALLOCATION_LIFECYCLE_V245_RESULTS.md)
completes 648 fresh targets and fails the frozen stage conditions (6/11 pass),
with independent audit valid and 22 focused tests passing. The single-goal
bad-kernel KL rule leaves return quality at 48/72, reduces late-B quality
from ONE_WAY's 28/36 to 25/36, and increases charged observations by 944.
All three losses follow changed A evidence inherited into B; the new branch
never activates in B. The failed rule is retained without adoption. Next fix
common inheritance to isolate return acquisition, then address the joint
evidence needs of current and later queries. The original Gate is unchanged.

[V244 complete-region return-query diagnosis](reports/GOAL_JOINT_REGION_V244_RESULTS.md)
finds strict bad kernels in all eight query regions and all original execution
events for 19 of 24 ONE_WAY return unknowns. At the fixed terminal prefixes,
proof improvements within these regions can reach at most 53/72 return
certificates, below the frozen 54/72 requirement. Eighteen focused tests and
independent audit pass; no observations or certificates are added. Next change
query acquisition allocation on a fresh matched lifecycle, with certificates,
budgets, stopping and the strong rebuilding control fixed. V243 and the original
Gate remain unchanged.

[V243 bidirectional evidence consolidation](reports/BIDIRECTIONAL_LIFECYCLE_V243_RESULTS.md)
completes 648 targets across three matched arms. TWO_WAY imports 5,488 paid
native B observations on returning to A, but both reuse arms certify 48/72
return queries and complete 145/216 targets jointly. TWO_WAY costs 42,112
observations versus ONE_WAY's 41,952 and REBUILD's 48,240; the frozen stage
fails 2 of 11 conditions. Twenty focused tests and full independent audit
pass with zero binary endpoint tolerance. All 24 return failures remain
query-only and include the goal SHORT-versus-RETRY comparison. Next test
whether candidate bad kernels survive all compatible paid constraints
before choosing between better evidence use and query-directed acquisition.
The original Gate is unchanged.

[V242 matched online reuse versus rebuilding](reports/REUSE_REBUILD_LIFECYCLE_V242_RESULTS.md)
completes 432 targets on three fresh lifecycles. Reuse saves 752 observations
(1.57%) and completes 130/216 targets jointly versus 125/216, but late-B
26/36 and A-return 48/72 miss the frozen quality requirements. Independent
audit retains `valid=false`: 18 binary endpoint checks expose slight inward
rounding in the shared scalar solver. The solver is repaired without changing
the Jeffreys model; 12 targeted tests and five independent exact fixtures pass.
The cohort remains unchanged. All A-return acquisition is query-blocked;
10,400 paid observations from unchanged B rows are excluded from A evidence.
Next isolate bidirectional evidence consolidation using the repaired solver,
with fixed certificates, acquisition, budgets and strong rebuilding control.

[V241 complete convex query qualification](reports/CONVEX_QUERY_QUALIFICATION_V241_RESULTS.md)
integrates all nine audited V240 comparisons into the full 24-case qualification.
Positive controls improve from 11/12 to 12/12; four of twelve old failures
remain certified, with zero false certificates. The frozen stage condition
is met. Twelve new integration tests and independent audit of all 144
comparisons pass, without new observations or optimization. Eight failures
remain uncertified. Next compare reuse against strong rebuilding on a fresh
matched lifecycle with the same online evidence, acquisition and stopping rules.

[V240 convex query-null diagnosis](reports/CONVEX_QUERY_NULL_V240_RESULTS.md)
distinguishes the nine remaining cases without acquiring observations.
Eight failures admit exact bad kernels in their fixed necessary-projection
regions; numerical precision and retry partitions cannot repair those regions.
The remaining positive comparison has a continuous global certificate:
its log-evidence lower bound is 13.822 versus the threshold 6.867.
Twelve focused tests and independent audit pass; old qualification is unchanged.
Next integrate the continuous proof into full qualification and redesign
lifecycle acquisition for the eight genuine region obstructions.

[V239 same-endpoint joint qualification](reports/LIFE_END_JOINT_EVIDENCE_V239_RESULTS.md)
uses the unchanged V235 engine and V238 paid endpoint tapes. Retaining source
evidence restores all nine regressed positive controls, reaching 11/12, while
the same four old failures remain certified. The stage condition still fails.
Six new tests and independent audit of 144 comparisons pass, with no new
observations or replay. Next test feasible bad kernels versus loose global
bounds for the nine uncertified cases before changing acquisition or proceeding
to matched rebuilding and lifecycle amortization.

[V238 life-end predictive qualification](reports/LIFE_END_QUERY_EVIDENCE_V238_RESULTS.md)
evaluates the original 24 policies using already-paid complete-life evidence.
Old failures improve from 0/12 to 4/12, but positive controls fall from the
early joint method's 11/12 to 2/12; the stage condition fails. Two controls
have 384 paid source samples per row and no validation samples, making the
conditional evidence identically one and discarding all source constraints.
Sixteen tests and independent audit of 144 comparisons pass, with no new
samples or Gate changes. Next use the existing V235 joint engine on these
same endpoints to isolate retaining source evidence, then test matched
rebuilding and lifecycle amortization after qualification.

[V237 acquisition-budget feasibility](reports/ACQUISITION_BUDGET_V237_RESULTS.md)
derives necessary fresh-suffix costs from the three fixed GAP risk witnesses.
Reaching 75% exclusion probability for each requires at least 3261.94 expected
new observations, exceeding the matched GAP/BALANCED headroom of 2896;
two lives have power upper bounds of 8.67% and 35.71% within their margins.
This closes append-only repair with other lifecycle costs held fixed.
No matched REBUILD cost exists in this cohort. Twelve tests and independent
audit pass, with no new samples or Gate changes. Next qualify whole-life-end
knowledge using already-paid later evidence, with explicit certification timing,
then establish matched rebuilding and test lifecycle amortization.

[V236 source-trained predictive evidence](reports/SOURCE_PREDICTIVE_EVIDENCE_V236_RESULTS.md)
uses frozen row-specific source training and validation-only likelihoods.
All six primary V235 risk witnesses remain admitted; the three old shared
rectangle witnesses are excluded. Four primary witnesses cannot be excluded
by any normalized mixture of the same validation likelihood, regardless of
source prior. The frozen continuation condition fails, so full qualification
is skipped and V236 is not adopted. Thirteen tests and independent exact audit
pass, with no new observations or Gate changes. Next test acquisition-budget
feasibility and whether additional evidence can preserve the reuse advantage.

[V235 necessary-row joint evidence](reports/JOINT_QUERY_EVIDENCE_V235_RESULTS.md)
excludes all 15 fixed old witnesses but certifies 0/12 old failures and
11/12 positive controls on the same 24 snapshots; it is not adopted.
All six primary SHORT/RETURN risk blockers admit new exact bad-ranking
witnesses, even with M <= L. Their observed likelihood separation is smaller
than the neutral mixture penalty, so numerical precision cannot repair these
six regions. The shared positive blocker remains unknown. Thirty tests and
three independent audits pass, with no new observations. Next establish
source-conditioned predictive evidence and its source/validation boundary,
then qualify it once with all acquisition costs retained.

[V234 shared-prefix qualification](reports/SHARED_PREFIX_SCORE_V234_RESULTS.md)
uses complete detour/retry rows and exact conditional-gap rectangles on the
same 24 snapshots. It restores four positive controls, retaining 11/12;
old failures improve to 2/12, with the extra repair due solely to the smaller
joint event budget's direct threshold. The frozen adoption condition remains
unmet. Three exact terminal-rectangle witnesses remain, including a positive
gap of 0.051480328; six original SHORT/RETURN risk blockers persist.
Fifteen tests and independent audit of 144 comparisons pass, with no new
observations. Next establish necessary-row joint query evidence and its
chronological validity, checking substantive differences from V232 first.

[V233 paired query-score qualification](reports/PAIRED_QUERY_SCORE_V233_RESULTS.md)
reconstructs actual paid observation order and tests only necessary operator
rows on the same 24 snapshots. It certifies 1/12 old failures but retains only
7/12 positive controls; it is not adopted. All five positive regressions involve
RETURN versus RETRY: four have about 80% zero paired scores, while another
also leaves 1360 retry observations unused. Seven old failures still have
SHORT versus RETURN risk blockers. Nineteen focused tests and independent
replay of 144 comparisons pass, with no new observations. Next qualify
shared-prefix conditional continuation differences with a newly frozen joint
confidence budget; the original scientific Gates remain unchanged.

[V232 global query likelihood qualification](reports/KERNEL_QUERY_PROFILE_V232_RESULTS.md)
implements outward dual bounds and complete RETRY probability partitions on
24 frozen V231 snapshots. Old failures remain 0/12 certified; positive controls
retain 11/12. Twelve new same-kernel counterexamples satisfy all 50 applicable
product-CS prefix constraints, including the positive regression. Seventeen
focused tests and both independent audits pass, with no new observations.
The confidence family still admits wrong rankings; V229/V231 are unchanged.
Next qualify direct paired action-score confidence using only necessary
operator rows and the original paid observation order.

[V231 oracle acquisition lifecycle](reports/ORACLE_GAP_LIFECYCLE_V231_RESULTS.md)
completes three fresh A→B→A′ lifecycles with known types and immediate
per-batch pooling. GAP costs 45488 observations versus BALANCED's 48384,
while late-B query certification improves from 23/36 to 26/36. A′ remains
48/72 for both: all 24 normal-type targets exhaust their cap. Eleven selected
terminal regions admit verified regret >.05 counterexamples for every pure
query policy. Thirteen tests and independent replay of 432 histories and
47 countermodels pass. A fixed joint-kernel candidate preserves 12 retained
true kernels and excludes all 11 saved countermodels for selected policies;
this produces no new query certificates. V229 remains rejected. Next implement
globally bounded query-null likelihood tests on retained evidence before
another paid lifecycle.

[V230 action-gap qualification](reports/ACTION_GAP_V230_RESULTS.md)
implements joint categorical confidence and candidate-specific multibatch
acquisition. Six fixed failure continuations improve from 0/6 to 1/6, saving
32 observations while model time rises 2.78 times. Four oracle joint regions
each admit a verified regret >.05 counterexample for every pure query policy;
16 witnesses include unchanged A constraints for B. All three independent
audits and 15 focused tests pass. V229 remains rejected. Next test budget-matched
gap-directed acquisition with known types before another lifecycle run.

[V229 fresh paid scoped lifecycle](reports/SCOPED_LIFECYCLE_V229_RESULTS.md)
completes 12 A→B→A′ lifecycles and 2592 target histories, with 4/6 frozen
conditions passing. Repair saves 30608 observations against cumulative rebuilding
and 6368 against parameter adaptation; both paired cost intervals are positive,
and the model processing ratio is 1.016. Late B jointly resolves/certifies
69/144 targets and A′ 113/288, below the required 108 and 216. A/A′ paths match
exactly across arms and A′ execution certifies 284/288; the remaining bottleneck
is query certification and acquisition, with low actual regret but broad bounds.
Six retained counterfactuals do not certify all queries merely by pooling the
current member. Next derive action-comparison confidence and candidate-aware
multi-batch acquisition before another frozen paid experiment.

[V228 scoped mechanism repair](reports/SCOPED_REPAIR_V228_RESULTS.md)
implements the A→B→A′ contract, 18 hidden operator/permutation hypotheses,
separate A/B confidence banks, exact query regret bounds and an optimistic
infeasibility certificate. REBUILD_CS has the same paid B source interface
and cumulative statistics as REPAIR_CS, isolating old-contract reuse.
Twenty tests and 648 deterministic integration records pass, including 1944
query bounds; no environment observations were drawn. Exact task qualification
finds 96/288 B goals infeasible under the unchanged risk .05 and utility 2
requirements. These are classified separately from uncertified learning and
execution success. This validates the new framework, with no performance Gate.
Next freeze source budgets, fresh streams and lifecycle cost/quality conditions,
then compare repair, cumulative rebuilding and ordinary parameter adaptation.

[V227 execution/model interface repair](reports/RETAINED_MODEL_V227_RESULTS.md)
passes 4/4 interface checks on all 1152 retained V226 histories, with no new
environment samples. Execution, acquisition, commits, certification and fees
remain identical. Keeping compatible source knowledge reduces LOW_UNION late
query regret from 0.14031 to 0.01017, but also lowers LOW_FIXED to 0.00667;
the query improvement is a shared interface repair. Four tests and independent
audit 86/86 pass. V226 remains scientifically rejected at 3/6; its 15488-sample
deficit against FULL_FIXED and 111/144 late certificates are unchanged.
Next complete the coverage proof and confidence budget for the bounded
[V228 A→B→A′ repair design](specs/SCOPED_REPAIR_V228_DRAFT.md), then freeze its
local-repair, full-rebuild and ordinary-parameter controls.

[V226 limited initial source evidence](reports/LIMITED_SOURCE_V226_RESULTS.md)
passes 3/6 Gates. LOW_UNION saves 34464 target samples against LOW_FIXED
and 35280 against ordinary classified predictive updates, but still costs
15488 more total samples than FULL_FIXED and certifies 111/144 late targets
versus 144. Quality, applicability and full-reference recovery fail.
Retained diagnostics locate a core interface problem: 20 late fallbacks
discard still-compatible source models, raising their query regret sum
from 0.272 to 19.01167 while certification remains failed. Accumulation
does narrow bounds and resolve assignments; execution fallback must be
separated from model knowledge retention before bounded mechanism repair.
Six tests and independent replay 77/77 pass; all risk checks pass. Preserve
this negative result and close the frozen recovery method without budget
or Gate retuning. General strategic learning remains unresolved.

[V225 matched mixture confidence sequences](reports/MIXTURE_CONFIDENCE_V225_RESULTS.md)
passes 4/5 Gates: STRONG_REFERENCE passes, LEARNING_EFFECT fails.
UNION_CS uses 22416 target samples versus unchanged original SET's 37264
and certifies 144/144 late targets versus 140. The paired sample-saving
and utility CIs are positive. FIXED_CS already saves 14624 of the net
14848 samples; accumulation adds only 224, below the frozen 64/life
learning requirement. All risk and coverage checks pass, as do six tests
and independent replay 123/123. Freeze this statistical method and next
test whether accumulation recovers limited initial source knowledge,
against ordinary parameter learning and the fully supplied CS reference,
counting all source and target costs. General strategic learning remains
unresolved; unknown mechanism changes need a new certificate scope.

[V224 unchanged strong SET reference](reports/STRONG_REFERENCE_V224_RESULTS.md)
passes 4/5 Gates; STRONG_REFERENCE fails. ORIGINAL retains the complete
old SET and its source bounds. UNION uses 37664 target samples versus
ORIGINAL's 36832, with both certifying 137/144 late targets. Learning saves
1808 samples against the calibration-matched FIXED library, but its 2640
extra samples relative to ORIGINAL leave a net 832-sample deficit. The
paired strong-reference cost CI is unfavorable. All risk, coverage and
assignment checks pass; four tests and independent replay 122/122 pass.
Next test time-uniform mixture confidence sequences, matching the initial
source region of fixed and cumulative controls to separate statistical
improvement from learning. General strategic learning remains unresolved.

[V223 fresh cumulative-confidence and paid-detour factorial](reports/DETOUR_SUPPLY_V223_RESULTS.md)
passes all 5 Gates. UNION_DETOUR uses 40496 target samples and certifies 140/144
late targets, versus FIXED_DETOUR's 66640 and 89. Without compulsory detour,
UNION_SET uses 35248 versus FIXED_SET's 63744 and certifies 143 versus 90;
the paired sample-saving CI is positive in both supply layers. The pilot
interaction is negative and compulsory detour costs another 5248 samples
relative to UNION_SET. All history risks and library coverage/assignment
checks pass. Eight tests and independent replay 122/122 pass. The four-arm
joint confidence budget is more conservative than V221, so these results
do not establish superiority over historical strong SET. Next preserve
the original source bounds and pair the full original SET, a calibration-
matched fixed library, and the cumulative model on fresh observations.
General strategic learning remains unresolved.

[V222 cumulative confidence with uncertain assignments](reports/ASSIGNMENT_UNION_V222_RESULTS.md)
is ready for a fresh test, with limited retained-trajectory gains. All 288
FROZEN targets enter the confidence model, including failures and ambiguous
assignments. The 4/8-target exact unions and DP outer envelopes have identical
endpoints in all 24 comparisons. After 24 targets, SHORT/RECOVERY widths shrink
3.10%/4.37%; DETOUR has zero target observations and no shrinkage. Of 275 fixed
next-target sampling prefixes, only two gain certification, belonging to one
target; none of the 36 targets certifies earlier. Next test source-only versus
cumulative confidence crossed with SET versus one paid DETOUR batch within
the same total target budget, separating learning from data supply. Four tests
and independent audit 364/364 pass. No new environment samples were drawn;
new sampling efficiency and general strategic learning remain unresolved.

[V221 chronological target-evidence persistence](reports/PERSISTENT_EVIDENCE_V221_RESULTS.md) passes 5/6 Gates.
PERSIST correctly commits 217 targets and 31376 samples, but uses
38272 target samples versus FROZEN SET's 35296 (+8.4%). Both certify
139/144 late targets. Full-query regret improves significantly, while the
paired cost CI is unfavorable. Of 217 commits, 198 leave all certificate
bounds unchanged; the remaining 19 change only SHORT endpoints. Three
retained local factorial snapshots show accumulated predictive counts
raising the query proxy past the unchanged stop threshold without changing
actions or the certificate lower bound. Processing is faster (3.63 versus
8.36 seconds), but the sampling goal fails. Both arms have zero observations
after first unique identification. Next address cumulative confidence with
uncertain target assignments, retaining all observations and feasible
assignment branches; first validate exact short-prefix unions and safe
outer envelopes. Four tests, first independent replay 121/121 and source
retention 28/28 pass. Historical failures remain preserved and general
strategic learning is unresolved.

[V220 observation-branch integration](reports/BRANCH_ACQUISITION_V220_RESULTS.md) passes 5/7 Gates.
Under identical fixed sources, pilot, real planning and fresh paired target
prefixes, BRANCH saves 18016 target samples versus MEAN (44976 versus
62992) and certifies 134/144 late targets versus 103. The isolated branch
prediction effect is supported, but SET remains cheaper (36160 target
samples), certifies 139 and has significantly higher utility. BRANCH
requires 364463 hypothetical plans and 306.75 seconds of target processing
versus SET's 8.93 seconds. Six additional late failures retain two candidates
and spend 18–20 final batches on a flat certificate lower bound; one reverse
success gives the net five-certificate deficit. Stop single-step acquisition
tuning and next test chronological persistence of certified unique-candidate
target evidence, with association uncertainty and cumulative confidence
frozen first. SET has 26208 such paid observations left unused. Four tests,
first independent replay 108/108 and source retention 28/28 pass; historical
failures remain preserved and general strategic learning is unresolved.

[V219 fixed-source acquisition isolation](reports/FIXED_SOURCE_ACQUISITION_V219_RESULTS.md) passes only RISK (1/6).
MEAN and SET use identical retained FULL source counts, pay the same
41472 historical source samples, and share fresh paired target prefixes.
MEAN needs 64048 target samples versus SET's 38240, certifies only
101/144 late targets versus 141, and loses 0.41797 utility with a fully
negative paired CI. Overall target acquisition is therefore a bottleneck
even under the fixed FULL library. Retained examples show MEAN exhausting
384 samples while SET certifies after 32 RECOVERY samples; 63 RECOVERY
batches eliminate candidates despite no predicted gain. Next keep source,
pilot and stopping fixed and test candidate-conditioned observation
branches before adding target consolidation. Two tests pass; independent
replay passes 108/108 after a zero-sample counter read repair, with the
failed audit and both code versions retained. Earlier frozen failures
remain preserved; general strategic learning is unresolved.

[V218 joint source/member acquisition](reports/JOINT_ACQUISITION_V218_RESULTS.md) passes RISK and APPLICABILITY (2/6).
JOINT certifies 112/144 late targets versus MEMBER's 78 and correctly
reuses the library 108 times, but uses 114240 samples versus MEMBER's
112672, LOCAL's 96608 and FULL's 77584. All sources reach their 1152
caps: source costs match FULL, while target costs remain 36656 higher.
Late query regret is 0.00760 and true utility 2.41925; quality fails
because LOCAL certifies 116 and the utility difference CI extends below
-0.05. Retained diagnostics show uneven source operator allocation and
25600 samples from singleton-candidate targets left outside persistent
knowledge. Next hold FULL's source evidence fixed and compare MEAN with
the original SET target acquisition, then separately test observation
branches or target consolidation. Independent replay 62/62 and source retention 27/27
pass; earlier frozen failures remain preserved. This experiment assumes
paid resets of retained opaque sources; general strategic learning remains
unresolved.

[V217 query and certificate deficit acquisition](reports/DEFICIT_ACQUISITION_V217_RESULTS.md) passes only RISK (1/6).
Late full-query regret improves to 0.00645 versus IDENTITY's 0.40672 and
FULL's 0.02317, but only 87/144 late targets certify, versus LOCAL's 125.
DEFICIT uses 98192 samples, IDENTITY 102736, LOCAL 95056 and FULL 68128.
Source savings of 29248 versus FULL are outweighed by 59312 extra target
samples. Query-first acquisition can leave too little budget for the
certificate, while a frozen weak source library repeatedly charges each
target for the same deficit. Next test joint source/target acquisition,
explicitly permitting paid resets of retained opaque source environments
within the existing source caps, and compare against static FULL.
Independent replay 60/60 and source retention 27/27 pass; earlier frozen
failures remain preserved and general strategic learning is unresolved.

[V216 source certification stopping](reports/SOURCE_STOPPING_V216_RESULTS.md) passes only RISK (1/5).
EARLY saves 29632 source samples but adds 62624 target samples, using
106608 total versus FULL's 73616 and LOCAL's 94272. Late certification
falls to 41/144, utility to 0.85137, and query regret rises to 0.56728.
ORACLE uses the identical early-source library and certifies all 144 late
tasks without target samples. All EARLY target observations were spent
on identity discrimination; 99 budget-exhausted targets already met the
query proxy but still lacked a certificate. The next intervention should
acquire evidence for query/certificate deficits while retaining identity
ambiguity, rather than continue max-min point-TV identity sampling.
Independent replay 60/60 and source retention 25/25 pass; the early-stop
hypothesis is rejected and previous frozen failures remain preserved.

[V215 query-directed source calibration](reports/QUERY_CALIBRATION_V215_RESULTS.md) passes COST,
QUALITY, RISK and APPLICABILITY but fails CALIBRATION_EFFECT. Both the
new allocation and the unchanged SET baseline use 60816 samples versus
LOCAL's 95152 (36.1% fewer), with savings CI [2425.33,3288]. All 144 late
targets certify, with no wrong transfers or risk violations. However,
all 36 terminal source count tables and all 288 target histories are
identical between the two methods: continuing to pay the full source
budget restored 384 samples per operator in this stream. The new
allocation has zero measured incremental effect. Next treat 1152 as a
source cap and stop at certification, comparing total source plus target
cost against a paired full-budget control. Independent replay 57/57 and
source retention 23/23 pass; earlier frozen failures remain preserved.

[V214 query-sufficient ambiguous mechanism sets](reports/QUERY_SUFFICIENT_V214_RESULTS.md) passes QUALITY,
RISK, APPLICABILITY and STOP_EFFECT; COST fails. With unchanged paid
calibration and certificates on fresh paired streams, SET stops when
all retained candidate point models support the selected full queries.
It uses 81072 samples versus STRICT's 104576 and LOCAL's 95776. Savings
over strict identity have lifecycle CI [1028,2894.67], with query
noninferiority; savings over LOCAL have CI [-124,2457.33]. Late transfer
certifies 122/144 tasks, including 52 ambiguous sets containing the true
identity; no wrong transfers or risk violations occur. Four weak-source
lifecycles erase robust total-cost evidence. Next separate chronological
library-maintenance effects from query-directed calibration needs using
retained paths before freezing another experiment. Independent replay
56/56 and source retention 21/21 pass; finite complete-library scope holds.

[V213 unknown finite-library mechanism identity](reports/LATENT_MECHANISMS_V213_RESULTS.md) passes QUALITY,
RISK and IDENTITY but fails COST. Opaque tasks reveal no weather/group
label; a declared stable three-kernel family is learned from three paid
calibration tasks. LATENT correctly identifies and certifies 125/144 late
tasks, with no wrong identifications or risk violations, mean true utility
2.92685 and full-query regret 0.041. Total samples 96016 versus LOCAL's
96528 give mean lifecycle savings 42.67, CI [-488,586.67]. Paid calibration
and identity discrimination offset target reuse savings; privileged ORACLE
requires 51312 samples. Retained-prefix exploratory replay suggests query-
sufficient ambiguous candidates could save 16736 samples, but this does
not change the frozen FAIL. Next freeze that stopping rule and validate
on fresh streams, keeping calibration unchanged. Independent replay and
source retention 19/19 pass; scope remains complete finite-library reuse.

[V212 contract-aware direct-count baseline](reports/CONTRACT_BASELINE_V212_RESULTS.md) retains all five old
gates in both orders but rejects the added incremental-advantage hypothesis.
DIRECT shares weather-conditioned real counts under the same supplied
contract, with no condition selection or maintenance. It needs 12640
samples in either order, versus REVISED's 14944 and 19200, and certifies
all 48 late tasks without new samples. Late pre-query regret is zero for
both methods; old-query retention and true risk hold. Extra maintenance
raises some constrained-plan utilities but does not satisfy the frozen
cost-and-query advantage criteria. Independent replay passes 57/57 per
order and source retention 38/38. The established positive result is
contract-authorized evidence reuse; the next learning question is mechanism
identity/applicability discovery when the correct grouping is not supplied.

[V211 fresh-stream and task-order replication](reports/ORDER_REPLICATION_V211_RESULTS.md) passes all five
frozen gates in both the original-order replication and a predeclared
interleaved order, with the V210 algorithm unchanged. Shared maintenance
uses 12352 versus 41760 member samples (70.4% fewer) and 15424 versus
43088 (64.2% fewer), respectively. Both certify all 48 late tasks, select
SHORT/DETOUR weather in 12/12 lifecycles, and preserve old-query quality
and true risk limits. Independent replay passes 57/57 per order; source
retention 36/36. A shared control without maintenance uses fewer samples
and also preserves old-query quality in this batch, but selects DETOUR
weather in only 8/12 and 7/12 lifecycles. The next decisive comparison is
a contract-aware baseline that directly stores weather-conditioned counts,
testing learning/maintenance value beyond certificate reuse itself.

[V210 contract-consistent strategic maintenance](reports/STRATEGIC_MAINTENANCE_V210_RESULTS.md) passes all five
frozen gates. Shared certificates plus paid condition maintenance require
15440 samples versus 42736 for the same learner/maintenance with member
certificates (63.9% fewer); mean lifecycle savings 2274.67 have paired
95% CI [1940,2560]. All 48 late tasks certify; 46 require no new samples.
SHORT and DETOUR weather selection reach 12/12, old-query regret does
not increase, and all valid-contract risk limits hold. A shared-certificate
control without maintenance uses 13264 samples but learns DETOUR weather
in only 5/12 lifecycles and doubles old risk-query regret. Independent
replay passes 57/57 and source retention 18/18. The next stage is frozen
replication with fresh sampling and unseen task order. This supports the
explicit cost-invariant task family, not general invariance discovery or
the original game's unrestricted strategic learning.

[V209 contracted risk-evidence reuse](reports/CONTRACTED_RISK_REUSE_V209_RESULTS.md) passes COST, QUALITY and REUSE (3/5),
but LEARNING and old-query retention fail. With an explicit cost-invariant
kernel contract, shared certificates require 11216 samples versus 41648
for the same learner with member certificates; all 48 late tasks certify
without new samples, and valid-contract risk limits hold. Mean lifecycle
savings are 2536, paired 95% CI [2434.67,2633.33]. Old risk-query regret
increases and DETOUR weather selection is only 5/12. The next bottleneck
is strategic knowledge maintenance after task certification stops acquisition.
A frozen counterfactual violating the contract invalidates all 24 shared
wet/low initial certificates. Independent replay passes 57/57 after a
counterfactual-only evaluator correction; acquisition and training ran once.
The scientific decision remains NOT_SUPPORTED; general invariance discovery
and the original H2/U005/U006 boundaries are unchanged.

[V208 task-sufficient constrained acquisition](reports/CONSTRAINED_ACQUISITION_V208_RESULTS.md)
passes QUALITY, LEARNING and RISK_RETENTION; COST fails.
REVISED certifies 45/48 late tasks with mean true goal utility 2.34947,
equal to LOCAL, while late pre-acquisition own-query regret is zero.
Final SHORT/DETOUR weather selection is 12/12 and 11/12; all histories
satisfy true risk limits and old-query regret improves.
Total samples are 39840 versus LOCAL's 39984. Mean lifecycle savings
12 have paired 95% CI [-1.3333,28], below the unchanged cost gate.
All 48 late acquisition histories match LOCAL exactly. The remaining
bottleneck is cross-task risk-evidence reuse under an explicit mechanism
contract; further allocation tuning is paused. Four tests, independent
56/56 and source 15/15 pass; main/audit once 19.53/10.02s, stderr 0.
The overall scientific decision remains NOT_SUPPORTED.

[V207 member probes and continuation acquisition](reports/CONTINUATION_ACQUISITION_V207_RESULTS.md)
passes LEARNING and RISK_RETENTION, but fails COST and QUALITY.
Direct member pilots and reachable continuation-threshold queries acquire
21088 retry observations for REVISED, eliminating the unobserved-retry path.
Its late pre-acquisition own-query mean regret is zero; final SHORT/DETOUR
weather selection is 11/12 and 10/12. Yet it certifies only 25/48 late tasks,
with true goal utility 1.965. Total samples are 45488 versus LOCAL's 45664;
mean lifecycle savings 14.6667 have 95% CI [-50.6667,84].
Retry consumes 46.36% of REVISED's budget: point-query disagreement resolution
competes with the member evidence needed by the hard-constrained plan.
That constrained acquisition test is completed in V208 above; quality
recovers, while member evidence cost remains equal to strong LOCAL.
Four tests, independent 56/56 and source 15/15 pass; main/audit once
40.00/11.49s, stderr 0. The scientific decision remains NOT_SUPPORTED.

[V206 paid online lifecycle](reports/ONLINE_LIFECYCLE_V206_RESULTS.md)
passes RISK_RETENTION only; COST, QUALITY and LEARNING fail.
Starting empty with every early task paid, REVISED uses 38496 samples versus
persistent LOCAL's 38480, and certifies 39/48 late tasks versus 40/48.
Mean lifecycle savings are -1.3333, paired 95% CI [-184,149.3333].
All histories satisfy true risk limits; old-query regret grows by only 0.00315.
Acquisition exposes two missing evidence paths: existing shared counts suppress
new-context probes, and maximum occupancy never samples RECOVERY_RETRY.
All three arms obtain zero retry observations. That acquisition revision is
now tested in V207 above; evidence coverage improves but constrained task
quality and cumulative benefit fail. Four tests, independent 56/56 and source
14/14 pass. One sampled run/audit take 16.37/7.25s, stderr 0; an import-path
startup failure before sampling is retained. No passing tests were rerun.

[V205 learned mechanism conditions](reports/CONDITIONED_MECHANISMS_V205_RESULTS.md)
passes TASK, CONDITION, TRANSFER and RISK_RETENTION; ACQUISITION fails.
All 12 lifecycles revise SHORT and DETOUR to weather conditions; GUIDED
chooses the critical operator in 48/48 targets and its zero-target own-query
policies have zero mean regret. It certifies 46/48 with 10528 target samples,
versus strong pilot-enabled COLD's 45/48 and 11280. Sample savings average
15.6667, paired 95% CI [14,17.6667], below the frozen minimum 16.
All target histories have zero risk violations; old GUIDED regret is unchanged.
Source learning still costs 36864 samples, so cumulative net benefit is unproved.
That paid online acquisition test is completed in V206 above. The acquisition
rule's untested-mechanism and continuation-evidence gaps are now exposed.
Eight tests, independent 93/93 and source 13/13 pass; main/audit once
9.50/3.31s, stderr 0. The overall scientific decision remains NOT_SUPPORTED.

[V204 target risk evidence acquisition](reports/TARGET_RISK_ACQUISITION_V204_RESULTS.md)
passes RISK and ALLOCATION, but fails RESTORATION and KNOWLEDGE.
GUIDED certifies 35/48 targets with 14944 new samples; the graph/cost cold
control certifies 36/48 with 14720 and higher true utility, 2.29425 versus 2.24398.
All target histories have zero risk violations. Against uniform, GUIDED saves
72.67 samples per target, paired 95% CI [52.33,94.67]; against strong cold,
the saving is −4.67, CI [−14,0]. Historical 64512 samples remain paid.
That mechanism-condition test is now completed in V205 above. Preserve
V204's failure and pause forecast and budget tuning on its four targets.
Eight tests, independent
93/93, source 11/11 and inputs 4/4 pass; main/audit once 52.32/7.75s, stderr 0.

[V203 fixed-evidence whole-policy risk planning](reports/ROBUST_ROUTE_PLANNING_V203_RESULTS.md)
passes both frozen risk/usefulness conditions with zero new samples or fits.
Complete-context uncertainty envelopes reduce true risk violations70/144→0/144
and maximum failure7.42%→3.02%. Observed-context utility retains72.00% of
the true constrained optimum, equal to the same-envelope independent learner.
Unobserved combinations require95% WAIT and retain only5.15% of optimal utility;
the absence of member risk evidence is the remaining bottleneck. Selected-leaf
pooling retains high utility and also has zero violations in this batch, but
its whole-context probability coverage is only75%, so it cannot certify members.
That acquisition test is now completed in V204 above, including a strong
graph/cost cold control and paid source costs; knowledge contribution fails.
Eight tests, independent57/57, source9/9 and inputs3/3 pass; main/audit
once0.61/0.49s, stderr0. This is retained-evidence reanalysis within the known
route grammar; general strategy and effective safe unobserved reuse remain open.

[V202 fixed-learner conditional revision and reuse](reports/CONTINUAL_ROUTE_KERNELS_V202_RESULTS.md)
passes all four frozen learning conditions in twelve independent chronological
lifecycles. SHORT and RETRY change from global sharing to weather conditioning
in12/12; final unacquired combinations gain0.16511 utility over frozen
knowledge, paired95% CI[0.12497,0.23594]. Final mean kernel TV is0.01760
and own-policy oracle regret0.00940. Manually correct weather grouping has
zero regret; old-context regret worsens0.00583 within the frozen limit.
Hard-risk planning remains unresolved:70/144 final plug-in plans exceed5%
actual failure risk, maximum7.42%; even the correct-grouping reference
violates64/144. That fixed-evidence uncertainty and condition-bias-aware
constraint-planning test is now completed in V203 above. The graph,
costs and candidate fields are supplied;64512 controlled generative samples
do not establish autonomous strategy or sample efficiency. Eight tests,
independent69/69 and source9/9 pass; main/audit once22.31/4.68s, stderr0.

[V201 structured route task](reports/STRUCTURED_ROUTE_TASK_V201_RESULTS.md)
passes all five frozen task-qualification conditions across twelve declared
contexts: eight change the goal/risk root action; four share DETOUR and then
choose different recovery actions on their actual continuation. Success needs
at least three steps. Full H4 beats receding H2 on this task by at least3.28
for goal and2.97 for risk. All hard-risk optimal mixtures satisfy F=0.05 and
improve goal utility over the best feasible pure policy by at least0.04333.
That fixed learner's chronological acquisition and reuse test is now completed
in V202 above, with oracle reserved for evaluation. V201 itself is task
qualification, with zero fits or sampled interactions; learning and old2048
H2 superiority remain open. Eight focused tests exit successfully;
independent52/52 and execution-time source8/8 pass. Main/audit once0.145/0.112s,
stderr0. The report records overwritten audit-test stdout and the subsequent
wrapper-only log-name repair; no successful check was rerun.

[V200 learned deep-state transfer](reports/DEEP_CONTROLLED_TRANSFER_V200_RESULTS.md)
completes one frozen SOURCE-only predicate/successor-model fit and own-policy
H3/H4 transfer study. Excluding H1, H4 deep cells/rows reduce4741/16214→96/299
against the union D4 baseline. LEARNED beats COARSE by0.4390 and repeated H1
by0.1722 at H4, but trails native H2 by0.8242; mean absolute success-probability
error is0.3455. No learned-policy fallback occurs. TASK also fails: only3
reward-preference changes and no goal-to-risk change. DEEP_REUSE and ADDED_DEPTH
pass; QUALITY and TASK fail, so advance=false. This does not close general
strategic learning, and the model is not adopted. Pause whole-board partition
tuning; establish a decision-discriminating task before testing local controlled
mechanism reuse or resuming a full lifecycle. Main/audit once163.71/108.26s,
stderr0; twelve focused tests, independent74/74 and frozen source12/12 pass.
Exact-support acquisition/evaluation costs are paid; no sample-efficiency or
total-cost benefit is established. Old H2/U005 FAIL/U006 unstarted stay.

[Main-line review and route change](reports/STRATEGIC_DIRECTION_REVIEW_2026-10-01.md)
ends repeated H3 root-ranking changes as the primary research direction and
suspends V198's proposed shared antisymmetric tree. The same frozen PROGRAM
beats TERMINAL in12/12 exposed replica groups across three cohorts, but beats
the same-input neighbor in only3/12; local continuation information is useful,
while further tree changes do not establish general strategic learning.

[V199 H4 reference feasibility](specs/REFERENCE_FEASIBILITY_V199.md)
now compiles one shared model for two retained kernels and14 existing queries,
plans through its own abstract successors, and replays its own policy on every
FULL ACTIVE state. Exact width0 reduces ACTIVE cells1479→508 and action
rows4400→1487 with zero utility regret and R/F/S prediction errors. Width1/64
reduces them to375/1063 with maximum regret0.008203 and component errors
0.009489/0.005/0; three coarser widths fail the frozen0.01 limits.
Layer decomposition limits this result: exact H1/H2/H3/H4 cell counts are
296/178/32/2 versus1256/189/32/2 ground cells;98.87% of eliminated states
come from H1, and H3/H4 are unchanged. V199 does not establish deep strategic
compression. Oracle construction, finite lookup mappings and successor TV
up to0.45 do not establish learnable transfer; there is no WON terminal.
The bounded learned-condition transfer test has now completed in V200 above.
Its deep compression improves on this layer limitation, but task qualification
and own-policy quality fail. A full learning lifecycle remains deferred.
Main/audit once13.29/12.22s, stderr0; independent21/21,
source7/7 and inputs5/5 pass. Eight focused tests pass after one fixture
assertion repair; its first failure is retained. H2 and old negative Gates stay.

[V198 actual-utility partition induction](reports/UTILITY_PROGRAM_PARTITION_V198_RESULTS.md)
changes split selection to actual SOURCE R-F+S action utility while retaining
continuation inputs and frozen controls. SOURCE heldout utility falls0.012420;
fresh TARGET UTILITY minus PROGRAM is -0.009715, nonpositive in all four
replicas, with48 versus45 regret roots. The neighbor-relative +0.004980 is
positive in2/4 replicas. The new learner is not adopted. Training scoring
matches actual decoding to2.22e-16; depth6 adds splits but worsens SOURCE CV,
so a strict greedy plateau is not established. Next test shared action-pair
regions with opposite leaf vectors for both directions during induction, keeping R/F/S and
SOURCE holdouts. Nineteen tests pass first attempt; audit232/232, source98/98,
inputs16/16 pass. Main/audit once77.09/45.29s, stderr0;17 training and17 audit
trees,96 exact labels,4696 TARGET virtual swipes. General strategy remains
open; H2 stays, U005 FAIL/U006 unstarted.

[V197 frozen continuation-model replication](reports/FROZEN_PROGRAM_REPLICATION_V197_RESULTS.md)
reuses every V196 model and library on one independent TARGET96 cohort, with
zero fits, SOURCE operations or configuration selection. PROGRAM minus TERMINAL
is +0.121169 and TREE32 +0.100512, both positive in all four replicas; these
benefits now repeat in all eight replicas across two cohorts. PROGRAM still
trails same-input PROGRAM_NEIGHBOR by0.035439, negative in all four replicas,
with43 versus36 regret roots. LINEAR +0.024430 is positive in only2/4 replicas;
NONLINEAR +0.006625 in1/4 and OLD_SHARED +0.024547 in2/4. Stable superiority
over the stronger baselines remains unestablished. The neighbor deficit is
reward/risk: delta R/F/S=(-0.014400,+0.021039,0). The largest loss picks an action
with failure probability1 versus0; its two directions share leaf15 and cancel
despite available validity/score distinctions. Next change SOURCE partition
induction to actual complete-vector action utility after projection, retaining
the representation and all R/F/S outputs. This one replication is closed.
Ten tests pass first attempt; audit225/225, source95/95, inputs14/14 pass.
Main/audit once54.68/17.02s, stderr0;96 new exact labels,4672 virtual swipes.
H2 stays, U005 FAIL/U006 unstarted; general strategic learning remains open.

[V196 relational continuation programs](reports/RELATIONAL_PROGRAMS_V196_RESULTS.md)
preserves both merge parents and shares twenty short continuation words.
SOURCE143/36 selects PROGRAM depth4/min4, TERMINAL depth2/min4 and neighbor k8.
Fresh TARGET96 PROGRAM minus TERMINAL is +0.169057, TREE32 +0.177590,
LINEAR +0.036687, NONLINEAR +0.070715 and OLD_SHARED +0.053673, each positive
in all four replicas. Same-input PROGRAM_NEIGHBOR is still better by0.019882:
45 regret roots versus PROGRAM59. Against LINEAR, success increases0.026563
and failure risk increases0.011000;24 new errors versus12 resolved errors
limit the claim. The continuation representation has local utility progress;
the applicability partition and general strategy remain unresolved.
The largest neighbor-relative loss already has four goal/dependency witnesses
for the preferred action; both pair directions still merge into score-only
leaf29 and cancel. This retained error loses a distinction present in the input.
Neither new decoder is adopted. Next do one fresh-start replication with all
models frozen and zero fits, before changing SOURCE applicability learning.
29 tests pass first attempt; audit233/233, source95/95, inputs12/12 pass.
Main/audit once72.34/36.35s, stderr0. Three libraries,34trees/7neighbor
configurations,6500/5004 SOURCE/TARGET virtual swipes,96 exact labels,
zero physical samples or parameter solves. H2 stays, U005 FAIL/U006 unstarted.

[V195 learned pair regions](reports/PAIR_REGIONS_V195_RESULTS.md)
uses complete positioned afterstates and SOURCE-learned three-output regions,
with a same-input RAW32 neighbor control. SOURCE143/36 selects depth4/min8
roots and RAW k32. Fresh TARGET96 TREE32 minus RAW32 is -0.091455, minus
CONDITIONAL -0.104066, LINEAR -0.150243, NONLINEAR -0.115059 and OLD_SHARED
-0.155623; every replica is negative against the last three. TREE32 has
63 regret roots and misses nine of eleven nonzero success differences.
The largest loss has both directions in leaf15, cancelling the complete
tail estimate. That leaf already contains 92 positive and 92 negative
success labels: coordinate applicability merges opposite consequences.
Neither new model is adopted. Next induce shared relational condition
programs preserving tile identity, merge dependencies and goal continuation.
Twenty-one tests pass after one faulty assertion is corrected; its first
failure is retained. Audit 228/228, source 91/91, inputs 10/10 pass;
main/audit once 74.90/30.60s, stderr0. Three libraries, seventeen trees,
seven RAW configurations, 96 exact kernels/plans/labels, zero parameter
solves. General strategy remains unresolved; H2 stays, U005 FAIL/U006 unstarted.

[V194 conditional action-pair transfer](reports/CONDITIONAL_PAIRS_V194_RESULTS.md)
selects nonnegative local complete R/F/S pair mixtures only on SOURCE143/36
groups. Goal-relative rank-stratified CONDITIONAL selects k=8, temperature=1;
the same-method PAIR98 control selects k=32, temperature=1. Fresh TARGET96
CONDITIONAL minus PAIR98 is +0.033460, positive in all four replicas, with
41 versus 61 regret roots. It remains below LINEAR by 0.026208, V192 NONLINEAR
by 0.016787 and OLD_SHARED by 0.029507. Against LINEAR, 23 resolved errors
and ten new errors still yield negative utility: losses total 4.759245 versus
gains 2.243318. The model is not adopted. Two high-loss replays show raw pair
estimates already reversed before projection; the largest loss misses a true
success difference of one with zero projection residual. Next learn transfer
applicability that distinguishes goal-reaching continuation structure.
Twenty tests, 229/229 audit, 89/89 source and 9/9 input comparisons pass;
main/audit once, 44.68/27.29 s, stderr 0. Six libraries, 38 prototype
configurations, zero parameter solves, 96 new exact kernels/plans/labels.
Designed moment features and finite H3 do not establish general strategy.
Keep H2; U005 FAIL, U006 unstarted.

[V193 retained kernel-transfer diagnosis](reports/KERNEL_TRANSFER_V193_RESULTS.md)
replays the fixed V192 model and all 96 targets. SOURCE coverage is calibrated
on 1,518 ordered action pairs, excluding the query's entire SOURCE group.
Forty-six of 50 errors and 17 of 18 new errors are within the SOURCE joint
Q95 distance; 28 of those 46 errors have opposite true tail-utility direction
to their nearest same-board SOURCE pair. Zero exact pair-label aliases appear.
The largest loss has true action gap +2.281642 but prediction -0.349365:
its nearest SOURCE tail gap is positive, while the global center combination
reverses the direction. Coverage expansion alone is not the supported priority.
Next learn conditional transfer of complete same-board action-pair consequences,
using goal-relative merge/blocker conditions and nonnegative local combinations.
Sixteen synthetic tests, 29/29 audit, 35/35 source and 8/8 input comparisons
pass; main/audit once, 7.48/8.24 s, stderr 0. No new fits, solves, features,
labels, kernels or SOURCE model evaluations. Q95 describes geometry; signed
contributions do not establish causality. General strategy remains unresolved.
Keep H2; U005 FAIL, U006 unstarted.

[V192 nonlinear relation learning](reports/NONLINEAR_RELATIONS_V192_RESULTS.md)
keeps the 98 inputs and SOURCE143/36 groups fixed, selecting an RBF model
(gamma=1, lambda=0.001) only by SOURCE-group validation. SOURCE regret roots
fall from 72 to 53 and mean regret from 0.109982 to 0.036994. Fresh H3 TARGET96
utility is lower than LINEAR by 0.024991, RELATION by 0.019763 and OLD_SHARED
by 0.013751; each contrast has two positive and two negative replicas.
NONLINEAR has 50 regret roots versus LINEAR's 42 and RELATION's 40.
The model is not adopted. Next fix this model and diagnose action-pair SOURCE
coverage and the R/F/S kernel contributions using retained roots and labels.
Eighteen synthetic tests and corrected 220/220 audit, 88/88 source and 8/8
input comparisons pass. Main runs once (47.21 s); the first audit's metadata
import crash remains retained (1.40 s, stderr 1616 bytes). Its two-field
correction passes a complete audit (28.79 s, stderr 0); no training or labels
are rerun. There are 31 fitted predictors, seven eigen decompositions and
96 kernels/plans; independent audit pays one incomplete plus 31 corrected
direct solves, without eigen/SVD repetition. General strategy remains
unresolved. Keep H2; U005 FAIL, U006 unstarted.

[V191 linear relation capacity](reports/RELATION_CAPACITY_V191_RESULTS.md)
certifies that no shared first_reward+beta·phi98 can reproduce all SOURCE143
rankings: exact margin upper bound is approximately -0.000451274; JOINT239
is also infeasible, bound -0.062751736. TARGET96 alone has a strict witness
with verified gap 0.693209, passing exact and actual float action replay.
The retained SOURCE-trained model has 72/143 regret roots, mean regret 0.109982.
Next change the consequence function class to shared nonlinear relation
combinations, with SOURCE-group selection and fresh frozen evaluation.
Seventeen tests, 576/576 audit, 83/83 source and 8/8 input comparisons pass;
main/audit once, stderr 0. There are 48 LPs and 47 symbolic balances,
no new fits, labels or kernels; audit repeats no solves. The negative result
does not make all 72 errors unavoidable, and nonlinear capacity remains open.
General strategy remains unresolved. Keep H2; U005 FAIL, U006 unstarted.

[V190 shared merge/blocker relations](reports/MERGE_RELATIONS_V190_RESULTS.md)
uses 98 fixed rank/order/packing columns and SOURCE143/36 selection, lambda=0.1.
All 20 known within-root alias losses disappear in development. On 96 new H3
boards, RELATION-minus-LINEAR is -0.013157 and minus-OLD_SHARED -0.015815,
both negative in all four replicas; regret roots are 37 versus 27 and 24.
The new learner is not adopted. Next test linear ranking capacity using retained
SOURCE/TARGET labels to separate function-class limits from fitting errors.
Twenty initial tests and one metadata regression pass. Initial audit 220/222
and its failure remain retained; two V184/V185 observer-metadata errors are
resolved by a bounded binding supplement, corrected 222/222. Main/audit run
once; 85/85 original source and 10/10 input comparisons pass, stderr 0.
There are 13 predictors and 96 kernels/plans, no physical samples/native updates.
General strategy remains unresolved. Keep H2; U005 FAIL, U006 unstarted.

[V189 six-feature information conflicts](reports/FEATURE_CONFLICTS_V189_RESULTS.md)
diagnoses the retained V188 TARGET96 without new fits or labels. Twenty of
LINEAR's 44 regret roots have unavoidable within-root alias loss, accounting
for 37.66% of its regret. An exact five-root balanced certificate gives a
common margin upper bound -17/160: arbitrary shared g(six_features) cannot
attain all representative-optimal rankings. Next retain tile ranks, ordered
merge relations and blockers through a shared relation representation, train
on SOURCE and test a fresh cohort. Twelve tests, 27/27 audit, 39/39 source
and 5/5 input comparisons pass; main/audit once, stderr 0. One LP and one
exact balance, no new samples or kernels. General strategic learning remains
unresolved. Keep H2; U005 FAIL, U006 unstarted.

[V188 shared mechanism interactions](reports/MECHANISM_INTERACTIONS_V188_RESULTS.md)
compares six-feature LINEAR with 26 fixed quadratic features on SOURCE143.
SOURCE-only selection chooses lambda=0 and 0.01 respectively. On 96 unopened
H3 boards, INTERACT-minus-LINEAR is -0.005479, negative in three of four
replicas; both have 44 regret roots. INTERACT beats RIDGE by +0.051837 in
all four replicas, but LINEAR is stronger; the interactions are not adopted.
Next diagnose retained LINEAR errors to distinguish representation information
loss from prediction error before choosing another learner. Fifteen tests,
216/216 audit, 81/81 source and 6/6 input comparisons pass; main/audit once,
stderr 0. There are 26 predictors and 96 exact kernels/plans, no physical
random samples or native updates. General strategic learning remains
unresolved. Keep H2; U005 FAIL, U006 unstarted.

[V187 position-shared rank relations](reports/POSITION_SHARED_V187_RESULTS.md)
shrinks the vocabulary from 2,777 to 285 tokens on fixed SOURCE143.
SOURCE-group selection chooses lambda=0.1; validation utility is 1.216261
versus RIDGE's 1.232649. On 96 unopened H3 boards, POOL-minus-RIDGE is
-0.014757 and POOL-minus-OLD_SHARED -0.003643; the representation is not adopted.
All 14,200 target token occurrences are known. A posthoc check finds no equal
feature action pairs; it does not support an alias impossibility claim.
Next test low-dimensional interactions of shared vacancy/merge/goal features.
Fifteen tests, 216/216 audit, 80/80 source and 6/6 input comparisons pass;
main/audit run once, stderr 0. There are 13 predictors and 96 exact kernels/plans,
with no physical random samples or native updates. General strategic learning
remains unresolved. Keep H2; U005 FAIL, U006 unstarted.

[V186 optimal-action ranking](reports/ACTION_RANKING_V186_RESULTS.md)
fixes SOURCE143, representation and lambda=0.1, then tests a one-sided ranking
loss on 96 unopened H3 boards. RANK-minus-RIDGE is -0.007137;
RANK-minus-OLD_SHARED is -0.058952, negative in three of four replicas.
RANK failure is 2.197% versus OLD_SHARED's 0.442%; regret roots are 44 versus 40.
RANK beats ONE by +0.140931 in all four replicas, but is not adopted.
The optimizer and independent dual converge. Fifteen tests, 218/218 audit,
79/79 source and 6/6 input comparisons pass; main/audit run once, stderr 0.
One new predictor and 96 exact kernels/plans; no physical random samples or
native updates. Next test position-shared rank/adjacency relations through
held-out SOURCE groups. General strategic learning remains unresolved.
Keep H2; U005 FAIL, U006 unstarted.

[V185 SOURCE coverage](reports/SOURCE_COVERAGE_V185_RESULTS.md) expands SOURCE
from 47 to 143 roots and tests another 96 unopened H3 boards. Selection again
chooses lambda=0.1. RIDGE improves by +0.019789 versus its old model, but two
replicas improve and two worsen; one root supplies 78.9% of positive gains.
LAYOUT and SHARED decline by -0.030059 and -0.013105. Unknown target tokens
fall from 12.45% to 1.62%; OLD_SHARED remains the strongest learned comparator.
Next fix SOURCE/representation and test optimal-action ranking directly;
scalar utility least squares would be equivalent to the current ridge projection.
Thirteen tests, 408/408 independent checks, 76/76 source and 5/5 input comparisons
pass; main/audit run once, stderr 0. There are 192 new exact kernels/plans and
15 predictors. Two pre-run syntax collection failures are retained and fixed.
General strategic learning remains unresolved. Keep H2; U005 FAIL, U006 unstarted.

[V184 fresh H3 confirmation](reports/FRESH_H3_CONFIRMATION_V184_RESULTS.md)
freezes V183 lambda=0.1 and all controls on 96 new boards, four replicas of 24.
RIDGE-minus-ONE is +0.116525, but RIDGE-minus-LAYOUT is -0.016168 and
RIDGE-minus-SHARED is -0.052338; every replica has these signs.
Regularization's old-target advantage is not confirmed. SHARED remains the
strongest learned comparator, closing 64.6% of oracle headroom versus RIDGE's
44.6%; positive-regret roots are 32 versus 49. Next expand independent SOURCE
consequence coverage with the representation fixed and use another unopened
evaluation cohort. Coverage insufficiency remains a hypothesis. Fourteen tests,
211/211 independent checks, 71/71 source and 5/5 input comparisons pass;
main/audit run once, stderr 0. There are 96 new exact kernels/plans and no new
predictors or physical samples. General strategic learning remains unresolved.
Keep H2; U005 FAIL, U006 unstarted.

[V183 SOURCE-selected regularization](reports/SOURCE_REGULARIZATION_V183_RESULTS.md)
selects lambda=0.1 by actual held-out SOURCE-group utility with fixed V182
rank/layout features. Held-out utility rises from 1.001213 at zero penalty
to 1.035727; six groups improve and one worsens. TARGET utility is +0.039675
versus LAYOUT, +0.004044 versus SHARED and +0.020874 versus ONE, closing 28.1%
of oracle headroom. Success returns to ONE's level. About 99.5% of gain versus
LAYOUT comes from one repaired root; nine target regret roots remain.
Next freeze model/strength/baselines and confirm on a predeclared new H3 board
cohort with complete exact outcomes. Thirteen pure tests, 20/20 independent
checks, 72/72 source and 6/6 input comparisons pass; main/audit run once,
stderr 0. Three main SVDs, 13 coefficient filters and 13 independent audit
coefficient solves; one numerical test tolerance fix and both attempts retained.
No new features, physical samples or native updates. Fresh confirmation and
general strategic learning remain outstanding. Keep H2; U005 FAIL, U006 unstarted.

[V182 rank/layout consequences](reports/RANK_LAYOUT_CONSEQUENCES_V182_RESULTS.md)
fits all 47 SOURCE action rankings with rank/layout complete-vector contrasts,
but TARGET utility is -0.018801 versus ONE and -0.035632 versus SHARED.
There are nine target positive-regret roots, four newly wrong versus SHARED
and one resolved. SOURCE pair loss is 1.61e-28; design rank122 spans all
169-47 independent within-root contrasts. The richer representation permits
interpolation; its transfer benefit is absent. SOURCE vocabulary has 2058 tokens;
441/3640 target tokens are unseen, with at least one in every target root.
Next keep the representation fixed and select regularization by held-out
SOURCE design-group action utility before freezing the full-SOURCE model.
Fifteen pure tests, 24/24 independent checks, 69/69 source and 8/8 input
comparisons pass; main/audit run once, stderr 0. One new predictor and one
independent SVD, no new physical samples or native updates. This reused H3
diagnostic does not promote LAYOUT. Keep H2; U005 FAIL, U006 unstarted.

[V181 arbitrary shared feature capacity](reports/SHARED_FEATURE_CAPACITY_V181_RESULTS.md)
proves that the fixed six-feature score loses cross-board decision information.
Even unrestricted nonlinear tuple values have certified margin upper bounds
-0.085938 on SOURCE and -0.123047 jointly. TARGET reaches only zero margin;
two reverse preferences force ties that choose wrong DOWN under the frozen rule.
A two-root SOURCE contradiction cannot be repaired by changing function shape
or fitting loss. SOURCE covers 26/34 TARGET tuples and every tuple in 16/24 roots.
Next retain tile ranks and local layout in a shared full-consequence model,
fit only SOURCE, and compare with unchanged TARGET labels and controls.
Fourteen pure tests, 54/54 independent checks, 37/37 source and 4/4 input
comparisons pass; main/audit run once, stderr 0. Three main LPs, no audit LP,
new fitted predictor, physical samples or native updates. This reused H3 capacity
diagnostic preserves V179's mean gain and success decline. Keep H2;
U005 FAIL, U006 unstarted.

[V180 shared ranking capacity](reports/RANKING_CAPACITY_V180_RESULTS.md)
proves that the fixed six-feature shared linear class cannot reproduce
all correct rankings, even at zero margin. Certified margin upper bounds
are -0.369141 on SOURCE, -0.123535 on TARGET and -0.410807 jointly.
Two SOURCE roots require the vacancy coefficient to be both <=-0.25
and >=0.488281. All 56 absorbing-goal labels are correct. These certificates
do not exclude arbitrary nonlinear functions of the same feature tuples.
Next test that broader capacity before choosing nonlinear learning or
adding state information. Seventeen pure tests, 62/62 independent checks,
35/35 source and 6/6 input comparisons pass; main/audit run once, stderr 0.
Three main LPs, no audit LP, no new predictor, physical samples or native updates.
V179 positive mean utility remains valid; this does not quantify the best
attainable mean utility or solve general strategic learning. Keep H2;
U005 FAIL, U006 unstarted.

[V179 shared action-conditioned consequences](reports/SHARED_CONSEQUENCES_V179_RESULTS.md)
replaces root partitions with one six-feature full-vector model on fixed exact H3 labels.
SHARED-minus-ONE is +0.090490 on SOURCE and +0.016831 on TARGET,
closing 52.4% and 22.7% of oracle headroom. TARGET has 11 improved,
3 worsened and 10 equal-value roots, zero fallback and six remaining
positive-regret roots. Utility increases while success probability decreases
by 0.019792. A per-root feature-restricted oracle preserves 98.5% of target
headroom; this does not establish shared linear attainability. Sixteen pure
tests, 23/23 independent checks, 66/66 source and 7/7 input comparisons
pass; main/audit run once, stderr 0. No new physical samples or native updates.
Next distinguish shared ranking capacity from the SOURCE fitting objective.
These are reused finite-H3 diagnostics. Keep H2; U005 FAIL, U006 unstarted.

[V178 action-afterstate structure](reports/AFTERSTATE_STRUCTURE_V178_RESULTS.md)
keeps V177 labels, objective, support and RAW/ONE baselines fixed.
STRUCTURE-minus-ONE is -0.002740 on SOURCE and -0.153002 on TARGET;
TARGET STRUCTURE-minus-RAW is -0.120194, with oracle headroom
+0.074259 and zero fallback. Only 12/264 candidates are comparable,
all vacancy predicates; every merge/goal predicate fails the unchanged
fit-child support requirement. The effective tree therefore does not
use those structural distinctions. Thirteen pure checks, 26/26
independent checks, 65/65 frozen-source and 7/7 input comparisons
pass; main/audit run once, stderr 0. No new physical samples or
native updates. Next replace per-leaf action constants with a shared
action-conditioned complete-consequence model using fixed aggregate
afterstate features. This remains a reused finite-H3 diagnostic.
Keep H2; U005 FAIL, U006 unstarted.

[V177 exact H3 learning diagnostic](reports/EXACT_H3_LEARNING_V177_RESULTS.md)
removes Monte Carlo label noise with the same utility partition learner.
The original source roster has 47 H3 roots plus one H2 root; the H2
root is excluded and retained. SOURCE TREE-minus-ONE is +0.047262;
TARGET is -0.032809 despite oracle-minus-ONE headroom +0.074259,
with zero TREE/ONE fallback. One cell-rank split does not transfer
action-dependent continuation risk. Twenty distinct pure checks,
128/128 independent checks, 60/60 frozen-source and 53/53 input
comparisons pass; main/audit run once, stderr 0. No new physical
samples or native updates. Next freeze action-conditioned afterstate
structure predicates while keeping exact labels, the utility objective
and support constraints fixed. These reused finite-H3 diagnostics
do not establish long-episode or continual strategic learning.
Keep H2; U005 FAIL, U006 unstarted.

[V176 probability-weighted first-spawn sampling](reports/SPAWN_STRATIFICATION_V176_RESULTS.md)
completes the fixed-policy acquisition probe at matched branch counts.
STRAT/IID utility variance is 2.77729; paired variance difference
+0.0189668 has conditional 95% CI [-0.0345057, +0.0724394].
The predeclared reduction condition is not met. The variance times
transition-cost ratio is 2.77197, descriptive only. No additional
blocks or strategy promotion follow. All 14,080 branches terminate,
acquiring 7,318,450 transitions. Twenty-five pure tests, 131/131
independent checks and 103/103 frozen-source byte comparisons pass;
main/audit each run once, stderr 0. New fits, updates and source games
are zero. Next use exact H3 complete-vector labels with the same
partition learner, calibrating oracle headroom before judging learning.
Keep H2; U005 FAIL, U006 unstarted.


[V175 frozen-board suffix replication](reports/FIXED_BOARD_REPLICATION_V175_RESULTS.md)
keeps V174 TREE/ONE policies and all 640 boards fixed, then acquires
16 new paired suffixes per changed root. TRAIN utility falls from
+0.14047 on the original labels to -0.04287; NEW-minus-OLD is -0.18334,
SOURCE CI [-0.28658, -0.08010] and fixed-board suffix CI
[-0.23206, -0.13462]. FRESH utility is -0.02747; neither cohort
establishes positive TREE benefit. FRESH-minus-TRAIN is +0.01540 with
both intervals crossing zero. Prioritize noisy-label fitting/selection;
an additional board-generalization penalty is unresolved.
All 9,440 branches terminate, acquiring 4,632,756 transitions.
Thirty-three distinct pure tests, 275/275 independent checks and
101/101 resumed-source byte comparisons pass. A recording interruption
is retained; its four complete branches are reused exactly without
resampling, and the extra teacher loads remain charged. No new fits,
weight updates or source games. Next test actual spawn-support sampling
at matched budgets before further partition growth, then require an
independent learned-policy utility comparison.
Keep H2; U005 FAIL, U006 unstarted.


[V174 SOURCE-heldout utility partitions](reports/UTILITY_PARTITION_V174_RESULTS.md)
implements actual heldout action utility as the split-generation objective,
with full outcome vectors and fresh confirmation/validation. Eight utility
splits and 32 SSE splits freeze before confirmation; neither generator
retains a split. Both final models equal ONE_LATE. Utility-confirmed minus
H2 is +0.0122 [-0.0945, +0.1189]; progression is FAIL (0/2).
Removing utility splits improves fresh utility by +0.1016 [+0.0074, +0.1958].
The complete trees have positive retrospective training effects in all
histories; those gains do not establish independent usefulness.
All 7,432 physical games terminate, acquiring 3,744,714 transitions.
Twenty-four pure tests, 537/537 independent checks and 98/98 frozen-source
comparisons pass; main/audit each run once, both stderr 0.
Next freeze boards/policies and replicate paired suffixes to distinguish
label sensitivity from failure to generalize state distinctions.
Keep H2; U005 FAIL, U006 unstarted.


[V173 independently confirmed partitions](reports/CONFIRMED_PARTITION_V173_RESULTS.md)
freezes DISCOVERY proposals, selects splits on new CONFIRM data and tests
frozen models on a third, fresh VALID cohort. Of 32 candidates, 26 meet
coverage/support rules and none confirm positive utility; every final
tree collapses to one leaf. CONFIRMED-minus-UNPRUNED utility is +0.0800
[-0.0424, +0.2024]; CONFIRMED-minus-H2 is -0.0420 [-0.1963, +0.1123].
Both progression conditions fail. Lower fresh pair prediction error
does not establish strategic learning. All 7,476 games terminate,
acquiring 3,749,455 transitions. Forty focused tests, 544/544 independent
checks and 95/95 frozen-source comparisons pass; main/audit each run once,
both stderr 0. A retained training counterexample shows lower vector SSE
can reduce policy utility. V174 above completes SOURCE-heldout utility
candidate generation; no split establishes independent benefit.
Keep H2; U005 FAIL, U006 unstarted.


[V172 learned consequence partitions](reports/CONSEQUENCE_PARTITION_V172_RESULTS.md)
implements the V171 follow-up learner using full-vector paired forced-action
labels and deterministic first rewards kept as numeric parameters. Each
history grows from three to nine learned leaves; all 256 fresh VALID boards
are unseen. PART_LATE-minus-COARSE_LATE utility is +0.0699
[-0.0664, +0.2062]; PART_LATE-minus-H2 is +0.0318 [-0.1654, +0.2290].
Both progression conditions fail. Late models use their own choices at
all roots, differing from H2 at 181/256. The same-root unpartitioned
control has lower fresh full-vector pair MSE; a posthoc clustered
difference is +0.2179 [+0.0812, +0.3546] for partition minus control.
This points toward noise-fitting during greedy split selection.
All 7,500 physical games terminate, acquiring 3,809,338 transitions.
Original replay/statistical checks pass; 12 original audit comparisons
fail because the solver violates its zero-sum coordinate convention.
A separate 20/20 equivalence audit confirms all 1,280 frozen actions and
observable contrasts unchanged; the original failed audit stays retained.
The active solver is repaired with a retained numerical regression test.
Thirty-eight distinct focused tests pass; sampling occurs only in the main
run. V173 above completes independent split confirmation and fresh testing;
no proposed split establishes positive utility.
Keep H2; U005 FAIL, U006 unstarted.


[V171 causal quotient planning](reports/CAUSAL_QUOTIENT_V171_RESULTS.md)
implements action-to-successor models and teacher-specific continuation vectors,
with same-data depth 1/3 planning and separate same-history/transfer arms.
All 3,460 physical games terminate, acquiring 1,767,734 transitions.
SAME_D3-minus-SAME_D1 utility is -0.0477 [-0.1412, +0.0458];
SAME_D3-minus-H2 is -9.1761 [-9.5993, -8.7528]. Both progression
conditions fail. Each of the four model arms wins 0/128 games, versus
H2's 70/128; SAME_D3 uses model actions in 92.05% of decisions.
Thirty-two focused tests, 481/481 independent checks and 90/90 frozen-source
comparisons pass; main/audit run once, both stderr 0. Tests add 16 transitions
separately. High model coverage does not preserve control: depth changes
only 0.737% of co-supported VALID actions, and only 0.1794% of fitted
transitions are forced first actions. A retained same-key/action reward
counterexample confirms non-exact abstraction; the contribution of each
failure mechanism remains unquantified. The learned paired-consequence
partition experiment is completed in V172 above; a useful fresh action
improvement remains unestablished.
Keep H2; U005 FAIL, U006 unstarted.

[V170 persistent strategies and whole-episode learning](reports/PERSISTENT_STRATEGY_V170_RESULTS.md)
completes two generations, final program selection and 128 fresh whole-game
pairs from ordinary initial states. COND-minus-LATCHED utility is +3.5035
[+2.9387, +4.0684], establishing feedback-refresh benefit in these selected
programs. COND-minus-H2 is -0.9476 [-1.4576, -0.4376]; failure probability
rises by 14.84 percentage points [5.91, 23.78], so progression fails and no
program is adopted. Persistent execution works throughout complete games,
but COND delegates 94.21% of decisions to H2; all three nontrivial programs
have negative heldout EVAL gains. All 5,872 games terminate, acquiring
3,787,356 transitions; focused replay tests add 24 retained transitions.
Forty-six focused tests, 649/649 independent checks and 89/89 frozen-source
comparisons pass; main/audit run once, both stderr 0. Teacher setup, fallback,
generation, selection and inherited costs remain accounted for. Intervals
condition on four existing teachers and frozen learned programs. V171 above
completes the first consequence-bearing strategic state model and bounded
model-planning experiment, separating same-history learning from transfer.
Its fixed coarse representation fails; general strategic learning remains
unresolved.
Keep H2; U005 FAIL, U006 unstarted.

[V169 joint condition/action generation](reports/JOINT_FEEDBACK_GENERATION_V169_RESULTS.md)
completes two generations, final same-candidate twin selection and fresh EVAL.
Three final programs differ from their source parents; feedback chooses a
different suffix from the twin in 144/512 EVAL branches, with both predicates
observed in ten roots. COND-minus-TWIN utility is +0.0053 [-0.1308, +0.1414];
COND-minus-H2 is -0.1537 [-0.3765, +0.0691]. Neither progression condition
passes, so no program is adopted. All 32 source games and 12,192 branches
terminate, acquiring 5,897,762 transitions. Forty-four final focused tests,
838/838 independent checks and 90/90 source comparisons pass; main/audit
run once, both stderr 0. Both-query teacher setup/load and inherited costs
remain accounted for. Intervals condition on fixed fresh roots and four
existing histories. The preregistered route closes fixed four-step,
single-probe search and moves to persistent state-conditioned control
programs trained and evaluated over complete episodes. V170 completes this
experiment above; general strategic learning remains unresolved.
Keep H2; U005 FAIL, U006 unstarted.

[V168 consequence-guided generation](reports/CONSEQUENCE_GENERATION_V168_RESULTS.md)
completes two mutation generations and fresh EVAL after all programs freeze.
Terminal feedback changes the final words in all four heldout folds, but
CONS-minus-FREQ utility is +0.0247 [-0.2213, +0.2706] and CONS-minus-H2
is -0.1116 [-0.3473, +0.1241]; benefit is not established and no program
is adopted. All 32 source games and 12,672 branches terminate, acquiring
6,080,526 transitions. Both routes have 5,888 branches each with identical
step caps; realized sample counts differ. Twenty-eight final focused tests,
786/786 independent checks and 88/88 source comparisons pass; main/audit
run once, both stderr 0. Both-query teacher setup/load and inherited costs
remain accounted for. Intervals condition on four existing histories and
new fixed roots. The nominated joint condition/action generation is
completed in V169 above; benefit remains unestablished.
Keep H2; U005 FAIL, U006 unstarted.

[V167 fixed-program confirmation](reports/FIXED_PROGRAM_V167_RESULTS.md)
rejects the exploratory S0/B candidate on fresh continuations. Across all
32 existing risk1 EVAL roots and 16 paired suffixes/root, B-minus-H2 utility
is -0.2019 [-0.3821, -0.0217]; failure probability rises by 5.47 percentage
points. Every history has a negative utility point estimate. All 1,024
branches terminate, acquiring 501,002 transitions; no new source games,
rule fits or weight updates. Twenty-four focused tests, 104/104 independent
checks and 90/90 source comparisons pass; main/audit run once, both stderr 0.
Both-query teacher setup/load and all inherited costs remain accounted for.
The intervals condition on these fixed roots and histories. The nominated
consequence-guided generation experiment is completed in V168 above;
benefit remains unestablished. Keep H2; U005 FAIL, U006 unstarted.

[V166 same-program ranking decomposition](reports/PROGRAM_RANKING_V166_RESULTS.md)
completes one retrospective routing pass with no new samples or rule fits.
Three semantic strata cover 192 triplets and 512 unique physical records;
shared risk1 H2 rows are accounted for without pooled independence claims.
For risk8, 10/64 A/B pairs have discordant terminal outcomes; risk mean
variance is about 38.4 times reward mean variance, with covariance retained.
All three pooled A/B ranking intervals cross zero. A distinct exploratory
signal is risk1 S0 fixed-B minus H2: +0.6342 [+0.1835, +1.0849], with both
reward and risk contributions positive. This is not adoption evidence.
Twenty-five focused tests, 181/181 independent checks and 30/30 source
comparisons pass; main/audit run once, both stderr 0. V167 above completes
the nominated fresh confirmation and rejects S0/B; candidate generation is
next. Keep H2; U005 FAIL, U006 unstarted.

[V165 retained-intervention headroom](reports/PROGRAM_HEADROOM_V165_RESULTS.md)
completes the fixed semantic match and independent suffix split without
new environment samples. All 32 roots and 128 A/B/H2 triplets are covered.
ROOT-minus-refitted-bit is +0.1066 [-0.5536, +0.7667] for risk1 and
+0.6088 [-0.6086, +1.8261] for risk8. ROOT-minus-H2 also crosses zero.
For risk8, ROOT-minus-original-GLOBAL is +1.6530 [+0.5465, +2.7595],
mostly from one history; refitting the fixed rule on the same target data
reduces this gap to +0.0425 [-0.0376, +0.1226], with a negative reversed-split
point estimate. This points toward consequence estimation and transfer
heterogeneity; insufficient merge-bit information is not established.
Twenty-seven focused tests, 318/318 independent checks and 29/29 source
comparisons pass; main/audit run once, both stderr 0. Paid V164 and earlier
costs remain. V166 above completes the nominated same-program ranking
decomposition. Keep H2; U005 FAIL, U006 unstarted.

[V164 support-aware consequence revision](reports/SUPPORTED_PROGRAM_V164_RESULTS.md)
is complete and is not adopted. Terminal paired A/B vectors now revise
observed program branches; unseen conditions retain their source assignment
with null terminal estimates. Seven of eight learned maps change.
LEARNED-minus-MODAL is +0.0392 [-0.1366, +0.2150] for risk1 and
-0.2730 [-0.9609, +0.4148] for risk8; LEARNED-minus-H2 is
-0.0862 [-0.2729, +0.1005] and +0.0191 [-0.8442, +0.8824].
Same-candidate mapping and conditional-versus-global contrasts also
cross zero. Five maps are constant and three conditional. All selected
predicates have TRAIN terminal support; actual EVAL source-prior use is
zero, so missing support does not explain this run's lack of demonstrated
benefit. The bounded learning implementation works; strategic utility
remains open. All 64 source games and 8,064 physical branches terminate,
acquiring 4,122,785 transitions. Eighteen focused tests, 77/77 independent
checks and 87/87 source comparisons pass; main/audit run once in
734.33/245.29s, both stderr 0. Eight symbolic tables are fitted with no
neural weight updates; all test and inherited work remains.
The proposed retained-intervention diagnosis is completed in V165 above.
Keep H2; U005 FAIL, U006 unstarted.

[V163 consequence learning](reports/CONSEQUENCE_PROGRAM_V163_RESULTS.md)
implemented full-vector terminal branch fitting, but its frozen support
requirement stopped EVAL: heldout3/risk1/P0 had true40/false0/none8.
Retain incomplete_training/HOLD and its 996,655 new transitions.
Twenty-seven focused tests, 72/72 checks and 86/86 source comparisons pass;
main/audit run once in 111.99/134.10s, both stderr 0.
V164 is a separately frozen fresh-data experiment; V163 remains stopped.

[V162 generated state-feedback programs](reports/FEEDBACK_PROGRAM_V162_RESULTS.md)
is complete and is not adopted. An observed post-spawn merge predicate
selects a source-derived three-action suffix after the shared first action.
FEEDBACK-minus-matched-FIXED is -0.0130 [-0.1410, +0.1150] for risk1 and
+0.2568 [-0.1876, +0.7012] for risk8; FEEDBACK-minus-H2 is
-0.1126 [-0.3247, +0.0995] and -0.6188 [-1.4118, +0.1742].
Feedback changes 157/512 and 111/512 branch suffixes; five of 32 roots
per query exhibit both predicates across suffix samples.
Both queries nevertheless select the same two alternating-axis templates.
TRAIN gains are positive in seven of eight selected cells, while EVAL
gains versus H2 are negative in six of eight. Conditional action frequency
plus global terminal screening has not established strategic utility.
All 64 source games and 4,992 branches terminate, acquiring 2,586,113
transitions. Twenty-one final focused tests, 73/73 independent checks and
84/84 frozen source comparisons pass; main/audit run once in
247.81/161.15s, both stderr 0. All development attempts and 392 test
transitions remain separately retained with inherited costs.
Intervals condition on fixed roots, four histories and training choices.
Next learn program-internal branches from paired TRAIN counterfactual
terminal consequences, with the same bounded grammar, a matched fixed
twin, H2 and equal-budget frequency-generation control. Separate local
conditioning from global selection before learning an external caller.
Keep H2; U005 FAIL, U006 unstarted.

[V161 experience-generated programs](reports/PROGRAM_CONSOLIDATION_V161_RESULTS.md)
is complete; heldout utility improvement is not established. Four-action
words are generated from fresh TRAIN trajectories in the other three
histories, normalized by D4, terminal-screened and frozen before fresh EVAL.
BEST-minus-H2 is -0.1375 [-0.3558, +0.0807] for risk1 and
-0.0011 [-0.8361, +0.8339] for risk8. Six of eight selections differ from
the frequency control, but BEST-minus-FREQ also crosses zero in both queries.
The programs execute 3.11/2.80 prefix steps on average; their intervention
is substantive. All 64 source games and 4,992 screening/evaluation branches
terminate, acquiring 2,554,756 transitions. Twenty final focused tests,
69/69 independent checks and 82/82 frozen source comparisons pass;
main/audit run once in 222.40/151.34s, both stderr 0. All development
attempts and their 115 test transitions are retained separately.
Conditional intervals do not establish population-history transfer or
general strategic learning. Next test a bounded feedback program generated
from TRAIN action/merge fragments, with one branch and the same four-step
cap, against its fixed-word source and H2. Missing feedback is a hypothesis
to test; caller learning remains deferred. Keep H2; U005 FAIL, U006 unstarted.

[V160 bounded mobility restoration](reports/MODULE_MOBILITY_V160_RESULTS.md)
is complete and is not adopted. On all 64 frozen roots and 32 fresh paired
suffixes, MOBILITY-minus-own-H2 terminal utility is -0.6994
[-0.8933, -0.5054] for risk1 and -2.6119 [-3.3245, -1.8994] for risk8.
Both sources and all four histories lose. Failure rises by 10.74/12.30
percentage points; restoration completes in only 20.02%/11.13% of branches.
The same own-H2 continuation isolates the bounded prefix intervention.
These intervals condition on the fixed roots and four histories; the three
tight-board roots cannot support a complete history-stratified comparison.
All 6,144 branches terminate, with 2,958,948 new environment transitions
and no fitting. Nineteen focused tests, 37/37 independent checks and 84/84
frozen source comparisons pass; main/audit run once in 429.70/177.49s,
both stderr 0. Test acquisition (72 transitions) and inherited costs remain.
Next freeze an experience-to-program consolidation algorithm: generate
bounded executable multi-step candidates from TRAIN fragments, screen their
query/continuation-conditioned terminal consequences on TRAIN, then evaluate
frozen candidates on new roots and histories before learning a caller.
Keep H2; U005 FAIL, U006 unstarted.

[V159 fixed spawn control variate](reports/MODULE_CONTROL_VARIATE_V159_RESULTS.md)
is complete and is not adopted. The first-eight-spawn, beta-one correction
with a frozen DIRECT critic does not reduce EVAL paired-label variance:
CV/RAW variance ratios are 1.00555/1.00093 for risk1/risk8.
All n32 decisions are identical to RAW, so primary control benefit is zero.
Retain the favorable risk8 n16 gain +0.0894 [0.0159, 0.1629], caused by
one changed decision in history 2; do not select n16 after evaluation.
The implementation preserves the terminal objective and uses RAW EVAL
utilities for scoring. Conditional zero mean does not guarantee useful
variance reduction. These inspected-path results are exploratory.
All 8,192 retained branches and 65,536 spawn events are processed with
846,104 DIRECT critic calls; zero new environment samples or updates.
Thirteen focused tests, 33/33 independent checks and 90 frozen source
comparisons pass; main/audit run once in 47.66/49.14s, both stderr 0.
Next change the module candidate itself: test a bounded mobility-restoration
module with an observable completion condition, followed by the same
own-H2 continuation as its controls. Establish reproducible module effects
before learning a call rule; a hand-specified candidate is not general
strategic learning. Keep H2; U005 FAIL, U006 unstarted.

[V158 fresh-suffix label precision](reports/MODULE_PRECISION_V158_RESULTS.md)
is complete. Raising the training suffix budget from 8 to 32 has not
established reliable root-local selection benefit. The fixed n32 candidate
gains +0.0244 [-0.0438, +0.0926] versus OLD for risk1 and
-0.1774 [-0.5007, +0.1458] for risk8. Its paired n32-minus-n8 gains
are +0.0287 [-0.0380, +0.0954] and +0.1401 [-0.1824, +0.4626].
For risk8, n32 loses -0.3793 [-0.7163, -0.0423] against rejecting
the initial module call, with negative means in all four histories.
All continuations use the same frozen OLD gate. Intervals condition on
the realized training decisions, roots and histories; they do not establish
general strategic learning. Keep all 8/16/32 results; do not choose n16
after observing its less negative risk8 mean or increase the sample cap.
All 8,192 branches terminate. New acquisition is 4,026,405 transitions:
2,013,613 TRAIN and 2,012,792 shared EVAL; inherited costs remain referenced.
Fourteen focused tests, 43/43 independent checks and 84 source comparisons
pass; main/audit run once in 361.92/245.83s, both stderr 0.
V159 above completes that fixed control-variate test; it does not reduce
EVAL label variance or change the n32 decisions. Move to a different
module candidate instead of further label repairs on the same fixed
eight-step substitution. Keep H2; U005 FAIL, U006 unstarted.

[V157 fixed suffix split-half selection](reports/MODULE_SPLIT_HALF_V157_RESULTS.md)
is complete. Selecting GATE calls with one half of retained suffixes does
not recover utility on the opposite half: gain versus OLD is
-0.0873/-0.4548 for risk1/risk8, versus apparent same-half gains
+0.1970/+0.9310. Both swap directions are negative; strict-positive
decision agreement is 50.0%/34.375%. Gains versus always rejecting are
-0.0219/-0.5072 and versus always accepting -0.0324/-0.4773.
Risk8 is negative in all four histories. These failures already occur
within roots without a learned representation; cross-root transfer alone
cannot explain them. The finite split does not establish that all labels
or modules are unlearnable. Retain the favorable secondary risk8/H2-target,
H2-source gain +0.4150 versus OLD, still -0.2240 versus always rejecting.
All 64 roots, 1,024 paired suffixes and 256 selection rows are retained.
Sixteen focused tests, 21/21 independent checks and eight frozen source
comparisons pass; main/audit run once in 38.78/37.36s, both stderr 0.
No new environment samples, planner calls or model fits; preserve the
2,017,530-transition acquisition cost, counted physically once.
V158 above completes that bounded fresh-suffix precision experiment.
The fixed n32 candidate does not establish stable benefit; do not
automatically increase sampling or select the best observed budget.
Keep H2; general strategic learning remains open, U005 FAIL, U006 unstarted.

[V156 fixed policy-semantic residual features](reports/MODULE_SEMANTICS_V156_RESULTS.md)
is complete. The fixed 12-dimensional representation worsens heldout
own-target MSE in all four query/target cells versus LOCAL and OLD.
LOCAL to SEMANTIC MSE is 0.6125 to 0.8621 / 0.5223 to 0.8027 for risk1,
and 7.9947 to 9.1977 / 5.4632 to 7.7506 for risk8 (H2/GATE targets).
There is no consistent local decision gain. Risk8/H2 retains a gain
of +0.0995 versus OLD, below LOCAL's +0.1277; a favorable OLD-source
subset does not offset worse H2-source performance. Do not adopt SEMANTIC.
The 512 LOCAL predictions reproduce V155 within component tolerance,
with identical gates. All 128 fits and 24,576 updates are complete.
Feature preparation costs 128 H2 queries, 6,036 enumerated model outcomes
and 21,284 leaf predictions; zero new environment samples.
Fifteen focused tests, 38/38 independent checks and 87 source comparisons
pass; main/audit run once in 4.26/2.67s, both stderr 0.
V157 above completes that fixed split-half test. Even within-root
empirical selection fails to reproduce gains on the opposite half;
test label precision before further representation or coverage changes.
Keep H2; general strategic learning remains open, U005 FAIL, U006 unstarted.

[V155 episode-grouped holdout of repairs](reports/MODULE_HOLDOUT_V155_RESULTS.md)
is complete. Each fold holds out both policy roots sharing a source seed,
fits on the other six, and freezes before prediction. Own-target heldout
MSE rises in three of four query/repair cells despite low training MSE.
REPAIR_GATE local gains are -0.0410/-0.0165 for risk1/risk8.
Retain REPAIR_H2's favorable risk8 signal: local gain +0.1277 and common
GATE-target MSE 5.3261 to 5.0717. Its gain is concentrated on H2-source
roots (+0.2384); OLD-source gain is +0.0169, with own-target MSE worsening
in all four histories. These are descriptive fixed-OLD continuation
comparisons; overlapping folds do not support naive independent intervals.
V156 above completes the matched policy-semantic residual comparison;
the fixed semantic representation does not improve overall transfer.
There are 64 fits, 12,288 updates and 576 predictions, zero new environment
or native planner calls, and no raw branch rereading. Ten focused tests,
24/24 independent checks and 80 frozen source comparisons pass.
Main/audit run once in 1.47/2.04s, both stderr 0. Keep H2;
general strategic learning remains open, U005 FAIL, U006 unstarted.

[V154 fixed-reference advantage repair](reports/MODULE_REPAIR_V154_RESULTS.md)
is complete. Both repairs use all 64 retained roots, identical OLD
initialization and 4,096 new updates. In fresh full games, REPAIR_H2-OLD
is +0.3645/-2.8435 for risk1/risk8; REPAIR_GATE-OLD is +0.3574/-2.7632.
All conditional seed intervals include zero. Both repairs have negative
mean differences against H2 and ALT; neither is adopted. Risk8 training
MSE falls from 7.5535/5.3261 to 0.2635/0.1775, without established control
benefit. Changing the continuation target alone has not solved the
fit-to-control gap. V155 above completes the grouped heldout test:
prediction transfer is weak and local gains are not consistent across
targets, queries and source strata.
All 512 physical games terminate, yielding 640 logical results and 499,608
new evaluation transitions. Each repair view charges the retained
2,017,530-transition training pool; physical acquisition is counted once.
Fourteen focused tests pass, independent audit 53/53, and 83 frozen
source files match. Main/audit run once in 74.72/55.53s, both stderr 0.
Keep H2; general strategic learning remains open, U005 FAIL, U006 unstarted.

[V153 paired module/continuation diagnosis](reports/MODULE_DIAGNOSIS_V153_RESULTS.md)
is complete. All 64 frozen roots receive 16 fresh suffixes and four branches.
On the preselected accepted risk8 roots from H2, original-target advantage
is overestimated by +2.8465 [1.4410,4.2520]; MSE excess over zero is
+8.4286 [2.5503,14.3070]. Estimation problems already exist under the
original H2 continuation. Retain the favorable local result: on gate-visited
risk1 roots, the frozen call rule gains +0.1650 [0.0252,0.3049] versus
rejecting the current module and continuing the same gate, positive in all
four histories and four suffix blocks. This is not full-game superiority.
The direct continuation shift on gate-visited risk8 roots is +1.2360
[-0.2844,2.7563]; continuation mismatch is not established as the cause.
Keep H2. V154 above completes the matched repair comparison using all
64 roots and a fixed reference gate; neither repair establishes a fresh
full-game benefit despite substantially lower training error.
All 4,096 branches terminate, using 2,017,530 environment transitions and
no fitting. Twenty-nine finite tests pass, independent audit 43/43, and
81 frozen source files match. Main/audit run once in 176.32/122.52s,
both stderr 0; finite tests separately consume 93 environment transitions.
Intervals are pointwise and conditional on the frozen roots/histories.
General strategic learning remains open; U005 FAIL, U006 unstarted.

[V152 common-seed replication of frozen modules](reports/MODULE_REPLICATION_V152_RESULTS.md)
is complete. All 80 V151 models and all five checkpoints are frozen; each
history uses 16 new seeds shared across checkpoints, queries and methods.
Final LEARN8-H2 is +0.1179/+0.9990 for risk1/risk8, with conditional seed
95% intervals [-0.7787,1.0145]/[-1.9118,3.9098]. Risk8 is positive in 2/4
histories; LEARN8-ALT is +0.7635 [-2.6904,4.2175]. The earlier large final
risk8 signal is not yet robustly replicated. Its same-seed LEARN8-H2 curve
is [0,+2.5276,+1.8296,-0.3575,+0.9990]; all adjacent-update intervals
include zero. Keep H2; there is no established stable improvement with
experience. V153 above completes the four-continuation diagnosis: it finds
original-target overestimation in an accepted risk8 subset and preserves
positive local gate decisions on gate-visited risk1 roots. V154 above
compares both repair targets without establishing full-game benefit.
All 1,152 physical games terminate, yielding 2,560 logical references and
1,129,190 new environment transitions; no new training or updates.
Seventeen finite tests pass, independent audit 41/41, 77 frozen files match.
Main/audit run once in 103.03/251.32s, both stderr 0. Intervals condition on
four fixed training histories; general strategic learning remains open.
U005 FAIL, U006 unstarted.

[V151 conditional executable policy modules](reports/POLICY_MODULES_V151_RESULTS.md)
is complete. Two frozen H2 policies supply one/eight-step interventions.
Root-conditioned three-component models retain weights and experience across
four batches, using identical complete triplets and the same shared pool budget.
At the final checkpoint LEARN8-H2 is-0.7800/+5.8969 for risk1/risk8,
positive in1/4 and3/4 histories. LEARN8-LEARN1 is-1.6826/+7.6953;
LEARN8-ALT (always switch) is-0.3196/+4.5614, with risk8 positive in all
four histories against both controls. Final risk8 wins are12/16 versus H2
7/16 and ALT8/16. This is a positive signal for conditional modules in risk8.
The full LEARN8-H2 curves are[0,+.7891,+.6838,+.7701,-.7800] and
[0,-3.5842,+.9326,-.1992,+5.8969]. Keep H2; broad benefit and stable
improvement with experience remain unestablished. V152 above completes the
larger common-seed replication: final risk8 gains shrink and remain uncertain.
Of1,197 complete triplets sharing the first action,739 diverge later within
the eight-step module and507 have different terminal components. These
consequences require more than a first-action afterstate difference. All640
fresh diagnostic roots are unseen in training.
Training uses2,097,152 actual transitions;640 complete evaluation games use
625,313. All1,352 complete triplets train both models;32 budget-censored
triplets retain their costs and train neither. The warm fits make40,960 updates.
Twenty-four finite tests ultimately pass, independent audit67/67, and75
frozen sources match. Main/audit run once in145.70/266.28s, both stderr0.
General strategic learning remains unresolved; U005 FAIL, U006 unstarted.

[V150 training-only cross-fitted tail shrinkage](reports/CROSSFIT_SHRINKAGE_V150_RESULTS.md)
is complete. Four fixed24/8 suffix folds learn one clipped coefficient per
history/query, scaling TRAIN32 tail weights while preserving immediate reward.
Freeze768 predictions before independent evaluation. CF changes24 actions
versus TRAIN32;22 come from history1 falling back to ZERO, with only two
other changes. CF still differs from ZERO on70 roots.
Combined MSE falls from0.3637/4.3804 to0.2467/2.3353 for risk1/risk8,
improving over TRAIN32 in all four histories and all four fixed suffix blocks.
ZERO MSE is0.2682/2.3910. CF versus ZERO action value is-0.0196/+0.0429,
positive in only1/4 and2/4 histories; CF versus H2 is-0.0226/+0.0778.
Keep H2: improved prediction error does not establish stable learned decisions.
V151 above completes conditional one/eight-step modules and new-game
evaluation: final risk8 improves, while risk1 degrades and earlier checkpoints
fluctuate. V152 above completes the frozen common-seed replication; stable
improvement remains unestablished.
General strategic learning remains unresolved.
The32 fold fits attempt32,768 updates,22,144 effective, with no new training
interaction. All11,072 fresh branches terminate, using5,905,121 transitions.
Twenty-two finite tests pass plus one affected-test rerun; real-label preflight
passes6/6, independent audit59/59, and79 frozen sources match. Main/audit run
once in287.97/341.65s, both stderr0. U005 FAIL; U006 unstarted.

[V149 nested training-label precision](reports/LABEL_PRECISION_V149_RESULTS.md)
is complete. TRAIN8 and TRAIN32 use nested V148 suffix means at the same256
roots, with identical zero-initialized UPDATED features, optimizer and32 passes.
Freeze all32 models and1,024 predictions before independent V149 evaluation.
Combined OLD/NEW MSE falls from0.8423/12.8590 to0.3725/5.5608 for risk1/risk8,
improving in all four histories and all four fixed eight-suffix blocks. Yet
ZERO is better at0.2090/2.9477; TRAIN32 loses to ZERO in every history.
TRAIN32 gate gains over ZERO are only+0.0026/+0.0060, positive in2/4 histories
for both queries. Keep H2. Better target precision does not yet establish
reliable learned decisions or full-game gains.
V150 above completes training-only cross-fitted tail shrinkage. It improves
independent MSE but not stable action gains, so the next intervention moves
to executable multi-step policy modules and fresh-state/full-game evaluation.
Two new learners attempt16,384 updates,11,072 effective, with no new training
interaction. Retained nested budget views are1,474,491/5,897,324 transitions;
full V148 acquisition remains charged. All11,072 fresh evaluation branches
terminate, using5,905,778 transitions. Seventeen finite tests pass, retained-label
preflight6/6, independent audit52/52, and78 frozen files match.
One main/audit run takes252.69/288.40s, both stderr0. General strategic learning
remains unresolved; U005 FAIL, U006 unstarted.

[V148 independent training-label remeasurement](reports/INDEPENDENT_LABELS_V148_RESULTS.md)
is complete. Keep all256 TRAIN roots and freeze768 ZERO/UPDATED/SHARED
predictions; independently remeasure all173 action disagreements with32 new
paired suffixes, retaining83 same-action roots as exact zeros. No model updates.
On NEW roots, UPDATED MSE gain over ZERO changes from+1.2135/+12.7789 to
-1.0244/-10.5709 for risk1/risk8; SHARED changes from+1.1457/+12.4966 to
-0.7530/-9.3696. Both models lose in all four histories and all four fixed
8-suffix blocks. OLD aggregate gains also reverse. Fixed-gate gains over H2
fall close to zero, although some gains over ZERO remain positive.
Keep H2: failure on the identical training roots rules out a transfer-only
explanation. V149 above completes the nested TRAIN8/TRAIN32 comparison:
more precise targets improve independent MSE but remain worse than ZERO,
and action gains remain inconsistent. Next address unreliable fitting with
fixed data and representation. General strategic learning remains open.
All11,072 branches terminate, using5,897,324 environment transitions.
Fourteen finite tests pass; independent audit39/39;76 frozen files match.
Main/audit run once in280.61/285.10s, both stderr0; audit replay adds23,608,716
swipes. A parallel lightweight summary reads5,536 retained pairs in1.20s.
U005 FAIL, U006 unstarted.

[V147 shared local advantage representation](reports/SHARED_LOCAL_ADVANTAGE_V147_RESULTS.md)
is complete. One boundary-aware unary/adjacent-pair representation replaces
six-cell addresses while retaining the labels,32-pass LMS schedule and gate.
H2/ZERO/UPDATED/SHARED each run64 fresh games, with44/37/16/16 wins.
SHARED minus H2 is -3.1909/-8.7394 for risk1/risk8, negative in all four
histories. SHARED minus ZERO is -2.1555/-5.6899; minus UPDATED is
-0.8217/+0.2420, with the risk8 positive mean coming from only one history.
Do not adopt SHARED; keep H2.
NEW held-out feature coverage rises from16.09%/14.06% to87.03%/88.37%,
and training-span projection from1.78%/1.47% to37.52%/37.71%. Yet utility
MSE worsens from1.0889/20.5714 to1.2926/24.6250. One training disagreement
collapses to zero; no NEW held-out disagreement does. Better sharing alone
does not establish useful consequence transfer.
V148 above completes independent TRAIN-label remeasurement: even at identical
roots the fitted MSE gains reverse. Next isolate label averaging with fixed
TRAIN8/TRAIN32 learners before further representation changes.
All256 games terminate, using239,979 new environment transitions and no new
training labels. SHARED attempts8,192 updates,5,504 effective. Twenty-three
finite tests ultimately pass; independent analysis passes58/58 and all78
frozen source files match. One main run takes63.96s and one analysis81.41s,
both with empty stderr. General strategic learning remains unresolved;
U005 FAIL, U006 unstarted.

[V146 retained-label and feature-transfer diagnosis](reports/TRANSFER_DIAGNOSIS_V146_RESULTS.md)
is complete with no new environment samples, model samples, fitting or games.
On128 NEW held-out disagreement roots, fixed half-suffix advantage signs
oppose on50.00%/46.88% for risk1/risk8; across all35 overlapping balanced
partitions the rates are49.06%/40.00%. UPDATED observed utility MSE is
1.08887/20.57136, mean-label noise variance is0.86363/13.93249, and the
untrimmed difference is0.22524/6.63887. Training-feature support is also weak:
covered squared norm16.09%/14.06%, training-span projection1.78%/1.47%.
These measures identify coexisting label instability and limited support;
they do not establish a unique cause or an error-attribution percentage.
V147 above completes the fixed shared-feature comparison, including a ZERO
control. Geometric support improves but prediction and control do not; the
next test independently remeasures supervision at fixed training roots.
Twenty-four finite tests ultimately pass, with the initial fixture correction
retained. Source reproduction passes5/5 and independent verification33/33;
all10 frozen source files match. One diagnosis takes1.42s and one verification
1.31s, with empty stderr. Only8.05MB of retained compressed records are read.
General strategic learning remains unresolved; keep H2, U005 FAIL, U006 unstarted.

[V145 visited-state experience expansion](reports/COVERAGE_EXPANSION_V145_RESULTS.md)
is complete. Four predetermined disagreement roots per V144 LEARNED game
provide4,096 paired H2-continuation branches. Effective training pairs rise
from45 to173. Keep the same features, alpha and32 passes; compare the old
PRIOR model with zero-initialized REPLAY (old+old) and UPDATED (old+new),
matching8,192 update attempts for the two new learners.
On256 fresh games, UPDATED minus H2 is -1.1444/-3.0843 for risk1/risk8;
minus PRIOR is -0.4205/-1.5847 and minus REPLAY is -0.3969/-2.9351.
H2/PRIOR/REPLAY/UPDATED win31/25/27/22 of64 games each. Keep H2.
New-root training utility MSE falls from1.2084/12.9732 to0.002439/0.018622,
while new holdout MSE changes only from1.0751/20.6736 to1.0889/20.5714.
The added experience does not establish strategic generalization.
V146 above completes the retained-suffix diagnosis: unstable labels and weak
training-feature support coexist. A controlled shared-feature replacement is
next; no additional suffix collection is needed for that comparison.
All branches and games terminate; acquisition uses2,190,351 transitions and
control236,947, totaling2,427,298. Thirty-three finite checks ultimately pass;
one finite assertion correction is retained. Independent analysis passes85/85.
One main run takes146.85s and one analysis205.53s, both with empty stderr.
All74 frozen source files match. The initial failed V144 analysis work is
included in inherited accounting. General strategic learning remains
unresolved; U005 FAIL, U006 unstarted.

[V144 paired consequence advantage learning](reports/PAIRED_ADVANTAGE_V144_RESULTS.md)
is complete. Eight fixed three-component learners train on128 retained roots;
128 roots from separate original games remain diagnostic validation. On192
new games, LEARNED minus H2 is -1.3225/+1.4309 for risk1/risk8, but LEARNED
minus the same untrained ZERO gate is -0.0850/-0.1205. The risk8 gain already
exists without learned weights. Do not adopt the learner; keep H2.
H1 selection rises from about6.5% to16.4%/17.1% without a mean learning gain.
Only45 training roots have different candidates, or2–10 per fitted model.
Validation utility MSE changes from0.28155 to0.26873 and3.40010 to3.47854;
small training error does not establish strategic generalization.
V145 above completes this fixed-learning-settings experience expansion;
its added data does not establish a gain against prior or matched replay.
All192 games terminate; new control uses181,496 environment transitions and
no new training interaction. One main run takes36.91s. Thirty-three finite
tests pass before execution; one additional test covers a corrected analyzer
counter-prefix collision. The original failed analysis is retained, and
repaired analysis passes62/62 checks without retraining or replaying games.
Analysis attempts take57.58s and58.81s; all stderr files are empty.
General strategic learning remains unresolved; U005 FAIL, U006 unstarted.

[V143 paired counterfactual outcomes](reports/COUNTERFACTUAL_OUTCOMES_V143_RESULTS.md)
is complete. Force each distinct selected first action, then use a common
frozen H2 continuation. Across256 fixed roots and eight shared suffixes,
LEARNED64 minus H2 yields -0.05229/-0.52267 utility for risk1/risk8,
negative in all four histories. H1_CONT minus H2 is -0.03010/-0.23999,
negative in three histories for each query; H1_CONT minus LEARNED64 is
+0.02219/+0.28268, positive in three. Keep H2.
These are realized conditional outcomes, extending the earlier proxy
diagnosis: improved continuation selection repairs only part of the loss.
The policy-bound difference learner is tested in V144 above, with original
games separated for training/validation and new games for control. It does
not establish a mean improvement over its untrained gate. The acquired
training outcomes no longer serve as unseen test evidence.
All3,616 physical branches terminate, producing2,048 paired experience
records. New environment transitions total1,875,576 and H2 enumerates
73,597,468 outcomes; no fitting occurs. Full compressed suffixes occupy
about3.7 MB. Thirty-four finite tests and33 independent checks pass;
one run takes95.12s and one analysis99.86s, both with empty stderr.
One-action interventions do not establish full-method or optimal values.
General strategic learning remains unresolved; U005 FAIL, U006 unstarted.

[V142 query-specific H1 continuation](reports/H1_CONTINUATION_V142_RESULTS.md)
is complete. Replacing shallow-tree priorities improves mean utility over
LEARNED64 by +0.5977/+3.0828 for risk1/risk8, with two/three positive
histories. It still loses to H2 by -3.2332/-6.3907 in all four histories,
and differs from SHALLOW by -1.3603/+1.8011. Keep H2.
On 1,973 identical roots, centered action-value MAE falls to0.1052/0.1364
from0.1855/0.2597 for deep programs, but remains above shallow0.0498/0.0531.
Action disagreement is41.23%/43.50%; stronger continuation choices alone
do not resolve the loss. Actual work is159–161 swipes and139–141 leaf
predictions per decision, approaching H2's181/156.
The paired alternative-action outcome experiment is completed in V143 above:
realized terminal returns support repairing candidate choices, with H2 kept
as the reference continuation and the main closed-loop control.
Sixty-four new games (12 wins,52 losses) plus192 retained games all terminate.
No new training;52,221 real transitions,2,039,549 control model samples and
83,402 diagnostic samples. Twenty-seven finite tests and42 independent
checks pass; one main run takes9.95s and one analysis12.34s, stderr both0.
Historical timings are not a concurrent speed benchmark. General strategic
learning remains unresolved; U005 remains FAIL and U006 unstarted.

[V141 shallow-sampling decomposition](reports/SHALLOW_SAMPLING_V141_RESULTS.md)
is complete. Holding the initial samples fixed and removing deeper program
continuation improves utility, but still loses to full H2. SHALLOW minus H2
is -1.8729/-8.1919 for risk1/risk8 (all four histories negative); LEARNED64
minus SHALLOW is -1.9580/-1.2817 (four/three histories negative).
On 1,973 identical retained H2 roots, shallow action disagreement is
18.60%/21.20%, versus47.81%/47.02% for deep programs. Centered value
deviations and H2-proxy regret also worsen under deep continuation in every
history. Both root sampling and deeper continuation need attention; keep H2.
The query-specific H1 continuation comparison is completed in V142 above:
it improves part of the deep-program loss but does not replace H2.
Sixty-four new games (14 wins,50 losses) pair with128 retained games, all
terminal. No training samples are added. New real transitions total53,238;
model samples are536,816 for control and104,269 for diagnostics.
Twenty-four finite tests and49 independent checks pass; one main run takes
14.12s and one formal analysis13.90s, both with empty stderr.
H2 values are a frozen proxy; no general strategic-learning success or
causal percentage attribution is claimed. U005 remains FAIL; U006 unstarted.

[V140 conditional policy-program planning](reports/PROGRAM_PLANNING_V140_RESULTS.md)
is complete. Final learned programs exceed same-structure random priorities
by +2.4685/+2.0871 utility (risk1/risk8), with four/two positive histories.
They nevertheless lose to H2 by -3.8309/-9.4736, negative in all four
histories for both queries. Final wins are learned7/64, H234/64,
random1/64 and direct0/64. The1/8/64-episode curve is not steadily improving.
Keep H2. Actual swipes fall to about75 per decision versus181, but runtime
rises to159–174 microseconds versus100–101; there is no total-time benefit.
The shallow comparison is completed in V141 above: first-layer sampling
loses to H2, and deeper continuation further degrades returns and root rankings.
All512 games terminate (52 wins,460 losses); new training samples are zero.
Evaluation uses317,023 real transitions,9,080,172 sampled model transitions
and2,749,506 enumerated outcomes. Forty-four finite tests are covered and
41 independent checks pass; the retained runner-test setup error was repaired.
One main run takes31.93s and one analysis23.62s, both with empty stderr.
This establishes a scoped learned-ordering contribution, not a replacement
for H2 or general strategic learning. U005 remains FAIL; U006 unstarted.

[V139 factored conditional fragments](reports/FACTORED_FRAGMENTS_V139_RESULTS.md)
is complete. Sharing guarded line effects and dynamic spawn patches raises
held-out coverage to 1,742/2,031 after one episode (85.77% pooled;85.51%
game/history mean) and 2,031/2,031 after eight and64 episodes. Every whole
numeric binding is unseen; the matched whole-path library hits only one
window at64 episodes, and the concrete cache has no hits. All exits,
rewards and5,805 H2 continuation probes match exactly. Each history needs
34 local programs by episode8, with no subsequent growth: four libraries
occupy24,925 bytes versus7,547,395 for8,023 whole-path programs.
The composition applicability stage is complete. V140 above tests learned
conditional programs in real decisions: learned priorities help relative
to random ones, but remain substantially weaker than H2. V139 itself keeps
H2 control fixed and does not establish strategic learning or policy improvement.
Twenty-five finite tests and39 independent checks pass; one main run takes
9.15s and one analysis4.05s, both with empty stderr. No new training samples;
64 evaluation games terminate, using63,944 real transitions and3,097,972
enumerated outcomes. U005 remains FAIL; U006 unstarted.

[V138 guarded cross-action fragments](reports/GUARDED_FRAGMENTS_V138_RESULTS.md)
is complete. The two-action, two-spawn conditional programs return executable
exit states and rewards, but held-out reuse remains weak: snapshots after
1/8 episodes have no hits; the64-episode library hits4/2,014 windows, including
3/2,013 unseen numeric bindings (0.149% pooled;0.148% game/history mean).
All four exits and H2 continuation action values match exactly. The final
library has8,023 programs versus8,029 concrete entries, yet occupies4.2 times
as many serialized bytes. Of2,010 misses,1,990 have no matching joint
action/spawn-cell/occupancy bucket and only20 fail guards.
The factored comparison is completed in V139 above: local programs and
dynamic spawn patches remove this coverage bottleneck on the held-out cohort.
Twenty-six targeted tests and33 independent checks pass. Training uses
retained data only;64 new H2 games all terminate, with63,432 new real
transitions and2,787,654 enumerated model outcomes. One run takes10.21s and
one analysis7.72s, both with empty stderr. No policy-improvement claim is made.
U005 remains FAIL; U006 unstarted.

[V137 matched terminal supervision](reports/TERMINAL_SUPERVISION_V137_RESULTS.md)
is complete. Terminal supervision reduces held-out teacher reward MSE
by 78–91% relative to one-step TD, and recomposed old-query MSE also falls
in all four groups. Control nevertheless worsens: TERMINAL minus TD utility
is -2.4811/-2.8447 for SINGLE and -1.5880/-2.0997 for CAPACITY (risk1/risk8).
Wins are TEACHER 137/256, TD 99/256 and TERMINAL 51/256.
The leaf replacement is not adopted. V138 above implements conditional
cross-action programs with executable exits; their whole-path applicability
remains too narrow and motivates factoring local dependencies.
Both arms replay the same 8,582 complete episodes, each with 8,378,626
updates; 83,795,608 TD source numbers match exactly. New training samples
are zero. All 768 physical evaluation games terminate, with 700,839 new
real evaluation transitions and 40,637,360 enumerated model outcomes.
Twenty-nine targeted tests and 39 independent checks pass. One run takes
393.77s and one analysis 148.44s, both with empty stderr.
U005 remains FAIL; U006 unstarted.

[V136 joint Bellman consequences](reports/BELLMAN_CONSEQUENCES_V136_RESULTS.md)
is complete. All twelve LEARNED-minus-fixed-TEACHER mean utility differences
are negative. Old-query differences are -.3933/-1.7047 for SINGLE and
-.7471/-3.7743 for CAPACITY (risk1/risk8). Eleven of twelve comparisons with
INITIAL are also negative. On held-out teacher trajectories, reward MSE
worsens in all four groups and success Brier remains close to its .25 prior.
The joint learner is not adopted; frozen H2 remains the control baseline.
The matched terminal-supervision comparison is completed in V137 above:
teacher reward prediction improves, while control deteriorates further.
All 1,536 physical evaluation games terminate (724 wins, 812 losses);
2,304 logical records include declared aliases. New work totals 9,851,539
real transitions and 450,809,058 enumerated model outcomes, with zero
stochastic model samples. Thirty-two targeted tests and 37 independent
checks pass. One main run takes 803.27s and one analysis 135.09s, both with
empty stderr. U005 remains FAIL; U006 unstarted.

[V135 planning on frozen learned values](reports/FROZEN_LEAF_PLANNING_V135_RESULTS.md)
is complete. H2 minus DIRECT utility is +4.1134/+10.0569 for SINGLE and
+3.0278/+8.9300 for CAPACITY (risk1/risk8), with all four histories improving
in all four comparisons. Wins increase from 30/256 to 154/256. This isolates
a positive planning contribution on the same frozen values. Per-decision
leaf predictions increase 43.9–44.3 times; native batching and Python overhead
make wall-time ratios unsuitable as claims of fewer model operations.
The fixed-teacher joint consequence experiment is completed in V136 above;
its estimates and old-query control do not improve. All 512 games terminate; new work is
464,788 real transitions and 11,353,154 enumerated model outcomes, with no
training or stochastic model sampling. Twenty-five targeted tests and 18
independent checks pass. One run takes 39.38s and one analysis 5.03s, both with
empty stderr. U005 remains FAIL; U006 unstarted.

[V134 context-conditioned n-tuple TD](reports/CONTEXTUAL_NTUPLE_V134_RESULTS.md)
is complete. Final GLOBAL minus SINGLE utility is -.1874/+1.6174 for
risk1/risk8, while GLOBAL minus the equal-allocated-parameter local CAPACITY
control is -.3689/-.3618. Global conditioning has no demonstrated specific
advantage and is not adopted. CAPACITY exceeds PARENT by +1.0370/+2.2089
(4/4 histories for both), but exceeds SINGLE in only 2/4 and 3/4 histories.
The fixed-leaf DIRECT/H2 comparison is completed in V135 above, with
consistent benefits and substantially more model operations per decision.
Training uses 12,582,912 transitions; 1,280 physical evaluation games all
terminate. Total new transitions are 13,635,650, with zero model samples.
Twenty-six targeted tests and 30 independent checks pass; one main run takes
1457.66s and one analysis 66.64s, both with empty stderr. U005 remains FAIL;
U006 unstarted.

[V133 fixed multistep query TD](reports/MULTISTEP_QUERY_TD_V133_RESULTS.md)
is complete. Final 32-step minus original one-step utility is -4.2017 for
risk1 and -7.2263 for risk8, negative in all four histories for both queries.
The 32-step method also loses to PARENT in every history; its final 128 games
have no wins. It is not adopted. SINGLE exceeds PARENT by +.6308/+1.3174
(3/4 histories each), while risk8 still declines from its middle checkpoint.
The context-conditioned representation and local capacity comparison is
completed in V134 above; its next step isolates planning on frozen values.
Training uses 8,388,608 transitions; 896 physical evaluation games all terminate.
Total new transitions are 8,981,006, with zero model-generated samples.
Thirty tests and 29 independent checks pass; one main run takes 683.52s
and one analysis 45.59s, both with empty stderr. U005 remains FAIL; U006 unstarted.

[V132 retained-update attribution](reports/TD_ATTRIBUTION_V132_RESULTS.md)
is complete. Replaying 1,572,864 retained transitions reproduces all four final
risk8 checkpoints exactly, with zero new samples. Half of the 64 first action
divergences are symmetric feature ties. All 64 fixed supplementary feature
probes exhibit strict ranking reversals: mean gap changes from -.026214
to +.025681. Signed contributions are -.000199 from direct loss updates,
-.034573 from winning boundaries and +.086667 from bootstrap updates.
Contributions from other boards sharing features total +.072897, versus
-.021002 from updates to the probe afterstates themselves. Category directions
vary across histories, so this does not identify one universal cause of decline.
The fixed multistep terminal-anchored comparison is completed in V133 above;
the next hypothesis concerns global conditions on the local representation.
Twenty targeted tests and 30 independent checks pass; one replay takes 7.51s
and one analysis 4.01s, both with empty stderr. U005 remains FAIL; U006 unstarted.

[V131 target-query online TD](reports/ONLINE_QUERY_TD_V131_RESULTS.md)
is complete. Under equal new-transition budgets, final PRIOR minus PARENT
utility is +.4083 for risk1 (4/4 histories improve) and -.8269 for risk8
(1/4 improves). PRIOR exceeds SCRATCH in all four histories for both queries.
Risk8 improves at 131,072 transitions but declines in every history by the
preselected final 524,288 checkpoint; wins fall from 14/64 to 6/64.
This is partial evidence of incremental learning, with high-risk adaptation
still unresolved. Update attribution and the fixed multistep target comparison
are completed in V132 and V133 above.
Training uses exactly 8,388,608 transitions, with 16 final active prefixes;
1,024 physical full evaluation games all terminate. Total new transitions
are 9,041,731, with zero model-generated samples. Zero-training PRIOR exactly
matches PARENT at 106,340 decisions and 382,577 legal action values.
Twenty-two tests and 28 independent checks pass; one main run takes 472.01s,
one analysis 19.53s, both with empty stderr. U005 remains FAIL; U006 unstarted.

[V130 paired n-tuple action-gap learning](reports/PAIRED_NTUPLE_V130_RESULTS.md)
is complete. Spatial priors help relative to scratch, but the learned residual
still degrades its parent: full-game utility differences are -2.1226/-3.8839
for risk1/risk8, negative in all four source histories. Training gap errors
fall sharply; held-out errors do not improve. Replacing the subsequent policy
adds -0.9115/-2.8453 utility relative to changing only the first action.
The residual is not adopted. Target-query n-tuple TD with matched new
transition budgets is completed in V131 above.
All 512 root slots are retained (336 training, 114 held out, 62 missing).
New work is 6,605,490 actual transitions across 128 acquisition games,
13,984 continuations and 384 full evaluation games, all terminal.
Twenty tests and 22 independent checks pass; one main run takes 288.38s,
one analysis 5.09s, both with empty stderr. U005 remains FAIL; U006 unstarted.

[V129 source-only policy calibration](reports/POLICY_CALIBRATION_V129_RESULTS.md)
is complete. Eight offsets fitted only to retained V126 training reduce
fresh-panel mean cross-policy gap errors from 2.8132/2.7815 to
.0183/-.0134 for risk1/risk8 (Monte Carlo SE .1509/.4674); every source
history reduces its mean bias. Source proposals stay unchanged.
Full control does not improve consistently: CAL minus UNCAL utility is
+.3259 (2/4 positive histories) and -1.1907 (1/4) with learned success;
constant-success controls give -1.0114 and -.2270 (both 0/4 positive).
Calibrated learned control still trails both frozen sources in all four
histories for both queries. It is not adopted as the default controller.
Source-initialized action-gap learning with matched parent continuations
and one frozen policy improvement is completed in V130 above.
Reused 6,635,452 training transitions; new work is 678,009 actual transitions
across 16 root-acquisition games, 880 forced continuations and 320 control
games, all terminal. Eighteen unique tests and 29 independent checks pass.
One main run takes 41.90s, one analysis 4.35s, both with empty stderr.
U005 remains FAIL; U006 unstarted.

[V128 paired forced-action diagnosis](reports/FORCED_ACTIONS_V128_RESULTS.md)
is complete: all 64 retained first disagreements reproduce exactly and map
to 62 unique boards, with 4,000 terminal physical continuations. Cross-policy
value comparison has a systematic offset: predicted risk_goal-minus-reward
advantages are 3.1070/3.4135 for risk1/risk8, versus measured .1422/.5340
(Monte Carlo SE .1103/.4041); every history overstates this advantage.
Within-policy first-action effects remain unresolved: -.1122/-.4052 with
SE .1206/.4389. Most first disagreements occur early; 14/64 are D4-related
numerical near-ties, retained without filtering. These forced source-policy
continuations do not explain the full adaptive-control decline.
Source-only return calibration and independent GPI evaluation are completed
in V129 above; V128 evaluation returns stayed out of fitting.
New work: 3,227,111 actual transitions, no training or model-generated samples.
Nineteen tests and 24 independent checks pass. One main run takes 190.33s,
one analysis 2.83s, both with empty stderr. U005 remains FAIL; U006 unstarted.

[V127 anchored success differences](reports/ANCHORED_SUCCESS_V127_RESULTS.md)
is complete. All 256 own-query verification games exactly reproduce the
frozen source histories. Final source-path Brier error beats the training
constant in all eight history/policy cells, with bounded probabilities.
Transfer still fails: learned GPI minus matched constant GPI is -4.0424
utility for risk1 and -5.3124 for risk8, negative in every history.
All 512 GPI games exactly match the corresponding risk_goal single readout.
The paired forced-action diagnosis on fixed retained boards is completed
in V128 above, separating action-gap uncertainty from cross-policy value bias.
Reused 6,635,452 training transitions; no fresh training samples.
New work: 1,600 terminal outer games and 1,190,724 transitions.
Twenty-two targeted tests and 31 independent checks pass; one main run
takes 156.58s, one analysis 7.38s, both with empty stderr.
U005 remains FAIL; U006 unstarted.

[V126 fixed-policy consequences for unseen queries](reports/POLICY_CONSEQUENCES_V126_RESULTS.md)
is complete. The reusable three-component interface works, but the current
unconstrained Monte Carlo fit fails the policy test: GPI loses to both frozen
source policies in all four histories for both unseen queries. Final GPI
utility is .1625 for risk1 and -7.5787 for risk8; all 768 learned-readout
evaluation games across checkpoints end in loss.
Failure prediction is worse than the training-prefix constant in all eight
history/policy cells, and all six policy/component mean MSEs are worse than
constant on held-out source paths. The failure already occurs before GPI's
distribution shift. The scalar-value anchor with bounded event counts and
exact own-query action recovery is evaluated in V127 above.
New work: 6,635,452 training and 184,603 outer transitions; 832 physical
outer games, all terminal. Twenty-one targeted tests and 30 independent
checks pass. One main run takes 458.15s; one analysis takes 8.28s, both with
empty stderr. U005 remains FAIL; U006 unstarted.

[V125 confirmed contexts with value learning](reports/CONFIRMED_VALUE_V125_RESULTS.md)
is complete on fresh training and evaluation streams. All eight learners keep
two contexts, preserve the source bank through B and recover it on return.
BANK and the matched delayed single-table control DELAY are identical in B.
On return, BANK minus DELAY is -467.625 reward points (1/4 histories improve)
and +.1934 risk-goal utility (2/4). Context protection works; consistent policy
benefits are not established. The MD's query-reusable, policy-conditioned
consequence branch with fixed source policies is evaluated in V126 above.
New work: 25,165,824 training and 536,748 outer transitions; 832 terminal outer
games. Twenty-three targeted tests and 36 independent checks pass.
One main run completes in 1,551.66s with empty stderr; analysis-only path
correction does not change the experiment. U005 remains FAIL; U006 unstarted.

[V124 confirmed context identification](reports/CONFIRMED_CONTEXT_V124_RESULTS.md)
completes the retained-trace routing milestone. All eight streams keep exactly
two modules, preserve source statistics through B, and switch once into B and
once back to source. Total switches fall270->16 and creations51->8; return
source-ID action coverage is99.9756% in every stream, with no further wrong
routing after128 observations. This is identity recovery on existing traces,
not measured value-policy improvement. Three of eight return prediction losses
increase slightly; both changes require128 observations.
Fresh-stream value learning with explicit TD handling before confirmation
is completed in V125 above. Seventeen targeted tests pass;
8388608 retained training ranks and2048 warmup ranks reused, no new samples,
TD updates or weight loads. One main replay completes in6.38s, stderr empty.
U005 remains FAIL; U006 unstarted.

[V123 persistent context routing](reports/PERSISTENT_CONTEXT_V123_RESULTS.md)
is complete on all eight retained V122 training streams, with exact baseline
action/event/final-state reproduction. Adding the fixed log64 reactivation
penalty reduces switches from28,812 to270 and preserves source statistics
through B in7/8 streams. It does not resolve identity: creations rise21->51,
final module counts rise3–4->4–11, and one previously recovered return stream
drops from99.98% to9.33% source-bank use. A rare block can create a duplicate
whose switching penalty then keeps it active; nearly equal probability
estimates do not establish recovery of the old value bank.
The separated detection/matching test is completed in V124 above. No new samples, TD updates or weight
loads;8,388,608 training ranks and2,048 warmup ranks reused. Thirteen targeted
tests pass; one main replay completes in8.29s with empty stderr.
U005 remains FAIL; U006 unstarted.

[V122 observed-context value banks](reports/CONTEXT_BANK_V122_RESULTS.md)
is complete. Final bank-minus-CONT means are negative in all four phase/query
comparisons: B reward -1,473.4 points and win-sensitive utility -.4855;
return reward -262.5 points and utility -2.0742. The V121 mean return decline
also does not repeat on this fresh outer cohort: CONT at return0 exceeds
frozen A by937.6 points (3/4 histories) and1.5447 utility (4/4).
Post-run replay finds identity drift: three of eight source-context estimates
move to about .40 during B, and their old value banks serve fewer than .16%
of returning decisions. B produces2,065–4,692 reactivations per history/query.
Do not replace continued TD with this bank rule. The retained-observation persistence test is completed in V123 above.
New work:8,388,608 training and535,999 outer transitions;832 terminal outer
games,16 retained training cutoffs. Twenty-one targeted tests and35 independent
checks pass. Peak value-bank memory is226.76MB;107 snapshots use1.63GB.
U005 remains FAIL; U006 unstarted.

[V121 unannounced parameter change and return](reports/NTUPLE_REGIME_V121_RESULTS.md)
is complete with the V120 learner fixed and exact new transition budgets.
Continued learning beats reset learning in all four histories for both queries
in both phases. Against frozen A knowledge, B reward improves by 2,758.4 points
in 4/4 histories, while B win-sensitive utility improves by .8150 in only 2/4.
At return, pre-update means decline by 527.5 points and .8049 utility; subsequent
learning improves them, but final-vs-frozen effects remain negative in 2/4
histories for each query. Experience is useful; stable old-task retention is
unresolved in that cohort. The context-bank test and fresh evaluation are
completed in V122 above.
New work: 16,777,216 training and 437,976 outer transitions, no model-generated
samples; 832 terminal outer games, 32 retained training cutoffs. All 16 targeted
tests and 26 independent checks pass. U005 remains FAIL; U006 unstarted.

[V120 persistent spatial n-tuple TD learning](reports/NTUPLE_LEARNING_V120_RESULTS.md)
is complete. Across four fresh training histories and two separately trained
objectives, the fixed learner improves with experience: reward scores rise
2,942.1 -> 5,804.4 -> 9,764.4 -> 14,482.0 at 0/256/1024/4096 games;
win-sensitive utility rises -2.5634 -> -.9790 -> .2177 -> 3.6589.
Final-vs-256 and final-vs-H2 effects are positive in all four histories for
both objectives. Final mean utility also exceeds MC4, but each objective has
two negative history effects and reward-query wins are 2/32 versus MC4's 8/32.
Training costs 22,124,667 actual transitions and 22,123,403 TD updates; it uses
no generated rollout samples. All 32,768 training and 384 outer games terminate;
17 targeted tests and 17 independent checks pass. This supports parameter
accumulation on the fixed task, not autonomous structure learning or sample
efficiency. The A/B/A-return test is completed in V121 above.
U005 remains FAIL; U006 unstarted.


[V119 direct model consequences at the frozen planning boundary](reports/ROLLOUT_CONSEQUENCES_V119_RESULTS.md)
is complete. With the same fixed policies, horizon and planner, MC4/MC16 beat
both the selected tree and H2 on both query means in all four A-return lives.
Reward-query scores: H2 10,769, TREE 5,488, MC4 15,524.5, MC16 16,988;
risk-query utilities: .9409, -2.1274, 6.2368, 6.1765. Wins across both queries
are 0/16, 0/16, 6/16 and 8/16 respectively. This locates a useful intervention
at the consequence-estimation boundary; it does not isolate approximation,
coverage or estimation noise. The MD's spatial n-tuple/TD learning baseline
is now implemented and evaluated in V120 above; the selector remains frozen. All 64 games terminate, 14 checks
and 13 targeted tests pass. New work: 42,021 actual transitions, 519,881,042
model spawns, no fitting/router updates. This is expensive online simulation,
not established knowledge compression or continual-learning success.
U005 remains FAIL; U006 unstarted.

[V118 source planning-utility consolidation](reports/UTILITY_CONSOLIDATION_V118_RESULTS.md)
is complete on the frozen V117 candidate histories. Fresh utility validation
selects five split updates, two shared updates and one KEEP. All four B/A-return
query means improve over the old MSE selector; A-return risk gains +1.5742,
positive in all four lives. However, all 24 life/phase/query utility differences
against H2 remain negative. A-return updating loses -0.4661 reward utility against
retaining the B-end consequences, while gaining +0.6787 risk utility.
The extra 51,639 validation transitions exceed the 48,637 inherited source
transitions. The fixed-interface consequence comparison is complete in V119
above; the selector remains frozen and the learning representation is next. All 520 new games lose;
16 tests and 17 completeness checks pass. New work: 144,468 real transitions,
897,820 model spawns and zero fits. U005 remains FAIL; U006 unstarted.

[V117 fixed consequence consolidation](reports/CONSOLIDATION_V117_RESULTS.md)
is complete. Separate mechanism banks outperform shared trees in all four B/
A-return query means; A-return risk utility gains +1.6970 with all four lives
positive. However, source-MSE consolidation selects no split candidate: two
shared updates and six KEEP decisions. Its A-return risk utility loses -2.0696
to SPLIT, negative in every life. All learned controllers still trail H2 in
all six phase/query means. The fixed-candidate utility-validation experiment is
complete in V118 above; its selection gains incur additional sampling costs.
All 480 games terminate LOST; 18 tests and 22 completeness checks pass. New work:
130,312 real transitions, 449,230 model spawns and 96 tree fits. U005 remains FAIL;
U006 unstarted.

[V116 mechanism-conditioned joint consequence learning](reports/CONTEXT_CONSEQUENCES_V116_RESULTS.md)
is complete. On fresh A-return games, CONTEXT reward MSE exceeds MIXED in all
four lifecycles. Both learned controllers fall below H2 in all six phase/query
means. Context offers a limited retention signal, while one returning lifecycle
ends with the wrong parameter module (p4=.29434 versus .1). All 432 games lose,
so the success component has no positive evidence. The fixed shared-versus-separated
consolidation comparison is complete in V117 above. V116 is not retuned.
All 21 targeted tests and 18 completeness checks pass. New work totals 116,657
real transitions, 351,858 model spawns and 72 tree fits. U005 remains FAIL;
U006 remains unstarted.

[V115 parameter memory across unannounced A/B/A-return regimes](reports/REGIME_MEMORY_V115_RESULTS.md)
is complete. Four fixed learners infer spawn probabilities from visible transitions;
all four library lifecycles retain two modules and reactivate their original module.
On A-return, LIBRARY reaches the declared parameter-error criterion in 115–159
new observations, versus 222–264 for RECENT, with lower initial log loss in all
four lifecycles. On novel B, however, log loss is worse than RECENT in all four.
Full-game advantages reverse across checkpoints: final A-return reward/risk
utility falls below every control. Parameter adaptation is now a usable component;
stable strategic improvement remains unresolved.
The frozen-router consequence experiment is complete in V116 above; its new
lifecycle exposes an additional wrong-module return. Further selector replication
on histories19–22 remains deferred. This does not declare stage1 successful.
All 72 training games and 560 evaluation games terminate; 23 targeted tests and
20 terminal checks pass. New work is 16,806 training and 272,657 evaluation
transitions plus 1,913,698 model spawn samples. U005 remains FAIL; U006 unstarted.

[V114 direct validation of deployment models](reports/DIRECT_VALIDATION_V114_RESULTS.md)
is complete. Replacing two-source validation proxies with the actual three-source
models changes 12 of 16 choices. H16 reward improves over the old selector, HALF
and FULL by +0.04737/+0.03440/+0.02011, all positive in A/B. H4 reward loses
-0.02348 versus the old selector in both blocks; risk gains over HALF remain
small and reverse across A/B. Deployment-model mismatch explains part of the
selection problem, while stable accumulation remains unresolved.
Further selector replication on histories19–22 is deferred. V115 advances
the separate parameter-adaptation lifecycle; the V114 improvement remains a
retrospective mechanism result on already observed V113 targets.
New work is 768 source model-root scores, 16 choices and 512 cached target
decisions; no fitting or sampling. All 13 targeted tests and 19 terminal checks
pass. U005 remains FAIL and U006 remains unstarted.

[V113 frozen update choices on fresh common targets](reports/FRESH_TARGETS_V113_RESULTS.md)
is complete. Three of eight pooled SELECTED-minus-HALF/FULL effects remain
positive on 64 fresh roots and 10,240 new terminal references. H4 reward gains
+0.02329/+0.01439, both positive in A/B. H16 reward loses -0.01297/-0.02726;
its previous advantage does not replicate. H4/H16 risk both lose to HALF
(-0.01923/-0.01479), negative in A/B, while H16 risk still improves over FULL.
The full four-source-bundle by four-target-history evaluation uses unchanged
models and choices saved before new references. No fitting or reselection.
The direct deployment-model validation comparison is complete in V114 above;
it improves H16 reward but worsens H4 reward, and still requires fresh confirmation.
New work totals 5,302,737 true environment transitions (36,904 source games and
5,265,833 reference suffixes), 40,960 model-prefix transitions and 1,024 neural
model-root scores. All 15 terminal checks and 20 targeted tests pass. Stable
accumulated gains remain unresolved; U005 remains FAIL and U006 unstarted.

[V112 nested source-history update selection](reports/NESTED_SELECTION_V112_RESULTS.md)
is complete. All four width/query combinations improve pooled utility over
both always-HALF and always-FULL. H16 reward improves by +0.01884/+0.02921,
positive in both aggregate A/B blocks; its gain over HALF comes only from
life11, while retaining HALF avoids life13's large loss but misses positive
updates in lives12/14. Risk gains over HALF still reverse across A/B.
Source/target update directions agree in 3/4 histories for both H4 queries
and 2/4 for both H16 queries. Stable accumulated gains remain unresolved.
The frozen-model fresh-target replication is complete in V113 above;
its eight pooled comparisons retain only three positive effects.
Twenty-four new fits, 24,000 steps and 768 inner model-root scores produce
128 derived outer decisions with no new outer neural score or sampling.
Each selector still consumes 1,536,000 source training transitions plus
3,896,279–3,934,746 inherited source-validation transitions, even if it selects
HALF. This is a positive signal on reused evidence, not sampling-efficiency
superiority or independent confirmation. All 26 terminal checks pass;
U005 remains FAIL and U006 remains unstarted.

[V111 equal-step half-data continuation](reports/HALF_CONTINUATION_V111_RESULTS.md)
is complete. H16 reward gains +0.03272 from adding the second batch relative
to the matched-step half-data control (A/B +0.01299/+0.05245), while continuing
on unchanged half data loses -0.04309 versus the original half model
(A/B -0.03200/-0.05418). Their sum reproduces V110's -0.01037: added data
partly offsets deterioration from extra optimization, without beating the
original half model. H4/H16 risk data effects are -0.06853/-0.01147 with
opposite A/B signs. H16 training ranking error remains zero while internal
holdout error is 34.82–63.98%; stable accumulation is still unresolved.
The fixed source-history validation rule and its learning costs are
evaluated in V112 above, with outer target references excluded from selection.
Eight new fits, 8,000 steps and 128 new decisions reuse 64 roots and 10,240
references with zero new sampling; 16 models and 256 decisions are inherited.
All 22 terminal checks pass. U005 remains FAIL; U006 remains unstarted.

[V110 pooled-history leave-one-history-out evaluation](reports/POOLED_HISTORY_V110_RESULTS.md)
is complete. Each fold trains on three histories and evaluates only the excluded
fourth. Full-minus-half utility changes are +0.00642/-0.06628 for H4 reward/risk
and -0.01037/-0.00560 for H16. Three of the four pooled effects are negative;
H4 risk and H16 reward remain negative in aggregate A/B reference blocks.
H16 pooled half still improves over H2 in both query means and both A/B blocks,
but further data and updating have not produced stable accumulated gains.
H16 full training ranking error is near zero while source internal-holdout error
remains 42.55–55.43% on its original four-replica labels.
The matched-step half-data continuation control is complete in V111 above;
its H16 reward result separates harmful extra optimization from a positive
second-batch effect relative to that continuation.
Sixteen fits, 16,000 steps and 256 held-out model-root decisions are new;
64 roots and 10,240 references are reused with zero new sampling. Each fold's
source acquisition is 768,000/1,536,000 half/full transitions; overlapping folds
reuse the same 2,048,000 unique original transitions. U005 remains FAIL;
U006 remains unstarted.

[V109 frozen-hidden/output-head updates](reports/FROZEN_HEAD_V109_RESULTS.md)
is complete. H4 reward improves over full-parameter continuation and its own
half-budget model by +0.02401/+0.03637; H16 risk improves by +0.02060/+0.05152.
All four aggregate comparisons stay positive in A/B. The other query still
fails to improve reliably over half: H4 risk is -0.01828 and H16 reward -0.00666.
Both widths improve risk over H2 in every history's A/B block. Head gradients
are approximately 3e-17–1.2e-16, but training ranking error remains 17–28% under
the fixed representation and loss. Restricting updates gives partial benefits;
stable improvement of both queries remains unresolved.
The pooled-history half/full comparison is complete in V110 above, with
all three source histories' acquisition costs retained.
Eight new fits and 8,000 steps produce 512 new model-root decisions; no new
sampling. Total networks retain 492/1,968 parameters, with only 4/16 trainable.
The original 48 models, 3,072 decisions and 10,240 references are inherited.
U005 remains FAIL; U006 remains unstarted.

[V108 query-gradient ablation](reports/QUERY_UPDATE_V108_RESULTS.md)
is complete. All four own-query comparisons of reward-only/risk-only updates
against joint continuation reverse direction across A/B reference blocks.
H4 risk-only updating improves reward over joint and half by +0.04178/+0.05414,
both positive in A/B. H16 risk-only updating improves risk over half by
+0.03561 but lowers reward by -0.02863, with both directions agreeing across
A/B. Single-query H16 training ranking error is zero while active-query
heldout error remains approximately 31–63%; query isolation has not resolved
the generalization bottleneck. The fixed-hidden/output-head comparison is complete in V109 above, with
total network capacity unchanged.
Sixteen new fits, 16,000 steps and 1,024 new model-root decisions reuse the
187 candidate records, 64 roots and 10,240 references. New sampling is zero;
32 models and 2,048 prior decisions remain unchanged. U005 remains FAIL;
U006 remains unstarted.

[V107 fixed-statistics parameter continuation](reports/INCREMENTAL_RANKING_V107_RESULTS.md)
is complete. Compared with fixed-statistics refitting from the original
initialization, continuation improves H4/H16 reward utility by +0.01026/+0.05139
but lowers risk-goal utility by -0.05028/-0.03620; all four directions agree
across A/B reference blocks. Relative to their own half-budget models, reward
gains are only +0.01236/+0.00191, with mixed training-history effects and
unstable risk effects. H16 continuation still beats H2 on both pooled query
utilities, but its heldout weighted ranking error remains 34.55–61.77% despite
zero training error. Reliable gains from added experience remain unresolved.
The matched joint/reward-only/risk-only update comparison is complete in
V108 above.
Sixteen new fits and 16,000 new optimizer steps reuse 187 candidate records;
1,024 new model-root decisions use the original 64 roots and 10,240 references.
New sampling is zero. Both arms reset Adam moments; continuation retains an
additional 1,000 inherited parameter steps. U005 remains FAIL; U006 unstarted.

[V106 crossed common-root evaluation](reports/CROSSED_RANKING_V106_RESULTS.md)
is complete. All 16 frozen V105 models were evaluated on the same 64 retained
roots; 256 original model-root decisions reproduce every score and choice exactly.
The H4 reward advantage over H2 falls from the original diagonal +0.07068 to
+0.00396 across the full model-by-root matrix, with opposite A/B signs.
H4/H16 full-minus-half reward effects are -0.01343/-0.02620, each negative in
both A/B blocks. Risk effects versus H2 remain positive at +0.06483/+0.09363;
pooled model-history row means are positive in three/four of four histories,
although some rows reverse across A/B. Evaluation-root variation matters,
and reliable improvement from additional training remains unresolved.
The matched fixed-statistics and parameter-continuation comparison is
complete in V107 above.
New sampling and fitting are zero; 1,024 model-root decisions and 5,120 candidate
scores reuse the original 10,240 references as one inherited evidence bank.
U005 remains FAIL; U006 remains unstarted.

[V105 fresh-history replication](reports/FRESH_RANKING_V105_RESULTS.md)
is complete on four new learning histories, with all 64 natural query roots
receiving 32 paired terminal references per option. The frozen R4/H4/uniform-shrink
recipe retains a reward gain over H2: +0.07068 reference utility, positive in
both pooled A/B blocks and three of four histories. Its +0.01409 advantage over
the wide model changes sign across A/B; full versus own half is -0.01539.
Risk reference utility versus H2 averages +0.06903, but only one of four
histories is positive. This partially replicates the reward signal and does
not establish stable capacity or continued-learning gains. The common-root
crossed evaluation is complete in V106 above.
All 384 natural games and 10,240 references terminate; 2,048,000 new training
transitions and 5,444,903 new evaluation/reference transitions, plus 324,480
candidate-model prefix transitions and 16 new fits. U005 remains FAIL;
U006 remains unstarted.

[V104 complete natural-root references](reports/NATURAL_REFERENCE_V104_RESULTS.md)
is complete. All 32 V103 natural query roots now have 32 paired suffixes per
candidate, reusing eight roots and sampling only the remaining 24. The full
capacity comparisons give eight positive and four negative reference effects.
R4/H4/UNIFORM_SHRINK reward improves over the wide model, its own half-budget
version and H2 by 0.21423/0.22402/0.14580 reference utility; all three remain
positive in A/B, both histories and the newly completed cohort. This complete
recipe is a candidate for new-training-history replication, not an adopted
replacement. R4/H4/REPLICA reward loses on the same reference comparisons.
Risk full-versus-half reference means improve in all six narrow models,
correcting the previous single-suffix interpretation; all six full models
still remain below H2 on reference risk utility in this original cohort.
The frozen-recipe fresh-history replication is complete in V105 above. All 3840 new trajectories terminate; 1,982,187 new
real reference transitions, with controller computations retained separately.
No new training, natural games, candidate-prefix sampling, fits or scoring.
U005 remains FAIL; U006 remains unstarted.

[V103 fixed nonlinear capacity](reports/CAPACITY_RANKING_V103_RESULTS.md)
is complete. Four hidden units versus frozen sixteen-unit models, with matched
per-parameter L2, gives 9/12 positive full-budget natural comparisons and
10/12 positive independent selected-utility differences (one tie, one loss).
Eight of ten positive reference differences reverse across A/B blocks.
R4 MEAN_SIGN risk has positive reference differences in both histories and
blocks; R4 REPLICA reward loses on references despite strong natural gains.
Training error remains 0–1.81%, and five of six narrow models lose natural
risk utility after the full-budget update. No overall replacement is adopted.
A zero-sampling matched-root decomposition confirms some suffix disagreements
persist on identical roots. The complete reference extension is finished in
V104 above; preserve these V103 observations.
All 832 games and 1280 references terminate; 1,096,064 new real evaluation
transitions, 512,000 model transitions and 24 narrow fits, plus 24 retained
wide models. U005 remains FAIL; U006 remains unstarted.

[V102 replica-disagreement ranking](reports/REPLICA_RANKING_V102_RESULTS.md)
is complete. Exact MEAN_SIGN reproduction holds at all eight checkpoints.
Full REPLICA improves natural R8 reward/risk over MEAN_SIGN by 86.75 points/
0.33374 utility, but independent selected utility falls by 0.09236/0.20885.
R4 has a local independent risk gain of 0.13966, confined to one history;
natural reward/risk falls by 1196.25 points/0.05627. R8 REPLICA and uniform
shrinkage select identically at every reference root. No overall replacement
is adopted. Training ordering error is 0.11%–0.72%, heldout 42.81%–60.94%.
The matched four-unit comparison is completed in V103 above; preserve these
V102 findings.
All 448 games
and 1280 references terminate; 937,532 new real evaluation transitions,
266,240 model transitions and 24 fits, with zero new training acquisition.
U005 remains FAIL; U006 remains unstarted.

[V101 fixed-heldout order replication](reports/HELDOUT_ORDER_REPLICATION_V101_RESULTS.md)
is complete. On 17 fixed heldout roots, two independent 16-replica reference
blocks disagree on 76 of 170 distinct candidate pairs; 84 agree and 10 contain
a tie. In R4, old labels also agree on 41 of those agreeing pairs, yet MSE and
ranking models reverse 20 and 21 of them. Finite-reference instability and
additional model ordering errors coexist. Ranking improves pooled ordering
error in three of four groups, but R4 risk worsens from 45.21% to 66.19% and
selected-reference gains remain inconsistent. No replacement is adopted.
The matched three-objective experiment is completed in V102 above; these
V101 references remain excluded from training.
All 2720 references terminate; 1,397,687 new real reference transitions and 250
candidate predictions, zero fits or model-prefix sampling. U005 remains FAIL;
U006 remains unstarted.

[V100 direct candidate ranking](reports/QUERY_RANKING_V100_RESULTS.md)
is complete. With matched inputs, capacity and optimizer schedule, ranking improves
all eight allocation/age/query natural mean comparisons against utility MSE, but
independent selected reward falls in all four configurations and ordering error
rises in seven of eight comparisons. Both full ranking models remain below H2:
reward by 1868.5/1359.75 points and risk utility by 1.61108/0.32361 for R8/R4.
Keep the R8 risk signal; no replacement is adopted. Training ordering error is
zero while heldout full-rank errors remain 20.7%–47.2%. The fixed-heldout replication is completed in V101 above; preserve these
V100 findings. All 320 natural games and 640
references terminate; 505,727 new real evaluation transitions, 274,560 model
transitions and 16 neural fits are retained, with zero new training acquisition.
U005 remains FAIL; U006 remains unstarted.

[V99 persistent terminal supervision](reports/TERMINAL_ANCHOR_V99_RESULTS.md)
is complete. Fixed half-return/half-Bellman targets make full-model choices
agree with prefix-only in 31/128 cases, versus 89/128 for original FQE. All four
full configurations lose risk-goal utility to FQE in both histories. R4 boundary
reward gains 1731.75 points over FQE and 1112 over MC, but loses 156.75 to
prefix-only; independent results are mixed. No general replacement is adopted.
The matched direct-ranking experiment is completed in V100 above; preserve
these V99 findings. All 832 natural games and 640 references terminate;
830,253 new real evaluation transitions, 512,000 candidate-prefix transitions,
4,128 new fits and zero new training acquisition are retained. U005 stays FAIL;
U006 remains unstarted.

[V98 fixed-budget root coverage](reports/ROOT_COVERAGE_V98_RESULTS.md)
is complete on two fresh histories. Four versus eight replicas increases
training roots from 40 to 76 at the same actual interaction budget, with 4.26%
fewer training rows. Full-budget reward gains are 411.0 points for paired FQE
and 463.25 for boundary FQE; both histories improve against their corresponding
eight-replica models. Independent selected-reference reward utility is unchanged
for paired FQE and falls 0.17694 for boundary FQE. Risk and continued-update gains
remain inconsistent. Keep the reward signal; reliable learned action ranking
remains unresolved. On eight retained validation roots, 30 of 32 full-model
choices agree with four-step prefix-only choices. The proposed persistent
terminal-supervision comparison is completed in V99 above. All 288 natural
games and 640 references terminate;
2,547,770 new real transitions, 4,128 main fits and 163,840
candidate-prefix model transitions are retained. U005 remains FAIL; U006 unstarted.

[V97 query-boundary learning](reports/QUERY_BOUNDARY_LEARNING_V97_RESULTS.md)
raises boundary training mass to 50% while preserving each trajectory pair's
original total mass. Boundary FQE gains 438.2 reward points over original FQE at
checkpoint 12 and 493.8 at frozen6; descriptive two-SE bands are above zero,
with 5/6 and 6/6 histories improving. Keep this reward signal as a candidate.
Risk gains remain unresolved, updating to checkpoint 12 does not establish a
gain over frozen6, and independent reward selection does not improve. Boundary
MC worsens reward performance and is not adopted. Its proposed fixed-budget
root-coverage comparison is completed in V98 above; preserve these V97 findings.
All 1728 natural games and 1920 references terminate; 3096 new fits, zero new
training acquisition, 2,029,057 real evaluation transitions and 983,040 model
transitions are retained. U005 remains FAIL and U006 remains unstarted.

[V96 paired Bellman advantage](reports/PAIRED_BELLMAN_ADVANTAGE_V96_RESULTS.md)
fits matched paired MC and 128-round Bellman models on retained V93 data and
keeps the four-step, 32-replica deployment interface. Current PAIR_FQE loses
200.0 reward points / 0.1835 risk utility to PAIR_MC; both descriptive two-SE
bands span zero. Heldout tail MSE falls 1.76%/3.42%, but independent candidate
MSE changes by -3.42%/+3.83%, and selected-reference risk utility falls from
+0.3540 to -0.0868. V96 does not support adopting its PAIR_FQE replacement.
The boundary reweighting experiment motivated by its 2.619% training share is
completed in V97 above; preserve V96's negative result.
All 1728 natural games and 1920 references terminate; 3096 new fits, zero new
training acquisition, 2,013,499 new evaluation transitions and 983,040 model
transitions are retained. U005 remains FAIL and U006 remains unstarted.

[V95 direct shared-value evaluation](reports/DIRECT_SHARED_VALUE_V95_RESULTS.md)
freezes V94 knowledge and replaces the fitted head with 32 paired four-step model
prefixes plus shared value. FQE DIRECT gains 121.5 reward points / 0.4247 risk
utility over its head, but both descriptive two-SE bands span zero. Frozen-6 FQE
DIRECT gains 654.0 reward points / 0.3770 risk utility over its head, with both
bands above zero; this local benefit does not establish improvement from further
learning. Independent candidate MSE rises about 2.8% in both queries at checkpoint
12, and selected-reference utility
falls from +0.2281/+0.6695 to -0.0422/+0.0595. This does not support bypassing the
head as a sufficient solution. Keep the risk signal and the negative reference
result; the completed paired Bellman experiment is reported in V96 above.
V95 used no new fits or training sampling; 1728 natural games and 1920 references all terminate. New work totals
1,987,690 environment transitions and 491,520 model transitions; direct selection
costs 412.59 aggregate seconds (current FQE about 0.535 seconds per trigger).

[V94 shared Bellman value](reports/SHARED_BELLMAN_VALUE_V94_RESULTS.md)
reuses the six V93 histories for matched MC-tail and fixed 128-round, MC-initialized
16-step H2 value learning. On 24 fresh terminal-reference roots, value MSE falls
15.43%/8.69% and candidate-head MSE falls 30.99%/3.97% (reward/risk). Natural
performance remains unresolved: final FQE versus matched MC_TAIL is -51.8 reward
points / +0.0194 risk utility; versus H2, -13.6 / +0.1406. All four descriptive
two-SE bands span zero. Updating FQE adds 533 reward points versus its frozen
head, including 309 from cancelling old interventions; risk utility falls 0.0221.
Retain the predictive improvement as a mainline candidate. The direct-evaluation
experiment and its unresolved decision benefit are reported in V95 above. All 3072 natural games and 1920
reference trajectories terminate; new work is 2,738,701 transitions and 9336 fits,
with zero new training acquisition. This establishes measured prediction progress,
not stable policy improvement or a sample-efficiency claim.

[V93 independent-history replication](reports/INDEPENDENT_HISTORY_REPLICATION_V93_RESULTS.md)
refits frozen V91/V92 algorithms on six fresh histories and compares prefix
acquisition with exactly equal extra terminal-sampling budgets. Final CORRECTED
loses 186 reward points and 0.066 risk utility to base MC, and 245/0.064 to H2.
Against budgeted MC it gains 294 reward points but loses 0.121 risk utility;
both descriptive two-SE bands span zero. Its small reward update combines
harmful new interventions with changed choices and cancellation gains. OOF
conditional variance rises 1.27%/5.13%, so stable behavioral gains and the intended
noise reduction have not replicated. All 2688 natural games finish (2671 LOST,
17 WON); new work totals 4,936,032 transitions and 264 fits, with all budget
truncations charged. Retain the current paired-tail correction as a negative
result/control. The following shared-value experiment is completed in V94 above.

[V92 paired continuation correction](reports/PAIRED_CORRECTION_FRAGMENTS_V92_RESULTS.md)
learns candidate-versus-H2 tails and corrects independent short-prefix predictions
with terminal residuals. On common fresh games its final reward/risk scores exceed
MC by 45/378, H2 by 447/609 and its own frozen checkpoint-6 model by 664/444.
Reward improves over the frozen model in all three histories, including positive
new interventions. Against V91 it gains 969 reward points but loses 722 risk
points, so the improvement is partial. Conditional estimator variance increases
1.83%/0.55%, and independent-reference MSE does not improve over MC. All 2496
full trajectories finish (2484 LOST, twelve WON); 26880 four-action prefixes end
at their planned ACTIVE boundary. New work is 1,442,895 transitions and 72 fits.
V93 above completes that independent-history and equal-extra-budget comparison.
The positive behavioral signals do not establish stable replicated gains, and
conditional estimator variance remains higher than MC.

[V91 shared H2 continuation learning](reports/SHARED_CONTINUATION_FRAGMENTS_V91_RESULTS.md)
combines four-action outcomes with query-conditioned tail predictions, using
whole-episode cross-fitting and the same history and selector as full-return MC.
On fresh reference roots, reconstruction variance falls 89%/94%; reward prediction
MSE improves, while risk bias remains positive. At checkpoint 12 it loses 391/561
reward/risk points to MC and 882/484 to H2. Its own risk update gains 439 points
over the frozen checkpoint-6 model, driven by newly enabled interventions, while
reward loses 516. Full-return-minus-prediction residual variance increases 7%/9%,
so the current tail model does not establish useful control-variate savings.
All 1728 new trajectories finish (1720 LOST, eight WON), using 939,478 new
transitions and 60 fits. V92 above completes paired correction with fixed
replica counts and shared acquisition: final behavior improves against MC/H2,
while terminal-residual variance still does not decrease.

[V90 fixed-cohort paired replay](reports/LEAF_REPLAY_FRAGMENTS_V90_RESULTS.md)
samples 64 fresh SNAKE_4/H2 pairs at every one of seven enabled V89 target
boards and five distinct same-leaf training boards. Target advantage is +40
points (two-SE band [-482, +562]), matched training advantage +65, and their
difference -25; all three remain unresolved. The old -2552-point loss does
not repeat. Life 0's predicted +2351-point advantage also fails to reproduce
on its original training boards (fresh mean -228). These results do not
establish a uniform within-leaf transfer failure or a stable new benefit.
All 1536 trajectories finish (1532 LOST, four WON), using 763,305 new
transitions and zero fits. V91 above implements that shared-continuation
comparison: lower conditional prediction variance does not yield a stable
behavioral improvement, and full-return residual variance increases.

[V89 matched-budget evidence resampling](reports/EVIDENCE_RESAMPLING_FRAGMENTS_V89_RESULTS.md)
starts both allocations from the same original V83 roots and spends exactly
720,000 training transitions each. Balanced/evidence-directed acquisition adds
two/three positive labels; the three unique candidates retain positive means
on fixed independent eight-replica confirmation, but all remain unresolved.
On 672 fresh games, evidence-directed SUPPORTED loses 351 reward points to
balanced allocation; seven newly enabled interventions lose 2552 points each
on average against H2. Both supported risk policies reproduce H2. POINT shows
a mixed risk improvement against balanced allocation while losing reward,
and remains slightly below BASE POINT on risk. New sampling totals 3,047,328
transitions including separate confirmation/evaluation; 18 trees are fitted.
Natural outcomes are 668 LOST and four WON. V90 above completes the proposed
fixed-cohort replay: the old loss does not repeat, but neither target nor matched
training roots establish a stable positive mean. The next method change addresses
long-term consequence estimation.

[V88 paired evidence learning](reports/EVIDENCE_LEARNING_FRAGMENTS_V88_RESULTS.md)
reconstructs individual paired replicas and learns positive, negative and
unresolved candidate labels. Of 608 training candidate labels, 562 (92.4%) are
unresolved; eleven of twelve fitted trees can only return H2 under the frozen
support rule. All 672 fresh games finish LOST. COVERAGE's evidence selector
intervenes in only six reward games and loses 456 points to H2 overall; its
newly enabled intervention loses 4016 points, and three changed candidates lose
2475 points on average against H2. REPEAT and COVERAGE risk exactly reproduce H2.
The matched POINT control has mixed results; evidence selection's risk gains
come entirely from cancelling interventions. New work is 393,318 evaluation
transitions and twelve classification fits, with no repeated training acquisition.
V89 above completes that matched-budget resampling test. Three unique new positive
labels retain positive independent means but remain unresolved; evidence-directed
SUPPORTED decisions lose reward through newly enabled interventions.

[V87 mean-only intervention update](reports/MEAN_UPDATE_FRAGMENTS_V87_RESULTS.md)
reuses both V86 datasets and freezes candidate rankings while learning a new
common R/F/S mean. All 240 fresh games finish LOST. Updating means changes
reward/risk scores by -17/-578 for COVERAGE and -55/+332 for REPEAT relative
to their old models on the same new streams. REPEAT's sole positive aggregate
update comes entirely from cancelling one intervention and returning to H2;
COVERAGE's six newly enabled risk interventions cause its full risk decline.
Lower mean prediction error has not produced better intervention decisions.
New work is 140,482 evaluation transitions and twelve mean-tree fits, with no
repeated acquisition. V88 above completes the proposed evidence-learning test:
most candidate labels remain unresolved, supported interventions do not deliver
new gains, and the risk improvements arise entirely from returning to H2.

[V86 coverage-versus-repeat allocation](reports/BUDGET_ALLOCATION_FRAGMENTS_V86_RESULTS.md)
spends exactly 720,000 new training transitions per allocation. COVERAGE expands
60 training roots to 92; REPEAT raises 33 existing roots from eight to sixteen
paired replicas. On 192 fresh games, scores are 9170/8303 for COVERAGE and
9357/9177 for REPEAT, versus H2's 9538/10438 for reward/risk queries. Both updates
remain below H2. On 24 independent validation roots, strict candidate ordering
is 70/142 for either update versus 71/142 for frozen V85. Independent eight-replica
halves choose the same best option at only 9/24 roots; reward selection benefit
disappears across halves, while risk retains positive selection information.
New work totals 2,559,817 interactions, including separately counted validation
and evaluation. V87 above updates only the frozen mean and separates newly
enabled intervention effects from H2 recovery. It finds no new aggregate
strategy gain from the mean update.

[V85 centered candidate differences](reports/CENTERED_CANDIDATE_FRAGMENTS_V85_RESULTS.md)
keeps each V84 checkpoint's mean R/F/S prediction fixed and separately learns
within-root candidate differences. In 576 new paired games, final CENTERED
scores are 8711/9740 for reward/risk, versus this run's JOINT 7897/9177 and
H2 8435/8627. Reward improves over JOINT in all three lifecycles; risk is mixed.
CENTERED still trails its one-step restriction and first frozen snapshot.
Heldout candidate ordering improves from 16/34 to 20/34 for reward but falls
from 22/34 to 19/34 for risk. New work is 330,971 evaluation transitions and
12 residual fits; acquisition and original anchor fitting are reused.
V86 above executes that matched-budget comparison: repeated estimates lower
prediction error more, but neither allocation improves independent-root ranking
or beats H2. Multi-step and continued-learning benefits remain unestablished.

[V84 joint candidate outputs](reports/JOINT_CANDIDATE_FRAGMENTS_V84_RESULTS.md)
reuses all V83 labels and predicts four separate R/F/S vectors from each state.
The final joint policy executes 16 four-step fragments in 48 games, resolving
the previous forced duration ties. Scores are 8172/9708 for reward/risk queries,
versus H2's 9487/9337, and both fall relative to the first joint snapshot.
All 576 new evaluations fail. Retained heldout candidate ordering matches
38/68 strict pairs; one-versus-four-step ordering matches only 10/24 pairs.
New interactions are 339,165 evaluation steps, with no repeated acquisition.
V85 above holds this mean fixed and fits within-root candidate differences.
It finds a reward improvement over JOINT on new paired games, while reliable
risk ordering, multi-step advantage and continued learning remain unresolved.

[V83 terminating policy fragments](reports/TERMINATING_FRAGMENTS_V83_RESULTS.md)
implements one observable initiation, a committed one/four-step SPACE or SNAKE
fragment, and a permanent return to H2. Final reward/risk scores are 6909/8954,
versus H2's 7552/8366; both checkpoints, ONE_STEP and FROZEN_6 give the same
scores. All 120 evaluation games fail. No four-step option is selected: none
of the 12 trees uses duration, and 11 ignore primitive identity too. Identical
one/four-step predictions let the fixed tie order always prefer one step.
Nine of 12 final FRAGMENT games exactly match H2 histories. The run spends
1,581,774 new transitions. V84 above reuses these samples to fit candidate-specific
joint outputs and test new paired games. Duration ties are resolved, but reliable
ranking and strategic improvement remain unresolved.

[V82 fixed-policy causal continuations](reports/PAIRED_POLICY_EFFECTS_V82_RESULTS.md)
repeats all 24 V81 heldout roots with 16 fresh paired streams and three fixed
interventions. Changing only the first action changes reward/risk scores by
-580/+158; continuing with P1 adds -4538/-4793. This continuation effect is
negative at all 24 roots, including all eight with an unchanged first action.
All 1152 continuations finish, using 268,868 new transitions. First-action
estimates remain unstable: nine of 16 overridden roots have a negative fresh
mean. V83 above implements executable policy fragments with explicit termination
and matching continuation outcomes; candidate and duration discrimination remains
a learning bottleneck. Neither experiment establishes a strategic improvement.

[V81 on-policy action advantages](reports/ON_POLICY_ACTION_ADVANTAGES_V81_RESULTS.md)
implements two rounds of paired terminal action differences and policy-driven
recollection. Final scores are 1453/2073 for reward/risk queries versus
10453/12617 for H2; all three lifecycles remain worse on both queries.
The first update scores only 735/2781. Its repeated action advantages reverse
reward sign in 46.6% of cases, while it overrides 70.7%/48.1% of H2 decisions.
Three successful branches occur under the initial H2 policy; none occur under
P1 in round two. All 120 evaluation games fail. The run uses 539,671 new
transitions and does not establish a strategic-learning improvement. V82 above
executes the fixed-root parent, first-action-only and fully revised continuation
comparison, locating the larger loss in subsequent policy replacements.

[V80 matched target-horizon learning](reports/TARGET_HORIZON_LEARNING_V80_RESULTS.md)
trains short-window and terminal consequence models on the same 15,920 rows,
with identical features, fitting recipe and depth-two planning. In 180 fresh
natural-game evaluations, final reward scores are 4081 for SHORT and 3786 for
TERMINAL, versus 9639 for H2. TERMINAL falls from its own frozen score of 6295
in all three lifecycles. Every training continuation and evaluation game fails;
terminal F=1/S=0 and both queries yield identical terminal-model trajectories.
Longer labels alone do not solve learning deterioration. V81 above executes
paired action-advantage learning under H2 followed by its learned successor.
V80 is not adopted as a continual-learning improvement.

[V79 paired terminal continuations](reports/PAIRED_TERMINAL_CONTINUATIONS_V79_RESULTS.md)
extends all 712 V78 acceptance trajectories with fixed models, roots and random
prefixes. All reach LOST; 132,332 new transitions extend 22,533 inherited ones.
At the final checkpoint, new-root reward deltas change from -11/-30/-19.75 at
32 steps to +425/-970/+793.75 at termination. Two of three reverse, establishing
horizon sensitivity within the same cohort. The unchanged acceptance rule
would accept 3/6 candidates on terminal outcomes, but V78 remains unmodified.
The second lifecycle still disagrees with natural games, leaving root/sample
distribution effects unresolved. V80 above tests terminal policy consequences
against matched 30-step targets on new natural-game seeds.

[V78 decision-driven knowledge acceptance](reports/DECISION_DRIVEN_KNOWLEDGE_V78_RESULTS.md)
adds paired action branches at training disagreements and compares whole-model
acceptance by prediction loss versus observed 32-step deployment utility.
The common candidate is accepted in 4/6 MSE updates and 0/6 decision updates.
Across 120 fresh full games, every outcome is LOST. Final reward-query scores
are 4078 for MSE, 2566 for decision/frozen, 7819 for statistics-only, and 8593
for H2. All three final candidates slightly hurt local 32-step reward but improve
full-game reward over frozen knowledge. Local acceptance therefore misses
longer-game gains on this cohort. V79 above tests paired terminal continuations
from the same retained prefixes. No V78 promotion.

[V77 persistent consequence learning](reports/MULTI_EPISODE_LEARNING_V77_RESULTS.md)
starts the new main research direction: one learner accumulates natural-game
experience, updates policy-conditioned reward/failure/success knowledge, and
uses it for query-conditioned planning. Three lifecycles complete 225 training
and 180 evaluation games; six of 18 proposed partition revisions are accepted.
At 75 training episodes, statistics-only learning scores 7443 on reward queries,
versus 3139 with partition revision and 7861 for short H2 planning. On risk/goal
queries, revision scores 4835 versus statistics-only's 2634, but H2 scores 7951.
Every game ends LOST, and the training stream contains no success labels.
The learning lifecycle is implemented; stable strategic improvement remains
unresolved. V78 above tests decision-driven experience acquisition and knowledge
acceptance. V74 SHARED remains the verified construction baseline.

The [V76 progress snapshot](reports/PROJECT_PROGRESS_2026_09_13.md)
records the preceding route and its published evidence scope.

[V76 query-conditioned decision learning](reports/CORE_DECISION_LEARNING_V76_RESULTS.md)
trains once on 1,500 old H2 observations and tests 48 fresh boards with six seen
and eight unseen queries. Direct rules attain only 337/672 optimal decisions,
versus 362 for one-step greedy and 672 for exact H2. Confidence fallback reaches
644/672, but all 28 remaining errors have confidence 1.0. Including source cost,
RULE/SELECTIVE cost 1.981/2.540 seconds versus EXACT's 0.860. Ground contracts,
all 728 H1 encodings and every matched H1 execution pass. Keep V74 SHARED;
query-dependent strategic learning remains open. Next preserve composable
continuation reward and terminal-risk information and verify action ordering.

[V75 guarded parametric H2 generation](reports/CORE_PARAMETRIC_H2_V75_RESULTS.md)
generates exact new numeric contracts: all 48 new H2 observations match ground,
and all 32 shifted bindings reuse a seed template. However, the frozen main
cohort reuses only 104/1,500 H2 inputs and complete cost increases 76.7%
(5.953 versus 3.368 seconds); even the binding probe remains 7.1% slower than
V74 after seed costs. Keep V74 SHARED as the current mainline and retain V75
as an experimental generator. Exact deployment packages and plans are preserved.
A separate retained-data diagnosis finds 144 within-task selected-action
patterns across 1,500 H2 observations, but many same-pattern states have
different values. V76 above executes the proposed learned decision-rule test
with separate value/risk validation; it does not establish a usable abstraction.

[V74 early effects and shared successors](reports/CORE_EFFECT_SHARING_V74_RESULTS.md)
preserves exact kernels, plans and all three complete 15,209-observation audits.
Risk predicates fall 77.2%, but early predicate sharing alone costs 1.2% more
than V73. Reusing identical action-afterstate successors additionally cuts
candidate scans 29.7%; combined complete cost is 3.400 versus 3.599 seconds
for V72 (5.5% lower). Prefer SHARED for this exploratory cohort. Expanded
observation geometries remain 1,660, and the new afterstate caches are counted
separately. A retained-data diagnosis finds only 8% possible exact H2 state
compression; the tested inactive-rank relation merges none. V75 above tests
the proposed numeric-parameter transition structures. General strategic
learning remains open.

[V73 grouped H2 contracts](reports/CORE_GROUPED_H2_V73_RESULTS.md)
preserves every retained model and plan; both procedural encoders pass all
15,209 observations, and both methods match 16 fresh H2 ground contracts.
Grouping reduces full probability-contract creation by 88.0% and costs 7.5%
less than the same H2 engine without grouping. Against V72, however, total
cost falls only 3.0% and only 14/32 roots improve. Predicate work and the
1,660 distinct higher geometries remain unchanged. V73 was retained as a
verified candidate with V72 still preferred at that stage; V74 above executes
the proposed earlier effect sharing and repeated-successor comparison.

[V72 local H1 contracts](reports/CORE_LOCAL_CONTRACT_V72_RESULTS.md)
enters H1 contracts from single-cell spawn descriptors and routes H1
observations procedurally, without an H1 board graph or member table.
All retained models, plans and 15,209 observation mappings remain exact;
32 fresh H1 boards also match the true action kernels. Concrete construction
falls from 15,209 to 1,660 states, line rewrites from 243,344 to 45,073,
and complete package size by 46.1%. With 87 matched execution observations,
method cost falls 12.3% (4.170 to 3.656 seconds). Adopt COMPOSED_LOCAL.
Boundary candidates are still enumerated; V73 above tests later grouping and
H2 direct construction without resolving that bottleneck. General strategic
learning remains open.

[V71 symbolic terminal successors](reports/CORE_SYMBOLIC_SUCCESSORS_V71_RESULTS.md)
reduces concrete generation from 131,923 to 15,209 states and from 226,074 to
23,103 successor boards. All four factorial arms preserve exact models,
active mappings and plans. Adopt symbolic COMPOSED construction with V70's
map: complete frozen-rule method cost falls from 9.039 to 3.865 seconds
(57.2%); against FULL with the same symbolic mechanism it saves 31.1%.
V71 leaves nonterminal enumeration unchanged; V72 above subsequently removes
the H1 concrete graph through direct local contracts.

[V70 direct observation encoding](reports/CORE_OBSERVATION_COMPILATION_V70_RESULTS.md)
eliminates future reconstruction on the covered model. All 15,209 active
observations, 60 retained routes and complete V69 kernels and plans are
preserved. Adopt the COMPOSED map: frozen-rule construction, export and cold
use cost falls from 11.136 to 9.368 seconds (15.9%), including result writing.
The decision DAG is 2.8% slower and 11.5% larger than that simple map.
V71 above subsequently reduces terminal generation; finite routing is
resolved, while general strategic learning remains open.

[V69 compositional dynamics](reports/CORE_COMPOSITIONAL_DYNAMICS_V69_RESULTS.md)
identifies executable source rules and generates correct new H3/H4 contracts.
All 32 targets, 448 root queries, 1,227 strict query switches and portable
models pass. Active planning states fall from 15,209 to 3,907; higher-layer
merges occur only at H2. Concrete generation remains unchanged. Source,
construction and 14-query cost falls 19.0%, but adding the same 60 observation
routings raises cost 53.5%. V70 above removes that cost within the covered
support. V69 remains the correct compositional reference; synthesis of
general observation predicates and reduced concrete generation remains open.

[V68 source-only strategic learning](reports/CORE_STRATEGIC_LEARNING_V68_RESULTS.md)
is complete: 48 source roots train a direct neural encoder and frozen multistep
kernel, followed by 24 new target roots with no target transition filling.
Seven tests and both portable models pass. The quotient reduces source states
from 6,183 to 1,271, but exact transfer fails on all 24 targets; only 28/336
root queries, from two layouts, attain the full-state optimum. Source semantic
coverage is 82.10% at H1, 0.72% at H2 and zero at H3. This fixed-class candidate
is closed. Its proposed variable-based relational dynamics are implemented
and tested in V69 above. Summary updated 2026-09-13.

[V67 strategic action contracts](reports/CORE_STRATEGIC_ABSTRACTION_V67_RESULTS.md)
return the mainline to executable state abstraction in standard 2048. Across
all 16 retained roots and 14 queries, active states fall from 1,194 to 498,
planning action rows by 60.0%, model bytes by 63.8%, and construction/use cost
by 18.0% against the same analytic-kernel baseline. Six new tests pass; full
independent policy audits preserve optimal values and all 139 strict query
switches. All 16 portable models recover their encoding indexes and replan
without importing the ground environment. A reward-only abstraction fails on
12 roots. V66's preceding rank anonymization gives no state compression and
is retained as a negative result. Higher-layer contracts and independent new
tasks are the next mainline work; query-cache optimization is suspended.

[V65 new-graph execution](reports/LMTA_PROBABILITY_EXECUTION_V65_RESULTS.md)
completes all 4,096 paired trajectories on 64 fresh sparse graphs without
limits. Eight tests and independent checks of 1,467 distinct queries and
12,288 decisions pass; Q values, actions and returns are exactly preserved.
Including preparation, execution, cleanup and trajectory serialization,
REUSE/BASELINE cost is 0.9008, with all 64 graphs faster and both execution
orders favorable. Mean return is 8.72119 for both; sampling and search work
are unchanged. Main and analysis commands total 25.83 seconds. This remains
an AIM engineering result. Its proposed query-cache experiment is suspended;
current work prioritizes strategic abstraction in standard 2048.

[V64 probability reuse](reports/LMTA_PROBABILITY_REUSE_V64_RESULTS.md)
preserves all 12,288 retained queries exactly; 13 tests and independent
accounting checks pass. Six paired rounds complete 1,536 blocks without drift
or limits. Two-day planning-plus-cleanup time has a median candidate/baseline
ratio of 0.9128, or 0.9299 including preparation and comparison overhead.
One-day gains are small and reverse in one round. Main and analysis cost
356.75 seconds, with no new environment samples. Its new-graph execution
confirmation is complete in V65, with preserved trajectories and lower
inclusive block cost.

[V63 sparse-graph coverage](reports/LMTA_GRAPH_COVERAGE_V63_RESULTS.md)
completes all 4,096 trajectories on 64 fresh 15-node sparse graphs without
resource limits. Nine tests and independent checks of 2,836 distinct queries
and 12,288 decisions pass. Two-day control gains 0.57373 mean reward, with a
graph-level 95% interval [0.39385, 0.75361]; the four-comparison reference interval
is also positive. Its action-value work is 27.50 times one-day work. Main and
independent analysis take 17.41 seconds. The within-call probability reuse
comparison is complete in V64, preserving retained outputs and search scope
with a modest two-day timing benefit.

[V62 new-graph trajectory scale trial](reports/LMTA_TRAJECTORY_SCALE_V62_RESULTS.md)
executes all 128 blocks on 64 new 13/15-node graphs: 125 complete and three
reach the cumulative action-value budget. Thirteen tests pass; 12,227 distinct
queries and all 49,027 decisions pass independent checks. Only the 13-node
sparse panel has a positive graph-level simultaneous interval. The 15-node
dense panel remains incomplete; sparse uncertainty is dominated by graph
variation. Main and analysis take 397.52 seconds. Its 64-graph sparse follow-up
is complete in V63, preserving the total trajectory budget under a fixed
whole-run computation cap; the three V62 limited blocks remain unchanged.

[V61 trajectory calibration](reports/LMTA_TRAJECTORY_V61_RESULTS.md)
completes 16,384 trajectories on 64 retained graphs without resource limits.
Twelve tests pass; all 49,152 decisions and transitions agree with independent
replay, and all 12 simultaneous intervals contain their exact expectations.
Sparse-panel gains are detected; both dense-panel difference intervals include
zero. Main execution takes 84.75 seconds, including 79.34 seconds of two-day
planning. An analysis zero-counter repair and both analysis attempts are charged;
main trajectories ran once. The fixed 13/15-node scale trial ran in V62 with
unchanged policies and trajectory budgets; three blocks reached budget limits.

[V60 changed-policy evaluation](reports/LMTA_CHANGED_POLICY_V60_RESULTS.md)
completes the single outstanding one-day policy on graph 580109: 1,043 states,
10 tests and independent checks pass. Its expected reward falls by 0.0001664;
16 new states replace 16 old states. Reusing the remaining certificates completes
all four panels under the analytic implementation. Run and analysis total
0.326 seconds. Paired trajectory calibration against retained exact values is
complete in V61, with propagation and planning costs recorded.

[V59 analytic short-window replay](reports/LMTA_ANALYTIC_SHORT_V59_RESULTS.md)
completes 128 cases and 188,499 states, with 16 tests and independent checks
passing. All Q values agree within tolerance; two-day policies are preserved
on all 64 graphs. One one-day nonroot action changes on graph 580109 after a
4.44e-16 Q gap becomes a computed tie, so that policy value cannot be reused.
Expected two-day outcome enumeration falls to 0.544–6.84% of the old work.
Run and analysis total 69.63 seconds. The changed one-day policy is now fully
evaluated in V60; V59's failed overall action-preservation result remains intact.

[V58 analytic full-lookahead scale validation](reports/LMTA_ANALYTIC_SCALE_V58_RESULTS.md)
completes 192 cases on 64 fresh nine/eleven-node graphs, with 13 tests and
independent checks of 274,253 states passing; no resource limit is reached.
Two-day control improves over one-day control on 51 graphs, ties on 12 and
degrades on one. At eleven dense nodes, full lookahead adds only 0.00402 mean
reward beyond two days; its expected action-value work grows 6.42-fold from
nine dense nodes. Run and analysis total 196.72 seconds. Its analytic short-window
comparison is complete in V59: all two-day policies and 63 one-day policies are
preserved, with the remaining one-day policy freshly evaluated in V60.

[V57 paired timing](reports/LMTA_PAIRED_TIMING_V57_RESULTS.md) completes six
interleaved rounds on 64 retained graphs, with 21 tests and independent timing
checks passing. Including warmup, all 778 blocks and 241,354 planning calls
complete without output drift or resource limits. Median planning-plus-cleanup
ratios are 0.988/0.837/0.930/0.525 for seven-node sparse/dense and nine-node
sparse/dense panels. Dense-panel savings persist in both execution orders;
seven-node sparse savings are unstable. Run and analysis total 126.52 seconds.
Its fixed new-graph and modest size validation is complete in V58, with fresh
policy certificates and all costs recorded.

[V56 analytic terminal expectation](reports/LMTA_ANALYTIC_TERMINAL_V56_RESULTS.md)
completes replay of 20,112 full-policy states on 64 retained graphs, with 15
targeted tests and independent checks passing. Every action is preserved;
maximum Q difference is 4.44e-16, allowing reuse of the original policy values.
Expected outcome enumeration falls to 32.7–51.2% of the original work, while
action-value and target-probability counts remain unchanged. The run and checks
cost 14.45 seconds in total. Its proposed fixed, interleaved timing comparison
is complete in V57, retaining the original actions and all timing costs.

[V55 exact-tie refinement](reports/LMTA_TIE_REFINEMENT_V55_RESULTS.md) completes
257 cases, 18 targeted tests and independent checks of 83,520 states, without
resource limits. It repairs the known V54 regression, but adds no value on 64
fresh graphs: two refinements trigger and neither changes the action. Two fresh
graphs still trail one-day control despite unique two-day best actions. This
trigger candidate is closed. Its proposed analytic final-day expectation
comparison is complete in V56, preserving all retained full-policy actions and
values while recording total costs. New environment samples are zero.

[V54 new-graph and size validation](reports/LMTA_SCALE_V54_RESULTS.md) completes
192 cases on 64 new seven/nine-node graphs, with 16 targeted tests and independent
checks of 62,519 states passing; no resource limit is reached. Two-day lookahead
improves on one-day control on 47 graphs, ties on 16 and degrades on one.
The negative case exposes an exact two-day tie hiding unequal later returns.
Expected action-value work is 13.7–40.1% of full lookahead, but 9.72–114.67 times
one-day work. Its proposed third-day refinement among exactly tied two-day
best actions is complete in V55, with both stages charged and a fresh panel.
No environment samples or updates were added.

[V53 two-day lookahead](reports/LMTA_LOOKAHEAD_V53_RESULTS.md) completes 192 cases,
20 targeted tests and independent checks of all 12,059 policy states. At three
days it improves on one-day greedy control on 24/32 graphs, with eight ties.
It retains 61.0%/82.9% of the sparse/dense panels' additional full-lookahead gain,
using 38.6%/35.0% of full-lookahead expected action-value evaluations. Its mean
absolute gains are 0.1496/0.0169 nodes, at 9.61/65.15 times greedy evaluation work.
Its new-graph and modest size validation with fixed resource limits is complete
in V54. No environment samples or learning updates were added.

[V52 exact small-graph policy headroom](reports/LMTA_EXACT_V52_RESULTS.md) completes
320 cold-cache policy solves on 32 seven-node graphs, with 15 targeted tests
and independent Bellman checks of all 116,442 retained states passing.
At three days, joint optimal control beats the original heuristic on 30/32
graphs. Under the same uniform allocation, long-term node choices beat exact
one-day greedy control on 25/32 graphs. Within the sparse panel, the node-choice
contrast exceeds the allocation contrast; their order reverses within the dense panel.
Its two-day lookahead comparison is complete in V53, separating decision
computation from full-policy evaluation.
The main panel adds no environment samples or learning updates; small-graph
headroom does not establish learnability or gains on the 500-node task.

[V51 best-action-set objective](reports/LMTA_BEST_ACTION_V51_RESULTS.md) completes
13 targeted tests and 6,000 updates with the original NodeQ, exact V49 initial
anchors and recorded batches. Training/external-graph optimal-node hit rates rise
to 68.75%/66.90%; both paired run-level intervals versus V49 are positive.
Relative score regret is 0.59%/1.01%, while pairwise ordering declines.
The frozen 95% hit requirement remains unmet: FIT_NOT_ESTABLISHED.
This objective candidate is closed and the V49–V51 supervised evidence is
consolidated. Its proposed small finite-horizon headroom probe is complete in
V52, with exact-solution and independent verification costs recorded.
V51 adds no environment sampling, RL updates or MCTS; all supervised costs remain.

[V50 learned first-message readout](reports/LMTA_READOUT_V50_RESULTS.md) completes
12 new tests, 5,040 exact initial anchors and 6,000 updates with the exact V49
batches. Six additional zero-initialized parameters reduce training/external-graph
relative score regret to 1.06%/0.88%, but optimal-node hit rates remain
55.68%/57.44%; the frozen fit requirement is unmet. The structural candidate
is closed. Its proposed best-action supervision comparison is complete in V51,
holding the original V49 NodeQ and budget fixed.
New environment sampling is zero; the supervised work and all old fees remain.

[V49 fixed supervised node-ranking probe](reports/LMTA_SUPERVISED_V49_RESULTS.md)
completes 24 teacher episodes and three fits of 2,000 updates, with 19 targeted
tests passing. Mean relative score regret drops to 1.51% on training states and
1.19% on held-out graphs; pairwise ordering reaches about 98%. Optimal-node hit
rates remain 48.33% and 51.90%, below the frozen 95% requirement, so the outcome
is FIT_NOT_ESTABLISHED. This shows substantial learning with insufficient
top-choice precision under the fixed budget. Its proposed first-message readout
comparison is complete in V50, reusing the retained data and original control.
New physical costs are 1,680 selections, 240 daily transitions and 30,348 draws;
6,000 supervised updates reuse the data. No new RL or MCTS is performed.

[V48 frozen endpoint component comparison](reports/LMTA_COMPONENTS_V48_RESULTS.md)
completes 240 hybrid episodes and six exact restoration anchors, with 17 targeted
tests passing. Replacing learned node selection with the score heuristic improves
Budget-HRL by 78.05 and LMTA by 59.78; both run-level intervals are positive.
Replacing budgets alone has no stable benefit. With score nodes, LMTA's learned
budget still trails uniform allocation by 17.60. Its proposed fixed supervised
score-ranking probe is complete in V49. New costs are 17,220 selections, 2,460 daily
transitions and 184,500 latent simulations; training remains closed.

[V47 reward-boundary and behaviour review](reports/LMTA_MECHANISM_V47_RESULTS.md)
finds correct reward accounting and terminal handling in seven scripted small-graph
episodes. All 720 retained evaluations are analyzed. Budget-HRL run 2 loses 73.05
despite identical daily seed counts in all 20 paired episodes; one LMTA
run seeds earlier yet also declines. Later allocation alone cannot explain the
observed degradation. Its proposed crossing of learned/uniform budgets with
learned/score-based node selection is complete in V48, using retained endpoint weights.
Six synthetic tests pass; the probes add 11 selections and 17 daily transitions.

[V46 paired weighted-aggregation training](reports/LMTA_WEIGHTED_V46_RESULTS.md)
completes 1,872 new episodes and 22 targeted tests, reusing retained V44 controls.
LMTA-RI reaches 243.22, exceeding the mean-aggregation endpoint by 29.03
(95% run-level interval [3.80, 54.27]), but its own-initial gain is unstable
and it remains below the score heuristic's 320.60. Only one of three continuation
conditions passes. All nine method/run curves decline from checkpoint 32 to 128;
the reward-boundary review is complete in V47 and leads to a component comparison.
The candidate training budget is closed, and intermediate policies are not adopted.

[V45 initial-structure comparison](reports/LMTA_STRUCTURE_V45_RESULTS.md)
completes all 58 graphs and nine retained policies with zero environment calls.
An unnormalized sum using the environment's inverse-indegree edge weights
recovers the exact initial single-seed one-step score within 1.33e-15.
All 5,916 conditional seed-Q vectors show node variation, versus none with
mean aggregation. Its proposed paired learning trial is complete in V46;
stable learning and sample-efficiency benefits remain unestablished.
The comparison takes 25.27 CPU wall seconds, with seven tests passing.

[V44 cross-graph learnability trial](reports/LMTA_LEARNABILITY_V44_RESULTS.md)
completes 1,912 episodes with valid accounting, but fails both prespecified
continuation conditions. LMTA-RI's mean held-out return falls from 227.80 to
214.18 across three training runs; the nonlearning score heuristic yields 320.60.
A zero-sample diagnostic establishes an initial-state blind spot: row-normalized
mean aggregation preserves identical node features and cannot distinguish their
topology. Its proposed structural-identifiability comparison is complete in V45;
the V44 training budget remains closed. Nine final inference policies and
the run sources are retained.

[V43 independent LMTA engineering probe](reports/LMTA_INDEPENDENT_V43_RESULTS.md)
implements a shared AIM environment, LMTA-RI, Flat DQN and Budget-HRL, completing
eight training and two held-out evaluation episodes per arm. Actual selections,
daily propagation, replay updates and latent search are counted separately.
This was an engineering result with only one LMTA high-level update, leading
to the completed V44 comparison with graph-aware replay and nonlearning
heuristics. The user's choice of independent implementation and
all unresolved paper details are recorded in the V43 specification.
[V42 original WS-option accounting](reports/LMTA_SAMPLE_ACCOUNTING_V42_RESULTS.md)
also retains its 1,600 additional reward-simulation calls and a reproduced
internal-state filtering problem. The released WS code and Budget-HRL are
distinct references.

[V41 layered comparison and branch closure](reports/LAYERED_ABSTRACTION_V41_RESULTS.md)
eliminates false terminal continuation and has no compiled action disagreements
across 625 snapshots. Policy quality remains optimal in only five of six
conditions; all six complete numeric models exceed ground P/r storage and
require more one-query preparation time. The prespecified continuation rule
fails, closing the current flat/layered BA efficiency-candidate branch. Further
project research requires a new task with actual reuse opportunities.

[V40 systemic diagnosis and future route](reports/SYSTEMIC_DIAGNOSIS_AND_ROUTE_V40.md)
identifies nonzero terminal continuation introduced by soft grounding, with
value bias persisting after convergence. Terminal clamping improves three of
six conditions and worsens three. Array-only backups remove the original-P
runtime dependency, but 20 near-tie action disagreements prevent a behaviorally
identical replacement; five of six operator-plus-readout arrays exceed ground
model storage. Its proposed bounded horizon-layered experiment is now complete
in V41, with the stopping condition applied.

[V39 author-code replication and exact-model transfer](reports/RATE_DISTORTION_V39_RESULTS.md)
reproduces DoorKey's optimal return and 0.133 joint information fraction through
the author's README entrypoint. The default warm-start entrypoint differs and
is retained. In three exact H2 2048 cases, the prespecified reward-unit
normalization recovers all optimal policies; raw units fail one case. This is
a new soft-abstraction baseline, with no demonstrated total-cost advantage or
general model guarantee. The original author planner accesses the full ground model.
The [current next step](specs/CONTROLLED_PREDICTIVE_QUOTIENT_NEXT_STEP.md)
records the completed V47 review and the proposed component comparison.

The U005 learned resource-forecast pilot completed successfully as an execution
and failed its scientific Gate (2/6; aligned AUROC 0.575822). The failed result
closes this representation's rescue path and leaves U006 assurance ineligible.
This independent exploratory worktree starts from its clean source `8dcd411b`.

The new development slice learns action-conditioned finite predictive cells
and compares repeated planning in their compiled model against a full-state
model using the same transition samples. See the
[diagnosis review](specs/GPT6_DIAGNOSIS_REVIEW_20260908.md) and
[development specification](specs/CONTROLLED_PREDICTIVE_QUOTIENT_DEVELOPMENT_V1.md).
The [first development result](reports/CONTROLLED_PREDICTIVE_DEVELOPMENT_V1_RESULTS.md)
records the finite compression, policy quality, prediction errors and construction costs.
The [next development step](specs/CONTROLLED_PREDICTIVE_QUOTIENT_NEXT_STEP.md)
targets an executable encoder for unseen development boards and query-dependent strategy changes.
The [V2 query-conflict diagnosis](reports/QUERY_CONFLICT_DEVELOPMENT_V2_RESULTS.md)
found a reached decision point where the same-data full-state model preserves the
optimal risk tradeoff and the approximate quotient does not. This motivated
query-guided local partition refinement before encoder migration.
The [V3 refinement result](reports/QUERY_REFINEMENT_DEVELOPMENT_V3_RESULTS.md)
repairs that regression and completes 12 new development cases: mean active cells
fall from 207.92 to 64 with no additional objective loss against the same-sample
full-state model on the audited queries. Sampling-induced risk errors remain,
and refinement construction prevents a total-cost win over ten queries.
A saved dynamics model also successfully replans a probe query in a new process.
The [V4 cost and sampling result](reports/COST_AND_SAMPLING_DEVELOPMENT_V4_RESULTS.md)
now makes the zero-tolerance empirical quotient (`build_quotient(empirical)`)
the default finite-model development baseline. It retains matched policy quality
at lower measured cost than either refinement builder. V4 reduces redundant
processing while preserving V3's partition and behavior, but its extra compression
does not justify construction cost in this workload. The 25 declared cases contain
23 distinct root boards; two newly seeded cases reuse exposed roots.
A nested 64/256/1024-sample curve improves most exposed decision errors but leaves
two wrong query outcomes at its largest budget.
The [V5 directed-sampling result](reports/DIRECTED_SAMPLING_DEVELOPMENT_V5_RESULTS.md)
completes a fixed-pilot, equal-budget comparison on 14 distinct roots and three
sampling seeds. Directed allocation improves eight and worsens two root-query
outcomes at budget 256, and improves one at 1024; all changes concern one exposed
root. The 11 new roots have no required query switches anywhere in their covered
closures, and both final-budget methods already solve them. Allocation adds about
40.5 ms per run and does not uniformly improve risk prediction. Uniform sampling
with the exact empirical quotient remains the default development baseline; V5
is retained as a candidate.
The [V6 mechanism characterization](reports/MECHANISM_CHARACTERIZATION_DEVELOPMENT_V6_RESULTS.md)
now retains 12 fixed structural challenges and three exposed controls. Two new
roots in one spawn-rescue family exhibit a reversal between one-step and H3
failure ranking: reward-only planning chooses LEFT, while the nine positive-risk
queries choose RIGHT. Two other cases have strict conflicts only on paths avoided
by the canonical optimal root policies; eleven have none. The exact quotient
preserves all 11,810 state-query policies while reducing 1,181 active states to
481 cells. These are privileged finite-model references.
The [V7 executable encoder result](reports/EXECUTABLE_ENCODER_DEVELOPMENT_V7_RESULTS.md)
now completes direct board encoding, a fixed same-sample comparison, and portable
model reload. Across 16 cases and three seeds, the learned rule achieves 360/480
optimal root policies versus 453/480 for both full-state and exact empirical
quotient baselines. It preserves both V6 risk-reversal roots, but already merges
training states requiring opposite actions and adds downstream failure risk.
Its mean construction plus ten queries costs 45.13 ms versus 2.06 ms for the
exact empirical quotient, despite smaller models. The 6,195-byte saved example
executes a new numeric query consistently after reload. V7 is retained as a negative development comparison.
The [V8 constraint and family-holdout result](reports/CONSTRAINT_ENCODER_DEVELOPMENT_V8_RESULTS.md)
now satisfies every source empirical-signature constraint in all twelve fits.
Uncapped SSE also satisfies them. Both recover all source policies, but V8 lowers
fit-held-out root-policy optimality from V7's 120/180 to 90/180; its overall
390/480 reflects source and exposed-regression gains. Complete family holdouts
remain at 193/360 for all three encoders versus 333/360 for the empirical
baselines. The terminal optimization preserves V7 results while reducing actual
feature work; V8 construction plus ten queries still costs 14.98 ms versus
2.12 ms for the exact empirical quotient.
The [V9 target-adaptation result](reports/TARGET_ADAPTATION_DEVELOPMENT_V9_RESULTS.md)
now restores the same-sample baselines' full-policy outcomes: 453/480 optimal
root policies in the primary scenario and 333/360 in family-holdout targets.
Direct target fitting achieves the same results. Source initialization halves
primary split-candidate work, but sampling, construction, ten queries and
amortized source fitting cost 47.39 ms versus 43.19 ms for direct target rules
and 19.28 ms for the exact empirical quotient. Identical-feature empirical
conflicts remain in one case; this is policy recovery on the declared queries,
not universal empirical equivalence. The 9,351-byte adapted example reloads
consistently.
The [V10 demand-driven feature result](reports/LAZY_FEATURES_DEVELOPMENT_V10_RESULTS.md)
preserves all 204 paired V9/V10 rule, model and planning comparisons exactly,
but costs more than concurrent V9. Primary adapted feature computations fall
40.57%, while construction plus ten queries rises from 21.07 to 24.61 ms;
family-holdout targets rise from 24.28 to 30.32 ms. Repeated boards account for
only 2–3% of profile calls, and actual swipe work falls by about 2%.
V10 remains a negative implementation comparison.
The [V11 feature-block result](reports/BLOCK_FEATURES_DEVELOPMENT_V11_RESULTS.md)
also preserves all 204 paired semantics checks. It removes terminal feature
contexts and batches mixed-group vectors, but average construction still costs
more than concurrent V9: 2.08%/12.65% for primary scratch/adapted builds and
6.52%/20.11% for family-holdout targets. Actual swipe, signature-validation and
pooling work remain unchanged. Use V9 direct target fitting for current
executable-rule construction and retain uniform sampling plus the exact empirical
quotient as the finite-planning baseline. Further feature-dispatch optimization
is paused.
The [V12 partial-observation result](reports/PARTIAL_OBSERVATION_DEVELOPMENT_V12_RESULTS.md)
completes 102 runs and 1,224 budget checkpoints. At the 128-row cap, query-driven
construction acquires about 77% fewer rows, but costs 168.23/173.47 ms for
primary/family-holdout targets versus the complete empirical quotient's
157.89/152.95 ms. Source-priority totals rise to 213.24/252.19 ms without improving
the complete-root-policy optimum counts. Those counts match the full baseline,
yet 27 root queries in each scope have larger losses; policy preservation is
not established. The next question is execution-time acquisition for unresolved
actions with matched total budgets, alongside separately measured incremental
interval updates. Source priority remains outside the default method. A saved
partial policy executes all ten declared queries consistently in a new process.
The [V13 execution-acquisition result](reports/EXECUTION_ACQUISITION_DEVELOPMENT_V13_RESULTS.md)
completes 48 case/seed runs and 480 query contexts per method. Incremental
updates preserve all 96 paired prefixes and 960 complete execution trees;
128-row-prefix acquisition and computation fall from 239.85 to 82.25 ms.
Execution-time acquisition improves 38 complete-root-policy values and worsens
five versus same-query upfront acquisition, with 435/480 optimal policies
versus 434/480 and the full empirical baseline's 453/480. Its incremental
implementation uses 32.73 expected rows and costs 42.28 ms per standalone query
versus upfront's 38.08 rows and 50.45 ms; ten-query preparation amortization
reduces these costs to 16.68 and 24.85 ms per query. All four acquisition arms
respect the 128-row path cap including initial observations. The five regressions
involve positive goal bonuses on roots whose total tile mass cannot reach 2048
within the horizon. The next isolated comparison will test this reachability
bound while retaining the current budgets and controls. Empirical sampling errors
remain separate. Two recorded-history artifacts replay consistently in fresh
processes; source priority remains paused.
The [V14 mass-bound result](reports/MASS_BOUND_DEVELOPMENT_V14_RESULTS.md)
now completes that isolated comparison. The legacy arm exactly reproduces all
96 V13 prefixes and 960 execution trees. Removing impossible goal bonuses makes
all 60 within-variant goal/no-goal history pairs identical, versus 12 for the
legacy bound. Online full-policy optimality rises from 435/480 to 453/480 with
18 improvements and no regressions; all five prior online-versus-upfront
regressions become optimal. Online mass-bound acquisition uses 30.62 expected
rows and costs 31.13 ms per standalone query versus concurrent legacy's 32.73
rows and 34.36 ms. Eight complete-root values still fall below the full empirical
baseline, with maximum added loss 0.000810547, despite matching its optimum
count. All eight occur in one exposed case and seed: finite samples still
misrank subsequent actions when empirical intervals close. Retain V14 as the
partial-observation candidate; next test uncertainty and repeated sampling of observed actions under
an explicitly matched total sample budget. Three recorded-history artifacts
replay consistently in separate processes. Source priority remains paused.
The [V15 resampling result](reports/RESAMPLING_DEVELOPMENT_V15_RESULTS.md) completes the next comparison.
All three online methods remain optimal on 453/480 full policies. With exactly
matched realized batch counts, directed resampling improves eight and worsens
15 outcomes relative to balanced resampling. Both use 25,167 expected samples
versus V14's 7,838 and cost more. Retain V14 for partial observation; next test
acquisition and stopping based on competing action-value gaps, with scoring
update costs tested separately. The frozen V15 results are not retuned.
The [V16 gap-stopping result](reports/GAP_DEVELOPMENT_V16_RESULTS.md) preserves all
480 full-policy outcomes when stopping is enabled under the same allocation,
reducing expected samples by 13.71% and standalone query cost by 6.00%.
The gap allocation still improves six and worsens 15 outcomes against balanced
resampling and costs more. Retain V14; next combine the stopping condition with
balanced allocation, keeping scoring-update optimization separate. The saving
is in deployment-path expectation; all-history physical sampling did not fall.
The [V17 balanced-stopping result](reports/BALANCED_STOP_DEVELOPMENT_V17_RESULTS.md)
preserves all 480 evaluated full-policy outcomes relative to original balanced
resampling and reduces expected samples by 10.37%. Including gap scoring,
standalone cost rises from 125.83 to 170.39 ms. Retain V14; next optimize repeated
score computation while requiring exact V17 acquisition, stopping and action
history reproduction. All-history physical sampling falls by only 0.84%.
The [V18 scoring-cache result](reports/SCORE_CACHE_DEVELOPMENT_V18_RESULTS.md)
reproduces all 480 original STOP histories exactly, including gap diagnostics.
With cache maintenance and copying charged, standalone cost falls by 31.81%
against original STOP and 15.08% against balanced resampling in the same run.
Use cached scoring for further resampling development while retaining V14 and
the full empirical quotient controls. Next decompose action-ranking errors in
fixed observed snapshots to separate transition estimates from continuation values.
The [V19 snapshot decomposition](reports/DECOMPOSITION_DEVELOPMENT_V19_RESULTS.md)
reconstructs all 24 fixed snapshots and satisfies the error identities. Both
cached regressions flip after a final downstream batch increases failure-risk
underestimation; the current-action transition term is unchanged. Next test
empirical-variance allocation propagated to action differences, keeping V18
stopping, execution and actual sample caps fixed. This diagnostic adds no
independent observations and does not yet establish a policy repair.
The [V20 variance-allocation result](reports/VARIANCE_ALLOCATION_DEVELOPMENT_V20_RESULTS.md)
improves seven and worsens thirteen outcomes against concurrent cached balanced
allocation. Mean samples fall by 0.1225%, while standalone cost rises from 83.78
to 84.10 ms; all methods remain at 453/480 optimal full policies. Retain V14 and
V18 cached balanced allocation. Next isolate local allocation from stopping-time
changes using common observed snapshots and fixed actual batch counts.
The [V21 common-snapshot result](reports/LOCAL_ALLOCATION_DEVELOPMENT_V21_RESULTS.md)
completes all 22 pairs at equal actual batch counts. Variance allocation improves
one and worsens four target actions, with no gap stopping in either arm;
local mean cost rises from 40.662 to 44.715 ms. Fixed-panel outcomes are mixed,
and these local regrets do not measure complete online policies. Next retain
the snapshots, budgets and rules for paired repetitions with new suffix streams.
The [V22 suffix-repetition result](reports/REPETITION_DEVELOPMENT_V22_RESULTS.md)
completes all 64 streams and 1,408 fixed-budget pairs. Variance allocation lowers
the target error-rate point estimate by 7.74 percentage points, but the 95%
stream-level Monte Carlo interval spans -16.48 to +1.00 points; local cost rises
7.67%. It also acquires 805 more first-observation batches. Retain the baselines;
next use the retained endpoints to ablate newly observed rows and assess their
information contribution, with all actual acquisition costs retained.
The [V23 information ablation](reports/PROJECTION_DEVELOPMENT_V23_RESULTS.md)
reproduces V22 exactly and adds no samples. Withholding newly observed rows
increases target error by 10.44 points for CACHED and 19.18 for VARIANCE;
the paired difference changes by 8.74 points (95% stream interval 1.60–15.87).
Next test explicit query-relevant unknown-frontier acquisition before balanced
resampling, keeping the starts, budgets, paired streams and both old controls.
The [V24 frontier trial](reports/FRONTIER_DEVELOPMENT_V24_RESULTS.md)
completes all 64 streams and 1,408 three-arm groups, with exact control replay.
FRONTIER increases target error by 4.05 points versus CACHED (95% stream interval
2.11–5.99) and local cost by 13.22%, despite closing every fixed-panel interval.
Retain the baselines; next inspect signed action-margin A/D errors in the retained
evaluations before selecting another allocation change, with no added sampling.
The [V25 signed-error diagnosis](reports/SIGNED_ERRORS_DEVELOPMENT_V25_RESULTS.md)
reproduces all 4,224 RAW targets with no new samples or oracle calls. Removing
A repairs 47 of the 70 FRONTIER-only errors versus CACHED; removing D repairs
29 but introduces 23 CACHED errors, exposing the role of error cancellation.
Next add the FRONTIER-plus-VARIANCE arm under the same starts, streams and
budgets to test the combination and its interaction, retaining all three controls.
The [V26 factorial result](reports/FACTORIAL_DEVELOPMENT_V26_RESULTS.md)
completes all 5,632 arms and exactly reproduces the three controls. The combined
rule increases target error by 8.66 points versus VARIANCE (95% stream interval
5.57–11.76) and local cost by 10.66%; its interaction is adverse. Retain the
baselines. Next evaluate the retained policies under true transition weights to
separate first-action loss from continuation loss, without further acquisition.
The [V27 frozen-policy result](reports/FROZEN_POLICY_DEVELOPMENT_V27_RESULTS.md)
completes all 5,632 retained policies with no new acquisition. VARIANCE,
FRONTIER and the combination have zero true-reach continuation regret; the
combination still raises total regret versus VARIANCE by 0.00015231 (95%
stream interval 0.00009795–0.00020668). Retire frontier expansion and retain
the baselines. Next compare frozen CACHED/VARIANCE on prospectively selected
new H2 development starts, using policy value and all actual costs.
The [V28 new-start result](reports/NEW_STARTS_DEVELOPMENT_V28_RESULTS.md)
completes 5,120 runs on sixteen prospectively generated H2 boards. Every paired
policy value is equal, with 99.375% optimality for both methods; VARIANCE adds
0.606 ms (1.67%) to independent query cost, including the full shared prefix
and query preparation. Retain the baselines. Next evaluate the retained
prefix-only policies to measure what the additional 32 batches contribute,
without further sampling or replanning.
[V29 prefix-policy evaluation](reports/PREFIX_BASELINE_DEVELOPMENT_V29_RESULTS.md) evaluated all 160 retained
prefix policies once against the existing endpoints. Optimality rose from 75% to
99.375% for both sampling methods: all 40 original error identities were repaired,
while one previously correct identity became wrong in both arms on all 16 streams.
Seven tests and 15 analysis checks passed; V28 quality and costs reproduced exactly.
Retain CACHED. Next, replay all 32 retained histories for the induced error to locate
the first harmful update and separate action-value error components; this diagnostic
has not run. The comparison is conditional on the fixed prefixes.
[V30 retained-history replay](reports/REGRESSION_DEVELOPMENT_V30_RESULTS.md) exactly reproduced all 32 selected
histories and 1,056 boundaries; ten tests and 20 analysis checks passed. Root choice
became wrong after batches 3, 15 and 29, with repairs after 13 and 25. Unequal
underestimation of continuation values drove these changes while root transition
estimates stayed fixed; all 32 acquisitions were first observations. Next, test
ranking the original structural acquisition candidates by their estimated impact
on the competing root-action gap, against CACHED on all 160 starts and 16 streams
at the same 32-batch budget. This candidate has not been frozen or executed.
[V31 gap-frontier comparison](reports/GAP_FRONTIER_DEVELOPMENT_V31_RESULTS.md) completed all 2,560 pairs at
32 batches per arm; 20 tests and 23 analysis checks passed, with exact CACHED
history/state/value reproduction. GAP_FRONTIER repaired the one remaining error
identity on all 16 streams without new errors, raising optimality from 99.375% to
100%. Full attributed query cost increased 1.24% (+0.473 ms; 95% stream interval
[0.179, 0.768] ms). Keep the baseline and frozen candidate for a prospective paired
comparison on new boards with independent prefixes and suffixes. That validation
has not been prepared or run; the present quality gain concerns one known identity.
[V32 new-start validation](reports/TRANSFER_DEVELOPMENT_V32_RESULTS.md) completed 2,560 pairs on 16 new boards
with independent prefixes and suffixes; 11 tests and 24 analysis checks passed.
Both methods attained 100% optimality, while GAP_FRONTIER cost 1.88% more per
attributed independent query (+0.692 ms; 95% stream interval [0.641, 0.744] ms).
Keep CACHED. Next, evaluate the retained policies after 0, 4, 8, 16, 24 and 32
local batches with a common completeness mask and all historical costs retained.
This finite sample-efficiency diagnosis has not run; without an advantage, stop
extending this candidate on the current generator.
The V33 retained-history budget curve completed all 5,120 histories at six
fixed checkpoints (7 tests, 18 analysis checks; full K32 reproduction). GAP_FRONTIER
has lower regret at K=8/24, higher regret at K=4/16, and equal regret at K=32.
This budget-specific signal retains CACHED as the baseline; the next comparison
will measure actual costs at all five positive budgets, preserving both favorable
and unfavorable points. No new samples were acquired, and historical fees remain.
The follow-up protocol and execution are pending; see the [V33 result](reports/BUDGET_CURVE_DEVELOPMENT_V33_RESULTS.md).

The V34 contemporary budget-cost comparison completed all 25,600 runs
(7 tests, 28 analysis checks; exact V33 history, policy and value reproduction).
GAP_FRONTIER at K=24 and CACHED at K=32 both attain zero regret on this retained
cohort, while measured full independent-query cost falls by 14.02% (36.549 to
31.424 ms). GAP_FRONTIER costs 1.46% more at the same K=24; other budgets retain
their quality tradeoffs. CACHED remains the baseline. The next prospective test
will fix GAP_FRONTIER K24, CACHED K24 and CACHED K32 on new boards and independent
prefix/suffix streams. That protocol and execution are pending. All 110,231,552
physically repeated samples were charged; see the [V34 result](reports/BUDGET_COST_DEVELOPMENT_V34_RESULTS.md).

The V35 three-configuration transfer completed all 7,680 runs on a new
16-board cohort with new prefix/suffix streams (9 tests, 21 analysis checks).
GAP24 costs 13.99% less than CACHED32 but repairs 2 cases and introduces 8 new
errors; equal quality did not reproduce. At the same budget it costs 0.98% more
than CACHED24 without a demonstrated quality benefit. CACHED32 remains the
baseline, and GAP24 is no longer being advanced as its replacement. The next
step will diagnose transition versus downstream-value estimation errors using
all retained CACHED24/CACHED32 endpoints; no further samples are planned for that
diagnosis. Its protocol and execution are pending; see the [V35 result](reports/BUDGET_TRANSFER_DEVELOPMENT_V35_RESULTS.md).

The V36 diagnosis covered all 5,120 retained CACHED24/CACHED32 endpoints and
20,480 legal actions (10 tests, 18 analysis checks). Removing downstream-value
error D in an oracle diagnostic repairs all 61/57 root-action errors, including
all 56 shared failures, with no new errors; removing transition error A repairs
only 4/3. Original states, full-policy values, and all V35 quality/cost streams
reproduce exactly. CACHED32 remains the baseline. The next finite diagnosis will
separate incomplete model coverage from estimation error within observed rows;
its protocol and execution are pending. No new samples were acquired; historical
costs remain charged. See the [V36 result](reports/ENDPOINT_ERRORS_DEVELOPMENT_V36_RESULTS.md).

The V37 continuation diagnosis completed all 5,120 endpoints (16 tests,
19 analysis checks). Removing observed-row estimation error E repairs 31/30
root-action errors at 24/32 batches; removing coverage error C repairs 0/8,
with no new errors in either diagnostic. C has the larger signed magnitude in
shared failures, but E removal repairs more rankings. Nonzero paired-regret
intervals include zero. CACHED32 remains the baseline; the next method test
will use disjoint samples to cross-select and evaluate H1 actions while fixing
coverage, allocation rules and the total sample budget. Its protocol and
implementation are pending; this diagnosis does not establish maximization
bias or a new algorithm benefit. See the [V37 result](reports/CONTINUATION_SOURCES_DEVELOPMENT_V37_RESULTS.md).

The V38 crossfit readout completed all 2,560 pairs (12 tests, 18 analysis
checks). Every root action and full-policy value matches CACHED32; all 57 errors
remain. Postprocessing adds 1.3068 ms per endpoint, with a 95% stream interval
of [1.2850, 1.3286] ms. CACHED32 remains the baseline and this crossfit branch
is closed. The next feasibility check will look for distinct observed rows
sharing an identical deterministic afterstate within each retained endpoint,
with immediate rewards kept separate. That check and a shared-statistics
estimator are not yet implemented. See the [V38 result](reports/CROSSFIT_DEVELOPMENT_V38_RESULTS.md).

All cases are exposed development material; independent scientific confirmation
has not been performed.

## Registered finite-objective status (V179)

The repository's finite, coverage-bounded central objective is now complete for
the preregistered symbolic-family scope.  V179 binds producer-free evidence for
an actual full 2048 episode, observation-derived cross-family abstract-model
synthesis, repeated receding multi-step planning in compiled models, strict OOD
no-transfer, matched factor-prior sample-tax reduction, complete typed plan
receipts, and certificate-failure-only local ground recovery.

The final indexed-lazy campaign
`43e174c7ffd17c5a0e18a584dc638ea2cb48a2695bd2073af0fc80e321d90687`
removed the exact V177 predecessor's `2,292` production receipt-history scans
and `488` eager retained-authorization updates; both are zero in V178r1.  Its
producer-free verification is
`990cffd9b99324c05281dcb190fb8ea5c514729486e923acbd1f4ce489f8f3a6`.
The aggregate completion audit is
`373e67b24f19b130f556fbf5249b5661c27430a2f1ff15bc12dadb38d7238561`,
with independent verification
`56fb4630b23cdfa0e28effaccaaabe30ddf8c9e18a40575ec30049fcabe9a3c9`.

This status is deliberately not a universal-world-model claim.  Complete
ground-model synthesis, open-ended invention, arbitrary unseen-domain transfer,
and broad IID sample efficiency remain false.  Official execution remains
disabled, scalar cost and break-even remain null, and Workload Economics and
Counter Completeness remain `NOT_RUN`.

The operational order is:

```text
authoritative exact coverage or a preregistered trusted observation/action catalogue
→ synthesize and freeze one portable auditable abstract world model
→ answer a workload of QuerySpecs by abstract contingent planning
→ independently audit each complete plan's value and risk
→ reuse unchanged when certified
→ otherwise find the slack-aware causal family on the earliest DirectBad antichain
→ compile a minimal finite-domain worker capability
→ jointly search local value/risk choices, rebuild, or use charged fallback
```

## V180r12r4 ordinal11 pre-campaign successor

The current V180r12r4 successor consumes the ordinal10 failure freeze
`4671ff59a5b141816c8cfe9a692a55354b799f077e6bf4efc8764ee991a34dc7`
as its immediate predecessor and retains ordinal9 as historical lineage.  Its
formal source boundary has 25 sorted, unique, regular `0644` single-link roots,
including the new ordinal10 failure-freeze module.  The source-closure,
materialization and launch rule IDs are respectively
`7f0d63c0143c72d3a41f9a4ad25b9fc29f6952ae05a1b4797cded68728d27090`,
`0dfee347b3b36527bcc06b81228545043b3aeff8c0163738001653b27e363b91`
and `77943eb671fdc3f1d90c977b7b6405f7127284b223ced1491ba69fda8e91e28a`.

Protocol freeze and prelaunch construction exact-join one source-bound
`app.slice` service-context capture with `cpu`, `memory` and `pids` enabled.
Before a campaign ATTEMPT, the measurement runner publishes a separate `0400`
host-conformance artifact containing the expected and observed parent/runtime
facts, per-field mismatches and typed cause.  The launcher and producer-free
verifier independently replay its canonical semantics and join its observed
membership to the formal measurement T1 receipt; it is not a campaign event or
CounterRecord.  The twelve wrapper self-reference literals remain zero at
`C_pre`; no ordinal11 campaign attempt has been created by this construction.

## Current fresh-campaign construction (V0-075, target locked)

V0-075 is a new authority family, not a third V0-072 attempt. Its construction
contracts now span `1.40.0` through `2.0.10`: the earlier contracts build the
source archive, law-free public target graph, private reveal/observer boundary
and multiround planning path; the newer contracts reconstruct the portable
evidence graph role by role before any production target access.

The public K7/W7/K7-minus-two structures are retained only as a same-structure
fresh statistical replication. The initially proposed spawn laws were exposed
during construction and are now regression fixtures only. A production law
must remain private behind a high-entropy salted commitment until a real final
preregistration and remote-main anchor exist; every target identity/tape will
then be new. No V0-072 target observation, model, policy, certificate,
journal, result, cache or retry authority is accepted.

Construction currently keeps target access disabled. The full campaign
contract is
[`specs/FRESH_TOTAL_LIFT_PARALLEL_CONFIRMATORY_CAMPAIGN.md`](specs/FRESH_TOTAL_LIFT_PARALLEL_CONFIRMATORY_CAMPAIGN.md).
Implemented pre-target boundaries now include a source-only exact replay
controller, private reveal/observer isolation, strict manifest/preregistration
construction, and independent remote-Git anchor replay. The exact source
replay has completed and charges all `1,006,720` source draws; its eight
public artifacts are frozen on `origin/main`. Batch-native partial-support
construction now also has a real multistage
observation→model→plan→row-specific-total-lift positive control. Target access
remains locked while the production occurrence, reconciliation, endpoint and
remaining semantic-authority chain are completed.

The current portable semantic cut is deliberately narrower than “production
authorized”:

```text
raw public context
-> M0: 11 producer-typed public roles
-> B1: observer-open binding
-> M1A: 6 signed-batch roles + iterative O(V+E) dependency DAG
-> M1B: 16 signed-control roles with exact ROOT/M0 binding
-> M2 root: OCCURRENCE_IDENTITY + ROOT_EXECUTION are FULL_PUBLIC
-> M2 lineage: batch public + sequence verification are FULL_PUBLIC
-> M2 lifecycle: support evidence/freezes/events are FULL_PUBLIC
-> M2 live epoch: row-source bindings are FULL_PUBLIC
-> M2 planning: NUMERICAL_MODEL + NUMERICAL_PLANNING_PROOF are FULL_PUBLIC
-> LIVE_MODEL_EPOCH is transitively FULL_PUBLIC
-> M2 dynamic child: 4 present proposal roles are transitively FULL_PUBLIC
-> discovery/validation intent roles are explicitly absent
-> raw construction-private replay regenerates the committed private law
-> SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION is
   FULL_CONSTRUCTION_PRIVATE_REPLAY
-> CONSTRUCTION_LINEAGE + lifecycle + lifecycle verification are
   FULL_CONSTRUCTION_TRANSITIVE
-> construction compiler replay closes CONSTRUCTION_PLANNING_INPUT as
   FULL_CONSTRUCTION_COMPILER_REPLAY
-> owner-bound replay closes CLOSED_RECONCILIATION as
   FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY
-> owner-bound root-only replay closes MULTIROUND_RESULT as
   FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY
```

Contract `1.68.0` adds a new construction-only atomic private-replay
attestation. Its trusted freeze performs the real private replay before
observer signing and rejects caller-supplied/legacy verification objects. The
public verifier still claims only `observer_signed=true` and
`independently_recomputed=false`: a generic signer holder can bypass the
helper. Contract `1.69.0` adds the fail-closed signer-owning sealed-child
transport. Contract `1.71.0` extends that custody shape through observer open,
the registered synthetic root batches, close, private replay and B3 signing
inside one child, but remains a construction-only noncertificate and adds no
portable role. Contract `1.70.0` reconstructs the M1B controls; contracts
`1.72.0` and `1.73.0` close the public root and batch-lineage roles listed
above. Contracts `1.74.0` and `1.75.0` then reconstruct lifecycle sources and
live row-source/epoch projections while preserving, respectively, the exact
private closure-verification and numerical model/proof frontiers. Contract
`1.76.0` reconstructs the dynamic-child proposal and binds every present
record to its exact epoch/model/proof and causal source graph; its four present
roles initially remain numerical-unresolved and two roles are explicitly
absent. Contract `1.77.0` then replays every live-epoch model/proof through the
public exact planner and binds models to their exact occurrence, open-prefix
and row-source records. Model/proof, live-epoch and the four present proposal
roles consequently close as `FULL_PUBLIC`. The construction planning input
deliberately remains unresolved at itself: no issuer-owned typed private
lineage is reconstructed or fabricated, and its compiler is not called.
Contract `1.78.0` supplies the missing construction-only authority without
rewriting it as public authority. It first completes hardened 1.77 replay,
then regenerates the committed private environment from bounded ephemeral
seed/salt inputs and calls only the registered construction lineage/lifecycle
producer APIs. The private closure verification closes as
`FULL_CONSTRUCTION_PRIVATE_REPLAY`; lineage, lifecycle and lifecycle
verification close only as `FULL_CONSTRUCTION_TRANSITIVE`. No secret value or
secret digest is retained or emitted, and currentness requires the five raw
inputs and a complete replay. This same-process cut is not a sealed production
secret channel. Contract `1.79.0` then invokes only the registered construction
planning-input compiler using the exact M0 schedule and the fresh lineage and
lifecycle from 1.78. The complete input, its uniquely selected standalone
numerical model, and every row-level batch/freeze evidence binding must match
the portable records byte-for-byte. The input closes only as
`FULL_CONSTRUCTION_COMPILER_REPLAY`; closed reconciliation and the final
multiround result initially remain their own unresolved producer frontiers.
Contract `1.80.0` adds the missing owner-side public construction producer.
It publicly replays the final live epoch, controlled closure, lineage and
lifecycle, verifies the complete closed append/freeze prefix, recompiles the
input, replans the proof and only then uses the reconciliation issuer inside
its owning module. The portable authority requires the resulting singleton
record and every schedule/closure/epoch/model/proof/input parent to match
byte-for-byte. `CLOSED_RECONCILIATION` closes only as construction
reconciliation replay. Contract `1.81.0` then reconstructs issuer-backed root
execution from the exact schedule and controlled open prefix, and derives the
terminal result from replayed parents without accepting a caller status or
claimed result. The portable cut is intentionally limited to the registered
root-only `CHILD_ACTION_ROW_CAP_EXCEEDED` occurrence: every optional child and
promotion role must be absent in the fresh bundle, and the result target is
read only after the owner producer has been fixed. `MULTIROUND_RESULT` closes
as `FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY`; the construction dependency
frontier is empty. Contract `1.82.0` then overlays the unchanged 67-role
semantic declaration registry on that exact DAG. It binds each of the 49
present records one-to-one across the verified bundle, legacy shape/content-ID
attestation and construction producer replay, while the exact 18 missing
child/promotion roles are proved absent by the fresh root-only empty-role
registry. Legacy `COMPLETE`/`INCOMPLETE` labels are preserved as historical
shape-replay status; the new `FULL_TYPED_REPLAY` status is a separate
construction-only lane. Per-record authority scopes remain unflattened and a
native-zero-inclusive scope histogram sums exactly to the bundle record count.

Contract `1.83.0` starts only after exact raw 1.82 replay succeeds. It binds
every tracked `src/acfqp/**/*.py` file—not merely a statically discovered
runtime subset—to a regular nonsymlink local Git blob whose worktree, index
and `HEAD` bytes agree. The historical 64-entry occurrence manifest remains
an exact subset lane; all additional ACFQP files remain in a separate
semantic-code lane. Git inspection uses the bound `/usr/bin/git` executable
under a clean environment.

The complete 337-file ACFQP snapshot is packed as a deterministic
`ZIP_STORED` archive and bound to the tracked dependency lock,
`pyproject.toml` and `/usr/bin/python3`. An isolated `-I -S` child reads the
sealed archive and compiles every exact member without adding it to
`sys.path`, importing it or executing tested code. This deliberately does
not claim a loaded-source manifest: an adversarial regression proved that
code imported inside the checking process could forge its own result.
The independent byte verifier reconstructs Git, both lanes, the archive,
runtime binding, compile manifest, DAG and content IDs without calling the
producer freezer or issuer.

This is local construction source/archive/compile provenance only. It is not
a final campaign manifest, remote-main anchor, OS attestation, third-party
source-tree proof or future target-worker loaded-code receipt. Production
still requires unqualified source/code provenance, complete native accounting,
typed terminal/campaign closure and an independent production complete-bundle
verifier.
Sample-efficiency, official, scalar, economics and counter-completeness Gates
remain locked.

Contract `1.84.0` freezes the next accounting boundary without pretending
that old summaries are native work. It first completes independent raw-1.83
verification, then binds the Phase-3E v1 registry (`49` leaves, `34`
operational), comparison profile and actual-projection profile. That registry
is immutable. Initial BUILD/ACQUISITION and REBUILD are separate stages.
Thirteen v2 path names are reserved, but their full
unit/lane/scope/reducer/axis semantics and `acfqp_counter_registry_v2`
artifact remain deliberately unfrozen. The reserved names intersect neither
the 49 v1 paths nor the 87 distinct legacy custom paths.

Five historical V0-075 custom catalogues contain `23/17/15/22/18` paths and
have zero exact path overlap with v1. The current root-only portable bundle
contains none of their typed vectors. Their custom documents, aggregate
totals and embedded semantic counts therefore cannot be re-labelled as
`CounterRecord`s, missing records or native zeroes. The 67-role semantic
registry remains unchanged; accounting and closure use a separate outer
companion registry.

This foundation freezes only the registry/gap matrix, outer-role topology and
the future noncertificate derivation
`CHILD_ACTION_ROW_CAP_EXCEEDED -> ROUTE_ATTEMPT /
ATTEMPT_BUDGET_EXHAUSTED`. Logical-occurrence closure remains dependent on a
typed rebuild/retry policy and exhaustion evidence. The foundation
materializes no WorkVector, actual projection or terminal. Raw 1.83's
unrecorded Git, subprocess, I/O, hash and peak work remains a
provenance/evaluation prefix and cannot be reconstructed retrospectively.
All-path accounting, campaign closure, loaded-source receipt, independent
complete-bundle verification, production, fresh science and certificate
Gates remain locked.

The next Gate must instrument the same non-fresh root-only construction
occurrence from execution start, using separate model-build/acquisition and
failed-abstract-prefix stage vectors, exact projections and a typed
noncertificate occurrence closure. It then expands to every failure/terminal
path and campaign reconciliation before any new final
preregistration/manifest/anchor or fresh target access.

Contract `1.85.0` materializes the scoped additive construction accounting-v2
schema after an exact issuer-backed independent verification of 1.84.  The
49-leaf immutable v1 prefix is preserved byte-for-byte.  Thirteen initial
BUILD/ACQUISITION definitions and seven separate closed-reconciliation
definitions produce a `69`-leaf registry with `53` operational and `62`
required leaves.  Accepted observer draws project to
`kernel_transition_calls`; rejection count remains required diagnostic
telemetry and is not charged again; repeated reconciliation compile/plan
work cannot reuse the initial-build paths.

Eight construction stages, the unchanged eight shared axes, all 53
coefficient-one projection terms, and the distinct actual-projection profile
are content-addressed.  Record and WorkVector schemas bind subject, stage
instance and stage kind.  This contract nevertheless emits zero live records
and zero WorkVectors: the trusted stage-start/completion authority and 11
hash/integrity/protocol/I/O/process/peak recorder gaps are still open.
Those 11 paths are only the current critical subset, not an exhaustive
operation-site inventory.  All 87 distinct legacy custom paths still require
an exact operation-site mapping to v2 or an explicit later registry revision;
an unmapped operation cannot be silently dropped.
All-path accounting, typed terminal/occurrence/campaign closure, production,
fresh science, scalar/break-even and certificate Gates therefore remain
locked.

Contract `1.86.0` repairs the registry before any live K7 accounting run.
The five historical counter catalogues contain 95 entries and 87 distinct
paths.  An exhaustive partition classifies them as 7 operation families to
re-instrument on existing leaves, 18 to decompose at native
protocol/integrity/I/O sites, 51 derived or diagnostic views, and 11 genuinely
missing operational families.  Historical summaries still cannot become
native records.

The immutable successor retains all 69 v2 leaves and adds stage-local
confidence, likelihood, LP, dominance, tie-break, outcome-projection,
proposal-binding, child-catalogue and quotient/action/concretizer work,
including a separate failed-child-audit leaf.  It has 116 leaves, 99
operational leaves and 109 required leaves.  Two new stages distinguish
incremental acquisition and checkpoint replanning while the observer remains
open; this work cannot be charged as initial construction or closed
reconciliation.  The unchanged eight axes receive 99 coefficient-one terms.

This is still schema repair, not live accounting.  Operation-site hooks,
derived formulas, hash/check/I/O/peak granularity and trusted stage lifecycle
attestations remain open, so the closure emits no CounterRecord, WorkVector,
terminal or campaign result.  Production, fresh science, scalar/economics and
certificate Gates remain locked.

Contract `1.87.0` corrects two further operation-ownership holes found by
walking the real K7 root-cap call graph.  Outcome projection and prior binding
may execute during initial build or open checkpoint replanning, while closed
private verification actually performs its own deterministic ground/random-
word/aggregate replay.  The immutable v4 successor preserves all 116 v3
leaves and adds eight required stage-local leaves, yielding `124` total,
`106` operational and `117` required leaves with `106` exact projection
terms.  The registered K7 scientific acquisition remains `4,224` accepted
draws; the current closure's additional `4,224` ground steps are replay work,
not new observations, and may not disappear from operational accounting.

This revision also implements issuer-owned stage lifecycle/event replay,
explicit native-zero WorkVectors and exact actual projection mechanics, plus
a context-gated same-process failed-child/result-audit hook that can avoid
redundant full replay.  The hook is not yet wired to an operational runner or
live-evidenced; legacy V2 portable replay remains the unchanged default.  No
operation-site-complete live vector is issued yet, so
formula/hash/check/I/O/process/peak, typed terminal/campaign, production,
fresh-science, scalar/economics and certificate Gates remain locked.

Contract `1.87.0`'s nonfresh K7 root-cap manifest originally classified the
five-stage execution plan as 13 direct-native hook sites plus 10 pending
common/hash/I/O/process/peak sites.  Contract `1.88.0` supersedes only that
manifest's hook-admissibility claim after a strict source-owner audit.  The v2
audit binds the exact v1 manifest as a negative predecessor and classifies its
43 audited entries as nine owner-matched v4 targets, 13 native-zero inherited
families, ten pending common/hash/I/O/process/peak sites, one derived-only route
reconciliation view and ten missing batch-v2 counter families.  In particular,
learned-planner, semantic-replay and abstract-planner counters cannot be charged
for work performed by the batch-v2 planner, and the closure private replay site
is the private observer verifier rather than the runner wrapper.  The v1 sink
is inadmissible and is not reused.  No emitter, live event or WorkVector is
issued; operation-site instrumentation and every Gate remain locked pending an
additive batch-v2 registry and actual source hooks.

Contract `1.89.0` supplies that additive schema without pretending the hooks
already exist.  The immutable v4 prefix is preserved exactly and 27 required
operational leaves are added at their real owners: ten initial-build leaves,
six failed-prefix dynamic-audit leaves and eleven closed-reconciliation
leaves.  The v5 registry therefore contains `151` leaves, `133` operational
leaves, `144` required leaves and `133` coefficient-one projection terms over
the unchanged ten stages and eight shared axes.  The interval-LP leaf semantics
is one event per executed greedy-allocation step, and live-model
descriptor/projection work is not relabelled as batch-planner work.  An
independent implementation rebuilds the strict-owner manifest, registry, stage
profile and projections from canonical manifest bytes and verified v4 bytes.

This remains a minimal known-owner-gap closure, not operation-family
completeness.  Runtime owner match, runtime stage attribution and the complete
event-boundary profile remain false; no source hook, live event, WorkVector or
terminal/campaign artifact is emitted.  Also, aggregate-row counts such as `41` are properties
of one exact private-law/namespace/occurrence fixture; they are not K7-wide
goldens and cannot populate an expected live vector until that full identity
is bound.  Common/hash/I/O/process/peak work, formulas, typed closure,
production, fresh science, scalar/economics and certificate Gates remain
locked.

Contract `1.90.0` adds the owner-correct partial-native execution layer.  The
additive V6 registry preserves V5 and contains `209` total, `182` operational
and `202` required leaves with `182` exact projection terms.  Its K7 root-cap
boundary catalogue has `150` entries.  An inactive-by-default runtime resolves
each positive event from the trusted active stage and a stage-neutral dispatch,
then verifies that the direct caller is the registered module's exact code
object.  The owned wrapper excludes another owned-wrapper run while a separate
lock isolates registered Bernoulli cache users across the five construction
stages; it preserves the underlying V2 result bytes and emits only an immutable
`PARTIAL_NATIVE_ONLY` transcript.  A separate V0-075 identity overlay binds
the exact public K7 context/arm/route/terminal without reusing the historical
V0-072 execution identity, and an independent verifier reconstructs the V6
schema, all boundary identities and the transcript chain from canonical bytes.

This is not a complete or official WorkVector.  No full live K7 transcript has
been frozen, and no `CounterRecord`, `WorkVector`, `ComparisonVector` or actual
projection proof is issued.  Seven common additive hash/check/I/O/process paths
and two mounted/working-set peak paths still require owner-native hooks; absent
work remains unknown rather than zero.  These locks are not a whole-process
sandbox, and same-process evidence callbacks remain cooperative.  Official
execution, scalar/break-even,
economics, fresh scientific endpoint credit and certificate issuance remain
false, null or `NOT_RUN`.

Contract `1.91.0` adds the fail-closed accounting-completion prerequisite. It
partitions the 202 required leaves exactly as `9 shared + 8 derived + 114
profile-zero + 71 owner-emittable` (89 registered sites), initializes every
leaf as unresolved, and keeps syntactically complete references explicitly
unverified. Typed shared-resource claims, path-specific zero rules,
owner-boundary coverage, occurrence identity joins and cutoff markers cannot
authorize numeric projection without independent source-byte replay. A
composite prerequisite manifest content-binds the exact authority graph and
all six typed missing-evidence sets. The current same-process path therefore
remains deterministically not ready and emits no formal vectors.

Contract `1.92.0` adds the first live shared-resource primitives without
unlocking that Gate: an identity-bound nine-path event meter, a deterministic
capped eight-role output-byte candidate fixed point, a strict K7 child-frame
schema, and a structural post-cutoff envelope/finalization join. The parser
rejects noncanonical/nonfinite JSON, bool-as-integer aliases and frame/identity
transplants; the envelope only checks local identity distinctness and event
ordering. A real supervisor-issued post-reap envelope, typed K7 route join,
atomic output commit including wrapper bytes, independent source replay and
formal 202-path materialization remain unconnected. Consequently no
CounterRecord, WorkVector or ComparisonVector is yet issued.

Contract `1.93.0` removes three structural degrees of freedom without claiming
an operating-system supervisor. The exact accounted K7 route now derives all
seven shared-resource identity fields; an issuer-owned six-event journal fixes
the internal order `window start -> business cutoff -> process reap ->
descendant scan -> final cgroup peak -> parent terminal`; and a structural
bridge derives the older outer-finalizer's source roles, post-cutoff sequence
arguments, lifecycle booleans and final peak from that journal. Journal source
documents remain caller-provided typed claims, and the journal sequence is
only an internal structural order—not verified OS time or cgroup/process
provenance. A new K7-only signer loader can validate the registered ordinary
`.git`-directory marker shape and an external private-key root without launching
Git, but it is not wired into the real child path. There is still no real K7
child, pidfd/cgroup/one-child authority, supervisor-owned source evidence,
atomic wrapper-complete output commit or formal `CounterRecord -> WorkVector ->
ComparisonVector` chain. All official, formal, counter-completeness, economics,
science and certificate locks remain false, null or `NOT_RUN`.

Contract `1.94.0` adds the first real host-side admission probe for the future
K7 OS supervisor. It performs bounded read-only capture of pidfd and unified
cgroup-v2 prerequisites, requires a preopened delegated-parent directory FD,
and stops before child launch when that authority is absent. The current WSL2
context therefore returns nonauthoritative `NOT_AVAILABLE` evidence rather
than substituting RSS polling or a process-group heuristic. A supplied
directory FD also remains `NOT_AVAILABLE`: exclusive leaf creation, atomic
child placement, pidfd reap,
post-reap peak evidence and the parent-owned accounting suffix remain the next
construction Gate. No formal accounting or official flag changes.

Contract `1.95.0` freezes that successor's prelaunch identity graph. It derives
the bootstrap entry from the sealed source snapshot and binds the complete
accounted route, signer registry, commitments, session/nonce, scientific
occurrence/schedule and its Phase-3E logical-occurrence mapping. A future
launched path must emit child-owned K7 business followed by a parent-owned
accounting suffix. The current unavailable host produces only a zero-launch,
zero-frame structural blocked result; it is not an attempt terminal and issues
no formal accounting object.

Contract `1.96.0` adds the first real mutating cgroup-v2 sub-authority. A
process-local issuer consumes the exact request nonce once before any cgroup
access, binds the admission object and the preopened parent FD by both stat
identity and `/proc/self/fd` target digest, and then creates a unique leaf only
through `dir_fd` operations. The leaf must be a domain cgroup on cgroup2, empty
with zero initial `memory.peak`, and expose the required controls; `pids.max=1`,
`cgroup.max.depth=0` and `cgroup.max.descendants=0` are written and read back
exactly. Every post-creation failure removes the owned leaf or raises a cleanup
failure, and a successful lease is process-local and unpickleable. A real
temporary systemd-delegated scope exercised the positive create/readback/close
path and confirmed leaf removal. This lease still launches no child and grants
no pidfd, accounting-vector, terminal or official authority; durable
cross-process nonce replay and the parent-owned executor remain the next Gate.

Contract `1.97.0` removes the fresh-exec request-authority blocker without
weakening V0-103. From the exact sealed source archive and three canonical
profile documents, the child side reconstructs the sealed transport, complete
lifecycle, V6 accounted-profile and successor-profile authority chain, then
reconstructs the complete successor request and requires byte-for-byte equality.
No live parent request object crosses the process boundary. The reconstructed
closure and request are process-local and unpickleable. This is still a
pre-business boundary: it launches nothing, proves no loaded-code or isolated
runtime fact, emits no successor frame and grants no shared-resource or formal
accounting authority.

Contract `1.98.0` implements the child-owned first successor frame. The exact
fresh-exec request replay drives one registered K7 `NO_PRIOR` owned partial
run; its real portable evidence graph and owned transcript/cache wrappers are
embedded and strictly replayed. Private-output scanning is request-bound and
uses the same single secure key read as signer construction. A real portable
integration test closes schema/topology drift. The parent-owned cgroup/pidfd
executor, accounting suffix, complete transcript semantics and formal vectors
remain the next Gate.

Contract `1.99.0` adds the real atomic Linux runtime beneath that frame. One
audited x86-64 native trampoline performs `clone3` directly into the leased
cgroup with a pidfd; the child installs parent-death, Landlock and seccomp
containment before executing a sealed memfd, while the parent enforces memory,
swap, output and deadline limits and proves reap, EOF, empty leaf and zero
descendants. A real delegated-systemd integration verifies execution,
setup-failure provenance and fork/file/metadata/cgroup/socket/parent-limit
denial. The runtime still emits only nonformal raw facts:
the business-entry join, parent accounting suffix, atomic two-frame result and
formal nine-path/202-leaf accounting remain locked.

Contract `2.0.0` performs that previously missing real join. One parent-owned
attempt seals the exact V0-105 replay inputs, enters the archive-loaded child,
executes the V0-106 owned K7 business once through the V0-107 atomic runtime,
and accepts only zero exit, EOF-before-reap, final peak, empty cgroup and no
descendants. After public replay of the frozen child frame, the parent creates
the second frame and strict replay permits exactly
`CHILD_OWNED_K7_BUSINESS -> PARENT_OWNED_ACCOUNTING_SUFFIX`, with a fixed-point
wrapper-complete byte count and no trailing data. The result is atomic only as
one immutable in-memory protocol object; no durable artifact writer is claimed.

This closes the executor integration, not accounting authority. The suffix
labels process launch, final working-set peak and two-frame output bytes as raw
nonformal facts and leaves the other shared paths unavailable. None of the nine
paths has a semantic receipt, so no `CounterRecord`, `WorkVector`,
`ComparisonVector`, projection proof, terminal, certificate, scientific result
or official authority is issued. The exact boundary is documented in
[`specs/K7_PARENT_ATOMIC_EXECUTOR.md`](specs/K7_PARENT_ATOMIC_EXECUTOR.md).

Contract `2.0.1` adds issuer-owned runtime lifecycle evidence and the exact
production nine-row shared-resource registry. It binds the V0-108 result to the
request/route, V6 registry and stage profile, sealed parent/runtime sources and
native trampoline. Final cgroup `memory.peak` verifies
`memory.working_bytes_peak` only for the child-runtime window and is frozen as
`VERIFIED_CHILD_RUNTIME_WINDOW_SCOPE_INCOMPLETE`. The native launch count is
`VERIFIED_RUNTIME_LOCAL_SCOPE_INCOMPLETE`. Neither covers the complete parent
attempt; the other seven hash, integrity, protocol, mount and I/O paths are
`NOT_CONNECTED`.

Thus V0-109 provides two exact window-local observations but zero eligible
attempt-scope shared-resource resolutions. It still issues no nine-path receipt
set, `CounterRecord`, `WorkVector`,
`ComparisonVector`, projection proof, terminal, certificate, scientific result
or official authority. See
[`specs/K7_ATOMIC_SHARED_RESOURCE_AUTHORITY.md`](specs/K7_ATOMIC_SHARED_RESOURCE_AUTHORITY.md).

Contract `2.0.2` / V0-110A opens one process-supervision session and activates
its process sink before request binding/replay. The sink remains active through
typed parent-result payload freezing and raw-journal closure. The returned
envelope is only a post-cutoff no-launch canonical wrapper; it does not prove a
complete publication/cleanup window, and any future post-cutoff helper launch
would be outside the current raw coverage.

When the parent branch receives a positive `clone3` result, the receiver first
advances a volatile write-ahead launch-edge lower bound, then obtains provenance
and materializes the typed event before pidfd validation or other fallible
post-clone work. Materialization failure retains a nonformal `PROTOCOL_FAILURE`
prefix rather than reverting to zero. Covered finalization failures retain a
closed journal, canonical nonformal emergency prefix, or—if both encodings
fail—a noncanonical emergency raw-field snapshot.

The resulting status is only
`VERIFIED_ATTEMPT_WINDOW_RAW_SCOPE_INCOMPLETE`. Canonical raw-byte replay is not
independent OS evidence. Import-time call-site pins resist ordinary public
module-symbol rebinding only; arbitrary same-process underscore/global/object
mutation, including `object.__setattr__`, plus sink/interpreter crashes and
no-loss coverage are outside the raw threat model. Exact promotion requires
external isolation and
supervisor/kernel attestation over the intended full publication/cleanup
scope. The nine shared-resource paths, `CounterRecord -> WorkVector ->
ComparisonVector`, terminal/certificate and official Gates remain locked. See
[`specs/K7_ATTEMPT_PROCESS_SUPERVISOR.md`](specs/K7_ATTEMPT_PROCESS_SUPERVISOR.md).

Contract `2.0.3` / V0-110B-1 adds the real prepared cgroup hierarchy needed
for future complete-attempt memory measurement. A fresh empty ancestor delegates
`memory+pids` to a one-process worker leaf while retaining capacity for a
broker-created business sibling. Request/admission/descriptor-bound single-use
authority, finite controls, a pre-descendant zero-peak check, a complete empty
topology snapshot, writable `cgroup.kill` openability and retryable unused
cleanup are enforced. Partial cleanup revokes all consumer access; post-identity
setup failure retains its descriptors in a process-local retry guard, while the
pre-identity create gap explicitly requires an external parent guardian. A
changed cap cannot prevent safe deletion and instead raises a typed
cleanup-complete protocol error. The positive path passes in a real
systemd-delegated user scope.

This is `PREP_ONLY`: descendant metadata can raise the ancestor peak, so
contract `2.0.3` deferred the exact window placement. Contract `2.0.5`
supersedes its proposed immediate-prelaunch reset by starting the retained
measurement window before descendant creation. Exclusive parent write
authority, atomic descriptor deletion and a crash-surviving guardian are not
proved; no worker has run and no pidfd/output lifecycle has been joined.
Exact process SUM requires an external two-launch broker plus no-spawn
worker/business execution, and its window must include final publication/output
and cleanup. Existing V0-107/V0-108 execution is not silently relabelled. The
remaining seven paths and `CounterRecord -> WorkVector -> ComparisonVector`
remain locked. See
[`specs/K7_OUTER_ATTEMPT_CGROUP.md`](specs/K7_OUTER_ATTEMPT_CGROUP.md).

Contract `2.0.4` / V0-110B-2A freezes the external-broker successor protocol.
Exactly five canonical, length-prefixed roles bind one request/route/broker-spec
and session: worker ready, one business request, business result, parent output
and worker EOF. Role-specific exact payload schemas prevent the worker from
selecting an FD, executable, argv, environment or cgroup. Strict replay rejects
missing, duplicated, reordered, extra, binding-mismatched/transplanted,
noncanonical and over-cap frames. The binding and stream are caller-
constructible offline values: byte-identical replay is allowed, sender
ownership and one-time nonce consumption are not proved, and the transcript
can never authorize a launch.

This is structural IPC only. The broker runtime, two sibling `clone3` launches,
kernel no-spawn proof, same-open-description `memory.peak` reset/read, complete
output/cleanup window and all nine semantic receipts remain unimplemented.
Consequently it emits no process or memory value and no `CounterRecord`,
`WorkVector` or `ComparisonVector`. See
[`specs/K7_OUTER_ATTEMPT_BROKER_PROTOCOL.md`](specs/K7_OUTER_ATTEMPT_BROKER_PROTOCOL.md).

Contract `2.0.5` / V0-110B-2B now prepares one real live broker session without
launching it. The outer lease transfers irreversibly into a process-local
guardian, which adds the fixed `business` sibling, owns the kill/peak/socket
descriptors, mints the execution spec and nonce, and rejects request reuse.
Real cgroup evidence corrected the memory-window placement: an empty prepared
two-leaf tree already carries kernel memory, so the unique `memory.peak` OFD is
reset at zero before descendant creation and retained across all later
preparation. No baseline subtraction is used. The real delegated-scope path
passes; launches, peer ownership, final peak, receipts and formal vectors are
still locked. See
[`specs/K7_OUTER_ATTEMPT_BROKER_PREPARATION.md`](specs/K7_OUTER_ATTEMPT_BROKER_PREPARATION.md).

Contract `2.0.6` / V0-110B-2C consumes that prepared session in a real
two-role native launch probe. One signal-blocked, single-threaded broker calls
`clone3(CLONE_INTO_CGROUP|CLONE_PIDFD|CLONE_CLEAR_SIGHAND)` first for
`worker`, then for `business`; the native parent branch writes the role edge
before returning to Python. Both children enter their fixed sibling cgroups,
install the existing no-spawn Landlock/seccomp bootstrap before `execveat`,
and are reaped through distinct pidfds. Failed runs retain only the valid
`(0,0)`, `(1,0)` or `(1,1)` prefix, and an interrupted reap retains a
process-local retry authority instead of closing its pidfd. That authority is
guardian-bound before the first clone; signals stay blocked through native-fact
recovery, retired pidfds cannot be resurrected from stale cells, and
`cgroup.kill` remains available for tree-only retry. A real delegated scope
launches and reaps two `/bin/true` images and closes the tree.

This remains a probe. Its launch cells are volatile, the direct peer
socketpair cannot prove authorship of the five protocol frames, and the final
peak is not yet a complete operational output window. It therefore signs no
exact `process.launches`, shared-resource receipt, `CounterRecord`,
`WorkVector` or `ComparisonVector`. See
[`specs/K7_TWO_ROLE_BROKER_PROBE.md`](specs/K7_TWO_ROLE_BROKER_PROBE.md).

Contract `2.0.7` / V0-110B-2D-1 freezes the production worker/business role
plan and implements both role-local protocol cores. The manifest derives the
dispatch program, argv, environment, cgroup, source/interpreter and exact FD
roles from the request and live-replayed prepared session rather than public
caller input. Its absent entry members and current argv are explicitly a
non-launchable template; 2D-2 must issue a new archive/request/manifest with a
real archive-loading bootstrap. Business uses owned FD duplicates, kernel
socket-domain/flag checks, binding snapshots, pre-seal rollback and typed
irreversible stages to publish one `BUSINESS_RESULT`. Worker admits a delayed
half-close without the old scheduling race and durably commits the canonical
pre-reap output. Temporary cleanup is inode-bound; post-rename recovery is
bound to the original directory/inode; successful completion retains both
output and receipt preimages.

This is not yet the live broker join. Kernel sender credentials, production
role launch, exclusive output-directory authority, role-specific sandboxing,
complete transcript, final peak/reaps/cleanup envelope and all nine semantic
receipts remain absent. Formal vectors and every official Gate remain locked.
See
[`specs/K7_PRODUCTION_ROLE_AND_OUTPUT_CORE.md`](specs/K7_PRODUCTION_ROLE_AND_OUTPUT_CORE.md).

Contract `2.0.8` / V0-110B-2D-2A issues the required fresh source identity
instead of relabelling the absent-wrapper template. The new archive contains
fixed worker/business process entries, a common public-input reconstructor and
two frozen `python -I -S -B -c` archive bootstraps. Each bootstrap verifies the
complete environment and FD namespace, sealed-versus-capability lane
separation, interpreter/archive digests and exact ZIP module origin before
entry. Runtime call-site provenance now reads exact ZIP member bytes, while the
business lifecycle secret is metadata-checked but not copied before its sole
business-core read.

This is executable source closure, not the live broker. Native launch,
role-specific sandboxing, sender credentials, transcript, output reread,
reaps, final peak and all nine accounting paths remain locked. See
[`specs/K7_PRODUCTION_ROLE_ARCHIVE_BOOTSTRAP.md`](specs/K7_PRODUCTION_ROLE_ARCHIVE_BOOTSTRAP.md).

Contract `2.0.9` / V0-110B-2D-2B prepares the concrete nonsealed resource
topology for those wrappers: two broker-mediated SEQPACKET pairs with
broker-only `SO_PASSCRED`, one result memfd with distinct business-RW and
worker/broker-RO descriptions, and one fresh output directory available only
to the worker and broker. Exact manifest/context/binding identities and
pairwise-disjoint FD roles are replayed; packet, option, memfd, directory and
cross-binding attacks fail closed under a process-local cleanup guardian.

No process or frame is created by this slice. Sandbox, native launcher, live
protocol, post-reap envelope and formal accounting remain locked. See
[`specs/K7_BROKER_RESOURCE_SESSION.md`](specs/K7_BROKER_RESOURCE_SESSION.md).

Contract `2.0.10` / V0-110B-2E-0 freezes the semantic input contract for all
nine shared-resource paths. Each path is bound to its V6 metadata, one exact
live source family, required component schemas, provenance obligations and a
fixed future replayer. V1 receipts/closures, mappings and self-reported
numeric values cannot cross this boundary; complete raw components remain
typed pending until independent path-specific replay exists.

This maps the nine sources but does not yet verify them or issue formal
records/vectors. See
[`specs/K7_NINE_PATH_SEMANTIC_RESOLUTION.md`](specs/K7_NINE_PATH_SEMANTIC_RESOLUTION.md).

## V0-074 repair construction (NONAUTHORIZING; fresh Gate NOT RUN)

Both anchored V0-072 attempts failed closed and produced no campaign result.
Attempt 2 has a valid durable hash chain, completed `4/15` occurrences, and
ended at the first K7 matched-direct exact-lift boundary:

```text
route-native checkpoint = CERTIFIED at 16384
attempt terminal         = ATTEMPT_CLOSURE_NONCERTIFICATE.PROTOCOL_FAILURE
result artifact          = absent
scientific endpoint      = forbidden
remaining retry slots    = 0
```

The independent evaluator incorrectly required actions for exact child states
represented by the partial model's frozen `OTHER` escape.  Proposed contract
`1.39.0` repairs that original path: modeled selected children still require
their decisions, while an exact child outside frozen modeled support is
charged once as `ABSORBING_POLICY_ABORT_FAILURE`, with failure one, zero
continuation reward, and an exact branch witness.  It also specifies a
pre-target content-addressed source proposal archive and isolated
occurrence-level process parallelism with byte-identical canonical merging.
Neither optimization changes draws, rational arithmetic, checkpoints,
confidence, caps, plans or certificates.

The checked-in archive/parallel runner is currently a synthetic
transport-and-scheduling control. It is not yet connected to the production
V0-072 proposal schema or campaign worker and therefore cannot authorize a
scientific rerun. The repaired exact path now independently replays the
operational robust-envelope containment checks and their attack tests; applying
them to a newly preregistered scientific bundle remains `NOT_RUN`.

The historical attempt is frozen in
`specs/V072_ANCHORED_ATTEMPT_2_FAILURE.json`; the repair contract is
`specs/PARTIAL_SUPPORT_TOTAL_LIFT_AND_PARALLEL_EXECUTION.md`.  Old K7 evidence
is regression-only.  A scientific sample-efficiency rerun requires a separate
preregistration, manifest and anchor plus fresh target identities/tapes and
genuinely fresh held-out occurrences. Official, scalar, economics,
counter-completeness and sample-efficiency Gates remain locked.

## Historical transfer-guided acquisition construction (V0-072)

V0-072 proposes contract `1.36.0`, schema `2.0.0`, and profile
`transfer_guided_adaptive_observation_acquisition_v1`. It freezes three
seven-vertex graph contexts (K7, W7, and K7-minus-two), five matched arms,
15 context-major occurrences, and at most two acquisition rounds. Every arm
starts with the same cold H2 schedule: 64 discovery draws and 2,048
validation draws per physical row, with conservative per-arm initial cap
506,880. Incremental work obeys
`C_R=2048*R+8256*|union(new child rows)| <= 160960`, with at most 19 new
child rows. At most 2,400 row-epoch authorities use
`beta=1/300000`, giving campaign tail at most `1/125` and conditional
confidence at least `124/125` without an independence assumption.

Before the two anchored attempts, the implemented and tested prerequisites
included:

- an exact-`Fraction` lazy H2 planner plus a separately implemented proof
  verifier for complete/pruned search prefixes;
- a verified V2 source archive that mechanically derives seven V0-068
  adjacent checkpoint roll-forwards, plus a separately implemented archive
  transform verifier that recomputes raw-prefix, exact fixed-policy,
  ranking, consensus, and identity obligations while retaining the explicit
  same-implementation V0-068 campaign boundary;
- exact split-support confidence with one `OTHER` event, immutable
  checkpoint prefixes, all-novel promotion, and a finite-union campaign
  authority;
- an evidence-first target selector: the complete public novel-child row
  list and exact draw upper freeze before gain/ranking, with independent
  row/count replay and fresh round-2 identity rules;
- a registered observer whose target APIs were initially locked behind the
  then-future semantically verified remote-`main` anchor, including raw
  commitments and full support-epoch-chain verification;
- generic immutable row-transcript and discovery-only cold-H2-closure
  authorities, each with a separately implemented verifier; their
  domain-separated synthetic K4 controls exercise incremental prefixes,
  arm-free random-word pairing, arm-bound evidence, and fresh promotion
  without sharing a registered context, law, stream, observation, model,
  endpoint, or claim identity; and
- an exact public-only adapter for all three clean held-out graph contexts,
  with independently replayed legal catalogues and context-total
  root-plus-child row caps `96/48/96`; a development-only
  confidence-to-row projection that preserves every exact interval and one
  row-bound adversarial `OTHER`; and
- an evaluation-only exact H2 ground enumerator, independent of the
  production model/planner implementation, whose registered entry was locked
  at that stage while separate K4/K5 controls covered feasible and infeasible
  cases;
  and
- a read-only execution-manifest readiness authority that can report missing
  components but cannot finalize a manifest, mint an anchor, or authorize a
  registered target observation.

Before either final anchor, a fake-placeholder development path produced only
in-memory tuples under eight now-retired development identities. No tape,
artifact, endpoint, or campaign output was persisted. The clean-generation
context/law/environment identities then had zero draws. The historical
audit-corrected draft preregistration
`7639f1ee57ee2d9a8c871a5f0270d15fdd92f712a735e2ae89b6155e057ba5c2`
had a null execution manifest and was neither an anchor nor an execution
credential. It superseded nonauthorizing drafts
`8b1e4747bb364ccddc04bb45d97a061c621650c907d31c979673f312acdffd29`
and
`e368be24adad7870d95c8e5059455d31e035783394e48040d113258388eaf4d4`.
The corrections permit one initial confidence epoch plus two promotions per
physical row while retaining the two-round, 480-authority-per-arm schedule
cap, and add the precise matched-direct checkpoint-cap noncertificate.

That draft-stage anchor rule was subsequently applied to two distinct frozen
chains. Both reached target execution and failed closed; neither wrote a
campaign result or endpoint. The second chain consumed the sole replacement
slot, so V0-072 now has no resume, retry, reuse, or third-attempt authority.

The positive empirical Gate is not run. Its primary endpoint is strict
SOURCE-versus-NO_PRIOR online-draw reduction; the matched endpoint also
requires SOURCE draws no greater than matched direct-ground planning,
noninferior certificate coverage, and zero false certificates. Completed
construction contract `1.34.0` and every official/economics/counter/sample
lock remain unchanged.

The preregistered contract and claim boundary are in
`specs/TRANSFER_GUIDED_ADAPTIVE_OBSERVATION_ACQUISITION.md`.

## Current source-guided acquisition construction (V0-071, Gate NOT RUN)

V0-071 targets profile
`source_frozen_certificate_sensitive_greedy_acquisition_v0`, but the strict
audit does not permit it to be called a completed Gate. The implemented slice
does establish these mechanics:

- exact target-current-model one-row certificate-slack ranking;
- proposal-only source multipliers bounded by `1/2 + (3/2)q`;
- the wrong control is the mechanical `q -> 1-q` reversal of the same prior;
- authorization freezes before any materialization;
- ranking counterfactuals cannot emit a model epoch or certificate; and
- a typed synthetic control performs one failed replan followed by one
  certified replan under the full robust planner.

The positive endpoints are explicitly
`SYNTHETIC_CONTROL_CERTIFIED_AFTER_ROUND_*`. Real K6 execution stops at
`AUTHORIZATION_READY`, a cap, or no positive gain. It therefore claims no
target acquisition, sample saving, transfer, or independent verification.

The audit found four construction blockers that must be closed by the next
revision:

1. source gains must be recomputed from source model/audit/raw evidence,
   rather than accepted as caller-supplied trials;
2. the cross-context feature key must remove sample-specific exact interval
   endpoints and `OTHER` mass;
3. a real observation materializer and a fresh round-2
   model/plan/frontier registry are required; and
4. the bundle verifier must independently replay source evidence, ranking,
   raw target observations, materialization, and certification.

The intended contract and its explicit non-closure state are documented in
`specs/SOURCE_FROZEN_CERTIFICATE_SENSITIVE_ACQUISITION.md`.

## Frozen model-only minimal-pair recovery Gate (V0-070)

Contract `1.34.0` freezes profile
`k6_model_only_minimal_pair_support_recovery_v0`.

V0-069 first tested whether a second, different K6 support row could repair
the failed transaction-1 certificate. It recomputed 49 eligible rows on the
immutable mixed model; none was individually causal, so it closed with zero
new observations and no `16384` or exact access.

V0-070 then rebuilt a fresh authority-bound registry and completed the
smallest joint extension without sampling. It replayed the selected
contingent policy through H1 and H2 for all 49 singleton overlays and all
1,176 canonical unordered pairs:

```text
singletons / fixed-plan covers = 49 / 0
pairs / fixed-plan covers      = 1176 / 0
terminal                       = NO_SOUND_FIXED_PLAN_PAIR_COVER
new observer draws             = 0
operational full replans       = 0
exact / global-16384 access    = 0 / 0
```

The standalone verifier independently implements the fixed-policy recurrence
and replays all 1,225 obligations. A separate finite positive control has
singleton failures but pair successes, preventing the negative K6 result
from being explained by an inert joint screen.

This closes only the current-selected-policy, cardinality-at-most-two
hypothesis. It does not justify brute-force `k=3`, exercise the dormant
materialization branch, or establish sample efficiency or project
completion. The next intervention must use source-frozen and target-evidence-
gated proof information to rank or reject acquisition while leaving the
target-local robust certificate unchanged.

The complete contracts are
`specs/K6_TWO_DISTINCT_ROW_SUPPORT_TRANSACTIONS.md` and
`specs/K6_MODEL_ONLY_MINIMAL_PAIR_SUPPORT_RECOVERY.md`.

## Historical observation-discovered partial-support H2 Gate (V0-068)

Contract `1.32.0` freezes executable profile
`observation_discovered_partial_support_campaign_v0`.

V0-068 removes exact target transition-support descriptors from the
operational planner. It retains symbolic states, complete legal-action
catalogues, the V0-066 relational state/action skeleton and a registered
finite H2 family, but receives dynamics only as replayable realized
transition tuples. For every state-action-time row, 64 discovery tuples
freeze the observed joint support; fresh validation at checkpoints
`2048/4096/8192/16384` estimates that support plus one explicit adversarial
`OTHER` event. A robust partial RAPM then plans and audits deterministic
contingent policies without an operational atom enumerator, support count,
spawn law or transition probability.

Each row epoch uses exact-rational uniform-Beta likelihood-mixture confidence
with tail `1/64000`. At most 512 distinct row-epoch authorities may be
considered, so the registered family guarantee is the Boole bound
`124/125`. Direct and quotient consumers of the same physical evidence
deduplicate statistically while retaining separate logical charges. The
checked-in SplitMix64 stream is deterministic replay infrastructure, not a
proof of IID randomness, so every positive remains strictly conditional:

```text
exact_iid_implementation_claimed = false
formal_exact_iid_plan_certificate = false
statistical_claim_scope =
  CONDITIONAL_ON_IDEALIZED_TARGET_LOCAL_UINT64_IID_AUTHORITY_
  NOT_PROVEN_BY_DETERMINISTIC_REPLAY_IMPLEMENTATION
```

The registered preliminary execution establishes the construction result but
not an observation-saving result:

```text
context                 direct route       quotient route
W5                      certify at 4096    certify at 4096
K6                      certify at 8192    certify at 16384
K6-minus-edge           exact fallback     exact fallback
```

At K6/8192 the base quotient and registered coordinate refinements fail. One
causally authorized support transaction promotes a single failed-frontier
row, uses 2,048 fresh promoted-row validation samples, builds seven new child
catalogues and 30 child rows at checkpoint 8,192, and charges 249,728
additional observer draws. The immutable replan still fails risk:

```text
failure upper           = 1321268563 / 17179869184 > 1/20
normalized regret upper = 1300423631 / 38654705664
status                  = FAILED_PROOF_FRONTIER
```

The runner preserves that failed epoch and continues; K6 quotient planning
certifies only at 16,384. K6 direct and quotient unique raw-observation totals
are `165120` and `578688`, respectively. Thus
`construction_gate_passed=true` and
`matched_observation_advantage=false`: this support repair narrows a real
missing-mass frontier but does not remove the unknown-support sample tax.

K6-minus-edge freezes `delta=2847/20000`, strictly between the exact ground
failure `2277/16000` and base quotient-lift failure `11393/80000`. Both
comparison lanes therefore emit no false partial-model certificate and use
the same complete-search, post-hoc-cap exact feasible fallback. Exact lift
and fallback work remain separately charged and cannot upgrade the
operational statistical claim.

Only complete same-implementation campaign replay—covering every considered
row, rejected candidate, promoted epoch, route freeze, exact lift/fallback
role and identity—has Gate authority. This is not independent-planner
verification, primitive/ontology invention, raw perception, exact-support
recovery, broad graph/domain generalization, changed-query reuse,
total-work economics or completion of the reusable hidden-world-model goal.
A later contract must authorize a distinct second support row or another
sample-tax operator; V0-068 permits no second promotion transaction.

All aggregate locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

The complete contract is in
`specs/OBSERVATION_DISCOVERED_PARTIAL_SUPPORT.md`.

## Historical target-local sequential sample-efficiency Gate (V0-067)

Contract `1.31.0` freezes campaign profile
`v0067_real_factorial_campaign_v0` and Gate profile
`v0067_v0066_graph_factorial_sample_efficiency_v0`.

V0-067 returns to the sample tax measured by V0-066 without weakening its
certificate. A uniform-Beta likelihood-mixture e-process supplies target-local
time-uniform confidence sequences at checkpoints
`2048/4096/8192/16384`; exact integer tests verify every dyadic outer
endpoint. The quotient and cold direct runners rebuild and audit the complete
registered H2 decision after each checkpoint and stop only at the first sound
plan certificate or the fail-closed cap.

The real `4+2` campaign contains four quotient cells
(`no-meta/meta × fixed/sequential`) on W5, K6 and K6-minus-edge, plus fixed
and sequential cold direct controls on W5/K6. Fixed and sequential streams
are seed-paired and raw-prefix verified; sequential runners generate only
the consumed prefix and never materialize then truncate the 131,072-draw
fixed row.

```text
quotient fixed, W5+K6       = 10747904 draws
quotient sequential, W5+K6  =   425984 draws
direct fixed, W5+K6         = 11796480 draws
direct sequential, W5+K6    =   737280 draws

quotient fixed, full family  = 18612224 draws
quotient sequential, family  =  1409024 draws
```

On the registered positive endpoint, sequential quotient planning uses
`311296` fewer target generative draws than matched sequential direct-ground
planning, a reduction of `19/45`. W5/K6 preserve normalized reward `3/64`, registered
risk and regret constraints. The Gate does not claim exact risk equality:
the W5 quotient lift is `1337/67500`, while cold direct risk is `99/5000`.
K6-minus-edge remains a real no-cover control and charges the same 60-row
exact feasible-plan fallback.

Eight deduplicated confidence authorities
(`1 quotient-fixed + 3 quotient-sequential + 2 direct-fixed + 2
direct-sequential`)—not sixteen cell labels—aggregate into four confidence
families and are combined without an independence assumption:

```text
joint tail upper       = 97/25000
joint confidence lower = 24903/25000
```

The source-only meta-prior is proposal-only. Its comparison/physical-unique
source-proxy costs are `5,451,776/5,242,880` draws, but meta and no-meta
target arms consume identical prefixes. Therefore the meta-prior has no
target main effect and no offline-inclusive amortization; the measured
saving belongs to the sequential target operator.

Frozen principal IDs are:

```text
source meta campaign  973a21dd8818510220091924eeeb3ed2fab7cace93b4efb3954f89bd2a878fed
source-prior evidence 1e38bda646e61421a378f7003be53deec389ae9ac9723ec007ae9521c7c5f722
pairing replay        50b8d3610eca69a0548fcf505015b152613891b6220c405a2a246ff6f8829005
counter subset        bc52d7a962ed760aa4a4714e0ef0773f01c2d5787bfb7d333960c5140349dac9
Gate result           fff9285c60a9691416227e81d857c7a389ddf732303688f024db77de65baf9d3
campaign              8074ae6583b85b9b69ce94aac35f64d1d96afcd51133383d3c9351228f6f1e5a
semantic verification e6d7be5ef451ab6bc5d711080cc5c132d1d7f51bc07798dc5c0c3fbbca66cc5a
```

Exact support-descriptor, fallback and standalone evaluation calls remain
separate `EXACT_KERNEL_QUERY` lanes and never enter the generative-draw
endpoint. Only the registered native evidence subset is reconciled; this is
not full counter completeness. The result is conditional on a pretrained source skeleton and
known exact symbolic support/reward/failure labels. Broad sample efficiency,
unknown-support learning, total-work/wall-clock savings, official execution,
scalar break-even, workload economics and counter completeness remain
locked. Full bundle verification is same-implementation semantic replay, not
an independently implemented planning algorithm. The complete contract is in
`specs/TARGET_LOCAL_SEQUENTIAL_SAMPLE_EFFICIENCY.md`.

The cache-filtered source selection is now 8,703,902 bytes, so the active
sealed-runtime and isolated-fallback source caps migrate from the historical
8 MiB profile to a content-bound 16 MiB V2 profile. V1 remains parseable;
old route uppers become stale and must be regenerated. This operational cap
migration changes no research endpoint or official/economics lock.

V0-068 subsequently weakens the exact symbolic-support oracle through
observation-frozen support plus an adversarial `OTHER` event. V0-067 remains
the historical known-support sequential control. A future meta-prior or
support-acquisition operator must show incremental target savings against
the same honest partial-support direct control.

## Current variable-cardinality two-domain relational RAPM Gate (V0-066)

Contract `1.30.0` freezes profile
`variable_cardinality_two_domain_relational_rapm_v0` and status
`CONDITIONAL_TWO_DOMAIN_VARIABLE_CARDINALITY_RAPM_CLOSED`.

V0-066 independently replays one source-only relational synthesis and exports
only a portable state/action AST skeleton:

```text
state  = cardinality_actions(legal_actions)
action = cardinality_resources(
           linked_filter(action_anchor, active_resources)
         )
```

The source constructor sees 120 anonymous rows but no target, query, kernel,
policy, dynamics, graph name, or domain identity. Its frozen human depth-two
grammar has 86 syntactic programs, 23 source-semantic representatives and 10
integer candidate pairs. The independent verifier shares no producer or
domain implementation. The exported skeleton contains no transition
probabilities, rewards, failures, policy or source decision.

Two isolated target consumers then use the same exact program IDs:

- the graph arm transfers from four-vertex source observations to held-out
  five- and six-vertex graphs. W5 acquires 22 local rows and synthesizes the
  target-local distinction `active_attribute_degree_signature`; K6 acquires
  60 rows and needs no refinement. Both produce complete H2 contingent plans
  with uniform distinct-action concretizers. A registered K6-minus-edge
  negative control acquires 60 rows, exhausts nine target-generated
  candidates without a sound cover, emits no false certificate, and invokes
  a charged 60-row exact fallback;
- the LMB arm uses a query-neutral seven-row bridge to bind the same anonymous
  action relation to `same_type_buffer_tokens`. Three target contexts each
  acquire two certificate-triggered statistical supports, for six supports
  and 98,304 target draws total, then certify a domain-specific symbolic H2
  policy. Operational exact ground rows remain zero; 13 exact rows belong
  only to standalone cold controls.

Graph construction uses 142 target-local rows and 18,612,224 draws, with no
complete target-closure call; the negative fallback is accounted separately.
The graph and LMB family tails are `287/250000` and `2/125`. Their Boole union
bound assumes no cross-arm independence and gives conditional joint
confidence `245713/250000`. Six executed wrong-arm evidence/model/campaign
transplants fail closed. Only the source log, portable skeleton and exact
state/action program IDs are shared; contexts, bindings, evidence, models and
dynamics remain disjoint.

Frozen principal IDs are:

```text
portable skeleton       77a9666172fb5cebf30820b12075fef92e190f3ccda6cdf44e4c902c7dc73322
graph campaign          8e839923dd2d965f6180fbff8abaebfbd6c5e9d6546cb60cb12666182bf7a77a
LMB campaign            baa37d57d60fb67c513e5655734e98d211e82ef278c1c0347bed864cf8a9f1d6
combined campaign       f71c28b83cff8854c406da85a97408d62480548568e15ca488e75bbfaca93c20
combined verification   f8e39e7822dc88477b246037eafd2ca6a2f48ff6c1e0af73580bb37c7affba41
```

This closes the registered construction Gate along both requested axes:
vertex count varies, and the shared relational skeleton is consumed in a
second domain. It does not prove automatic primitive/ontology invention,
generic model-selected planning, unconditional statistics, observational OOD
generalization, changed-query reuse, independent target verification or
sample efficiency. The LMB selector is domain-specific; both target
verifiers are same-implementation semantic replays. Official execution,
scalar cost, break-even, workload economics and counter completeness remain
locked. All 62 V0-066 focused tests and all 1,412 repository tests pass. The
full contract is in
`specs/VARIABLE_CARDINALITY_TWO_DOMAIN_RELATIONAL_RAPM.md`.

V0-067 subsequently tests that acquisition trace with a target-local
sequential operator and proposal-only source meta-prior. V0-066 remains the
historical cross-cardinality/two-domain construction Gate.

## Cross-geometry relational RAPM Gate (V0-065)

Contract `1.29.0` freezes profile
`observation_driven_cross_geometry_relational_rapm_v0`.

A complete 120-row H2 source log spans three pairwise non-isomorphic
four-vertex graphs: P4, star, and paw. Source-only bounded program closure
selects the legal-action-count state coordinate and occupied-neighbor-count
survivor coordinate. The proposal contains neither dynamics nor a policy.
The held-out target split contains three further non-isomorphic graphs:
C4, diamond, and K4; no source graph is isomorphic to a target graph.

Every target starts with an all-missing RAPM, acquires only failed-proof
authorized root and continuation rows, estimates probabilities only from
replayable target draws, and replans locally. The three context builds use
`48/60/72 = 180` target rows and `11,796,480` draws. C4 certifies under the
base coordinates. K4 builds its own statistical row for the
`legal-action-count=6` support key; that key already occurs among the source
base supports, but target action availability requires replanning to action
coordinate 2 rather than reuse of a fixed source schedule. Diamond first
fails closed under the base profile,
then a proof-triggered search over the source-frozen registry adds the
smallest certifying state/action distinction and constructs genuinely new
vector-valued support keys; no target program or primitive is invented. All
six occurrence-bound audits certify at
simultaneous confidence `3011/3125`, and occurrence-cold exact controls give
risk `99/5000`.

No-transfer routes use exact ground fallback without an abstract certificate.
A hidden-mechanism semantic OOD fixture and an unregistered topology both
fail closed, cross-structural evidence transplants are rejected, and a vertex
permutation preserves the relational support and mapped certificate. The
frozen campaign and same-implementation verification IDs are:

```text
campaign     2399c56dd7378429cc08dabb52d7bb76c61bc26f7541dccb535badfe193a7d7a
verification ea29a7e0c885166c1b321df24a53edc37975fe680f9bc97f4fa38288830ea329
```

This licenses observation-driven relational-schema transfer, target-local
statistical RAPM construction/replanning, and one certificate-triggered
coordinate recovery only inside the registered finite four-vertex
graph-merge family. It does not license broad graph generalization, a second
domain, raw perception, primitive invention, unknown outcome support,
cross-structural RAPM reuse, independent-algorithm verification, sample
efficiency, official execution, or scalar economics. All 33 V0-065 focused
tests and all 1,350 repository tests pass. The full contract is in
`specs/CROSS_GEOMETRY_RELATIONAL_RAPM.md`.

V0-066 subsequently closes both of those follow-up axes under its narrower
portable-role contract. V0-065 remains the historical four-vertex Gate.

## Observation-driven relational support Gate (V0-064)

Contract `1.28.0` freezes profile
`g2048_observation_driven_relational_support_v0`.

From 144 complete, anonymous, source-only H2 rows, a bounded relational DSL closes
to 56 semantic programs and exhausts 432 state/action-coordinate candidates. It
selects the number of legal actions and the number of occupied neighbors of the
chosen survivor, producing six anonymous support templates without D4
canonicalization, relative-survivor labels, or named `ROOT`/`CHAIN` rows.

Three structurally identity-disjoint held-out rank-relative contexts start with
all-missing partial statistical RAPMs. In each context a failed model proof
authorizes eight root rows, observed successors expose two continuation supports,
and a second failed proof authorizes sixteen continuation rows. The resulting
context-local model certifies two registered point queries with no query-local
ground work after the 24-row context build. Target probabilities come only from
replayable draws; known symbolic outcome support is still registered. Family
confidence is `239/250`. A wrong proposal fails closed, and six cold exact-ground
controls reproduce J0.

This advances automatic hidden-coordinate/support construction only inside a fixed
human relational vocabulary, fixed 2x2 graph, and finite structural family.
Primitive invention, unknown support, unseen graph geometry, cross-structural model
reuse, independent-algorithm verification, broad generalization, sample efficiency,
official execution, and scalar economics remain open. The full contract and frozen
IDs are in `specs/OBSERVATION_DRIVEN_RELATIONAL_SUPPORT.md`.

## Sequential source-stopping Gate (V0-063)

Contract `1.27.0` freezes profile
`g2048_preregistered_sequential_source_stopping_v0`.

V0-063 preserves the complete V0-062 target certificate and V0-061
no-operator/cold-direct controls, but preregisters ordered source checkpoints.
One 4,096-draw block is acquired for each of the three frontier rows in a
source context. The first checkpoint must continue; the second uniquely and
unanimously freezes `ROOT_TOWARD + CHAIN_A_AWAY`; the third source context is
never enumerated.

```text
V0-062 fixed source draws       = 147456
V0-063 stopped source draws     =  24576
unchanged operator target       =  98304
source + target                 = 122880
unchanged no-operator target    = 147456
registered saving               =  24576 = 1/6
```

The source guard only controls stopping and has no confidence-certificate
authority. Target certificates remain target-only at confidence `347/350`.
The wrong prior still fails in all three contexts before three explicit tail
fallbacks and emits zero false certificates.

This is an offline-inclusive reduction only on the registered finite
known-D4 family. It is not broad sample efficiency, automatic
coordinate/support discovery, official execution, or scalar economics.
V0-064 subsequently executes the observation-driven coordinate/support
construction Gate under its separate claim boundary. The V0-063 contract is in
`specs/SEQUENTIAL_SOURCE_STOPPING.md`.

## Source-frozen sample-tax intervention Gate (V0-062)

Contract `1.26.0` freezes profile
`g2048_source_frozen_boundary_capability_operator_v0`.

Three target-disjoint source contexts contribute 147,456 offline-source
generative-oracle samples. A source-only exhaustive boundary-capability check uniquely
proposes `ROOT_TOWARD + CHAIN_A_AWAY`, with `CHAIN_B_AWAY` retained as a
broad tail. The unchanged V0-061 contexts and six H2 occurrences remain
held out; production exposes only the proposed two target rows per context
and certifies from target observations alone. All five evidence-event classes
are explicit; source/operator interaction, logged-observation, and synthetic
rollout counters are native zero.

```text
operator target rows / draws    = 6 / 98304
no-operator target rows / draws = 9 / 147456
target-online reduction         = 49152 = 1/3
cold-direct rows / draws        = 198 / 4866048
```

A registered wrong proposal fails all three target proofs, acquires exactly
one tail row per context, and emits zero false certificates. The source prior
can change work but cannot narrow target bounds or authorize a plan.

Offline cost is not hidden: source plus target is 245,760 observations, so
this finite campaign does not show offline-inclusive or broad sample
efficiency. Official execution, scalar/break-even economics, automatic
coordinate/support discovery, and aggregate Gates remain locked. The full
contract is in `specs/SAMPLE_TAX_INTERVENTION.md`.

## Matched end-to-end acquisition Gate (V0-061)

Contract `1.25.0` freezes profile
`g2048_matched_adaptive_vs_cold_direct_ground_v0`.

V0-061 keeps V0-060's three safe-chain contexts and six point/uniform H2
queries, but replaces its all-six-row abstract control with a genuine cold
direct-ground statistical planner. The adaptive route first freezes a failed
proof, samples only nine certificate-required abstract rows, builds three
honest `3 observed / 3 missing` partial RAPMs, and reuses each model once.
The direct route independently enumerates and samples the complete reachable
ground state-action graph for every occurrence, plans a deterministic ground
policy, certifies it, and discards the occurrence-local model.

```text
adaptive rows / draws / model reuses = 9 / 147456 / 3
direct rows / draws / model reuses   = 198 / 4866048 / 0
registered direct/adaptive draw ratio = 33
```

Both routes use error radius `1/64`. Joint exact-rational family accounting
binds 18 adaptive and 252 direct obligations, giving confidence lower
`42967/43750`. Production planning receives no kernel or transition
probabilities. Standalone evaluation independently replays all 5,013,504
observations, all 198 ground rows, both selected routes, and six exact J0
problems.

The 33× result is restricted to this registered workload and its known human
D4 prior. It is not automatic hidden-coordinate/support discovery, broad
sample efficiency, or by itself a sample-tax-reduction operator. V0-062 now
uses it as the unchanged no-operator/cold-direct control; official execution,
scalar/break-even economics, and broad generalization remain later Gates.
The full V0-061 contract is in
`specs/MATCHED_END_TO_END_ACQUISITION_WORKLOAD.md`.

The current repository Gate contains 1,412 tests in 115 modules. For fast
development, `scripts/run_pytest_parallel.py` runs modules concurrently and
memoizes only repeated content-ID reads on the identical frozen object;
mutation-attack modules automatically use fresh IDs. The formal release path
still recomputes every ID:

```bash
# exact parallel development lane
PYTHONDONTWRITEBYTECODE=1 \
python3 scripts/run_pytest_parallel.py -j 4 tests

# formal fresh lane
PYTHONDONTWRITEBYTECODE=1 \
python3 scripts/run_pytest_parallel.py --fresh-ids -j 4 tests
```

Six-node sharding reduced the compatible full-suite critical path from
16–19 minutes to 208.1 seconds without dropping a test, sample, exact
fraction, oracle replay, or attack. Execution details are in
`specs/TEST_EXECUTION.md`.

## Raw replayable multi-context acquisition Gate (V0-060)

Contract `1.24.0` freezes profiles
`g2048_raw_replayable_multicontext_partial_statistical_v0` and
`g2048_certificate_directed_vs_uniform_acquisition_v0`. All 14 focused tests
and all 1,256 repository tests pass.

V0-060 replaces the V0-059 trusted aggregate G2048 ledger with a compact trace
of every stochastic outcome. It registers three separately keyed safe-chain
spawn-law contexts (`P(rank 1)=199/200, 249/250, 999/1000`) without modifying
the canonical `99/100` fixture. In each context an all-missing partial RAPM
first fails its H2 risk proof. That proof authorizes exactly
`ROOT_TOWARD`, `CHAIN_A_AWAY`, and `CHAIN_B_AWAY`; the adaptive lane samples
only those three rows, while the other three legal rows remain explicit
vacuous `[0,1]` uncertainty. An independent control samples all six rows.

Each observed row contains 16,384 counter-based draws packed one exact
ground-outcome index per nibble. The model builder and production planner have
no kernel input and receive no exact probabilities. Exact-rational Hoeffding
calibration freezes radius `1/64`, 54 simultaneous obligations, family tail
`27/700`, and confidence lower `673/700`. Both lanes select
`TOWARD, AWAY, AWAY`, certify reward `3/64`, risk below `1/20`, and zero
regret. A second preregistered query per context reuses the immutable model
with zero new draws.

```text
adaptive rows/draws/missing rows  = 9 / 147456 / 9
direct-control rows/draws          = 18 / 294912
within-context zero-draw reuses    = 3
cross-context model reuses         = 0
```

The standalone evaluation verifier independently replays all `442,368`
individual draws and runs three unrestricted exact J0 controls. Their
failure probabilities are `199/20000`, `249/31250`, and `999/500000`;
each lies inside both statistical certificates. Exact replay does not promote
the production evidence to `exact_sound`.

The direct arm is a uniform all-six-row statistical control, not a matched
direct-ground planner. Consequently the observed `147,456`-draw difference
is not a sample-efficiency or sample-tax-operator claim. Automatic `D4` or
coordinate discovery, broad structural generalization, complete accounting,
official execution, scalar cost, and economics remain locked. The full
contract is in
`specs/RAW_MULTICONTEXT_ACQUISITION_CONTROL.md`.

## Current multi-domain observed/statistical held-out Gate (V0-059)

Contract `1.23.0` freezes profiles
`multidomain_observed_statistical_heldout_campaign_v0` and
`g2048_d4_empirical_hoeffding_partial_rapm_v0`. All 15 registered focused
tests and all 1242 repository tests pass.

The preregistered 12-occurrence campaign composes two deliberately different
world-model authorities. LMB retains the V0-058 observation-driven program
closure and honest partial RAPM: the first strict H2 occurrence acquires
exactly three certificate-authorized target rows, and two later occurrences
perform fresh model-only planning/audit with zero additional ground rows.
G2048 uses the known exact `D4` structural quotient as a registered human
prior, but obtains all six binary transition rows only from a frozen
393,216-sample offline aggregate ledger. An exact-rational Hoeffding/union
proof gives radius `1/128` and simultaneous confidence at least `347/350`.

The robust statistical planner enumerates all eight deterministic H2 semantic
policies and selects `TOWARD, AWAY, AWAY`, with:

```text
reward                    = [3/64, 3/64]
failure                   = [9277983,75716127] / 2147483648
risk threshold            = 1/20
normalized regret upper   = 0
G2048 online samples      = 0
```

Eight `D4` point occurrences and one orbit-uniform occurrence reuse that
model. The production campaign has no G2048 kernel input. A standalone
evaluation-only exact quotient replay confirms value `3/64` and failure
`99/5000` lie inside the statistical certificate without promoting it to
`exact_sound`.

Principal identities include:

```text
g2048_catalogue_id          = 1c97e476c25b0a1f0f37ce2796ae4cf9bb138bf29dbd80271792e2ef988dbcb1
g2048_sample_ledger_id      = 07793df8d27bacbd68f40b878c8de8483d03c22b6e323d5477dce06806154f7e
g2048_statistical_model_id  = 78a3ed52d6d7284d8690708b2177b962c6cffbd33064925efe66f6fa1f520d9d
campaign_preregistration_id = a15ffeb13b9890b720def2e0029ea72e870c3cd855dc3efcab132e915e9de3ce
campaign_result_id          = e536ace0665fc7c01fb6d79a025a17eba4adb1d3950cfe14e7a627cfc6886c78
campaign_verification_id    = 49e7662ce463d4640fdc9cb8cf8aa0fec5dde1c92b49a83f10e6ab2cfd335719
```

The full contract is in
`specs/MULTIDOMAIN_STATISTICAL_HELDOUT_CAMPAIGN.md`. V0-059 does not claim
automatic `D4` discovery, shared cross-domain coordinates, raw symbolization,
exact-sound statistical dynamics, broad structural generalization or sample
savings. Its 393,216 logged samples are the first explicit statistical sample
tax in the mainline; a Laplace-style heuristic operator or KG-OP meta-prior
will be evaluated only after richer independently replayable acquisition
traces exist.

## Current observation-driven program-closure and held-out H2 Gate (V0-058)

Contract `1.22.0` freezes profiles
`lmb_observed_program_closure_partial_rapm_v0` and
`lmb_observed_program_closure_heldout_h2_v0`. All 19 registered tests pass.
Starting only from the preregistered `8 state / 11 row / 7 observed` symbolic
source graph, the constructor performs a bottom-up depth-two closure over the
frozen human primitive/operator vocabulary, retains 215 type-tagged semantic
program representatives, and exhausts the complete bounded
`(174+1)*(37+1)=6650` state/action-coordinate search. It selects

```text
state  = cardinality(legal_actions)
action = buffer_at_type(buffer_counts, selected_tile_type) <= 3/2
```

and builds an honest `7 observed / 4 missing` partial RAPM. This is automatic
program composition and selection inside the frozen vocabulary; it is not
primitive/operator invention, raw symbolization or learned dynamics.

The separately preregistered target `removed_mask=35, buffer=(2,1), H=2` is
absent from the source log. Its first query epoch keeps all three target rows
vacuous, so model-only planning and a role-distinct selected audit fail
soundly at reward `[0,4]`, failure `[0,1]`. That certificate failure
authorizes exactly the target's three rows. One safe row reaches an
already-registered source successor whose second-step dynamics are reused;
the other two rows fail. No successor catalogue or successor transition is
queried. The immutable final epoch is `10 observed / 4 missing`, replans
inside the model and certifies reward/failure/regret `1/0/0`.

Principal identities include:

```text
program_registry_id     = 1331c29c9f23390b296d3be3777b99cda7eba915755bbd7d92808b411df1a9b0
candidate_trace_id      = a2addf7fc8a78889793d0fa381041e9e12f41e010d51f21580040108e938281a
synthesis_result_id     = f4b4904a5d1944e97dcf4dfc8e2fd7620b74dedf32f60ee2dd94e41f7b22666f
preregistration_id      = 3389cec70655a35e69a606c2ef72daca00c5c6362f780fe78bb4218911d3dcd5
initial_epoch_id        = 027abab818aae2bd0469f5ab4f45197457bcc08a66700c434a87799a708f40f1
authorization_id       = b30d795691a056c08ead4a003e187d7b57ed8ad2829f73c5a4a2c190065614aa
final_epoch_id          = b835afe210574787aa668640d12500d7829268c1d041e521defdaaa687792efe
heldout_result_id       = f70cbc1c48645c071ab842c0ec328d22157a61458b72a17933daf82e9ae7efdd
```

The full chronology, identities, attacks and claim locks are in
`specs/OBSERVATION_DRIVEN_PROGRAM_CLOSURE_HELDOUT_H2.md`. V0-058 does not
claim unknown-vocabulary invention, statistical/learned dynamics, broad
held-out or cross-domain generalization, sample reduction, economics or
official execution. Its two construction modules bring the complete staged
Python package to about 6.5 MiB, so the content-addressed isolated-fallback
runtime-source ceiling migrates from 6 MiB to the independently frozen 8 MiB
sealed-manifest ceiling; actual bytes are still charged exactly and old route
uppers become stale through the changed profile ID.

## Historical interleaved certificate-triggered durable H2 epoch Gate (V0-057)

Contract `1.21.0`, schema `1.0.0`, and profile
`lmb_h2_interleaved_certificate_triggered_durable_epoch_v0` now freeze the
next mainline construction Gate. All 85 registered positive, attack,
deterministic-replay and fresh-store evaluation tests pass, so the Gate emits
`CERTIFIED_REGISTERED_H2_INTERLEAVED_CERTIFICATE_TRIGGERED_DURABLE_EPOCH_CONTROL`.
Its canonical principal identities are:

```text
orchestrator_sha256      = 9808009f3e9aa2c444466799679e80772a444e69f49ede632f09a0153f8ea419
result_id                = 092c92708f67a2b0044abce792a96e9afed5cda56a017d1b99063433861ce01c
verification_id          = 6330a3a6be2b4a3e1365f8cf62cc8c4dec6ad02b80c7aba5fd65e64c4f28e9d9
campaign_snapshot_id     = 4add6d49870f37692622db051b56b830158e30ab9cf0dbe65140c44718e02553
preregistration_id       = 530e7c76f29c7590826abacb44e13cf3559481ae7f21b54c68a166a24fb57435
source_chain_id          = a070baa803adf19a435fbcc558016b2a729313b5cfd06776c309f5e35a5b8f45
authorization_id         = 09aecbb5df77b7d102928f0f1a3c4bd1ced8bf33f9218ed4a58ed336eed998ef
accounting_id            = dce0c871d4f2ebecfba185e39d8097737cd850541f6bcbbfa38f28c355981a5a
event_log_id             = 6b0de30820c6460a783e558ed514b37499087c14d7d73505e76cb4b9d231a21d
C1_payload_id            = 2fb3897106fff1387ebe6f3edb5618c88fe597e0e952b1531805da3db359fc3e
C1_commit_id             = 0272231a20d8162882fdf309c008c19fb3e3265f4d10bc2df918c9ec11430737
C2_payload_id            = d81d33a52705488ab9944c2911222f54b2a773f26ba2decf5bb4ad53eb4b2a49
C2_commit_id             = 2164daa10ae031ab4b36e0f3602c0d015430befca256ee13c8bde2899b066e29
first_facet_tip_id       = adea7a973cfaa2bc3a5e671b82417c04dcaed942a521dd97b8d6e9aa830aad66
final_facet_tip_id       = 1c135cd185268051e992191628a7f9788079c01ebb5169db43ad96f3d5d919cf
```

The registered workload starts from the authentic V0-047 first query-local
V3 epoch, not a caller-supplied completed result:

```text
live first epoch = 11 observed / 9 missing
query order      = Q_R,Q_S,Q_R,Q_S,Q_R
Q_R              = regret tolerance 3/4, risk tolerance 1
Q_S              = original strict tolerances 0,0
```

Before campaign-root creation or source ground access, the preregistration
binds the exact eight input-authority identities (including the kernel
digest), the base structural/environment/model/coordinate scope, complete
semantics profile, state/action realizations and concretizer rows, H2
initial/reward/return/goal formulas, policy class, candidate order and proof
registry. It explicitly says `derived_source_artifact_ids_absent=true`: no
prospective first/final V3 model, checkpoint, source-chain or result ID is
smuggled into this pre-source scope.

Q_R uses a new epoch-bound typed query because `(3/4,1)` is outside the
historical V0-043 threshold registry; that registry remains byte-for-byte
unchanged. Q_R must independently derive its formula result and certifies the
first epoch with zero additional query-triggered ground access. Only the
subsequent selected Q_S failed proof may authorize the exact nine V0-047
round-two rows. Those rows freeze the immutable final `20/0` V3 epoch, after
which Q_S replans and certifies and all later queries remain model-only. The
first Q_S proof fails value/risk while
`external_coverage_failed=false` and
`external_coverage_certified=true`; coverage is not its failure reason.

C1/C2 retain the authentic strict-Q_S lower-proof core: 30 active nodes per
epoch, including the real strict E/F gate nodes. Q_S roots consume and replay
those nodes directly. Only Q_R uses a separate epoch-bound overlay of eight
relaxed E/F variants. Every such facet binds the preregistration, eligibility,
Q_R query, epoch/model, metric and exact source-D parent. Candidate and
independently selected roots also carry distinct proof requests bound to
role, occurrence, model, epoch, evidence request, metric and proposal where
applicable. The nine-row model change invalidates 28 unique strict
lower nodes and reuses only the two extensional C0 nodes; C2 therefore has a
58-node union with 30 active and 28 historical nodes, and no persisted roots.
Both epochs still select semantic schedule `A0A0`, so this is deliberately
not a semantic-policy-switch claim.

C1 and C2 are separate checkpoint stores. C2's predecessor is a cross-store
lineage pointer to an externally verified C1 commit, not a traversable commit
inside C2. The C2 loader independently opens C1 and requires C2's exact
historical set and complete retained records to equal C1 active minus the two
shared C0 nodes; final workers snapshot C1, C2 and their facet store.
Likewise, `facets-c1` and `facets-c2` are separate epoch-local
append-only chains, each with its own W0/genesis; the first tip is never the
final genesis's predecessor.

Five logical occurrences each resolve 50 lower obligations. The registered
append-only query-facet trace is:

```text
8/42, 0/50, 8/42, 0/50, 0/50
total = 16 query-facet builders / 234 exact lower hits
```

Occurrence 2 also performs a fresh final-epoch proof execution after the
strict failure and nine-row repair. The five-occurrence projection uses that
recertified result as occurrence 2's closure; the failed first attempt remains
native certificate-triggering work and is not a logical closure entry. Its
`28 new / 2 reused` core update is also recorded separately. Native accounting
retains both occurrence-2 workers:

```text
main six workers  = 16 builders / 284 hits / 30 roots
reset six workers = 24 builders / 276 hits / 30 roots
operational total = 12 launches / 40 builders / 560 hits / 60 roots
logical projections = main 16/234; reset 24/226
```

The selected failure freezes `3 selected-risk / 9 unrestricted-value /
9 distinct requested` rows; the exact nine acquired outcomes are `3 safe /
6 terminal failure`. Operational host accounting additionally replays the
seven registered counters:

```text
checkpoint loads / cross-store checks / facet loads = 23 / 9 / 36
worker result comparisons / snapshot hashes         = 12 / 64
immutability comparisons / semantic assertions      = 32 / 12
```

The campaign also freezes 23 owner-bound, monotonically sequenced live events.
A fresh-store verifier replays both arms with the same implementation in a
separate evaluation lane, launching another 12 workers; it explicitly reports
`same_implementation_full_replay=true` and `independent_algorithm=false`.
Its evaluation-prefixed host counters reproduce the same
`23/9/36/12/64/32/12` vector and remain outside operational work.
These are operation-family identities, not samples or complete work.
Recorded bytes cover query/occurrence inputs, worker result outputs and
serialized checkpoint/facet footprint only; they are not cumulative I/O
traffic or a complete counter registry.

Literal source pins live in
`src/acfqp/h2_interleaved_durable_epoch_pins_v1.py`: they bind the complete
orchestrator bytes and registered upstream module/callable sources before host
root/ground access and before worker checkpoint/query reads. The pins module
does not self-hash or derive pins at runtime.

The positive API boundary is a process-local runtime-minted claimed-result
handle plus durable campaign bytes. Copying or deserializing the wrapper does
not mint semantic authority. The fresh verifier validates that live handle
and the durable snapshot, then performs the second clean producer execution
in a fresh store under the identical frozen literal source-pin set. The
evidence is exactly one operational producer execution plus one fresh
same-implementation evaluation replay; no third campaign is required. This
is not a generic cross-process final-wrapper parser or independent algorithm.

The exact contract, required attacks and claim locks are in
`specs/H2_INTERLEAVED_DURABLE_EPOCH.md`. Both V3 epochs remain query-local,
nonpromotable and not globally transition-closed. No sample-efficiency,
byte/CPU/wall/total-work, economics, generic changed-model/query, H>2,
generalization, learned-dynamics or official-execution claim is opened. The
result carries only its implemented closed claim fields; generic reuse/H>2,
independent-verifier, scalar and Gate statements remain ledger-level locks,
not invented result fields.

## Historical preregistered durable H2 multi-query workload (V0-056)

Contract `1.20.0`, schema `1.0.0`, and profile
`lmb_h2_preregistered_durable_multiquery_workload_v0` extend V0-055 from one
durable recovery occurrence to a frozen ten-occurrence H2 workload. Before
the V0-055 source producer runs, the protocol freezes three threshold-only
queries:

```text
Q1 = (normalized regret tolerance 0,   risk tolerance 0)
Q2 = (normalized regret tolerance 3/4, risk tolerance 0)
Q3 = (normalized regret tolerance 0,   risk tolerance 1)

occurrence order = 1,2,3,1,2,3,1,2,3,1
```

The implementation Gate, 21 registered attack cases and fresh-store
evaluation replay pass, so status
`CERTIFIED_REGISTERED_H2_PREREGISTERED_DURABLE_MULTIQUERY_WORKLOAD_CONTROL`
is emitted. The principal canonical pins are campaign `8edf8a660fe3...`,
evaluation `48e8919a0899...`, protocol `928b8233021b...`, proof semantics
`5880e0a9a4d7...`, preregistration `2cde4f37b9e7...`, and W0/W1/W2
`4e9deaec2baf...` / `8d15aae30b49...` / `8e33d23a1369...`. The matched and
reset-initialization ID vectors are `f8fe8f4dd584...` and
`20339c4e312e...`. Full artifact IDs and literal code/source hashes are frozen in
`specs/H2_DURABLE_MULTIQUERY_WORKLOAD.md` and
`src/acfqp/h2_durable_multiquery_workload_pins_v1.py`.

The source API remains target blind. It runs the exact V0-055 Q1 path:
C1's `4 observed / 1 missing` model selects N but fails the regret
certificate, after which one source-pinned M ground row is authorized and C2
is frozen as `5/0`, reward 1, risk/regret zero and certified M. Only then may
the ten target occurrences begin.

W0 is not an ID-only cache. It carries the canonical 21,983-byte semantic
projection of all 18 active C2 lower-node documents, pinned by SHA-256
`b122d4ec7d98b723717a0f547c693516aa74c64ce8e8e5051318063ce9a15a55`.
Fresh model-only target processes parse the typed result fields and parent
topology. Regret and risk gates are computed from U0/plan values and only
their consumed threshold facets; selection is derived after those gates and
binds their result node IDs. Candidate audits, proposal, three fresh roots and
the final certificate are formula-derived from the resolved 18-node map,
never supplied by query/address answer tables.

The persistent target-facet arm performs:

```text
Q1: 0 lower builders / 18 exact hits
first Q2: 3 / 15, appending two regret gates + selection
first Q3: 3 / 15, appending two risk gates + selection
all seven later occurrences: 0 / 18

global total = 6 builders / 174 hits / 30 fresh roots
W0 / W1 / W2 logical lower counts = 18 / 21 / 24
target ground calls = 0
```

A matched C2 base-reset arm discards query facets after every occurrence and
therefore records `18 builders / 162 hits / 30 fresh roots`. It nevertheless
performs and retains ten typed W0 initializations, one per reset occurrence,
and records each initializer's projection/checkpoint read and W0 output bytes
plus worker-reported store bytes. These are scoped observed bytes:
`query_store_io_complete=false` because host before/after/final lease and
snapshot reads plus verification rereads remain incomplete. The `18/162/30`
tuple does not include or erase that I/O and supports no byte- or
total-work-saving claim. A separate
source-blind trusted literal comparator starts from the source-independent
four-row offline projection proved equal to V0-055 C1, but reacquires the
missing M row independently for every occurrence. Its dynamic one-call guard
and recorder produce exactly ten
ground transitions, ten complete catalogues, 40 policy evaluations and ten
optimizer calls. Every paired route selects M and returns reward/failure/
regret `1/0/0`.

These are operation-family call traces, not samples or a complete
`CounterRegistryV1`/WorkVector. No scalar combines proof calls, ground calls,
processes or bytes; no official break-even or total-work ordering is emitted.
The projection is valid only for the registered threshold-only Q1/Q2/Q3
family: its input slices remain opaque, so reward-basis, horizon, action,
dynamics, initial-support or structural changes are not authorized.

V0-056 proves only finite source-before-target reuse of one actual C2
semantic world-model/proof state, exact facet-local
changed-query derivation, cross-process lookup-before-builder avoidance and a
matched conditional-online direct control. It does not prove generic
cross-query or H>2 reuse, statistical generalization, coordinate invention,
partial/learned dynamics, independent-algorithm verification, sample efficiency, or
byte/CPU/wall-clock/total-work savings. Official execution remains false;
official scalar cost and break-even remain null; workload-economics,
counter-completeness and sample-efficiency Gates remain `NOT_RUN`. Full
semantics and attacks are in
`specs/H2_DURABLE_MULTIQUERY_WORKLOAD.md`.

V0-057 now freezes that next construction Gate: it connects the authentic
V0-047 `11/9 -> 20/0` query-local model-epoch change to exact durable
invalidation, replanning/recertification and later interleaved reuse. Its
implementation and evaluation pass all 85 registered tests; the status and
canonical principal identities above are frozen. V0-058 now advances the
construction mainline from a fixed handwritten coordinate catalogue to
complete bounded program closure and applies the selected coordinate to a
source-log-held-out H2 query before certificate-triggered three-row recovery.
V0-059 composes that path with a finite known-D4 G2048 statistical model and
a twelve-occurrence two-domain workload, exposing a 393,216-sample offline
tax while keeping production kernel-free. The next Gate requires raw/
replayable stochastic logs across multiple structural contexts. A
Laplace-style heuristic operator, offline/online meta-prior or other
sample-tax intervention remains a later, separately preregistered control
informed by those richer traces.

## Historical durable action-local H2 recovery slice (V0-055)

Contract `1.19.0`, schema `1.0.0`, and profile
`lmb_h2_two_generation_durable_action_local_recovery_v0` compose the
V0-054B strict one-row switch with two generations of durable, root-free H2
lower-proof state. This remains a registered seed-4 H2 construction control:
the proof DAG is machinery for keeping planning and recertification inside the
reusable model, not the scientific endpoint.

The binding order is:

```text
C1: first 4/1 model + 18 typed lower nodes + 0 roots
-> P1 fresh model-only process: load/reuse 18, recompute 0, build 3 fresh roots
-> host verifies the failed N proof
-> authorize and execute the source-pinned V0-054B M row
-> freeze its detached immutable overlay projection
-> P2 fresh model-only process: restore/reuse 18, then compute/reuse 10/8
-> certify the strict N -> M switch
-> C2: 28 typed lower-node union, 18 active + 10 historical + 0 roots
-> P3 fresh model-only process: load/reuse 18, recompute 0, build 3 fresh roots
```

Both checkpoints are canonical, externally selected, immutable and root-free.
Their node documents are parsed back into strict typed proof nodes rather than
treated as opaque cache values. Complete plan/request/role-bound roots are
always reconstructed in the consuming process. P1 and P3 therefore each
record operational lower-proof consumption as `0 recomputed / 18
loaded-reused + 3 fresh roots`; P2 records the successor computation as
`10 recomputed / 8 reused + 3 fresh roots`.

No ground access is permitted before the host has verified P1's failed proof.
The exact source-pinned V0-054B runner then performs the sole operational
ground transition, the registered `(x1,M)` row. P1, P2 and P3 are three fresh
model-only processes and each records zero ground transitions. Detached row
and overlay bytes preserve provenance but cannot mint or replace the live
ground authority. The resulting final model and certificate retain the strict
semantic change from `A0A0/N`, reward 0 and failed regret, to `A0A1/M`,
reward 1 and certified risk/regret zero.

The counts above are scoped proof-runtime telemetry. In particular, the 18
semantic validation obligations needed to accept a checkpoint are not
relabelled as 18 native physical computations, and this contract does not
claim native-compute completeness. Its verifier performs a separate
same-implementation evaluation replay with one evaluation-lane ground call
and three evaluation-lane process launches; it is not an independent
algorithm.

V0-055 proves only this registered H2 durable recovery composition. It does
not prove generic durable or crash-safe persistence, hostile-worker security,
cross-query reuse, generic `H>1` or `H>2`, generic action-local minimality,
automatic coordinate invention, partial/learned dynamics, or sample,
byte/CPU/wall-clock/total-work savings. Official execution stays false;
official scalar cost and break-even remain null; workload-economics,
counter-completeness and sample-efficiency Gates remain `NOT_RUN`. Full
semantics and attacks are in
`specs/H2_DURABLE_ACTION_LOCAL_RECOVERY.md`.

V0-056 now consumes this historical C2 control in a preregistered matched
multi-occurrence/multi-query workload. V0-055 remains the source and
durability prerequisite; its artifacts and narrow claims are not rewritten.

## Historical one-row action-local H2 semantic-switch slice (V0-054B)

Contract `1.18.0`, schema `1.0.0`, and profile
`lmb_h2_action_local_semantic_switch_v0` register a six-tile seed-4 LMB
control whose first query-local model contains four exact rows and one missing
off-policy challenger row. The pure proof subprofile
`lmb_h2_action_indexed_semantic_switch_v0` contains an explicit 18-node H2
lower DAG and imports no ground kernel.

The first epoch is built without a transition call:

```text
x0 --S/tile4,reward0--> x1
x1 --N={tile1,tile2,tile3},reward0--> horizon
x1 --M=tile0--> missing
coverage = 4 observed / 1 missing
```

Model-only planning selects reachable schedule `A0A0/N`. Its failure upper is
zero, but the complete action catalogue leaves `M` as the unique missing
unrestricted H1 maximizer. The unrestricted H2 upper is 3, so normalized
regret is `3/4` and the plan is not certified. The ordinary selected-policy
support frontier contains only `S` and the three `N` rows and is explicitly
non-authorizing.

The new `UnrestrictedChallengerFrontierV1` follows the failed `REGRET_N`
proof circuit through `U0`, `U1`, `Q_M`, and `ROW_M`. It is also
non-authorizing. A separate one-row necessity proof and content-addressed
request must be frozen before the single-use authority can call the exact
registered `(x1,tile0)` transition. Exactly one row is acquired; the first
model remains byte-for-byte unchanged and the successor epoch is `5/0`.

The action-indexed DAG then derives the actual reverse-edge invalidation cone:

```text
first lower DAG: 18 computes / 0 hits + 3 fresh roots = 21 computes
final lower DAG: 10 computes / 8 hits + 3 fresh roots = 13 computes
affected:   ROW_M,Q_M,U1,U0,PLAN_M,REGRET_N,REGRET_M,
            RISK_M,COVERAGE_M,SELECTION
unaffected: ROW_S,ROW_N1,ROW_N2,ROW_N3,Q_N,PLAN_N,RISK_N,COVERAGE_N
```

Each submitted epoch graph is independently replayed from its exact
model/query and compared across all 18 nodes, audits, roots and proposal; a
fully re-signed but semantically false graph is rejected. The one permitted
kernel call likewise goes through a source-pinned gate entry and a guard that
closes directly over the canonical step.

All three complete roots are rebuilt in both epochs. The final exact row has
reward 1 and risk 0, so replanning switches strictly from `A0A0/N` with value
0 to `A0A1/M` with value 1; normalized regret becomes zero and the final
candidate is certified. This is a numeric policy improvement, not a
tie-breaking label change.

V0-054B proves only this registered action-local closed loop. Its evaluation
verifier is same-implementation deterministic replay, not an independent
algorithm. Generic causal minimality, generic `H>1`, durable/cross-query reuse,
automatic coordinate invention, partial/learned dynamics, sample,
byte/CPU/wall-clock/total-work savings, workload economics, and official
execution remain locked; `official_N_break_even` remains null. Full semantics
and attacks are in
`specs/H2_ACTION_LOCAL_SEMANTIC_SWITCH.md`.

V0-055 now composes this strict semantic switch with two root-free durable
lower-proof generations. V0-054B itself remains the historical live,
nonpersistent one-row control.

## Historical same-query durable H2 proof-state slice (V0-054A)

Contract `1.17.0`, schema `1.0.0`, and profile
`lmb_h2_same_query_durable_proof_state_v0` carry the exact V0-053 final-epoch
lower proof DAG into two fresh Python processes. The producer consumes only the
owner-bound V0-053 result, reconstructs its final model-only workload, and commits
exactly 30 lower nodes:

```text
U1,U0,P1,P0,C0,C1,D,E,F,G = 30 entries
R = 0 persisted entries
```

The store has no mutable `HEAD`; an external commit ID binds canonical payload,
manifest and commit bytes. Each loader replays the four model-derived candidate
requests (`44 = 34 computes + 10 hits`) and requires the recomputed 30-node
payload and four candidate-audit identities to match exactly before seeding a
cache.

Two separately launched `python -I -s -B` workers each run request-reset,
occurrence-reset and durable arms:

```text
two-occurrence request reset       = 110 / 0
two-occurrence occurrence reset    =  70 / 40
two-occurrence durable continuation = 10 / 100
```

Every durable request constructs a fresh occurrence-/role-bound `R`; all ten
lower resolutions hit. Thus 60 lower constructions are avoided inside the two
worker executions relative to occurrence-reset. This is deliberately not called
a total-work or sample saving: checkpoint construction, loader replay, process
and I/O work, and trusted parent validation remain real work.

Worker output is untrusted. The parent derives the complete expected occurrence
from its own verified lease and exact-compares every load binding, resolution,
root, proposal and audit commitment before minting success. Evaluation then
rebuilds a fresh store and two further processes and checks the original store
snapshot before and after replay. This is deterministic replay with the same
pinned proof implementation, not an independently implemented algorithm.

The warm process imports the ground-kernel module only to install a fail-closed
guard; it obtains no target kernel instance and performs zero transition,
catalogue or optimizer calls. Both occurrences retain semantic `A0A0`.
Persistence is therefore established only for this exact same-query H2 control.
Generic persistence, changed-query/model reuse, semantic policy change,
sample/total-work reduction, economics and official execution remain locked.
The exact source chain, trust boundary, attacks and canonical IDs are in
`specs/H2_DURABLE_PROOF_STATE.md`.

V0-054B now supplies the separate strict action-local switch without changing
V0-054A's same-query persistence claim. Sample-tax operators/meta-priors remain
downstream of measured multi-query traces.

## Historical live H2 query-local epoch-invalidation slice (V0-053)

Contract `1.16.0`, schema `1.0.0`, and profile
`lmb_h2_live_query_local_epoch_invalidation_v0` connect the authentic V0-047 first
`11/9` V3 epoch to its final `20/0` V3 successor through the V0-052 temporal proof
DAG. Production accepts exactly the eight upstream V0-047 authorities. It cannot
accept a completed V0-047 result, caller-selected rows or plans, model pair, closure,
cache, controls, or expected outcomes.

The live order is:

```text
base failure authority and round one
-> first immutable V3
-> four candidate DAG roots
-> DAG-derived proposal and independent selected failed root
-> derive and freeze the nine-row round-two request
-> execute exactly nine authorized transitions
-> final immutable V3
-> derive exact row delta and proof invalidation
-> four new candidate roots
-> replan and independently certify
```

No round-two transition can precede the first selected failed root. Reading a
completed V0-047 result and reconstructing the trace afterward is only a post-hoc
control, never the live passing path.

The exact delta changes the nine round-two boundary rows from missing to observed.
Although acquired from the time-one frontier, they are stationary model rows:
`U1/U0` both scan them, `P1/P0` both consume the changed coord-3 realization, and
`C1` consumes their changed reachability facet. Direct consumed-facet changes are
therefore `U1/U0/P1/P0/C1`; `D/E/F/G/R` are rebuilt as descendants. Only `C0` is
extensionally unchanged across epochs.

Two five-request epoch workloads resolve 110 slots in each matched arm:

```text
request-reset computes / hits                    = 110 / 0
epoch-reset global-DAG computes / hits            = 70 / 40
continuous cross-epoch facet-DAG computes / hits = 68 / 42
```

All five final-epoch `C0` resolutions hit the two distinct `A0/A1` entries built in
the first epoch. Thus only `70-68=2` avoided constructions are attributed to
cross-epoch reuse. They are not transition samples, total work, bytes, or wall time.
The proof controls share the same evidence transaction and perform no additional
operational sampling; independent full replay remains evaluation-only.

Both epochs genuinely replan, but both select the same semantic Gray `A0A0` schedule
with key `(0,1,0,1,0,1,0,1)`. Their model-bound plan/proposal/root IDs change; their
semantic actions do not. V0-053 therefore opens only
`registered_h2_live_query_local_epoch_invalidation_claimed=true`, not a semantic
policy-change claim.

Generic changed-model/H>2 proof, cross-query or persistent caching, sample
reduction/efficiency, total-work/economics, learned dynamics, coordinate invention,
and official execution remain locked. Scalar cost and break-even stay null, and all
three associated Gates stay `NOT_RUN`. The full live order, exact delta, controls,
attacks, inherited source goldens, and claim boundary are in
`specs/LIVE_QUERY_LOCAL_EPOCH_INVALIDATION.md`.

The next construction Gate is a preregistered repeated H2 occurrence family with
durable epoch/proof state and a separate action-local sparse delta that produces a
genuine semantic policy change. Only its measured acquisition/proof trace can justify
a later Laplace-style or KG-OP-style sample-tax intervention.

## Historical H2 stage-local temporal proof-DAG slice (V0-052)

Contract `1.15.0`, schema `1.0.0`, and profile
`lmb_h2_stage_local_bellman_proof_dag_v0` consume the unchanged V0-047 **final
query-local H2 V3** model. They do not use the later promoted V5 H1 model and do not
perform another model promotion. Four candidate plans run in Gray order
`A0A0 -> A0A1 -> A1A1 -> A1A0`, followed by a separately keyed independent selected
certificate for `A0A0`.

Each request resolves eleven temporal slots:

```text
U1 -> U0       P1 -> P0       C0 -> C1
D <- U0,P0,C0,C1
E,F <- D       G <- C0,C1
R <- every lower node
```

Lower nodes bind only the exact source and local stage/action/parent facet needed by
their semantics. The root always binds the complete plan, query, thresholds, request
and proof role; legacy V0-043 plan-/threshold-bound rows exist only at that root. The
three matched cache scopes freeze:

```text
logical slot resolutions                         = 55 in every arm
request-reset computes / hits                    = 55 / 0
plan-partitioned computes / hits                  = 45 / 10
global temporal-DAG computes / hits               = 35 / 20
global compute prefixes                           = 11,19,27,34,35
global hit prefixes                               = 0,3,6,10,20
target transition / catalogue / optimizer calls  = 0 / 0 / 0
```

Only `45-35=10` avoided constructions are attributed to cross-plan temporal reuse;
`55-35` also includes the selected request's exact same-plan lower-node reuse. This
opens only
`registered_h2_stage_local_bellman_recurrence_claimed=true` for the registered
frozen-model control. It is not generic H>1 recurrence, cross-query or changed-model
incremental proof, changed-threshold or changed-reward incremental proof, persistent
caching, a closed-loop repair result, sample reduction, sample efficiency,
total-work/economics evidence, or official execution. Scalar cost and break-even stay
null; workload-economics, counter-completeness and sample-efficiency Gates stay
`NOT_RUN`.

V0-053 now consumes the first-to-final overlay Gate that V0-052 left open. V0-052
itself remains a frozen-model proof control and cannot be retroactively relabelled as
live model evolution. Canonical V0-052 identities remain frozen and must match
independent replay.
The complete contract is in `specs/H2_TEMPORAL_PROOF_DAG.md`.

## Historical identity-bound incremental proof-DAG slice (V0-051)

Contract `1.14.0`, schema `1.0.0`, and profile
`lmb_identity_bound_incremental_proof_dag_v0` factor the unchanged V0-043 H1
fixed-plan proof into eight domain-separated nodes. `U/P/C/D` retain intrinsic
Bellman, selected-policy, reachability, and root metrics; `E/F/G` apply the current
regret, risk, and external-coverage obligations; `R` always rematerializes the full
query-, threshold-, plan-, and role-bound audit result. Existing V0-043 row artifacts
all bind `thresholds_id`, so they are never reused as threshold-neutral evidence.

Seven unique contexts change exactly one of `rho0`, regret tolerance, or risk
tolerance at a time. Each context still enumerates two plans and makes a separate
independent-selected certificate request. The three matched reset scopes produce:

```text
proof requests / node resolutions       = 21 / 168 in every arm
request-reset computes / hits            = 168 / 0
occurrence-reset computes / hits         = 112 / 56
global-DAG computes / hits               = 62 / 106
selected-plan certificates               = 7
target transition / catalogue calls      = 0 / 0
```

The registered changed-query attribution is only `112 - 62 = 50` avoided proof-node
constructions; the larger `168 - 62` difference also contains within-context
factoring. Every `rho0` change re-derives `C,D,E,F,G,R`, every regret change re-derives
`E,R`, and every risk change re-derives `F,R`. All 21 roots match unchanged monolithic
V0-043 audits byte-for-byte, while candidate roots remain unable to authorize the
selected role.

This is a registered H1 changed-query proof-reuse control, not H>1 incremental
Bellman evaluation, persistent caching, total-work or wall-clock improvement,
sample-efficiency evidence, or a Laplace/KG-OP tax-reduction operator. Official,
scalar, economics, counter-completeness, and sample-efficiency Gates remain locked.
The exact dependency, invalidation, authority, trace, and attack contracts are in
`specs/INCREMENTAL_PROOF_DAG.md`.

## Historical exact identity-bound certificate memoization slice (V0-050)

Contract `1.13.0`, schema `1.0.0`, and profile
`lmb_identity_bound_certificate_memoization_v0` retain the complete V0-049
held-out family, planner, candidate order, tie break, and independent selected-plan
certificate, but start an isolated append-only proof cache empty. Every occurrence
still enumerates the same two H1 plans and issues two
`CANDIDATE_RANKING_AUDIT` requests plus one separately keyed
`INDEPENDENT_SELECTED_PLAN_CERTIFICATE` request. Candidate audits may pass or expose
a failed proof frontier; only the selected role must contain a complete certificate.

The semantic memo key binds the model/source/promotion, observation authority, query,
complete thresholds and return-bound proof, contingent plan, planner/tie-break,
auditor implementation and proof role. A selected-certificate key also binds its
planner-result identity. Logical occurrence identity is deliberately excluded from
that semantic key so an exact repeat may hit, but every hit or miss emits a fresh
occurrence-bound use receipt. Runtime execution authority is owner bound, the trace is
append-only from a canonical empty state, and the independent verifier replays every
cache transition and every source miss.

Against the unchanged V0-049 no-reuse arm, the frozen result is:

```text
logical proof requests / plan candidates = 30 / 20 in both arms
no-reuse complete audit executions       = 30
memo complete audit executions           = 9
memo misses / inserts / hits              = 9 / 9 / 21
matched selected-plan certificates       = 10
target transition / catalogue calls      = 0 / 0 in both arms
first prefix with fewer full audits       = 4
```

The first three distinct queries populate nine role-bound entries: two distinct
candidate-plan entries under the candidate role plus one selected-certificate entry
per query. The remaining seven occurrences reuse them exactly. Model, query, threshold, plan, auditor,
planner, source, promotion, authority, or proof-role changes invalidate reuse. Merely
changing a registered occurrence creates a new receipt around the same semantic hit.
The reduction `21/30 = 7/10` applies only to complete proof computations: lookup,
validation, hashing, receipt, I/O, and independent replay work remain explicit.

This is exact-repeat certificate memoization, not cross-identity incremental proof,
partial Bellman reuse, persistent cross-process cache authority, a Laplace/KG-OP
sample-tax operator, sample efficiency, statistical generalization, total-work or
wall-clock improvement, or official economics. Official execution remains false;
scalar cost and break-even remain null; workload-economics, counter-completeness and
sample-efficiency Gates remain `NOT_RUN`. The next proof-reuse Gate requires a new
identity-bound proof-dependency DAG and affected-descendant re-derivation artifact; it
may not relax the V0-050 exact key. Full identities and attacks are normative in
`specs/CERTIFICATE_MEMOIZATION.md`.

## Historical held-out family amortization slice (V0-049)

Contract `1.12.0`, schema `1.0.0`, and profile
`lmb_preregistered_h1_heldout_family_amortization_v0` extend V0-048 from one
target to a preregistered workload. Before source acquisition, the protocol
freezes three distinct H1 targets at LMB states `removed_mask=11/19/35` and a
ten-occurrence order `Q1,Q2,Q3,Q1,Q2,Q3,Q1,Q2,Q3,Q1`. All three states are
absent from V0-045; the source runner still has no target or protocol input.

Promotion independently verifies the complete V0-047 source through the
unchanged V0-048 component, retains all 20 rows, 13 exact evidence records and
three boundary catalogues, and creates a separate
`PreregisteredReusablePartialRAPMV5`. V5 does not widen V4 in place. It permits
only the three registered initial states with `H<=1`, preserves
`acquisition_query_neutral_attested=false`, and makes no closure, exact-quotient
or unrestricted-reuse claim.

Every warm occurrence enumerates two model plans and performs three exact model
audits, certifying reward/failure/regret `1/0/0` with zero target transition,
catalogue or ground-optimizer calls. Each matched cold route receives only its
QuerySpec, logical occurrence and exact kernel; it cannot see the promotion or
source result. It makes one complete catalogue call, executes three transitions,
enumerates all three ground actions and independently obtains the same `1/0/0`
result. Source evidence comparison occurs only after cold selection.

The source-inclusive operational acquisition vector stays `(13 transitions,
3 catalogues)`, while the matched cold prefix is `(3N,N)`. Cold is strictly
smaller for `N=1..3`, the vectors are incomparable at `N=4`, and warm is
strictly smaller for `N=5..10`. If independent promotion replay is included as
a diagnostic evaluation lane, the corresponding relation changes at `N=9`.
These are vector relations—not an official scalar break-even:

```text
official_scalar_cost = null
official_N_break_even = null
sample_efficiency_claimed = false
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

The exact trace also exposes the next likely tax: ten warm occurrences perform
20 candidate evaluations and 30 fixed-plan audits even though their target
ground calls are zero. This makes identity-bound certificate memoization or
incremental proof the next intervention to test; it does not yet prove that
such an operator is sound or beneficial. No LLM or subagent participates in
the production planner, promotion, cold optimizer, or certificate logic. Full
identities and acceptance tests are in
`specs/HELDOUT_FAMILY_AMORTIZATION.md`.

## Historical preregistered cross-query promotion slice (V0-048)

Contract `1.11.0`, schema `1.0.0`, and profile
`lmb_preregistered_h1_cross_query_promotion_v0` advance the central loop from
within-query refinement to a distinct held-out query. Before V0-047 source
acquisition, the protocol freezes an H1 target at LMB state
`removed_mask=11, buffer=(1,2)`. That state is absent from the V0-045
observation graph and differs from the V0-047 H2 source initial state. The
already-frozen source runner has no target or promotion input.

Promotion independently replays the complete V0-047 result and selects all 20
final rows, all 13 exact evidence records, and all three boundary catalogues.
It forbids a target-filtered subset. The new
`PreregisteredReusablePartialRAPMV4` is a separate immutable epoch: V0-045 is
not mutated, source acquisition remains explicitly non-query-neutral, and reuse
is authorized only for the preregistered initial state with horizon at most one.
There is no global closure, exact-quotient, or unrestricted-reuse claim.

The held-out consumer accepts no kernel or transition interface. It enumerates
two H1 abstract plans and independently certifies reward `1`, failure `0`, and
normalized regret `0` with zero warm-target transition/catalogue/ground-optimizer
calls. A separate evaluation-only cold trace makes one direct catalogue call and
three transitions; their outcomes exactly match the promoted source evidence.
Source acquisition (`13+3`), promotion replay (`13+3`), warm target (`0+0`), and
cold target evidence (`3+1`) remain separate work lanes.

This is one authentic preregistered cross-query reuse/promotion positive control,
not statistical generalization or a sample-efficiency result. Source amortization
and a complete cold-start planner are not included, so scalar cost and break-even
remain null and the sample-efficiency Gate remains `NOT_RUN`. The next construction
Gate is a preregistered family of held-out logical occurrences with promotion
amortization and matched end-to-end cold baselines. Those traces—not an LLM—will
determine whether a later Laplace-style heuristic operator or KG-OP-style
offline/online prior should target coordinate, transition, certificate, or model-
verification cost. Full identities and acceptance tests are in
`specs/CROSS_QUERY_PROMOTION.md`.

## Historical multi-step query-local refinement slice (V0-047)

Contract `1.10.0`, implementation schema `1.0.0`, and profile
`lmb_h2_multistep_query_local_exact_refinement_v0` execute the first genuine
two-stage version of the central loop. Starting from the complete V0-045 model,
typed V0-044 H2 proposal, and independently failed V0-043 audit, the authority
derives four time-zero rows without caller-selected states, rows, or caps. Four
exact transition calls expose three previously external active states; three direct
boundary action-catalogue calls register their nine legal rows without replaying transitions.

The fixed V0-045 coordinates are then evaluated on those new states. All three
reuse the existing state-coordinate signature `(3,)` and the two semantic action
labels `(False,)` and `(True,)`. The immutable first `QueryScopedPartialRAPMV3`
epoch has `11 observed / 9 missing` rows. Model-only planning enumerates four H2
plans, and independent audit moves the earliest failed-proof frontier from
`time=0, horizon=2` to `time=1, horizon=1`; external coverage is no longer the
failed obligation.

The second authority freezes the union of three selected-plan risk rows and nine
unrestricted value challengers: nine distinct rows and exactly nine further
transition calls. The final V3 epoch has `20/0` observed/missing rows over its
registered query-local catalogue. Model-only replanning and independent audit
certify reward `1`, failure `0`, and normalized regret `0`. A semantic-label
lexicographic tie rule acts only after exact numerical ties, so unrelated content
hash changes cannot silently change the selected contingent plan.

The complete operational acquisition trace is `4 + 9 = 13` exact transition
calls, three direct boundary action-catalogue calls, two model-only replans, eight
candidate-plan audits, zero planner/auditor kernel calls, and zero direct ground-optimizer calls.
Each transition performs one internal action-legality enumeration; those 13 checks are
charged inside the transition calls and are not additional catalogue acquisitions.
The reusable base remains byte-identical; both V3 epochs are query-owned,
nonpromotable, non-query-neutral, non-exact, and not globally transition-closed.
This is real within-query coordinate reuse, not held-out reuse, learned dynamics,
general causal minimality, sample saving, or aggregate-Gate completion.

V0-048 now executes the next distinct cross-query promotion control; V0-047 remains
the immutable source regression and is not retroactively relabelled as reusable.
Its full identities remain in `specs/MULTISTEP_QUERY_LOCAL_REFINEMENT.md`.

## Historical certificate-triggered H1 refinement slice (V0-046)

Contract `1.9.0`, implementation schema `1.0.0`, and profile
`lmb_h1_query_local_exact_row_refinement_v0` close the next narrow part of the central
loop. The input is the complete V0-045 H1 typed-planner result and independently failed
typed V0-043 audit—not a bare frontier. A separate authority replays that full chain
and derives the evidence request; callers cannot supply a row subset or acquisition
cap.

For the fixed H1, `delta=0`, fixed-plan, fixed-concretizer row-completion problem, the
one reachable unresolved realization contains four missing rows, each with weight
`1/4`. Leaving any one row unknown permits failure upper `1/4>0`, so all four rows are
individually necessary inside this declared evidence family. Request preparation uses
zero kernel calls. The executor validates the canonical LMB kernel and all registered
legal-action catalogues, then performs exactly four authorized transition calls and no
other ground-row access.

Those outcomes are all safe and reward-zero: one successor is registered and three are
known external states. The reusable V0-045 model remains byte-identical. A new
query-owned `QueryScopedPartialRAPMV2` changes coverage from `7 observed / 4 missing`
to `11 / 0`, but remains non-query-neutral, non-promotable, not transition-closed, and
not an exact quotient. Rebased abstract planning enumerates two plans with zero further
kernel access. Independent audit certifies the selected H1 plan with reward, failure,
and regret all zero.

Canonical counts and IDs are:

```text
authorized operational exact-kernel calls = 4
extra ground-row access                   = 0
base model                                = 1676785661c8fb00f54ddef93dc84d53c08b81781249de66ae5e4129a450bc18
evidence request                          = 1ff845f3eecc05a098b3437c7e4b8356bcd28ea1dd0d4cc4ace8e52bc382cd2c
query-scoped model                        = 7c709a2cb568398954b1c357dfd1bb68798be91bc4a9ed192e915976126276df
fixed-plan certificate                    = ea6d196cd6054871f8cb0e6809210df9bb83975ff49baea8a516f69b1a2af303
complete result                           = 8c37b241d15b06f05dfe34189b37e324addd2c93605d4c718868d8a0544cf057
```

This is a real certificate-failure → minimal scoped evidence → immutable overlay →
replan/re-audit positive control, but only for the registered H1 row-completion case.
It is not general causal minimality, an acquisition policy, multi-step external
coverage repair, base-model promotion, raw symbolization, learned dynamics,
generalization, scale, or sample saving. Four exact calls are charged; the 4096-
candidate offline coordinate search is separate construction work and is not being
called free.

V0-047, described above, now generalizes this authority to a real two-round H2
failed-proof path with boundary registration, active coordinate reuse, and a later-stage
frontier. V0-046 remains the immutable H1 row-completion regression. Its full normative
details and identity table are in `specs/QUERY_LOCAL_EVIDENCE_REFINEMENT.md`; no H1
artifact is retroactively relabelled as multi-step or promoted into the reusable base.

## Current observation-only typed-coordinate synthesis slice (V0-045)

Contract `1.8.0` (synthesis schema `1.0.0`, typed V0-042 `1.2.0`, typed planner
`1.1.0`, typed audit wrapper `1.2.0`) closes the narrow construction-to-planning chain on the hardened
finite observation control. Profile
`lmb_query_free_observed_typed_coordinate_synthesis_v0` receives only the exact
allowlisted observation log, deterministic profile and observation authority. It uses
no query, kernel, behavioural target/signature, V0-041 result, caller-selected subset,
planner, audit, J0, ground solver or callback.

The system evaluates a fixed human-written typed DSL—eight state and four action ASTs—
over all eight registered states and eleven legal rows, then exhausts all 4096 subset
candidates. Seven observed rows supply congruence evidence; four unobserved legal rows
remain explicit uncertainty and are neither positive nor negative comparisons. The
selected programs are:

```text
state:  cardinality(legal_actions)
action: buffer_at_type(buffer_counts, selected_tile_type)
atom:   integer <= 3/2
```

The resulting query-neutral partial RAPM has six total/four active cells, five abstract
entries/actions and six realizations. It preserves seven singleton rows, four unit-
unknown rows, the shared joint simplex and horizon cap six. The original V1 action
schema is unchanged: semantic labels remain nonempty boolean tuples. Raw integer DSL
values compile to exact boolean midpoint atoms; they never become integer labels.

The typed value table, proposal and pure V0-042 builder are internal derivation
objects, not certificate authority. A downstream consumer must supply the complete
`ObservedTypedPartialRAPMResultV1` and replay V0-045. Typed V0-044 does that once, freezes
the model, and enumerates plans without rerunning synthesis per candidate. H3 evaluates
eight plans and proposes reward/failure `4/0`; H1 evaluates two and exposes interval
`[0,3]` with failure upper one. The proposal is still not a certificate. Independent
typed V0-043 replays the full V0-045 chain for the selected plan: H3 certifies, whereas
H1 returns a nonauthorizing `UNRESOLVED_POLICY_PATH_DISTINCTION` frontier.

This is coordinate discovery only inside a fixed DSL over already-symbolized logged
states/actions. It is not raw perception/symbolization, unknown semantic or DSL
invention, a neural/learned latent model, true/exact dynamics recovery, statistical
consistency, generalization, scale or sample saving. The frozen V0-045 result/model IDs
are `4834efc30b9ae292e33f83932525195df1997ae31f7c7898b452b6175815ded2` and
`1676785661c8fb00f54ddef93dc84d53c08b81781249de66ae5e4129a450bc18`; the full table
is in `specs/OBSERVED_TYPED_COORDINATE_SYNTHESIS.md`.

V0-046 now executes this former next Gate for the exact H1 row-completion control: a
separate authority proves four individually necessary rows, acquisition is charged,
the base remains unchanged, and a query-owned overlay replans and certifies. It does
not authorize base promotion. V0-047 then executes a separate H2 two-round path,
registers three evidence-derived boundary states, reuses the selected coordinates, and
moves the failed frontier to the next stage before certification. A failed
frontier alone still cannot authorize ground access or mutate the reusable base; the
complete typed failure chain remains mandatory.

All aggregate locks remain unchanged:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

## Current partial-model contingent-plan proposal slice (V0-044)

Contract `1.7.0`, implementation schema `1.0.0`, registers profile
`partial_model_contingent_plan_proposal_v0`. This query-scoped consumer first
reconstructs the complete V0-042 source graph and partial RAPM, then reads one frozen
V0-043 threshold object. That object content-binds the exact string
`goal_id="default"`; a foreign or non-string goal is rejected, not treated as another
query/goal profile. The production API accepts exactly the five V0-042 source/model
objects plus `thresholds`; the verifier adds only `claimed_result`. There is no kernel,
transition callback, `J0`, ground solver, feasibility oracle, second query or caller-
selected production cap.

For each stage, the producer enumerates the Cartesian product of every active cell's
semantic-action domain. If that product has size `S`, it enumerates all `S^H`
deterministic global contingent plans and runs the existing V0-043 fixed-plan audit on
every candidate. Selection is deterministic and hierarchical:

1. `INTERNAL_V0043_AUDIT_PASS_REWARD_MAX`: among candidates whose internal V0-043
   replay returns `CERTIFIED_FIXED_PLAN`,
   maximize reward lower bound, then minimize failure upper bound, then plan ID;
2. `RISK_FEASIBLE_REWARD_MAX`: if tier 1 is empty, apply the same ordering among
   candidates whose failure upper bound is at most `delta`;
3. `MIN_FAILURE_RISK_FALLBACK`: if both earlier tiers are empty, minimize failure upper
   bound, then maximize reward lower bound, then plan ID.

The word `INTERNAL` is essential: the proposal is not certificate authority. The
selected plan must be submitted to an independent V0-043 audit. Every result freezes
`proposal_is_certificate_authority=false`,
`selected_plan_requires_independent_v0043_audit=true`, and false feasible-plan,
infeasible-query and optimal-ground-policy claims under claim kind
`MODEL_ONLY_CONTINGENT_PLAN_PROPOSAL`.

Production uses content-addressed action-domain, candidate-summary, trace, result and
cap-profile artifacts. Its fixed cap is `65536`, with cap-profile ID
`9176c40aec0b6ecb3c7645a61363cefa32d9d13396ab33ee70fb0238f171932b`;
the caller cannot override it. If the exact candidate count exceeds the cap, the
producer returns typed `CAP_EXHAUSTED` after source reconstruction and counting but
before any candidate audit: evaluated candidates and audits are zero, summaries are
empty, selection is `NOT_APPLICABLE`, and no plan or certificate is emitted. A named
private lower-cap path exists only as a nonproduction control and its result is rejected
by the public verifier.

The frozen controls are:

```text
H3 observed query:
  per-stage assignments = 2
  required / evaluated candidates = 8 / 8
  fixed-plan audits / source reconstructions = 8 / 9
  selection = INTERNAL_V0043_AUDIT_PASS_REWARD_MAX
  selected plan = 1cad00f91105976061f7ec4b1e31529cdedb16ac185d948a005e3c2643c06bbc
  reward L/U = 4/4; failure L/U = 0/0
  distribution / maximum-support normalized regret = 0/0
  internal and independent V0-043 outcomes = CERTIFIED_FIXED_PLAN

H1 missing-state query:
  same partial model/build; different threshold/result IDs
  candidates = 2; selection = MIN_FAILURE_RISK_FALLBACK
  reward L/U = 0/3; failure upper = 1; risk feasible = false
  candidate audit = FAILED_PROOF_FRONTIER / UNRESOLVED_POLICY_PATH_DISTINCTION
  local recovery authorized = false

private cap-4 control on the H3 query:
  required candidates = 8; outcome = CAP_EXHAUSTED
  evaluated / audits / source reconstructions = 0 / 0 / 1
  summaries empty; selected plan absent; public verification rejected
```

The trace records exact finite model work:
`source_graph_reconstruction_count = 1 + fixed_plan_audit_count`, candidate counts,
zero external-transition-authority calls and zero ground-search calls. These are
model-work/sample-tax telemetry, not environment interactions or samples; the trace
sets `work_economics_claimed=false`.

This slice proves bounded exhaustive proposal and deterministic selection only on the
registered finite partial model. It does not turn a selected plan into a certificate,
prove feasibility/infeasibility, equal `J0` or the ground optimum, establish an exact
quotient or transition closure, invent coordinates, authorize a causal frontier/local
repair/fallback, demonstrate learning/generalization/scale/sample savings/economics, or
open official execution, Phase 3, Phase 3E or aggregate Gates. In particular, cap
`65536` is a bounded-search limit, not a scalability claim.

Contract `1.8.0` adds the typed V0-045 consumer surface without changing this historical
manual V0-044 result. The typed proposer replays one complete V0-045 result, freezes its
verified model and uses the common bound core for candidate ranking; independent typed
V0-043 remains the sole plan-certificate authority. See the preceding V0-045 section.

## Current robust fixed-plan audit slice (V0-043)

V0-043 connects a downstream, query-scoped auditor to the unchanged V0-042 partial
RAPM. Profile `partial_fixed_plan_robust_audit_v0` first reconstructs the complete
allowlisted V0-042 source graph and derived model. Only after that invariant check may
it read frozen thresholds and one supplied deterministic finite-horizon contingent
abstract plan. The plan has contiguous stages `0..H-1`, assigns every active cell at
each stage, permits no policy randomization, and must satisfy `H<=6`.

The audit receives no kernel, transition API, ground solver, planner, J0 or feasibility
oracle. It uses every registered ground-action row to construct an unrestricted reward
upper bound, then evaluates only the supplied plan with the V0-042 joint simplex. Shared
unknown mass is charged once in Bellman arithmetic. Per-destination reachability uppers
are proof diagnostics, never an independently summable probability distribution.

The canonical nonnegative LMB `N=6` reward-scale proof, ID
`6fb0235260099bf0dda06c93a0c2e7122e18ff16439a959f51ca904d551d9b98`, binds the
structural, environment, log, semantics, observation-authority and acquisition-manifest
identities: two match events plus terminal-clear bonus upper two give `R_max=4`. Reward
weights are exactly `match=1` and `terminal_clear=1`; normalized-regret tolerance is
registered only at `{0,1/20}`, and risk tolerance only at `{0,1/20,1/10}`. Threshold ID
also content-binds exact `goal_id="default"`; foreign strings, integers and string-like
duck objects are invariant violations. Value certification is pointwise over every
exact ground state in `rho0`; the distribution-average regret is a
diagnostic and cannot hide one bad low-mass support point. Risk remains distributional,
while any unknown row or known external continuation reachable under the supplied plan
with remaining horizon above one independently blocks selected-plan external-coverage
certification.

The frozen controls are:

```text
H=3 observed-path control:
  unrestricted reward upper = 4
  supplied-plan reward lower/upper = 4/4
  distribution/max-support normalized regret = 0/0
  failure lower/upper = 0/0
  unrestricted proof rows = 33
  outcome = CERTIFIED_FIXED_PLAN

H=1 missing-state negative regression:
  unrestricted reward upper = 3
  supplied-plan reward lower = 0
  normalized regret upper = 3/4
  failure upper = 1
  earliest frontier = (time=0, remaining=1,
                       UNRESOLVED_POLICY_PATH_DISTINCTION)
  outcome = FAILED_PROOF_FRONTIER
```

A failed frontier is a `NONAUTHORIZING_PROOF_OBLIGATION_HINT_V1`: it proves neither
infeasibility nor causal necessity/sufficiency and cannot authorize local recovery.
`unresolved_exposure_sum` is a sum of representative proof exposures, not a
probability. Forged source rows, return bounds, proof chains, zeroed unknown mass,
foreign model/plan identities, invalid horizons, mutable/duck nested inputs and
coherently re-signed results terminate as an invariant violation, not as a normal
negative regression.

This slice certifies only a supplied fixed plan, conditionally on V0-042's external
trust root. It does not search for a plan, prove optimality or infeasibility, establish
transition closure, authorize repair, demonstrate automatic coordinates or learned
dynamics, or open official execution, economics, counter-completeness, sample-
efficiency, Phase 3 or Phase 3E Gates.

## Current observation-log partial-dynamics slice (V0-042)

V0-042 moves the main construction line beyond construction-time exact-kernel access.
Profile `lmb_deterministic_observation_partial_rapm_v0` accepts only an immutable
observation log, a frozen coordinate proposal, a deterministic/stationary semantics
profile, and an exact preregistered observation-authority graph. Constructor and
verifier receive neither a kernel nor a QuerySpec. They accept the source graph only
when its authority ID is in the frozen code/ledger allowlist and every structural,
environment, profile, acquisition, state, catalogue, receipt, event, log and evidence-
ledger binding matches. Coherently re-hashing modified source bytes therefore creates
an unregistered authority and fails closed.

The canonical seed-0 LMB acquisition manifest freezes eight literal states, eleven
legal state-action rows and seven event receipts before query registration. It is not
derived from an initial-state transition closure; acquisition and construction each
record zero QuerySpec inputs. Seven rows are observed deterministic singletons and four
remain missing. A Portable model recomputes every state/cell/action cross-link, ground-
row ID, concretizer support, observed/missing realization partition and exact weighted
realization ambiguity from its ground rows. Keeping an allowlisted authority ID while
self-signing a different derived model cannot turn missing evidence into a singleton.

Each missing row retains unit mass over one machine-visible joint outcome simplex:
continuation to every registered active cell or the external boundary, terminal
success, and terminal failure. The coupling fixes `continuation + terminal = 1` and
`failure <= terminal`; an independent marginal box is forbidden. `EXTERNAL_STATE`
cannot alias a registered state and is active, nonterminal and nonfailure only. Reward-
feature and destination names are unique, the concretizer is uniform over distinct
ground actions, and the model binds `semantics_horizon_cap=6`. Coverage does not claim
transition closure or an exact quotient; outside-catalogue support or a horizon above
the cap requires rebuild or fallback.

The fixed coordinates are `legal_action_count` and `completes_match`. Production
ancestry is empty, origin is `manual_preregistered_generated_ast_v1`, and no target
exact audit may select or certify them. Evidence accounting contains all five evidence
classes across all four lanes, including explicit native zeros; the canonical log has
exactly seven `offline_source/OFFLINE_LOGGED_OBSERVATION` events and native zero in the
other 19 cells. Receipts and observations are one-to-one; replay or evidence relabelling
fails. Construction records zero exact-kernel queries, generative samples and synthetic
rollouts in addition to its separate zero query-input counter.

This remains an in-memory exact-graph authority boundary:
`in_memory_exact_graph_required=true` and `transport_authority_claimed=false`.
Content IDs prove integrity and binding, not observer honesty, catalogue completeness,
stationarity or public authenticity; the external allowlist is the trust root. V0-042
is not automatic coordinate synthesis, a plan certificate, exact quotient,
infeasibility proof, public-key/cross-process authority, learned-model-quality result,
sample-efficiency/generalization result, or a Phase 3/3E/economics/counter Gate. The
sample-tax concern remains recorded but non-blocking. A bounded partial-model plan
producer and independent selected-plan audit are now connected for the finite control;
log-only coordinate synthesis and certificate-triggered local recovery remain open.

## Current generated-coordinate exact synthesis slice (V0-041)

V0-041 moves the main construction line from selecting named human features to
generating typed coordinate programs. Profile `lmb_structural_typed_expression_dsl_v1`
accepts only an exact `LMBKernel` and frozen `SuiteBuildCoverage`. From raw LMB
primitives it deterministically instantiates eight state ASTs and four state-action
ASTs under a fixed typed production-template DSL; its source and registry contain
neither V0-039 named feature `action_count` nor `completes_match`.

Production exhausts all `2^8 * 2^4 = 4096` coordinate-subset candidates. Direct exact
one-step state-action homomorphism obligations are the sole selector. The canonical
25-state result chooses the generated state program
`cardinality(legal_actions)` and action program
`buffer_at_type(buffer_counts,selected_tile_type)`, generates thresholds `3/2,5/2`,
compresses total/active `25/18 -> 5/3`, and emits four singleton abstract entries plus
one portable RAPM. Typed ASTs, the DSL registry/spec, complete trace, implementation
digests and certificate are content-addressed; the independent verifier rebuilds the
registry, all 4096 candidates, the quotient and portable model.

This is program generation inside fixed, human-designed production templates over raw
LMB primitives. It still assumes complete exact finite coverage and the full exact
kernel. It is not unknown-semantic invention, partial/learned dynamics, scalable or
cross-domain generalization, or a sample-efficiency/Phase 3/Phase 3E Gate result.

## Prior-guided held-out exact-audit control (V0-040)

V0-040 is a non-blocking proposal/authority control beside the main construction
line. Under production profile `source_unanimous_exact_v1`, two distinct source
coverages (mask 11 and mask 13) must independently accept the same V0-039 fixed-grammar
hypothesis. Only that unanimous hypothesis may be proposed to the distinct held-out
target coverage (mask 7). The recorded positive broad-tail mass is metadata only:
V0-040 executes one proposal and no wide-tail schedule, ranking learner or target
candidate enumeration.

The proposal is never certificate authority. The held-out target is accepted only by
an independent exact ground-homomorphism audit, which then constructs a portable RAPM.
The positive golden records source-offline exact-kernel calls/unique rows `14/14`,
target exact-kernel calls/unique rows `21/7`, one target candidate evaluation, and
zero environment-interaction samples. Its certificate states
`global_minimality_verified=false`; one unchanged target model serves two in-coverage
queries. A separately role-locked `nonproduction_external_control_v1` can inject the
empty hypothesis: its three exact-kernel calls produce
`PRIOR_MISMATCH_FALLBACK_REQUIRED`, no model/certificate, and no infeasibility claim.

The sample-tax concern is registered now without blocking construction. Exact-kernel
queries, environment interactions, generative-oracle samples, offline observations and
synthetic rollouts remain separate telemetry classes. No sample-saving operator,
scalar or break-even is claimed until the real mainline access pattern exists and a
later matched-authority experiment is preregistered. Therefore
`SAMPLE_EFFICIENCY_GATE_NOT_RUN` and
`sample_efficiency_gate_blocks_mainline=false` coexist with the unchanged official,
scalar, workload-economics and counter-completeness locks.

## Current direct homomorphism synthesis slice (V0-039)

V0-039 constructs an exact LMB state-action quotient without receiving or importing a
prebuilt behavioural quotient/signature target. Its production API accepts only an
exact `LMBKernel` and frozen `SuiteBuildCoverage`, internally freezes the full eleven-
feature state grammar plus the one-feature `completes_match` action grammar, and
directly tests every one of the 4096 state/action-subset candidates against the exact
ground kernel.

For each candidate it proves equal semantic-label sets within each state cell,
identical raw reward/failure/termination/successor signatures before mixing aliased
ground actions, and identical same-label dynamics across cell members. The deterministic
minimum selects state feature `action_count`, action feature `completes_match`, and
thresholds `3/2,5/2`; the golden compresses total/active `25/18 -> 5/3`, has four
abstract entries, and a singleton envelope. The complete trace contains all 4096
candidates and typed label-set, within-state-action-alias and cross-state-dynamics
witnesses.

Restricted exact, no-exact and cap-exhausted controls cannot publish a production
model/certificate. They use a separate role-locked control verifier; the production
verifier rejects restricted provenance, incomplete canonical registries and duck-typed
results. A fresh process still constructs successfully when the behavioural module is
poisoned; the old behavioural oracle is imported only later for evaluation and agrees
exactly. Content-addressed artifacts, frozen state/action implementation digests, exact
transport/runtime types, independent reconstruction and two-query fresh-process reuse
are covered by attack tests.

The valid claim is direct exact homomorphism synthesis inside fixed human-readable
state/action grammars on exact finite coverage. It is target-free at construction, but
still uses the exact ground kernel and fixed grammar; it is not feature invention,
partial/learned dynamics, unknown-domain or scalable discovery, held-out/cross-domain
generalization, or a full Phase 3/3E/economics/counter Gate. All official locks remain
unchanged.

## Current automatic feature-realization slice (V0-038)

The new LMB vertical slice automatically realizes a reusable portable RAPM from a
preregistered human-readable current-state feature grammar. Its production constructor
sees only an exact `LMBKernel` and frozen `SuiteBuildCoverage`; it internally fixes the
complete canonical registry/spec, so callers cannot encode query bits by selecting a
feature subset. Restricted registries use a separate non-production control API. It
has no `QuerySpec`, J0, Q/value/frontier, policy, or held-out input and exhausts all 2048
subsets of the eleven registered features, generates reduced-rational `<=` atoms at
adjacent-value midpoints, and matches each resulting predicate partition against the
query-neutral exact controlled behavioural quotient on the same coverage.
That target is a complete exact ground-model behavioural oracle; the slice removes
query/J0/Q/value/policy/held-out leakage, not target-signature supervision.

The deterministic selector minimizes feature count, split count, feature names, then
partition ID. The canonical result selects only `action_count`, thresholds `3/2` and
`5/2`, and exactly realizes `25 -> 5` total states/cells and `18 -> 3` active
states/cells with a singleton envelope. Registry, spec, predicate tree, complete
candidate trace, bidirectional mismatch witnesses and certificate are content
addressed. Their frozen V1 constants are enforced, and independent replay rebuilds the
target trace/adapter/model, realized partition/quotient and portable model/registry. A
restricted grammar that cannot realize the target returns
`NO_EXACT_FEATURE_REALIZATION` plus either a
`TARGET_SEPARATED_FEATURE_ALIASED` or `TARGET_MERGED_FEATURE_SEPARATED` witness and no
model/certificate. A separate 36-state seed-0 canonical-initial control has an 11-cell
target and 7-cell `action_count` candidate and exhibits both mismatch directions in
its trace; it is not the 25-state positive golden.

The feature adapter source digest is independently frozen; canonical transport parsers
preserve JSON list/string types, and exact nested runtime-type checks reject proxy
objects that serialize to honest bytes while exposing altered behaviour. Restricted
exact controls likewise cannot change the canonical production trace or claim.

One unchanged serialized RAPM is loaded by fresh planner subprocesses for two distinct
in-coverage QuerySpecs. The valid claim is automatic selection of coordinates and
threshold atoms from this fixed LMB grammar—not feature invention, partial/learned
dynamics, oracle-free unknown-quotient discovery, unknown-domain or scalable discovery,
held-out/cross-domain generalization, or a full Phase 3/3E/economics/counter Gate. All
official locks remain unchanged.

## Current Phase 3E boundary (V0-037)

The project target remains:

> **自动合成一个可复用的抽象世界模型，使多步计划能够主要在该模型中完成；系统只在抽象模型无法以给定价值与约束误差认证当前 contingent plan 时，才局部恢复 ground distinctions。**

The registered H2 model-failure path now has a scoped successful LOCAL terminal and
logical-occurrence closure.  Its preparation trace natively records exactly 4 causal,
18 protocol, 3 integrity and 5 cap events.  That incremental work and its derived
failed-prefix aggregate are retained post-core with
`RETAINED_POST_CORE_NOT_YET_OCCURRENCE_CHARGED`; content-ID hashes, I/O and accounting
materialization are excluded, so this is not counter-complete occurrence accounting.

An independent selected-route bundle fixes 54 roles and replays the source lease,
identities, route arithmetic/selection, access order, native-work reductions, selected
upper, terminal and occurrence topology.  Its highest result is
`VERIFIED_LOCAL_ROUTE_ACCOUNTING_AND_TOPOLOGY`, not a semantic certificate: the
transport does not contain enough ground proof/post-audit input to mint live semantic
authority.  Bounded rebuild/new-epoch/single-retry support is likewise control-plane
mechanics only.  The repaired canonical H2 transaction 1 certifies, so a genuine
transaction 2 is unreachable there; that Gate now requires a separate dependent-
horizon fixture with a real failed ground post-audit and fresh deeper frontier.

None of this demonstrates automatic RAPM synthesis, unknown strategic abstraction or
cross-domain generalization.  The current locks remain
`official_execution_allowed=false`, `official_scalar_cost=null`,
`official_N_break_even=null`, `WORKLOAD_ECONOMICS_GATE_NOT_RUN`, and
`COUNTER_COMPLETENESS_GATE_NOT_RUN`.

The root `DECISION_LEDGER.md` and the files in `specs/` are the published
normative contract. The local `markdown/` discussion history and `reference/`
literature/repository archive are provenance inputs, are intentionally ignored by Git,
and are not part of the public checkout.

## Quick start

```bash
python3 -m pip install -e '.[test]'
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider
acfqp-phase05 --output artifacts/phase05
python3 scripts/verify_phase05.py artifacts/phase05
acfqp-exact-d4 --output artifacts/exact_d4
python3 scripts/verify_d4_baseline.py artifacts/exact_d4
acfqp-aliased-cegar --output artifacts/aliased_cegar
python3 scripts/verify_aliased_cegar.py artifacts/aliased_cegar
acfqp-phase3a --output artifacts/phase3a
python3 scripts/verify_phase3a.py artifacts/phase3a
acfqp-phase3b --output artifacts/phase3b
python3 scripts/verify_phase3b.py artifacts/phase3b
acfqp-phase3c --output artifacts/phase3c
python3 scripts/verify_phase3c.py artifacts/phase3c
acfqp-phase3d --phase3c-bundle artifacts/phase3c --output artifacts/phase3d
python3 scripts/verify_phase3d.py artifacts/phase3d
python3 third_party/laplace_smdp_940598d/experiments/run_gridworld_bellman_kron.py \
  --out-dir artifacts/legacy_gate_actual
python3 scripts/check_legacy_gate.py --actual-dir artifacts/legacy_gate_actual
```

On a development machine where the ignored `markdown/` and complete `reference/`
corpus have been restored, `python3 scripts/build_reference_manifest.py` rebuilds the
optional local provenance manifests. The artifact runners bind both manifests when
both exist; a public checkout with neither manifest records an empty mapping. A
half-present manifest pair is rejected.

The Phase 0.5 command writes complete JSON artifacts and a SHA-256 manifest for
both tiny benchmark fixtures.  Fallback is an explicit algorithmic outcome and
is charged in the artifact rather than hidden.

The exact-`D4` command writes the separate safe-chain positive-control bundle.
Its verifier reconstructs the registered group profile, orbit/action quotient,
distinct-action concretizers, zero-width model, lifted policy, and J0 equality;
that profile contains no CEGAR split or fallback artifact.

Ledger `V0-026` additionally freezes a separate safe-chain aliased CEGAR profile.
It keeps the same ground structural key and query, but uses a ten-cell histogram base
partition, order-dependent `canonical:first/last` actions, and a preregistered six-atom
action-frame geometry grammar. Exact counterexamples and the standard candidate ranking
must select two local four-bit splits before the run certifies with no fallback. This is
a deliberate action/partition-aliasing positive control; it is not the exact-`D4`
baseline and is not evidence of automatic predicate or symmetry discovery. Its runner
and independent verifier use their own profile key and multi-iteration artifact bundle;
the two commands shown above generate and independently recompute that bundle.

Ledger `V0-027` freezes the next, deliberately narrow construction slice under profile
`phase3a_true_state_alias_oracle_control_v0`. Unlike V0-026, its accepted cells contain
active states from more than one complete known-automorphism orbit. The train-only
G2048 build uses the canonical safe-chain query plus a strict `H=1` bridge query whose
states `(0,2,2,2)` and `(0,2,4,2)` are non-`D4`, jointly policy-reachable members of
one oracle cell. Its 20-state training-support union closes to 192 states and the
oracle-signature build compresses that closure to 8 cells (`24x`). The query-independent
exact LMB behavioural minimizer compresses 25 states to 5 cells (`5x`). The acceptance
threshold is checked separately on active states/cells
(`68/7` and `18/3`), so terminal aggregation cannot manufacture the pass. One frozen
RAPM per domain is then evaluated on held-out queries whose support is already covered;
held-out query contents cannot select the partition, and every registered row must
preserve both exact reward and exact failure.

The nontriviality gate is also joint: within one active cell, the same lifted training
policy graph must actually reach states from at least two different registered physical
automorphism orbits. Cell membership alone, or reaching one orbit member per query,
does not pass.

Reuse is claimed only across the registered two-domain held-out suite: G2048 varies
initial support/distribution and horizon, while LMB varies reward basis, horizon, and
risk. Neither domain is claimed to cover all four variation types by itself.

This closes the immediate “the cell is only a known symmetry orbit” weakness, but it is
still an exact-model/oracle positive control. It does not claim human-readable
predicate invention, oracle-free discovery of an unknown quotient, a shared
cross-domain coordinate system, or the full Phase 3 `60/20/40` aggregate Gate. A
successful bundle therefore reports `PHASE3A_SLICE_PASS` together with
`PHASE3_AGGREGATE_NOT_RUN`, never a full Phase 3 pass.

Ledger `V0-028` freezes the next additive slice,
`phase3b_portable_rapm_campaign_v0`. Unlike the G2048 Phase 3A oracle-signature
builder, its two domain models are synthesized only from complete exact one-step
reward-feature, failure/terminal, and successor behaviour. Construction cannot read
`Q*`, values/frontiers, selected policies, query reward/risk/horizon, or evaluation
results. The evidence for that boundary is the builder API/data flow plus static source
audits of the behavioural builder and portable planner; it is not a claim that the
entire Phase 3B runner has a closed import DAG. Each serialized RAPM contains its
coverage and content-addressed coverage ID, state planning kinds, partition, nominal
model, exact envelope, concretizer, reward-feature registry, `normalizer_rules`, and
goal IDs. Every rule has exactly `proof_id`, `kind`, `reward_basis`, and `feature_caps`,
with `kind=nonnegative_feature_caps_v1`. Each registered normalizer proof binds one
complete `reward_basis`: a unique,
feature-name-sorted vector of nonnegative exact raw weights containing every registered
reward feature, including zero-weight entries. A query's raw weights must equal that
basis exactly, so proof IDs cannot be reused across reward bases. The rule also supplies
nonnegative per-step and/or total caps for every positive-weight feature; every emitted
cap record has at least one non-null cap, while zero-weight features may be omitted. The planner
sums `weight * min(H * per_step_cap, total_cap)` over those features and rejects a
normalizer below that deterministic bound; normalized weights are exactly
`raw_weight / normalizer`. This registry does not authorize unregistered rewards or
non-`default` goal semantics. The three LMB proofs bind complete
`(match,terminal_clear)` bases `(1,1)`, `(1,0)`, and `(0,1)` for canonical,
match-only, and terminal-clear-only rewards respectively; they cannot be cross-used.

Every query occurrence is then loaded inside a fresh bubblewrap mount/network namespace
with only the staged `portable.py`, `portable_planner.py`, and `portable_runtime.py`, the
current read-only model/query pair, and an initially empty writable output directory.
The project checkout and other requests are not mounted; Python starts with `-S`, and a
content-addressed runtime attestation records the namespace, inputs, module origins,
and output hashes. The ground oracle remains an independent evaluation/fallback path.
Portable query schema v1 binds the raw and normalized reward weights,
normalizer/proof ID, risk, horizon, initial cell distribution, and the single currently
supported `default` structural stopping goal; new goal-dependent stopping semantics
require a later schema/model extension. The
registered campaign contains eleven genuine queries (six G2048 and five LMB), reuses
one unchanged model per domain, and includes multi-step planning in both domains. The
query-neutral fixed points compress G2048 `192 -> 10` states and `144 -> 17`
state-action pairs, and LMB `25 -> 5` and `40 -> 4`.

Running this Phase 3B profile requires Linux `bwrap` (bubblewrap). The standalone
portable planner itself remains Python-standard-library-only; bubblewrap is the campaign
runner's isolation dependency.

The independent verifier rebuilds both authoritative kernels, coverage closures, and
behavioural models, including the G2048/LMB normalizer-rule registries; reprojects every
ground query; recomputes the portable-envelope and
live ground audits, serialized-concretizer lift, and J0 comparison; checks IDs,
cross-links, isolation attestations, and exact counters; and can rerun the isolated
planner for each occurrence.

A passing campaign reports `PHASE3B_PORTABLE_RAPM_PASS` together with
`PHASE3_AGGREGATE_NOT_RUN`, `LOCAL_HYBRID_GATE_NOT_RUN`, and
`WORKLOAD_ECONOMICS_GATE_NOT_RUN`. It demonstrates no-Q/value-signature synthesis,
portable round-trip planning, in-coverage reuse, and exact-sound certification for this
registered workload. The Phase 3B bundle itself does not demonstrate automatic
predicate invention, certificate-triggered local hybrid repair, amortized break-even,
the full Phase 3 or Phase 5 Gate, scale, or learning.

Ledger `V0-029` freezes the additive contract-`0.8.0` execution profile
`phase3c_certificate_triggered_local_recovery_v0`. It reuses one immutable,
query-neutral, eleven-cell stage-1 aliased safe-chain RAPM for two queries. The
registered canonical `H=1, delta=0` query must remain `ABSTRACT_CERTIFIED`. The
canonical `H=2, delta=1/20` query must first fail its complete abstract certificate and
only then route to `LOCAL_GROUND_RECOVERY`.

The failed-proof frontier is formed from **direct** selected-action proof residuals,
not recursively accumulated ancestor bounds. For the `H=2` query it consists of the
two reachable `h=1` histogram cells with 12 ground states. The authorized local view
contains their 32 state-action pairs/128 outcomes. The strict ancestor dependency uses
only the selected abstract action's concretizer support: 8 pairs/32 outcomes. Thus total
authorization is `40 < 48` state-action pairs and `160 < 192` outcomes relative to the
same query's full all-action graph, and also `40 < 144` covered pairs. The isolated
repair process can read only an occurrence-bound request, the sanitized 32-pair
frontier slice (IDs and Bellman branches, with no state/action payload or accounting),
and a redacted abstract boundary carrying the ancestor handoff plus the value/risk
certificate scalars. It accepts a candidate only when both regret and risk pass. It
selects the unique
cardinality-minimal query-owned overlay: reopen only the eight-state
`(empty=1, histogram=((1,1),(2,2)))` cell, whose local action view has 16 available
state-action pairs/64 positive-probability outcomes, and freeze 8 patch decisions. The
patch must select different legal ground actions for reachable members that the base
cell aliases. The exact serialized RAPM and `BuildEpoch` bytes and their IDs remain
unchanged; replacing any of them is `REBUILD_REQUIRED`, not local recovery.

The stitched policy deliberately keeps the root and rare `(2,3)` decisions abstract.
Its post-repair sound failure upper bound is `397/20000 < 1/20`; exact lifted failure
is `317/16000`, reward is `3/64`, and normalized regret upper bound is zero. J0 failure
`99/5000` is opened only after the hybrid policy and post-certificate freeze, solely as
evaluation truth. No full fallback or rebuild is used. A passing run reports
`PHASE3C_LOCAL_RECOVERY_PASS`, `LOCAL_HYBRID_GATE_PASS`,
`PHASE3_AGGREGATE_NOT_RUN`, and `WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

This is evidence for certificate-triggered, strictly local recovery while preserving a
reusable abstract-primary world model. It does not claim predicate invention
(`grammar_used=false`), discovery of an unknown quotient, workload break-even, full
Phase 3/5, scale, learning, or cross-domain generality. Bundle SHA-256 manifests prove
content integrity and replay binding, not public-key source authenticity.

Ledger `V0-030` freezes the additive contract-`0.9.0` profile
`phase3d_general_local_recovery_v0`. It closes the three limitations intentionally left
by Phase 3C without changing that historical profile. Exact active Bellman derivations
and certificate slack reduce the safe-chain authorization from `40/160` state-action/
outcome records to `24/96`; only the eight-state common frontier cell is causal. A
trusted compiler then reduces the four-node/twenty-realization selected-policy boundary
to a worker capability with one frontier input, zero exits, one reward-min form, and
one risk-max form. The source graph and the equivalence/minimality evidence remain on
the trusted side.

The isolated standard-library worker performs one cap-aware global enumeration of
deterministic value/risk assignments instead of selecting minimum-risk actions state by
state. It exhausts 257 safe-chain assignments and, after the operational sound
post-audit, certifies reward `3/64` and risk upper bound `397/20000`. The separate
standalone-verifier evaluation lane performs the exact hybrid lift and reproduces exact
risk `317/16000`, with 8 patched and 12 retained abstract decisions. A separate
two-cell/two-member control exhausts 25 assignments and reaches
`(reward,risk)=(1,1/25)` under thresholds
`(3/4,1/20)`, while the old independent minimum-risk rule has value zero. Passing
returns `PHASE3D_GENERAL_LOCAL_RECOVERY_PASS`,
`GENERAL_LOCAL_RECOVERY_GATE_PASS`, `PHASE3_AGGREGATE_NOT_RUN`, and
`WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

This is a strong but finite claim: causal localization is limited to the current
earliest antichain, capability minimality is relative to the fully enumerated finite
port domain and sparse min/max-affine representation, and exact global search is
complete only under its declared caps. It is not automatic predicate/quotient
discovery, one-shot repair of dependent horizons, economics, scale, learning, or
cross-domain empirical generality. The next construction stage is workload economics
and dynamic routing; learned proposal/model synthesis follows only after that Gate.

Ledger `V0-031` additionally freezes the operational boundary between those two
profiles. Phase 3D must consume a complete, independently verified Phase 3C artifact
bundle through `--phase3c-bundle`; it binds the serialized RAPM, `BuildEpoch`, and the
local-query pre-certificate instead of calling the Phase 3C constructor. It also
consumes the verified source locality and authorization documents: the current 16-pair
causal frontier must be a strict subset of the source 32-pair frontier, while the
current 8 reverse-dependency pairs must exactly equal the source 8. The frozen
pre-certificate supplies the action-unrestricted reward upper bound, so operational
pre/post audits never rebuild ground `U_all`.

Binding may collect the complete 144-action namespace without evaluating a transition.
That frozen binding-time catalogue then supplies causal scoring, ancestor legality, and
capability costs; those stages make no new ground-action or ground-step calls before
authorization. Transition closure, partition, quotient, and portable-RAPM construction
also have exact zero counters, and `SuiteBuildCoverage.from_queries` is explicitly
forbidden on this path. After certificate failure, materializing the authorized causal
frontier performs exactly 16 ground steps; the patch-restricted sound post-audit performs
exactly 8 more. Thus the operational total is 24 ground-step calls, with zero accounting
steps and zero steps outside the authorized frontier or patched cells. The `24/96`
pair/outcome figure is the authorized capability scope (16/64 frontier plus 8/32 frozen
reverse dependency), not a claim that all 96 outcomes were re-executed.

The operational post-certificate records reward lower bound `3/64`, failure upper bound
`397/20000`, null exact-hybrid fields, and status
`EVALUATION_ONLY_NOT_RUN_IN_OPERATIONAL_RUNNER`. Exact hybrid lifting is deliberately
absent from the operational runner. The standalone independent verifier may perform that
evaluation-only replay, yielding exact failure `317/16000`, 8 patched decisions and 12
retained abstract decisions, and may invoke J0 after the operational artifacts are
frozen.

The Phase 3D bundle therefore embeds byte-identical
`safe_chain/base_portable_rapm.json` and `safe_chain/base_build_epoch.json`, together
with `safe_chain/source_phase3c_run.json`,
`safe_chain/source_phase3c_manifest.json`, and
`safe_chain/source_phase3c_local_pre_certificate.json`, plus
`safe_chain/source_phase3c_locality.json` and
`safe_chain/source_phase3c_authorization.json`. The standalone verifier still
rebuilds authoritative semantics to detect coordinated forgery, but that work is an
evaluation-only lane and is never counted as operational planning or recovery.

Ledger `V0-032` freezes the contract-`1.0.0` accounted dynamic-routing profile. The
current non-official implementation now goes beyond schema-only preconstruction. Its
one-decision `run_phase3e` consumer accepts a frozen RAPM/failed-plan authority package,
binds every preselection read to the exact RAPM, BuildEpoch, failed-certificate,
selected-plan, action-catalogue, frontier/proof-or-typed-null, cardinality, cap,
formula, and comparison-profile identity, and freezes a semantically replayed strict-
dominance decision before route execution. The charged semantic authority is an exact
dependency closure: the decision must reference the causal result and both route
uppers, each upper must have exactly one matching cardinality verification, and missing,
duplicate, or extraneous results fail closed. The runner executes only the selected
route, preserves native execution and verification work separately, and checks their
exact eight-axis aggregate against the selected upper. Binding the failed certificate's
identity inside this generic runner does not itself mint `ABSTRACT_AUDIT` authority;
the model-only source/plan/proof/audit chain supplies and replays that authority before
the H2 handoff.

The registered safe-chain positive control exercises a genuine LOCAL path. Frozen
Phase 3D metadata supplies the causal/cardinality evidence without a ground transition;
the local upper strictly dominates the isolated-fallback upper; and only after freeze
the adapter performs `16/64` materialization steps/outcome rows, launches the isolated
finite-domain worker, stitches its overlay, and performs an `8/32` sound post-audit.
The result is independently typed as `CANDIDATE_FOUND` then `CERTIFIED` and remains
within its preregistered upper. Capability, worker result, stitched plan, and post-audit
certificate are bound to their exact declared IDs; a `SEARCH_CAP_EXHAUSTED` or
`NO_FEASIBLE_ASSIGNMENT` worker result instead closes the legal short
materialize→compile→worker prefix without fabricating stitch/post-audit artifacts and
can proceed only through a fresh fallback decision. The companion capped ground
fallback has exact safe-chain cardinality and result authority and isolated process/
resource accounting.
Its worker revalidates the frozen Phase 3C manifest/query/BuildEpoch/action catalogue/
RAPM, performs the complete `48`-transition/`192`-outcome search with `5696` Bellman
backups, and returns `FEASIBLE_CERTIFIED` without host solver replay. The historical
callable adapter that cannot produce the required isolation evidence is rejected.

The generic occurrence layer can preserve up to two continuous local transactions. A
failed transaction-1 post-audit requires a deeper frontier, a newly stitched plan
identity, fresh common work/cardinalities/uppers/decision, and complete semantic
authority. That fresh decision may select LOCAL transaction 2 or execute direct
FALLBACK immediately; the fallback branch does not fabricate a second local
transaction. A negative local worker closure likewise enters a new fallback decision.
Terminal and occurrence replay bind the actual runner aggregate, route evidence,
freeze/access identities, and every retained work component, so a cheaper valid
WorkVector cannot be spliced onto a certificate. These controls are exercised as a
generic orchestration path, but there is not yet a registered live benchmark whose
first sound post-audit fails and whose deeper second decision completes. The canonical
H2 transaction 1 now certifies, so transaction 2 is unreachable on that fixture; a new
dependent-horizon benchmark is required rather than another patch to canonical H2.

Ledger `V0-033` closes the four former scoped P0 plumbing gaps without changing this narrow
claim. Operational accounting can now seal a common-prefix or route-execution core,
freeze the exact semantic/nonsemantic verification obligations, materialize their
operational suffix, and bind the reducer-correct aggregate in an exact manifest and
receipt. Missing, duplicate, substituted, padded, stale, pre-plan, or wrong-lane
charges fail replay. Aggregate `WORK_VECTOR`/`ACTUAL_PROJECTION`, route/attempt
terminal classification, and occurrence-terminal authority are invoked in the
standalone evaluation lane, so they verify an
already closed operational aggregate without recursively charging themselves into it.
Registered nonsemantic checks no longer accept caller-selected evidence IDs: each
check kind consumes typed live evidence and recomputes access/freeze reconciliation,
execution-vector integrity, native aggregation, selected-upper compliance, or prior-
run continuation authority. Verification-source CounterRecords must also be disjoint
from the sealed core, preventing the same observation from being charged twice.
If a continuation package is rejected after some operational verifier calls but before
a complete receipt exists, `PARTIAL_ACCOUNTED_COMMON` preserves exactly those observed
semantic/nonsemantic records and reducer-replays them with the common core. It is a
fail-closed occurrence-accounting kind, not a successful two-stage receipt or
continuation authority, and it cannot pad unobserved work.
The selected-route WorkVector authority is minted by the one-decision runner and
transported from its immutable history into transaction-2 or fresh-fallback
authorization; continuation planners no longer have a prior-work substitution seam.

The additive sealed-executor profile binds an inert executor recipe and an exact
runtime-tree manifest before route selection. `RuntimeFactoryCardinalityV1` derives
the exact file/byte/manifest cardinalities and factory counter upper from that manifest
and its `RuntimeManifestCapProfileV1`; the separate sealed
`GroundFallbackCapProfileV1` partitions the route-wide fallback cap between factory
and worker. Each sealed candidate route binds a route-specific
cardinality source, so both compared uppers reserve factory work without consulting
actual route work; after selection the factory rechecks the selected source/upper
chain. For the registered sealed safe-chain fallback this is one route-wide cap:
`control.cap_checks=5815`, split before selection into the factory reserve `3` and
the fallback worker allowance `5812`. The upper therefore remains `5815`; the
factory charge is not appended a second time. Historical unsealed profiles keep
`reserved_route_cap_checks=0`, omit that field from their payload, and retain their
original schema, domain and content identity. Only after the typed route freeze may a
single-use factory resolve and byte-verify the preregistered CAS tree, create a private
read-only lease, and construct the selected executor. It rejects preconstructed legacy
callables, live-checkout fallback, foreign recipes, symlinks, extra files, byte changes,
pre-freeze construction, and factory reuse. Runtime snapshot creation is build/rebuild
work, not a query preselection operation. On success, the construction receipt binds
`postconstruction_access_event_log_id` and exact factory work; the runner requires that
ID to equal the final selected-route `AccessEventLogV1` in the returned
`Phase3ERunResultV1`.

Selected-route exceptions with one uniquely replayable native-work ownership chain
produce a typed noncertificate carrying the available
execution/verification work, marginal aggregate, context/decision/upper, freeze/access
evidence, and exception classification. The occurrence result boundary independently
reconstructs its ordered aggregate and binds each completed run and transaction before
accepting the terminal; reordering, splicing, rehashing, closure relabelling, or reuse
of an old terminal authority fails closed. Python-level local-adapter failures also attach
and fail-close the adapter-owned recorder. Local materialization, compilation, launch,
solver, and post-audit counters, and fallback staging, launch, worker-native, and output
counters, are charged incrementally so a later exception cannot erase already observed
work. A sealed failure additionally carries `SealedExecutorFailureMergeProofV1`: the
factory partial WorkVector/comparison/projection triple, either a complete delegate
triple or typed nulls, and the exact merged partial triple. Its companion failure
evidence binds runtime/recipe/cap/constructor identities, the registered failure stage,
freeze, merge proof, and final post-failure access-log ID. Replay rejects source,
subject, reducer, stage, registry, or log substitution. This does not invent
unobservable work: an abnormally terminated isolated child still requires durable
child-side streaming before its incomplete internal work can be claimed. The exact
merge is currently replayed inside the failed-route/occurrence boundary; it is not yet
a separate FQ7 semantic attestation or manifest-level independent-verifier result.

The occurrence runner now catches that scoped route-level exception, preserves all earlier
successful common/marginal pairs plus the exact failed prefix/partial marginal, and
replays one occurrence aggregate. Successful replay mints a typed logical-occurrence
`Phase3EOccurrenceTerminalArtifactV1` under the evaluation-lane
`OCCURRENCE_TERMINAL` authority. A selected-route exception closes as
`ATTEMPT_CLOSURE_NONCERTIFICATE.PROTOCOL_FAILURE`; fallback-cap exhaustion closes as
`ATTEMPT_CLOSURE_NONCERTIFICATE.FALLBACK_CAP_EXHAUSTED`. Both have plan and
infeasibility counts zero, noncertificate count one, and all three denominators
retained. Neither can be relabelled as a plan or infeasibility certificate.

This is an authority-gated vertical slice—not an official Phase 3E run. Ledgers
V0-036/V0-037 connect an isolated H2 model-only `ABSTRACT_AUDIT=FAIL` through an
honestly accounted `ABSTRACT_FAILED_PREFIX`, opaque ground handoff, no-replanning
proof/frontier translation, production route cardinalities and uppers, strict
marginal selection, exactly one selected post-freeze factory, and a scoped successful
LOCAL terminal/occurrence closure. The unselected route is rejection-only. The
preparation trace now accounts for exactly 4 causal, 18 protocol, 3 integrity and 5 cap
events, but its incremental and aggregate vectors are retained post-core and not yet
occurrence-charged; global content-hash and I/O work remain incomplete, so
`official_execution_allowed` remains false.

The independent H2 selected-route bundle now has 54 fixed roles and verifies only
`VERIFIED_LOCAL_ROUTE_ACCOUNTING_AND_TOPOLOGY`; it cannot mint the semantic certificate
from transport. The planner-free exact-cache
preflight compares all source-derived identity coordinates but cannot authorize
infeasibility until a durable kernel-bound complete-search proof and independent
verifier exist.  Runtime authority is now exact-live and internally minted rather
than a token copied inside a dataclass: semantic/protocol results, prepared estimates,
continuations, trusted local/fallback provenance, occurrence/campaign/cache/workload
handles reject copy, replacement, member substitution, and cross-role reuse.

Complete native hash/I/O/runtime instrumentation, durable/serialized semantic proofs,
a new dependent-horizon transaction-2 fixture, operational rebuild semantics, full
campaign/workload replay, the later scalar economics revision, and ultimately
feature invention and general automatic RAPM synthesis beyond the registered LMB
grammar remain open. See
`specs/PHASE3E_PRECONSTRUCTION_LIMITATIONS.md` for the exact boundary.

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

## Scope

Phase 0.5 contains no neural encoder, learned model, MCTS, option, first-hit
reduction, POMDP adapter, or vision component.  Those remain gated extensions.
The inherited Laplace snapshot in `third_party/` is isolated and checked by the
legacy gate; it is not silently imported as if its spatial abstraction were a
semantic quotient proof.

Construction established that the original tiny G2048 query is ground-infeasible
at every registered positive risk threshold. It is retained as the explicit
soundness/fallback regression, while a separately keyed safe-chain fixture provides
the feasible positive-test route. The resulting decisions and exact regression values
are published normatively as ledger entries `V0-019` through `V0-024`; the ignored
discussion files are historical provenance, not required public documentation. The
`V0-024` baseline performs no CEGAR split and is not evidence of automatic symmetry or
predicate discovery.

The query-owned initial-support implementation and coverage-specific build identity are
frozen by ledger `V0-025`; resolved `V0-RISK-003` is no longer an open construction
blocker. The executable aliased refinement contract and its narrow claim boundary are
frozen separately by ledger `V0-026`. The cross-automorphism, train/held-out Phase 3A
construction slice and its still-oracle-bound claim boundary are frozen by `V0-027`.
The primary reusable-world-model objective, workload/build-epoch semantics, route and
cost equations, and the immediate portable Phase 3B campaign are frozen by `V0-028`.
The first certificate-triggered local-recovery execution slice and its direct-frontier,
isolation, immutable-base, overlay, replay, and narrow-claim rules are frozen by
`V0-029`.
The slack-aware causal family, sparse worker capability, and cap-aware joint value-risk
recovery contract are frozen by `V0-030`; it resolves `V0-RISK-004..006` only within
the registered finite Phase 3D scope.
The verified frozen Phase 3C-to-3D consumption boundary, source provenance topology,
zero-build counters, and evaluation-only verifier reconstruction are frozen by
`V0-031`.
The contract-`1.0.0` accounted dynamic-routing design is frozen by `V0-032`: full
domain-separated identities, native counter completeness, strict shared-axis marginal
route selection, typed evidence/terminal authority, trusted cap replay, no host full
replay, and estimate-before-execute access order. This is an implementation contract,
not an official Gate result; `official_execution_allowed=false`, scalar cost and
break-even remain null, and both counter-completeness and workload-economics Gates
remain `NOT_RUN` until every registered path and independent attack test passes.
Ledger `V0-033` additively freezes the two-stage non-self-referential accounting rule,
invocation-typed terminal evaluation, runner-owned continuation WorkVector authority,
content-addressed post-freeze executor construction, and typed occurrence-failure
aggregate described above; it opens no Gate and changes no historical result.
The current implementation provides the scoped integrated local and fallback vertical
slices, registered-safe-chain causal/cardinality authority, generic route-upper and
decision replay, route-result/post-audit authority, a scoped LOCAL terminal/occurrence
closure, a 54-role accounting/topology bundle verifier, bounded rebuild/retry mechanics,
and generic two-decision control. It still lacks durable planner-free cached-
infeasibility authority, serialized inputs for independent semantic certificate replay,
a dependent-horizon transaction-2 benchmark, complete all-path hash/I/O/runtime
instrumentation, semantically authorized operational rebuild/retry, integrated full
campaign/workload execution, and a semantic/campaign bundle verifier. FQ12 deliberately
keeps the official scalar and `N_break_even` null: vector prefix and componentwise
worst-frontier mechanics may proceed, but scalar crossing is deferred to a later ledger
revision.
The earlier profiles retain their original claims and are not retroactively relabelled.

The current K7 accounting-construction edge has executable archive-only role
bootstraps, a fixed broker resource topology, from-birth role sandbox material,
one-shot launch records, kernel-credential packet authentication and raw
read/stage/mount journals. These pieces have not yet been joined into the one
complete production broker envelope, so the nine semantic resolutions and
formal `CounterRecord -> WorkVector -> ComparisonVector` chain remain locked.
The resource graph now transfers irreversibly to a runtime owner, and all nine
shared paths have raw internal replayers. They have not yet been joined into
one production live envelope: the actual worker first-role output join,
path-specific semantic replayers, and the atomic formal vector materializer
remain required.

The role bootstrap now installs and verifies post-exec denial from the exact
sealed-archive sandbox module before importing either role entry; a one-shot
archive/role/PID/FD-bound attestation gates all common/core imports.

The complete nine-source adapter now preserves each source journal's honest
local closure while binding all paths to one runtime attempt and measurement
window; it does not pad unequal event counts or treat that structural join as
numeric semantic authority.

The successor verified-nine envelope now executes all nine registered semantic
replayers and freezes exact per-path materialization authorizations under that
same runtime identity. Formal accounting remains locked until the 114 explicit
native-zero, 71 owner-emittable and eight derived paths also close.

The owner-event successor now independently replays the complete production
five-stage chain and exact loaded source inventory, closing all 89 operation
sites into 71 nonformal path candidates.  Missing events are never inferred as
zero; only a complete owner window may issue a zero candidate.  Formal
accounting remains locked pending the 114 profile-zero, eight derived and
atomic 202-path joins.

The eight derived-only equations now have a replayable DAG. Process outcomes
and solver-stage exclusion are semantically closed; route outcomes remain
explicitly blocked until the production business-result bytes and the complete
native transcript share one stronger terminal authority. No incomplete DAG
result can enter a formal vector.

Contracts `2.0.42` and `2.0.43` now freeze honest migration inventories for
the canonical raw infeasible fallback and real abstract-PASS path. The fallback
retains 13 exact V1 source values but all 202 V6 paths remain formally blocked;
the abstract path independently partitions all 202 blockers without promoting
legacy aggregates, events, reconciliations or an unmeasured mounted peak.
Neither contract creates a production CounterRecord, vector, terminal,
certificate or Gate result. See
[`specs/K7_CANONICAL_INFEASIBLE_FALLBACK_RAW_ACQUISITION.md`](specs/K7_CANONICAL_INFEASIBLE_FALLBACK_RAW_ACQUISITION.md)
and
[`specs/K7_ABSTRACT_PASS_RETAINED_V1_EVIDENCE_INVENTORY.md`](specs/K7_ABSTRACT_PASS_RETAINED_V1_EVIDENCE_INVENTORY.md).

Contract `2.0.44` adds a separately versioned, single-stage V6
`DIRECT_FALLBACK` construction chain and an exact seven-site source manifest.
It validates owner/gateway binding, immutable positive-event chaining and
failure-prefix retention without changing the frozen five-stage V1 runtime.
Its seven source methods are explicitly a test shim rather than fallback
business primitives, so the profile issues no production owner evidence or
accounting artifact. See
[`specs/K7_DIRECT_FALLBACK_ROUTE_SEGMENT_CONSTRUCTION_V2.md`](specs/K7_DIRECT_FALLBACK_ROUTE_SEGMENT_CONSTRUCTION_V2.md).

Contract `2.0.45` replaces that shim with an independently copied real exact
fallback whose seven ledger primitives own the corresponding positive events.
The route session is bound to one ledger and the exact authorized search
frame; each counter mutation requires a recorded-event acknowledgement, and
the 208-event canonical H1 chain is reconciled before return and completion.
The production-owner source/runtime binding has independent mutation-boundary
coverage, but the result still stops before the nine shared-resource receipts,
formal 202-record accounting, FQ9 terminal and occurrence closure. See
[`specs/K7_DIRECT_FALLBACK_PRODUCTION_OWNER_SLICE_V2.md`](specs/K7_DIRECT_FALLBACK_PRODUCTION_OWNER_SLICE_V2.md).

Contract `2.0.46` adds the next pre-execution blocker: durable proof/current
identity and typed access-order replay produce an exact 182-leaf candidate
(`166+7+9`) and exactly eight comparison axes. The nine shared-resource rows
are finite but not yet enforced by the selected runner, so the object remains
`FINITE_ADMISSION_CAP_CANDIDATE` with route selection, execution and formal
actual-compliance disabled. See
[`specs/K7_DIRECT_FALLBACK_ROUTE_UPPER_V6.md`](specs/K7_DIRECT_FALLBACK_ROUTE_UPPER_V6.md).

Contract `2.0.47` implements the bounded nine-path cap mechanics behind that
blocker. One issuer-owned construction session atomically reserves SUM work,
retains working/mounted MAX peaks, admits only named sandbox staging and
preserves all failure prefixes under mutation and callback attacks. Its
source-site registrations remain explicitly unverified and no formal V7
decision or production runner consumes it, so the V6 candidate and all Gates
remain locked. See
[`specs/K7_DIRECT_FALLBACK_SHARED_CAP_AUTHORITY_V1.md`](specs/K7_DIRECT_FALLBACK_SHARED_CAP_AUTHORITY_V1.md).

Contract `2.0.48` freezes the exact nine successor source sites and the typed
aggregate-evidence formula schema. It deliberately emits no numeric upper:
paired count/extent, mount intervals, whole-route output fixed point, cgroup
peak plan and launch-cardinality authorities are still required. Its
manifest-bound join derives all site IDs from independently replayed canonical
bytes, closing manifest/site splicing without promoting the historical generic
cap factory. Live owner wiring, V7 routing, formal vectors and all Gates remain
locked. See
[`specs/K7_DIRECT_FALLBACK_SHARED_SOURCE_MANIFEST_V1.md`](specs/K7_DIRECT_FALLBACK_SHARED_SOURCE_MANIFEST_V1.md).

Contract `2.0.49` adds the separate production-only cap boundary but keeps it
permanently `V7_AUTHORITY_PENDING`. The issuable engine is an exact immutable
tuple of nine non-callable owner sentinels; it contains no mutable backing,
callback, receipt/event mint or private transaction path. A later V7 adapter
must independently bind the formal route decision and semantic aggregate
evidence before executable owner methods can exist. See
[`specs/K7_PRODUCTION_SHARED_CAP_ENGINE_V2_LOCKED.md`](specs/K7_PRODUCTION_SHARED_CAP_ENGINE_V2_LOCKED.md).
