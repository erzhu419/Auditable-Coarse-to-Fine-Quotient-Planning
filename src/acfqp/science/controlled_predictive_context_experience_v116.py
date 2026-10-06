"""Fixed-policy natural episodes and causal contexts for their observed labels."""
from collections import Counter

from acfqp.science.controlled_predictive_lifelong_experience_v77 import targets
from acfqp.science.controlled_predictive_lifelong_planner_v77 import POLICIES, policy_action
from acfqp.science.controlled_predictive_regime_experience_v115 import observed_rank, run_episode


def policy_game(seed, policy, rule, p_four, max_steps=2000):
    """Execute one fixed continuation policy without giving it the hidden regime."""
    if policy not in POLICIES:
        raise ValueError(f'unknown continuation policy {policy}')
    planning_counts = Counter()

    def act(board, index):
        return policy_action(board, policy, rule, work=planning_counts)

    game = run_episode(seed, act, p_four, max_steps=max_steps)
    return game, dict(planning_counts)


def causal_records(game, policy, episode, router):
    """Attach pre-spawn context to labels anchored at the same afterstate.

    The fixed policy needs no router while collecting its trajectory. Replaying
    the observations in their original order gives each anchor exactly the
    context available before its spawn; later outcomes never revise it.
    """
    contexts, events = [], []
    for index, step in enumerate(game['steps']):
        context = dict(step=index, context_p4=router.predict(),
            context_module_id=router.module_id,
            context_observations_seen=router.observations_seen)
        contexts.append(context)
        event = router.observe(observed_rank(step))
        if event is not None:
            events.append(dict(event, step=index))
    records = targets(game, policy, episode, stride=4, horizons=(30, 31))
    for record in records:
        context = contexts[record['anchor_step']]
        record.update({key: context[key] for key in (
            'context_p4', 'context_module_id', 'context_observations_seen')})
    steps_count = len(game['steps'])
    anchors = (set(range(0, steps_count, 4)) | {steps_count - 1}) if steps_count else set()
    possible = 2 * len(anchors)
    return records, dict(causal_contexts=contexts, module_events=events, counts=dict(
        observed_transitions=steps_count, labeled_records=len(records),
        candidate_windows=possible, censored_windows_omitted=possible - len(records)))
