# V263 persistent consequence library results

V263 is the first small implementation of the new multi-episode direction:
store action-conditioned reward/failure/success consequences, validate a new
opaque episode against the existing modules, and replan for each query instead
of retaining a fixed action label. It is exploratory and has no scientific
Gate.

The frozen four-phase lifecycle used 64 samples for each of the three route
operators per phase, with 48 fit observations and 16 held out for validation.
The phases were `A0=normal`, `B=wet`, `A_prime=normal`, and `C=blocked`; weather
was hidden from the learner. The fixed split threshold was Brier score `1/2`.
All three query weights were evaluated at the same fit checkpoint: reward
`(1,0,0)`, risk `(1,4,4)`, and goal `(1,0,4)`.

| arm | correct query policies | exact regret sum | structural behavior |
|---|---:|---:|---|
| `RESET` | 11/12 | 0.15 | relearns each phase; misses `A_prime` goal |
| `GLOBAL` | 10/12 | 0.9835 | one pooled module; misses `A_prime` risk and `C` goal |
| `LIBRARY` | **12/12** | **0** | splits at `B`, reuses the original module at `A_prime`, and keeps two modules through `C` |

The persistent arm used 768 local categorical observations in total. It created
one module at `A0`, triggered a second module from the held-out `B` disagreement,
reused the first module for `A_prime`, and reused the second module for `C`.
The last reuse is a useful limitation: the current splitter can preserve the
right query policy without proving that a module's mechanism identity is
correct. The validation Brier scores and assignments are retained in
[`summary.json`](persistent_consequence_v263/summary.json).

**Post-run accounting correction:** the original runner did not provide a
fair arm comparison. `GLOBAL` merged all 64 observations per operator before
scoring while `RESET` used 48, and `LIBRARY` committed its validation suffix
before scoring. The table above is retained as an execution record but must
not be treated as evidence of a library gain. V265 corrects this by scoring
all arms from the same 48-observation prefix and keeping the final 16 draws
audit-only.

The run itself exited 0 with zero-byte stderr. The focused regression suite
passed 4/4 tests. It does not establish general strategic learning, sampling
efficiency, a confidence certificate, or any improvement to the original Gate.

Protocol: [`PERSISTENT_CONSEQUENCE_LIBRARY_V263.md`](../specs/PERSISTENT_CONSEQUENCE_LIBRARY_V263.md). Implementation:
[`persistent_consequence_library_v263.py`](../src/acfqp/science/persistent_consequence_library_v263.py).
