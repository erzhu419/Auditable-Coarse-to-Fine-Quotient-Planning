# V266: query-action agreement for consequence-module reuse

V265 showed that Brier-based abstention can prevent harmful transfer but does
not improve over rebuilding. V266 changes only the applicability rule. It uses
the paired V265 streams and the same four phases, 48 fit observations and 16
audit-only observations per operator. No new simulator data are drawn.

For each new opaque phase, the current local posterior is compared with every
existing persistent module on the three frozen queries: reward `(1,0,0)`, risk
`(1,4,4)`, and goal `(1,0,4)`. A module may be reused only when its complete
optimal-action set agrees with the local model for all three queries. If no
module passes, the learner abstains from transfer and creates a separate local
module. The current phase is never merged into a rejected module. There is no
Brier threshold or ambiguity margin.

`RESET` and fair `GLOBAL` remain controls; `V265_GUARDED` is retained as the
previous applicability rule; `ACTION_AGREEMENT` is the new arm. All arms are
scored from the same 48-observation prefix. The final 16 observations are
audited only and never alter a model. This paired development diagnostic is not
a scientific Gate, confidence certificate, or U006 authorization.
