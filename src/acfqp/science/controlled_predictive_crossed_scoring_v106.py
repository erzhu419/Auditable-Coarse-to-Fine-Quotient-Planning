"""Cross-score retained roots with the unchanged V105 trained scorers."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter
from .controlled_predictive_capacity_ranking_v103 import CandidateModel
from .controlled_predictive_fragments_v83 import OPTIONS, QUERIES


def _event(scores):
    option, value = 'H2', 0.
    predictions = {}
    for candidate, score in zip(OPTIONS, scores):
        predictions[candidate] = dict(value=float(score))
        if score > value:
            option, value = candidate, float(score)
    return dict(option=option, value=value, predictions=predictions, score_semantics='rank_score')


def score_models(source, run, roots):
    """Return retained bindings, decisions and actual costs, stopping on a failed binding."""
    started = perf_counter()
    settings = run['settings']
    lives, methods = sorted(settings['lifecycles']), settings['methods'][2:]
    roots = sorted(roots, key=lambda r: (r['life'], tuple(QUERIES).index(r['query']), r['episode']))
    models, decisions, loaded = [], [], []
    counts = Counter(model_payloads_loaded=0, model_root_scores=0, diagonal_model_root_scores=0,
        neural_candidate_predictions=0, neural_hidden_activations=0, neural_model_fits=0,
        optimizer_steps=0, new_environment_transitions=0, new_synthetic_transitions=0, model_prefix_trajectories=0)
    expected_roots = {(life, query, episode) for life in lives for query in QUERIES
        for episode in range(settings['evaluation_replicas'])}
    expected_methods = {f'R4_H{width}_UNIFORM_SHRINK_DIRECT{suffix}'
        for width in (4, 16) for suffix in ('', '_FROZEN_HALF')}
    checks = dict(source_run_complete=run['status'] == 'complete',
        model_roster_complete=len(methods) == 4 and set(methods) == expected_methods
            and sorted(row['life'] for row in run['allocations']) == lives
            and sorted(row['id'] for row in run['lifecycles']) == lives,
        deployment_metadata_match=True, frozen_model_config_match=True, frozen_model_training_match=True,
        root_roster_complete=len(roots) == len(expected_roots) == len({r['root_id'] for r in roots})
            and {(r['life'], r['query'], r['episode']) for r in roots} == expected_roots,
        diagonal_contexts_match=True, diagonal_scores_exact=True, diagonal_choices_exact=True,
        scoring_roster_complete=False)

    def finish():
        return models, decisions, dict(source=str(source), checks=checks, counts=dict(counts),
            seconds=perf_counter() - started)

    if not all(value for key, value in checks.items() if key != 'scoring_roster_complete'):
        return finish()
    allocations = {row['life']: row for row in run['allocations']}
    histories = {row['id']: row for row in run['lifecycles']}
    for life in lives:
        allocation, history = allocations[life], histories[life]
        metadata = allocation['model_metadata']
        checks['deployment_metadata_match'] &= (metadata == history['allocations'][0]['model_metadata']
            == history['evaluation']['model_metadata'] and set(metadata) == set(methods))
        if not checks['deployment_metadata_match']:
            return finish()
        stages = {row['budget']: row for row in allocation['construction']}
        for method in methods:
            item = metadata[method]
            width = int(method.split('_')[1][1:])
            budget = settings['budgets'][0] if method.endswith('_FROZEN_HALF') else settings['budgets'][-1]
            payload = json.loads(Path(item['path']).read_text())
            counts['model_payloads_loaded'] += 1
            model = CandidateModel.from_payload(payload)
            stage, fit = stages[budget], stages[budget]['fit_logs'][str(width)]
            checks['frozen_model_config_match'] &= (item['replicas'] == 4 and item['budget'] == budget
                and item['family'] == model.family == 'UNIFORM_SHRINK'
                and item['hidden'] == payload['hidden'] == model.hidden == width
                and item['parameter_count'] == payload['parameter_count'] == model.parameter_count == 123 * width
                and model.parameters[0].shape == (121, width) and model.mean.shape == model.scale.shape == (121,)
                and payload['optimizer_steps'] == 1000 and payload['learning_rate'] == .01
                and payload['l2_coefficient'] == .001 / 1968 and payload['l2_reference_parameters'] == 1968
                and payload['initialization_seed'] == 10001 and payload['score_semantics'] == 'rank_score')
            checks['frozen_model_training_match'] &= (item['episode_cutoff'] == model.checkpoint
                == stage['episode_cutoff'] == fit['checkpoint']
                and model.training_episodes == fit['training_episodes'] and model.uniform_gamma == fit['uniform_gamma'])
            models.append(dict(training_life=life, method=method, metadata=deepcopy(item)))
            if not checks['frozen_model_config_match'] or not checks['frozen_model_training_match']:
                return finish()
            loaded.append((life, method, model))
    # Verify original same-history decisions before computing the new crossed cells.
    for diagonal in (True, False):
        for life, method, model in loaded:
            for root in roots:
                if (root['life'] == life) != diagonal:
                    continue
                event = _event(model.score_candidates(root['features'], counts))
                counts['model_root_scores'] += 1
                decisions.append(dict(root_id=root['root_id'], training_life=life, method=method, event=event))
                if diagonal:
                    counts['diagonal_model_root_scores'] += 1
                    original = root['original_predictions'][method]
                    checks['diagonal_contexts_match'] &= (original['board'] == root['board'] and original['step'] == root['step'])
                    checks['diagonal_scores_exact'] &= (original['predictions'] == event['predictions']
                        and original['value'] == event['value'] and original['score_semantics'] == 'rank_score')
                    checks['diagonal_choices_exact'] &= original['option'] == event['option']
                    if not all(checks[name] for name in ('diagonal_contexts_match', 'diagonal_scores_exact', 'diagonal_choices_exact')):
                        return finish()
    checks['scoring_roster_complete'] = (counts['model_root_scores'] == len(models) * len(roots)
        and counts['diagonal_model_root_scores'] == len(methods) * len(roots))
    return finish()
