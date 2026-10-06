# V265: fair-prefix consequence library with explicit abstention

V263/V264 are retained but their arm comparisons were invalid: GLOBAL saw 64
observations per operator before scoring while RESET saw 48, and LIBRARY
committed its audit suffix. V265 fixes that accounting and tests the next
representation change, an explicit applicability decision.

Each of four fresh lifecycles uses `A0=normal`, `B=wet`, `A_prime=normal`, and
`C=blocked`, opaque context IDs, and 64 draws per operator. Every arm is scored
from exactly the first 48 draws per operator; the final 16 are audit-only and
never update a module. The first 32 draws are the guarded arm's assignment
prefix and draws 33–48 are its routing check. All arms share the same streams.

`RESET` fits only the current 48-draw prefix. `GLOBAL` pools current and prior
48-draw prefixes into one module. `LEGACY_LIBRARY` is the corrected V263
splitter: it selects the closest existing module by fit-prefix Brier score and
creates a module if that score exceeds `1/2`. `GUARDED_LIBRARY` compares the
best existing module on the routing check with a local current-episode model.
It reuses only when the existing module is within the fixed ambiguity margin
`1/20` of the local model and below the `1/2` split threshold; otherwise it
abstains from transfer and creates a new module. The last 16 draws are scored
afterward but remain outside every model.

The three fixed queries are reward `(1,0,0)`, risk `(1,4,4)`, and goal
`(1,0,4)`. Primary descriptive outputs are policy correctness, exact regret,
module assignment, and audit Brier score. This is a development comparison,
not a scientific Gate or a confidence certificate.
