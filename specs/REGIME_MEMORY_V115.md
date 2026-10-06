# V115: persistent parameter modules across an unannounced A -> B -> A return

The V100–V114 update-selector diagnosis is closed as a bounded mechanism study, not a successful general-learning stage. Defer the previously proposed selector replication on histories19–22. This experiment advances GPT_MultiEpisode.md section7's parameter-change task and section9's persistent module interface. It does not depend on claiming stage1 success.

## Frozen mechanism

Retain the V69 learned swipe/reward program, uniform empty-cell spawn locations and goal rank. Estimate only the probability that a newly spawned tile has rank2 (value4); no supplied spawn probability, true phase identity or change notification reaches the learner. Infer each observed rank from the visible deterministic afterstate and its next board. Initial two spawns are charged but do not train the learner. The harness changes the true rank2 probability across A=.1, B=.3, A_RETURN=.1, with fresh episodes throughout.

Four learners receive the same chronological post-action observations. All start Beta(1,1), predict before each observation, and share ordinary cumulative updating for the first256 observations. FROZEN then stops updating. POOLED updates one cumulative posterior. RECENT uses only the most recent256 ranks with the same prior. LIBRARY initializes one module with the first256 observations, then routes each non-overlapping64-observation block. Buffer contents persist across game and phase boundaries.

For each old module, score the block's ordered Bernoulli sequence by its beta posterior predictive log probability. Compare the best old score with the Beta(1,1) predictive log probability minus log64. Create a new module only if its penalized score is strictly larger; otherwise choose the best old module, with smallest id breaking ties. Update only the chosen module with the entire block. A return to a different existing module is a reactivation. Within a pending block, predictions use the currently committed module; later routing cannot rewrite earlier predictions. Retain an incomplete final block without committing it. No phase reset, parameter grid, module-count cap or outcome-dependent extension.

## Fixed lifecycle and evaluation

Four independent lifecycle seeds0–3 each experience six full GREEDY source games per phase (72 source games). GREEDY uses the supplied swipe program and immediate score/vacancies, not the spawn probability. Source seed=115000000+life*10000+phase_index*100+episode_index. Max2000 actions per source/evaluation game; retain CUTOFF and its cost. If A has fewer than256 training observations, retain that result and mark the warmup condition unmet rather than adding games.

Evaluate snapshots after A game6, B games1/3/6, and A_RETURN games1/3/6. Every checkpoint runs the four learned methods and KNOWN_PARAMETER, the same H2 planner supplied the true parameter as a calibration reference. It is not a full-game optimal policy. Use both existing reward/risk_goal queries and two fresh paired game seeds per case:115900000+life*100000+phase_index*10000+after_game*100+replica. Planning RNG seed adds1000000 and consumes the existing common per-step draw schedule. Total560 evaluation games. Evaluation never updates memories or enters later routing. Snapshot prediction probabilities are fixed during each evaluation game. Paired seeds are shared across methods/queries at a checkpoint, never across different checkpoints.

Retain all source/evaluation trajectories, per-observation predictions, block events and checkpoint/final memory payloads. Snapshot the implementation before the unique main execution. Use four lifecycle workers. All files, including temporary test outputs, remain inside the project's workspaces directory.

## Outcomes and costs

For B and A_RETURN, summarize the first256 prequential observations' mean log loss, Brier score and absolute probability error. Retain every phase's64-observation block curves. Describe recovery as the end index of the first64-consecutive-prediction window with mean absolute parameter error <=.05; report missing when no such window is observed. This definition never changes data acquisition, checkpoint timing or module selection. Compare LIBRARY against FROZEN, POOLED and RECENT with lifecycle as the independent unit.

Report complete-game score, existing query utility, survival steps and terminal outcomes at all checkpoints, with LIBRARY minus the other learners and KNOWN_PARAMETER. Average paired replicas within life, then weight the four lives equally; report all life values. Separate parameter prediction/reuse evidence from actual planning benefits. No selective query/phase reporting, significance claim or scientific Gate.

Count shared actual source transitions once physically and attribute the complete shared acquisition to each learner. Initial spawns, source-policy computation, each learner's updates/routing/predictions/storage, model-based planning and evaluation interactions are separate. The supplied deterministic rule is inherited prior knowledge, not re-learned for free. Known probabilities used only by the harness/reference are not learning observations. This is shared passive experience, fixed update grammar and parameter-module reuse; it is not autonomous strategy discovery or structural rule invention. Preserve U005 FAIL and U006 unstarted.
