# V74: sharing action effects before successor expansion

Frozen 2026-09-13 before the main cohort executes. Reuse the V69 learned rule,
32 H3/H4 roots, 14 queries, and exactly V73's 95 observation inputs. Run once
per root in rotating order, with four independent, cold compiler/worker arms:
BASE = V72 COMPOSED_LOCAL; LATE = V73 DIRECT_GROUP; EARLY = direct H2 construction
with shared per-action effects; SHARED = EARLY plus repeated H2 successor reuse.
No new source fit, target labels, or query-dependent tuning.

EARLY tests each action's current legality before looking up its effect. An
exact effect key retains ordered output lines and their integer score
contributions. Its value is total reward and the status for each spawn rank.
For the existing proven vacancy family (at least three holes before patching),
each legal move still leaves at least two holes: line scores and goal indicators
suffice without output adjacency. Keep this family separate from exact keys.
Only cache misses perform reward summation and terminal predicates. Output
geometry alone never establishes action legality. The final H1 contract still
retains the original action labels, rewards, and exact Fraction status mass.

SHARED reuses immutable spawn-group results for identical action-afterstate
row tuples within the same frozen-rule compiler. The current incoming action
reward remains outside that result. This can skip entire candidate scans;
it does not equate unequal H2 geometries. Preserve first occurrence order to
retain V69 cell IDs. Export only H>2 labels for the three direct methods and
route H1/H2 using each arm's own compiler and the exact saved kernel.

Primary mechanism comparisons: EARLY/LATE for predicate sharing, SHARED/EARLY
for avoiding repeated successor scans. Compare complete costs to BASE as well.
Count actual line rewrites, effect-key scans/hits, reward/terminal predicates,
spawn candidates, group reuse, retained group entries, and Fraction work.
Count distinct H2 geometries plus higher concrete states; flat-to-row changes
are not abstraction. The unchanged 200,000 geometry cap applies to all arms.

Cost includes compiler/cache creation, model construction, export, cold process
startup, loading, routing indices, all matched routes, 14 plans, result writing,
and cleanup including caches. One actual common terminal-rule compilation is
attributed once to each method. Source learning is historical. Verification
is recorded separately; nested stage timings must not be added twice.

Save all arm artifacts before comparison. Require exact old kernels/cell IDs,
policies/values/planning counts, expected high labels, and all actual routes.
Independently audit all 15,209 old active observations for LATE, EARLY, and
SHARED. Inherit the 448 optimal root queries and 1,227 strict query switches
only after all 32 roots preserve these artifacts. Reuse the retained V73
16-board H2 oracle: save all new EARLY/SHARED predictions before reading its
ground contracts, then compare exact nested two-step distributions. These
are repeated observations, not new samples; count zero new ground calls.

Run focused legality/risk/sharing checks and a small H3 integration before
the main cohort. Record failed attempts without overwriting or tuning on the
main results. Adoption requires exact preservation and lower complete cost;
report the mechanism counters and H3/H4 costs so aggregation cannot hide a
regression. Timing is a single descriptive run. General strategic learning
and unequal-geometry H2 abstraction remain open. U005 FAIL, U006 unstarted,
and closed historical candidates remain unchanged.
