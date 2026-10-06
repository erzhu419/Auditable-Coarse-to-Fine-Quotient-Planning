# V269 factorized residual consequence protocol

V268 showed that a joint detour/retry table adds finite-sample noise. V269
tests a different structural hypothesis without changing the V266 assignment:
the current context has a 48-row local posterior, while a prior context
distribution supplies a fixed baseline for the same operator and category.

For each operator, the local 48-fit counts receive Jeffreys `1/2` mass plus a
baseline posterior weighted by the frozen doubled-count parameter
`KAPPA = 48`, equivalent to 24 categorical pseudo-observations after
normalization. `FACTORIZED_MODULE` uses the selected V266 module's history as the
baseline; `GLOBAL_SHRINK` uses all previous contexts. With no history, KAPPA
is zero and the estimator is exactly RESET. The current context is never added
to its own baseline. The 16-row audit suffix never updates any estimator.

The four arms are RESET, LOCKED_MARGINAL (the V266 action-agreement module),
GLOBAL_SHRINK, and FACTORIZED_MODULE. No weather or phase label is used as a
feature. Exact weather laws are used only for post-hoc scoring. The experiment
replays the same four seeds and `48 fit + 16 audit` streams and is exploratory;
it does not reopen the original Gate or start U006.
