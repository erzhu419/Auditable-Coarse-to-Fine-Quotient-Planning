"""Choose a consolidation update using held-out chronological batches only."""
from collections import defaultdict

COMPONENTS = ('reward', 'failure', 'success')
CANDIDATES = ('NEW_SHARED', 'NEW_SPLIT')


def _mean(values):
    return sum(values) / len(values)


def _summary(parts):
    covered = bool(parts) and all(part['covered'] for part in parts)
    components = {name: _mean([part['components'][name] for part in parts]) if covered else None
        for name in COMPONENTS}
    return dict(covered=covered, components=components,
        joint_loss=_mean(list(components.values())) if covered else None)


def _score(records, predictions, groups):
    if predictions is None:
        predictions = [None] * len(records)
    if len(predictions) != len(records):
        raise ValueError('predictions must align with validation records')
    batches = {}
    for batch, policies in groups.items():
        policy_scores = {}
        for policy, games in policies.items():
            game_scores = []
            for episode, horizons in games.items():
                horizon_scores = []
                for horizon, indices in horizons.items():
                    covered = all(predictions[index] is not None for index in indices)
                    if covered and any(len(predictions[index]) != 3 for index in indices):
                        raise ValueError('predictions must contain joint reward/failure/success vectors')
                    components = {name: _mean([
                        (float(predictions[index][component]) - float(records[index]['target'][component])) ** 2
                        for index in indices]) if covered else None
                        for component, name in enumerate(COMPONENTS)}
                    horizon_scores.append(dict(horizon=horizon, anchors=len(indices),
                        covered=covered, components=components,
                        joint_loss=_mean(list(components.values())) if covered else None))
                game_scores.append(dict(episode=episode, horizons=horizon_scores, **_summary(horizon_scores)))
            policy_scores[policy] = dict(games=game_scores, **_summary(game_scores))
        batches[str(batch)] = dict(batch=batch, policies=policy_scores, **_summary(list(policy_scores.values())))
    covered = all(batch['covered'] for batch in batches.values())
    return dict(batches=batches, all_batches_covered=covered,
        mean_joint_loss=_mean([batch['joint_loss'] for batch in batches.values()]) if covered else None)


def _groups(records):
    if not records:
        raise ValueError('scoring requires held-out validation records')
    grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
    for index, row in enumerate(records):
        grouped[row['batch']][row['policy']][row['episode']][row['horizon']].append(index)
    return {batch: {policy: {episode: dict(sorted(horizons.items()))
        for episode, horizons in sorted(games.items())}
        for policy, games in sorted(policies.items())}
        for batch, policies in sorted(grouped.items())}


def score_candidate(records, predictions):
    """Report the same hierarchical losses without making an update decision."""
    records = list(records)
    return _score(records, predictions, _groups(records))


def select_update(records, predictions, incumbent='KEEP'):
    """Require complete coverage, no harmed batch, and at least one improvement.

    Each batch weighs policies equally, each policy weighs episodes equally,
    and each episode weighs horizons equally after averaging its anchors.
    Missing incumbent coverage can be repaired; missing candidate coverage
    cannot be accepted. Exact loss ties preserve KEEP or prefer NEW_SHARED
    between otherwise eligible updates.
    """
    records = list(records)
    if incumbent not in predictions:
        raise ValueError('selection requires incumbent predictions')
    groups = _groups(records)
    scores = {name: _score(records, predictions.get(name), groups) for name in (incumbent,) + CANDIDATES}
    acceptance = {}
    for name in CANDIDATES:
        equal, improved, harmed, uncovered, newly_covered = [], [], [], [], []
        for batch in groups:
            candidate = scores[name]['batches'][str(batch)]
            previous = scores[incumbent]['batches'][str(batch)]
            if not candidate['covered']:
                uncovered.append(batch)
            elif not previous['covered']:
                newly_covered.append(batch)
                improved.append(batch)
            elif candidate['joint_loss'] < previous['joint_loss']:
                improved.append(batch)
            elif candidate['joint_loss'] > previous['joint_loss']:
                harmed.append(batch)
            else:
                equal.append(batch)
        reasons = []
        if uncovered:
            reasons.append('missing_validation_batch_coverage')
        if harmed:
            reasons.append('worse_than_incumbent_on_covered_batch')
        if not improved:
            reasons.append('no_strict_improvement')
        eligible = not reasons
        acceptance[name] = dict(eligible=eligible, reasons=reasons or ['accepted_non_worsening_update'],
            equal_batches=equal, improved_batches=improved, harmed_batches=harmed,
            uncovered_batches=uncovered, newly_covered_batches=newly_covered)
    eligible = [name for name in CANDIDATES if acceptance[name]['eligible']]
    selected = min(eligible, key=lambda name: scores[name]['mean_joint_loss']) if eligible else incumbent
    return dict(selected_candidate=selected, incumbent=incumbent, batch_order=list(groups),
        scores=scores, acceptance=acceptance,
        selection_reason='minimum_eligible_batch_mean_with_shared_tie_priority' if eligible else 'no_eligible_update')
