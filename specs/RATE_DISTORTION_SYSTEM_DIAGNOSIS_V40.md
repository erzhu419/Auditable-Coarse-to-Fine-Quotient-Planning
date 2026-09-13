# V40: exact operator compilation and systematic error diagnosis

Frozen 2026-09-10 before V40 outcomes. Scope: all six V39 exact-2048 conditions,
the same public H2 boards, gamma .95, reward units, legal-action completion,
author commit and independent adaptive beta ladder [6,7,8,9,10]. No new boards,
sampling, beta selection or formal Gate; U005 FAIL and U006 ineligibility remain.
Reconstruct only the missing encoders and Q iterates deterministically, using
V39's unchanged fitting functions. Re-enumeration and reconstruction costs are
reported; they are not new independent evidence. Check against retained V39
final policies, root values/predictions, information and active code counts.

## Equivalent compiled operator

With legal-pair encoder E and representative selector L, the author update is
T(u)=L F E u. Compile rewards and successor choice sets to evaluate

T(u)[z] = r(g[z]) + gamma * sum_s P(s|g[z]) * max_a dot(E[s,a,:], u).

Only exact equal decoder representatives and successor choice sets may be
merged. Never exchange expectation and maximum or average competing actions.
The runtime object owns only numeric arrays; no original MDP, 2048 state,
callback or transition-provider reference. Save/load six final-beta operators
and execute them in a fresh process that does not import the author/project
model code. Readout mappings needed to execute policies are counted separately.
This is an executable max-linear operator, not automatically a smaller quotient
MDP or a rule for unseen boards.

Compare compiled and author updates on all reconstructed adaptive snapshots at
their respective beta, including every legal action after grounding. Require
absolute operator error <=1e-12; separately report action disagreements and
their exact policy consequences, including near ties. Do not declare behavioral
identity from numeric tolerance alone. Compare fixed-point values and original
policy evaluation as well.

Timing: six final-beta operators, five interleaved blocks per implementation,
200 backups per block, one BLAS thread. Report block median/range, compile
time, exact array counts and bytes; common fitting/model acquisition remains
separate and is not refunded. Author scalar backup units are not actual work.
Do not claim statistically established speedup from these small local timings.

## Diagnosis without changing V39

For the frozen final-beta encoder/decoder, separately analyze its retained
adaptive snapshot and its converged fixed point (tol 1e-12, max 20,000 updates).
At q=E u and delta=u-L F E u, verify per legal pair

q-Fq = E*delta + (E*L-I)*Fq.

The two terms distinguish remaining iteration error and projection error.
Record sup residuals and gamma-contraction error bounds; never substitute the
author's value-max residual for the full abstract-Q residual.

For pi=greedy(q), y(s)=q(s,pi(s)), d=y-r_pi-gamma*P_pi*y, verify

y-V_pi = (I-gamma*P_pi)^(-1) d.

Partition d by original H2/H1/absorbing state and report signed root
contributions. Also partition (E*L-I)*Fq by representative horizon, recording
both mixing mass and signed contributions; mixing mass alone is not attribution.
Preserve the absorbing state's discounted self-loop in this identity.

One diagnostic intervention is frozen: keep E/decoder/beta unchanged, but zero
the grounded terminal continuation before each Bellman backup and at final
readout, then solve this changed operator to convergence. Compare root value
prediction, exact policy return and full-state policy changes with the original
converged operator. This isolates a terminal continuation channel; it is not an
equivalent optimization or a replacement of V39. No horizon-refitting or further
repair is added after outcomes. If clamping worsens decisions, retain that fact.

## Report and next-route decision

Separate demonstrated numerical identities/interventions from hypotheses.
State whether the bottleneck is unfinished iteration, projection/terminal
semantics, literal memory/work, reward units, or a combination. Keep the broader
history scoped: U005 measured skill classification, V15-V38 local sampling and
estimation, V39/V40 known-model control. None alone establishes impossibility of
abstract planning. Propose a bounded next route with success and stopping
conditions, based on these results rather than another open-ended tweak chain.
