# V263: persistent query-reusable consequence library

> Retired as an arm-comparison protocol. The implementation committed the
> validation suffix before scoring `LIBRARY` and gave `GLOBAL` more observations
> than `RESET`. V265 is the corrected shared-prefix protocol; V263 outputs are
> retained as an engineering record only.

## Question

After V262 closed the targeted-row route, can a learner retain action-conditioned
reward, failure and success consequences across opaque episodes, split a module
when a frozen validation prefix disagrees, and replan when the query changes?
This is a local development diagnostic. It does not reopen U005, start U006,
or change the original scientific Gate.

## Frozen lifecycle

The simulator supplies four fixed phases with one opaque context identifier per
phase: `A0=normal`, `B=wet`, `A_prime=normal`, and `C=blocked`. Weather is used
only for post-hoc scoring; the learner sees no weather label. Operating cost is
`low`, retry cost is `19/20`, and the route operator supports are fixed by the
V205 task. Each operator receives 64 categorical observations from a fresh
seeded stream. The first 48 observations per operator are the fitting prefix;
the last 16 are a held-out validation suffix. No simulator probability or
optimal action is supplied to a learner.

The persistent library starts with no modules. It assigns a phase to the module
with the smallest fit-prefix categorical Brier score. It creates a new module
when that score is above the predeclared `1/2` weak-prior threshold, then scores
the validation suffix before committing it. The module is a posterior over
action-conditioned outcome rows and is queried through the reusable
`(reward,failure,success)` consequence vector. Query weights are fixed as
`reward=(1,0,0)`, `risk=(1,4,4)`, and `goal=(1,0,4)`.

## Arms and measurements

* `RESET` fits only the current phase and discards it afterward.
* `GLOBAL` pools all phases into one persistent module.
* `LIBRARY` keeps the frozen module assignment/split procedure.

Every arm is scored at the same fit checkpoint after 48 observations per
operator. Report predicted policy, exact post-hoc policy, exact regret, module
count, observations, and validation Brier score. The four-phase sequence is a
single development lifecycle, not four independent episodes or a confirmation
cohort.

The intended diagnostic is structural: a useful library should reuse the first
normal module at `A_prime`, create or select a different consequence module for
`B`, and preserve query-dependent action changes. A positive observation here
only justifies a larger frozen lifecycle; it is not a claim of general
strategic learning or sampling efficiency.

## Accounting and limits

All 768 categorical draws are local simulator interactions. Fit, validation,
module assignment, posterior construction and query scoring are reported as
local computation; exact weather laws are read only for audit metrics. No
server data, checkpoints, assurance identity or old Gate evidence are used.
The route grammar is supplied and finite, and the module posterior is not a
confidence certificate. V262's negative result and the historical U005 FAIL are
retained unchanged.
