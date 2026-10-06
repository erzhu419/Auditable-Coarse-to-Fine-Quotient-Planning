"""Score frozen source bundles and apply retained query choices to new histories."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter
import numpy as np
from .controlled_predictive_capacity_ranking_v103 import (
    CandidateModel, RATE, L2, L2_COEFFICIENT, L2_REFERENCE_PARAMETERS, SEED)
from .controlled_predictive_crossed_scoring_v106 import _event

BUNDLES = (11, 12, 13, 14)
TARGETS = (15, 16, 17, 18)
WIDTHS = (4, 16)
QUERIES = ('reward', 'risk_goal')
STAGES = ('HALF', 'FULL')
METHODS = tuple(f'POOLED_H{width}_{stage}' for width in WIDTHS for stage in STAGES)


def _episodes(roster):
    return {query: sorted([[life, episode] for life, q, episode in roster if q == query])
        for query in QUERIES}


def score_frozen_models(source_run, roots):
    """Cross all 16 retained models with new roots; query choices remain fixed."""
    start = perf_counter()
    settings = source_run['settings']
    if (source_run['status'] != 'complete' or settings['lifecycles'] != list(BUNDLES)
            or settings['widths'] != list(WIDTHS) or settings['feature_dim'] != 121
            or settings['optimizer_steps'] != 1000 or settings['learning_rate'] != RATE
            or settings['l2_coefficient'] != L2_COEFFICIENT
            or settings['l2_reference_parameters'] != L2_REFERENCE_PARAMETERS
            or settings['initialization_seed'] != SEED):
        raise ValueError('frozen scoring requires the complete unchanged V112 source recipe')
    root_ids = {r['root_id'] for r in roots}
    expected_roots = {(life, query, episode) for life in TARGETS for query in QUERIES for episode in range(8)}
    if (len(root_ids) != len(roots) or len(roots) != len(expected_roots)
            or {(r['life'], r['query'], r['episode']) for r in roots} != expected_roots
            or any(np.asarray(r['features']).shape != (5, 121) for r in roots)):
        raise ValueError('frozen cross scoring requires all 64 new target roots')
    folds = {fold['heldout_life']: fold for fold in source_run['inherited_folds']}
    rows = {(row['heldout_life'], row['method']): row for row in source_run['models']}
    expected_models = {(bundle, method) for bundle in BUNDLES for method in METHODS}
    if (len(folds) != len(source_run['inherited_folds']) or set(folds) != set(BUNDLES)
            or len(rows) != len(source_run['models']) or set(rows) != expected_models):
        raise ValueError('all four source bundles and 16 frozen models are required')
    choices = {(row['heldout_life'], row['hidden'], row['query']): row for row in source_run['selections']}
    expected_choices = {(bundle, width, query) for bundle in BUNDLES for width in WIDTHS for query in QUERIES}
    if len(choices) != len(source_run['selections']) or set(choices) != expected_choices:
        raise ValueError('all 16 retained query choices are required')
    binding = []
    for bundle, width, query in sorted(expected_choices):
        choice = choices[bundle, width, query]
        sources = [life for life in BUNDLES if life != bundle]
        stage = choice['chosen_stage']
        method = f'POOLED_H{width}_{stage}'
        if (stage not in STAGES or choice['chosen_method'] != method or choice['source_lives'] != sources):
            raise ValueError('retained choice differs from its frozen source bundle')
        binding.append(dict(bundle_id=bundle, hidden=width, query=query, source_lives=sources,
            chosen_stage=stage, chosen_method=method, chosen_model_path=rows[bundle, method]['metadata']['path']))
    counts = Counter(model_payloads_loaded=0, model_root_scores=0, neural_candidate_predictions=0,
        neural_hidden_activations=0, derived_decisions=0, cached_decision_lookups=0,
        new_environment_transitions=0, new_synthetic_transitions=0, neural_model_fits=0,
        optimizer_steps=0, model_prefix_trajectories=0)
    loaded, payloads, models = {}, {}, []
    for bundle in BUNDLES:
        fold = folds[bundle]
        sources = [life for life in BUNDLES if life != bundle]
        if fold['source_lives'] != sources or set(TARGETS) & set(sources):
            raise ValueError('frozen source bundle includes a new target history')
        for width in WIDTHS:
            for stage, checkpoint in zip(STAGES, (256000, 512000)):
                method = f'POOLED_H{width}_{stage}'
                metadata = rows[bundle, method]['metadata']
                payload = json.loads(Path(metadata['path']).read_text())
                counts['model_payloads_loaded'] += 1
                model = CandidateModel.from_payload(payload)
                update, fit = payload['update'], fold['fit_logs'][method]
                training = fold['data_log'][stage.lower()]['training_roster']
                statistics = fold['data_log']['half']['training_roster']
                if (metadata != fold['model_metadata'][method] or metadata['heldout_life'] != bundle
                        or metadata['source_lives'] != sources or metadata['hidden'] != width
                        or metadata['stage'] != stage or metadata['family'] != 'UNIFORM_SHRINK'
                        or any(metadata[key] != checkpoint for key in ('checkpoint', 'budget', 'episode_cutoff'))
                        or metadata['parameter_count'] != 123 * width
                        or update['heldout_life'] != bundle or update['source_lives'] != sources or update['stage'] != stage
                        or update['training_roster'] != training or update['statistics_roster'] != statistics
                        or fit['training_roster'] != training or fit['statistics_roster'] != statistics
                        or any(life not in sources or life in TARGETS for life, _, _ in training + statistics)
                        or model.training_episodes != _episodes(training)
                        or model.hidden != width or model.parameter_count != 123 * width
                        or model.checkpoint != checkpoint or model.family != 'UNIFORM_SHRINK'
                        or model.optimizer_steps != 1000 or model.parameters[0].shape != (121, width)
                        or model.mean.shape != (121,) or model.scale.shape != (121,)
                        or payload['learning_rate'] != RATE or payload['l2'] != L2
                        or payload['l2_coefficient'] != L2_COEFFICIENT
                        or payload['l2_reference_parameters'] != L2_REFERENCE_PARAMETERS
                        or payload['initialization_seed'] != SEED
                        or payload['uniform_gamma'] != fit['uniform_gamma']
                        or update['optimizer_state'] != 'reset_zero_moments'
                        or update['new_optimizer_steps'] != 1000
                        or update['inherited_parameter_steps'] != (0 if stage == 'HALF' else 1000)
                        or update['parameter_lineage_steps'] != (1000 if stage == 'HALF' else 2000)):
                    raise ValueError('frozen payload differs from retained model, training roster or recipe')
                if stage == 'FULL' and any(payload[key] != payloads[bundle, f'POOLED_H{width}_HALF'][key]
                        for key in ('mean', 'scale', 'uniform_gamma')):
                    raise ValueError('full model differs from its frozen half statistics')
                loaded[bundle, method], payloads[bundle, method] = model, payload
                models.append(dict(bundle_id=bundle, method=method, metadata=deepcopy(metadata)))
    decisions, cached = [], {}
    for row in models:
        bundle, method = row['bundle_id'], row['method']
        for root in roots:
            event = _event(loaded[bundle, method].score_candidates(root['features'], counts))
            decision = dict(bundle_id=bundle, root_id=root['root_id'], target_life=root['life'], method=method, event=event)
            decisions.append(decision)
            cached[bundle, root['root_id'], method] = event
            counts['model_root_scores'] += 1
    for choice in binding:
        for root in roots:
            if root['query'] != choice['query']:
                continue
            event = cached[choice['bundle_id'], root['root_id'], choice['chosen_method']]
            decisions.append(dict(bundle_id=choice['bundle_id'], root_id=root['root_id'], target_life=root['life'],
                method=f"SELECTED_H{choice['hidden']}", chosen_method=choice['chosen_method'],
                chosen_model_path=choice['chosen_model_path'], event=deepcopy(event)))
            counts['derived_decisions'] += 1
            counts['cached_decision_lookups'] += 1
    return models, decisions, dict(counts=dict(counts), choices_binding=binding,
        checks=dict(complete_new_root_roster=True, retained_model_roster=True, frozen_model_metadata_and_recipe=True,
            frozen_training_and_statistics_rosters=True, new_target_histories_excluded=True,
            retained_query_choice_binding=True, no_target_references_used=True,
            cross_scoring_roster_complete=counts['model_root_scores'] == 1024,
            derived_roster_complete=counts['derived_decisions'] == 512,
            selected_events_exact=all(row['event'] == cached[row['bundle_id'], row['root_id'], row['chosen_method']]
                for row in decisions if row['method'].startswith('SELECTED_'))), seconds=perf_counter() - start)
