"""Validate each deployed three-source model on its independent source roots."""
from collections import Counter
from math import fsum, isfinite
import json
from pathlib import Path
from time import perf_counter
import numpy as np
from .controlled_predictive_capacity_ranking_v103 import (
    CandidateModel, RATE, L2, L2_COEFFICIENT, L2_REFERENCE_PARAMETERS, SEED)
from .controlled_predictive_crossed_scoring_v106 import _event
from .controlled_predictive_frozen_cross_scoring_v113 import BUNDLES, WIDTHS, QUERIES, STAGES, METHODS, _episodes
from .controlled_predictive_nested_selection_v112 import _root_index
from scripts.analyze_controlled_predictive_crossed_ranking_v106 import event_metrics
from scripts.analyze_controlled_predictive_natural_reference_v104 import reference_values


def score_source_models(source_run, roots, root_dir):
    """Read unchanged retained parameters at their migrated location and score source roots."""
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
    expected_roots = {(life, query, episode) for life in BUNDLES for query in QUERIES for episode in range(8)}
    if (len(root_ids) != len(roots) or len(roots) != len(expected_roots)
            or {(r['life'], r['query'], r['episode']) for r in roots} != expected_roots
            or any(np.asarray(r['features']).shape != (5, 121) for r in roots)):
        raise ValueError('source scoring requires all 64 retained validation roots')
    folds = {fold['heldout_life']: fold for fold in source_run['inherited_folds']}
    rows = {(row['heldout_life'], row['method']): row for row in source_run['models']}
    expected_models = {(bundle, method) for bundle in BUNDLES for method in METHODS}
    if (len(folds) != len(source_run['inherited_folds']) or set(folds) != set(BUNDLES)
            or len(rows) != len(source_run['models']) or set(rows) != expected_models):
        raise ValueError('all four source bundles and 16 frozen models are required')
    counts = Counter(model_payloads_loaded=0, model_root_scores=0, neural_candidate_predictions=0,
        neural_hidden_activations=0,
        new_environment_transitions=0, new_synthetic_transitions=0, neural_model_fits=0,
        optimizer_steps=0, model_prefix_trajectories=0)
    loaded, payloads, bindings = {}, {}, []
    original_root = Path(source_run['source']).parents[1]
    root_dir = Path(root_dir)
    for bundle in BUNDLES:
        fold = folds[bundle]
        sources = [life for life in BUNDLES if life != bundle]
        if fold['source_lives'] != sources or bundle in sources:
            raise ValueError('frozen source bundle includes its excluded history')
        for width in WIDTHS:
            for stage, checkpoint in zip(STAGES, (256000, 512000)):
                method = f'POOLED_H{width}_{stage}'
                metadata = rows[bundle, method]['metadata']
                disk_path = root_dir / Path(metadata['path']).relative_to(original_root)
                payload = json.loads(disk_path.read_text())
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
                        or any(life not in sources or life == bundle for life, _, _ in training + statistics)
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
                bindings.append(dict(bundle_id=bundle, method=method, source_lives=sources,
                    retained_model_path=metadata['path'], loaded_model_path=str(disk_path)))
    decisions = []
    for row in bindings:
        bundle, method = row['bundle_id'], row['method']
        for root in roots:
            if root['life'] not in row['source_lives']:
                continue
            event = _event(loaded[bundle, method].score_candidates(root['features'], counts))
            decisions.append(dict(bundle_id=bundle, root_id=root['root_id'], validation_life=root['life'],
                method=method, event=event))
            counts['model_root_scores'] += 1
    return decisions, dict(validation_source_models='three_source_deployment', model_bindings=bindings,
        counts=dict(counts), checks=dict(complete_source_root_roster=True, retained_model_roster=True,
            frozen_model_metadata_and_recipe=True, frozen_training_and_statistics_rosters=True,
            source_only_scoring=True, no_reference_values_used_for_scoring=True,
            original_metadata_paths_preserved=True, scoring_roster_complete=counts['model_root_scores'] == 768),
        seconds=perf_counter() - start)


def select_updates(source_decisions, roots):
    """Keep HALF unless the deployed FULL model improves equal-source pooled utility."""
    start = perf_counter()
    root_index = _root_index(roots, BUNDLES, 8)
    expected = {(bundle, root['root_id'], method) for bundle in BUNDLES
        for root in roots if root['life'] != bundle for method in METHODS}
    cached = {}
    for row in source_decisions:
        key = row['bundle_id'], row['root_id'], row['method']
        if (key not in expected or key in cached or row['validation_life'] != root_index[row['root_id']]['life']
                or row['event'] is None):
            raise ValueError('decisions must match the source-only deployed-model roster')
        cached[key] = row['event']
    if set(cached) != expected:
        raise ValueError('complete direct source decision roster is required')
    utilities = {root['root_id']: reference_values(root['reference_log'], root['query'], 32)['pooled']
        for root in roots}
    selections = []
    for bundle in BUNDLES:
        sources = [life for life in BUNDLES if life != bundle]
        for width in WIDTHS:
            for query in QUERIES:
                folds = []
                for validation in sources:
                    group = sorted((root for root in roots if root['life'] == validation
                        and root['query'] == query), key=lambda row: row['episode'])
                    deltas = []
                    for root in group:
                        values = utilities[root['root_id']]
                        half = event_metrics(cached[bundle, root['root_id'], f'POOLED_H{width}_HALF'], values)
                        full = event_metrics(cached[bundle, root['root_id'], f'POOLED_H{width}_FULL'], values)
                        delta = full['selected_reference_utility'] - half['selected_reference_utility']
                        if not isfinite(delta):
                            raise ValueError('every source root requires a finite utility difference')
                        deltas.append(delta)
                    folds.append(dict(validation_life=validation, source_lives=list(sources),
                        root_ids=[root['root_id'] for root in group], mean_utility_delta=fsum(deltas) / 8))
                average = fsum(row['mean_utility_delta'] for row in folds) / 3
                stage = 'FULL' if average > 0 else 'HALF'
                selections.append(dict(heldout_life=bundle, hidden=width, query=query, source_lives=sources,
                    validation_folds=folds, mean_utility_delta=average,
                    chosen_stage=stage, chosen_method=f'POOLED_H{width}_{stage}'))
    return selections, dict(validation_source_models='three_source_deployment',
        counts=dict(selections=len(selections), validation_folds=len(selections) * 3,
            root_comparisons=384, cached_decision_lookups=768, neural_candidate_predictions=0,
            neural_model_fits=0, optimizer_steps=0, new_environment_transitions=0, new_synthetic_transitions=0),
        checks=dict(complete_source_root_roster=True, complete_direct_decision_roster=True,
            complete_reference_replicas=True, excluded_bundle_history_unused=True,
            deployed_three_source_models=True, equal_root_history_weight=True,
            strict_positive_full_else_half=True, pooled_reference_only=True), seconds=perf_counter() - start)
