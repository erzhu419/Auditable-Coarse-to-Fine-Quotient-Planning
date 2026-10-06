# V305 — observed-context persistent reward/risk parameters

V304 isolates harmful A1 initialization/history on fixed B facts. Repair
parameter sharing directly with persistent contexts selected only from observed
spawn statistics. Reuse all V303 A1/B/A2 closed factual tapes, original four
SOURCE parents, 64 lifecycles, chronological 80/20 splits and task beliefs.
No new training acquisition, target, feature, alpha or H2 planning change.

Arms: SOURCE and SHARED_LOCAL reuse the exact audited V303 SOURCE/LOCAL_RISK
receipts; CONTEXT_LOCAL fits the unchanged V301 LOCAL method at alpha .0025.
Each new context starts with original SOURCE reward weights and zero risk
logits. Matching contexts retain the same arrays and cumulative updates.

Extract n=sum(module.alpha+module.beta-2)+pending.n and
k=sum(module.alpha-1)+pending.fours from the current FIT-prefix spawn memory.
These include initialization, warmup and every FIT-prefix observation, without
the active-module selection bias. A context stores accumulated (n_old,k_old).
For Beta(1,1) priors and equal same/disjoint-model odds use
logBF=logB(1+k_old+k,1+n_old+n-k_old-k)
      -logB(1+k_old,1+n_old-k_old)-logB(1+k,1+n-k).
Reuse the largest logBF when >=0, otherwise create a SOURCE-initialized context;
ties choose the earliest context. Commit current FIT statistics once. No stage
label, task label, true environment probability or heldout game label enters
the router. The context count is an algorithm output, not forced to two.

Evaluate the five original cells A1_A/B_A/B_B/A2_A/A2_B. Select among stored
contexts by maximum logBF using the task's original observed FIT snapshot;
selection does not update or create contexts. Planning p remains the exact
original V303 fixed observed task belief. Evaluate all 32 original seeds per
cell, static H2, max 8,192 steps. Retain all cutoffs. There are 10,240 new
CONTEXT games and 20,480 reused SOURCE/SHARED checkpoint games. Unchanged
contexts must reproduce their prior same-task games exactly. A1 fit/heldout/
evaluation must match V303 LOCAL A1. A newly allocated B context must match
V304 fresh LOCAL B using the same facts, not its inherited B branch.

Primary: final after-A2 equally weighted A/B whole-game utility,
CONTEXT_LOCAL minus SHARED_LOCAL. Use 20,000 paired lifecycle bootstrap draws
within the four fixed parent groups, seed 30500001. CI lower >0 and no cutoff
supports structural repair. Separately report final CONTEXT minus SOURCE,
each final task minus SOURCE, A loss after B, B loss after A2, and final A
versus first A. Dual-task benefit requires both task SOURCE contrasts to have
CI lower >0. Retention uses the unchanged zero-margin interval criterion;
average benefit cannot substitute for individual tasks or capability retention.

Count all original SOURCE/dynamics and A1/B/A2 raw economically for every arm.
New training raw is zero. Count new reconstruction, fits, heldout scoring,
context copies/zero initialization, peak parameter bytes, router work and all
new evaluations. Reused control timing is inherited, not newly executed work.
Keep V303's historical CPU gap explicit. Freeze before new fits and retain
every negative result without routing, alpha, task or seed tuning.

This tests context conditioning and extra parameter capacity together on retained
batch boundaries; it does not isolate those contributions or establish blind
online task discovery, endogenous acquisition or independent confirmation.
U005 remains FAIL; U006 assurance is not started.
