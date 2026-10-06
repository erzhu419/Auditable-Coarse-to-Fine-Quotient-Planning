# V257: coupled risk-constrained impossibility on paid snapshots

Question: can the original full D-row confidence region certify the16 V256
query-ready but execution-unresolved targets without further observations?
Use the completed, independently valid V256 artifact as immutable evidence.
Freeze all6 life/arm jobs, all432 terminal targets and all949 initial/member
plan snapshots; primary roster is the16 TRAJECTORY_REUSE B terminal targets
with query_certified=true and execution_resolved=false. Selection uses those
retained observable decisions, never oracle utility. Include both arms and
every retained snapshot in the false-impossibility check.

Change only the deterministic goal-impossibility upper bound. Do not change
query evidence, execution mix, acquisition/stopping histories, risk1/20, goal2,
native event labels, pool threshold720 or member threshold8640. No new samples,
events or alpha: all bounds are functions of the same confidence regions.
Source/pool/member/actual execution costs remain the previously paid V256 fees.

For each snapshot regenerate the original box/simplex vertices and four
policy rectangles (r_min, g_max), where g=reward+4*delivery. Obtain lambda_old
by minimizing lambda/20+max_p(g_max_p-lambda*r_min_p) exactly over lambda0 and
all nonnegative intersections of the four lines. Choose the smallest lambda
on objective ties. This is the old LP's exact dual, not a tunable grid; require
its value to equal the retained old goal_upper.

Keep a paired-box reference at that same lambda using complete vertex-policy
(risk,goal) pairs. It is a valid relaxation upper bound, not the exact optimum
over a single shared unknown kernel. The primary new method uses the original
D joint-CS intersection from plan.joint_constraints[D], with q equal to the
retained R DELIVERY upper bound. With s equal to S DELIVERY upper and costs
cS,cD,cR, calculate:

    WAIT: 0
    SHORT: -cS-lambda+(4+lambda)*s
    RETURN: -cD+support_D(DELIVERY:4, LOST:-lambda, RECOVERY:0)
    RETRY: -cD+support_D(DELIVERY:4, LOST:-lambda,
                         RECOVERY:(4+lambda)*q-cR-lambda)

RETRY is monotone in q because D_RECOVERY>=0 and4+lambda>0. S/R are binary,
so their retained marginal projections enclose the original regions. Use the
unchanged V230 support proposal and outward weak-dual witnesses for both D
directions. Optimizer status or a primal suggestion never certifies a bound.
The joint candidate is lambda/20 plus the largest branch. Final new upper is
min(old upper, paired-box upper, joint candidate), all valid simultaneously on
the original confidence event. Certify impossibility only for strict upper<2.
No new search for lambda after evaluating the full-region supports.

Retain exact lambda/rectangle/paired-point proofs, original snapshot references,
D coefficients and every support witness, branch values, candidate/final bounds,
and per-stage/life/type counts. Retain all16 full member histories and earliest
newly certified prefix. Freeze every bound before posthoc true-law scoring.
Independent audit must not import the V257 producer/core; recompute old LP,
paired-box bounds, branch coefficients, all outward D dual proofs and exact
final values using established independent mathematics. Verify evidence/source
references and zero new observations, then true risk-constrained optima.

Primary outcome: newly acquired terminal impossibility certificates out of16.
The bottleneck is fully addressed only if all16 obtain certificates, every
new bound is no looser than its old bound, zero false impossibility claims hold
across all949 snapshots, and independent audit is valid. Report partial or zero
improvement unchanged. Do not alter the method or threshold after seeing data.
Earlier certification in a retained history is a same-evidence diagnostic;
removing those observations would change later pools, so it is not a measured
lifecycle cost saving. A fresh prospective lifecycle would be a separate stage.
Report computation cost and bound reduction; no new interaction-saving claim.
V256 stays frozen and passed. Original scientific Gate FAIL; U006 unstarted.
