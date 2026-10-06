# V267: held-out query-family transfer

V266's action-agreement rule was evaluated on the same three queries that
controlled module reuse. V267 separates those roles. It replays the paired
V266 streams with the same 48 fit and 16 audit observations per operator and
freezes three new probe queries:

* `moderate_risk = (1,2,2)`;
* `high_goal = (1,1,6)`;
* `strict_risk = (1,6,2)`.

`PRIMARY_AGREEMENT` reuses a module only when the original reward/risk/goal
queries agree. `ALL_QUERY_AGREEMENT` requires agreement on all six queries.
RESET and GLOBAL remain controls. The current phase is compared with historical
modules before its fit prefix is merged; the final audit suffix never enters a
model. Primary and held-out policy correctness, exact regret, assignments and
candidate checks are reported separately.

This is a paired held-out-query diagnostic, not a new interaction experiment.
It tests whether the current consequence module contains reusable information
beyond the queries used to gate reuse. No confidence certificate, scientific
Gate or U006 assurance is involved.
