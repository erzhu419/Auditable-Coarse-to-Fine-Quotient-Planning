# V264: fresh-stream replication of the V263 consequence library

> Retired as a fair comparison for the same reason as V263: the inherited
> runner exposed different observation prefixes to the arms before scoring.
V265 corrects the accounting while retaining these outputs.

V263's one lifecycle showed a useful persistent module split and query reuse,
but one lifecycle cannot separate a structural effect from a favorable sample
stream. V264 freezes the V263 algorithm, threshold, phase order, sample counts,
queries, and accounting, and runs four fresh paired lifecycles with seeds
`264401, 264402, 264403, 264404`.

Each lifecycle is `A0=normal → B=wet → A_prime=normal → C=blocked`; the learner
sees only opaque context IDs. Each operator has 64 draws, with 48 fit and 16
validation observations. The module split threshold remains Brier `1/2`.
The three arms remain `RESET`, `GLOBAL`, and `LIBRARY`. The primary descriptive
readout is the 12-query policy-correct count per lifecycle and its paired regret
against the exact post-hoc route laws. No seed, phase or threshold is replaced
after reading a result. This is still development evidence, not a Gate.
