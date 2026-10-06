"""Frozen ranking recipe on fresh learning histories, with matched natural roots."""
from collections import Counter
import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS
from scripts.analyze_controlled_predictive_evidence_learning_v88 import _mean, _summary, _cohort, _effect, _across_lives
from scripts.analyze_controlled_predictive_query_ranking_v100 import analyze_simulation
from scripts.analyze_controlled_predictive_natural_reference_v104 import reference_values, root_metrics, summarize_cohort

FAMILY = 'UNIFORM_SHRINK'
CURRENT = tuple(f'R4_H{hidden}_{FAMILY}_DIRECT' for hidden in (4, 16))
METHODS = ('H2_ONLY', 'PREFIX_ONLY_DIRECT') + CURRENT + tuple(name + '_FROZEN_HALF' for name in CURRENT)
CONTRASTS = tuple([(CURRENT[0] + suffix, CURRENT[1] + suffix) for suffix in ('', '_FROZEN_HALF')]
    + [(name, name + '_FROZEN_HALF') for name in CURRENT] + [(name, 'H2_ONLY') for name in CURRENT])
TERMINAL = ('WON', 'LOST')


def analyze_natural(run):
    settings = run['settings']
    stages = {life['id']: life['evaluation'] for life in run['lifecycles']}
    checks = dict(natural_lifecycle_roster=len(stages) == len(run['lifecycles']) == len(settings['lifecycles'])
        and set(stages) == set(settings['lifecycles']), natural_method_rosters=True, natural_streams_paired=True,
        natural_controller_wiring=True, all_natural_games_terminal=True)
    work = {name: Counter() for name in ('ground_work', 'planning_counts', 'outcomes')}
    paired, summaries = {}, {}
    for life, stage in stages.items():
        checks['natural_method_rosters'] &= set(stage['methods']) == set(settings['methods'])
        checks['natural_controller_wiring'] &= bool(stage['wiring']) and all(value is True for value in stage['wiring'].values())
        for method in settings['methods']:
            for game in stage['methods'][method]['games']:
                work['ground_work'].update(game['environment_counts'])
                work['planning_counts'].update(game['planning_counts'])
                work['outcomes'][game['status']] += 1
                checks['all_natural_games_terminal'] &= game['status'] in TERMINAL
        for query in settings['queries']:
            cohort, grouped = _cohort(stage, query, settings)
            paired[life, query] = cohort, grouped
            checks['natural_method_rosters'] &= cohort['roster_complete']
            checks['natural_streams_paired'] &= cohort['seeds_paired']
    for method in settings['methods']:
        summaries[method] = {}
        for query in settings['queries']:
            rows = [dict(id=life, **_summary([row for row in stage['methods'][method]['games'] if row['query'] == query]))
                for life, stage in stages.items()]
            complete = all(row['games'] == row['terminal_games'] == settings['evaluation_replicas'] for row in rows)
            summaries[method][query] = dict(lifecycles=rows, primary_estimable=complete,
                mean_score=_mean(row['terminal_means']['score'] for row in rows) if complete else None,
                mean_utility=_mean(row['terminal_means']['utility'] for row in rows) if complete else None)
    comparisons = {}
    for left, right in settings['contrasts']:
        comparisons[left + '_minus_' + right] = {}
        for query in settings['queries']:
            rows = [dict(id=life, **_effect(paired[life, query][1][left], paired[life, query][1][right],
                paired[life, query][0]['keys'])) for life in settings['lifecycles']]
            comparisons[left + '_minus_' + right][query] = _across_lives(rows)
    return dict(checks=checks, methods=summaries, comparisons=comparisons,
        work={name: dict(value) for name, value in work.items()})


def analyze_references(run):
    settings = run['settings']
    work = {name: Counter() for name in ('ground_work', 'planning_counts', 'outcomes')}
    checks = dict(reference_root_rosters=True, deployed_reference_predictions_match=True,
        reference_audits_pass=True, reference_work_accounted=True, reference_delta_rosters=True,
        all_reference_trajectories_terminal=True, no_reference_refitting_or_rescoring=True)
    rows, missing, trajectories, seconds = [], [], 0, 0.
    for life in run['lifecycles']:
        stage, life_id = life['evaluation'], life['id']
        validation = stage['validation']
        checks['no_reference_refitting_or_rescoring'] &= validation['new_selector_calls'] == validation['new_model_transitions'] == 0
        seconds += validation['seconds']
        records = {(record['root']['query'], record['root']['episode']): record for record in validation['roots']}
        expected = {(query, replica) for query in settings['queries'] for replica in range(settings['evaluation_replicas'])}
        checks['reference_root_rosters'] &= (len(records) == len(validation['roots']) == len(expected)
            and set(records) == expected and not validation['missing_roots']
            and settings['validation_roots_per_query'] == settings['evaluation_replicas']
            and settings['reference_replicas'] == 32 and settings['reference_block_size'] == 16)
        games = {method: {(game['query'], game['replica']): game for game in stage['methods'][method]['games']}
            for method in settings['methods']}
        for query, replica in sorted(expected):
            natural = {method: game[query, replica] for method, game in games.items()}
            row = dict(root_id=f'life_{life_id}_{query}_{replica}', life=life_id, query=query, episode=replica,
                reference_origin='new', natural=natural, reference_complete=False, reference_metrics={})
            rows.append(row)
            if (query, replica) not in records:
                missing.append(row['root_id'])
                continue
            record = records[query, replica]
            root, log = record['root'], record['terminal_log']
            for name in work:
                work[name].update(log[name])
            trajectories += log['trajectories']
            audit = record['audit']
            checks['reference_audits_pass'] &= bool(audit) and all(value is True for value in audit.values())
            checks['reference_work_accounted'] &= (log['trajectories'] == settings['reference_replicas'] * len(OPTIONS)
                and sum(log['outcomes'].values()) == log['trajectories']
                and log['planning_counts'].get('model_uniform_draws', 0) == 4 * log['ground_work'].get('sampled_transitions', 0))
            predictions = record['predictions']
            binding = set(predictions) == set(settings['methods']) - {'H2_ONLY'}
            for method, event in predictions.items():
                game = natural[method]
                binding &= (root['life'] == life_id and root['source_seed'] == game['seed']
                    and event['step'] == root['step'] == game['initiation_step'] and event['board'] == root['board']
                    and event['option'] == game['selected_option'] and set(event['predictions']) == set(OPTIONS)
                    and event['score_semantics'] == ('prefix_utility' if method == 'PREFIX_ONLY_DIRECT' else 'rank_score'))
            checks['deployed_reference_predictions_match'] &= binding
            reference = record['paired_reference']
            terminal = not log['censored_root'] and set(log['outcomes']) <= set(TERMINAL)
            complete = (set(reference) == set(OPTIONS[1:]) and all(len(vectors) == settings['reference_replicas']
                and all(len(value) == 3 for value in vectors) for vectors in reference.values()))
            checks['reference_delta_rosters'] &= complete if terminal else not reference
            checks['all_reference_trajectories_terminal'] &= terminal
            row['reference_complete'] = terminal and complete and binding and record['reference_complete']
            if not row['reference_complete']:
                missing.append(row['root_id'])
                continue
            values = reference_values(dict(log, pair_deltas=reference), query, settings['reference_replicas'])
            row.update(reference_utility_means=values,
                reference_metrics=root_metrics(dict(root, natural=natural, predictions=predictions), values))
    matched = summarize_cohort(rows, settings)
    for queries in matched['comparisons'].values():
        for entry in queries.values():
            histories = entry['lifecycles']
            entry['direction_counts'] = dict(
                natural={name: sum((row['natural_mean_utility_delta'] > 0 if name == 'positive' else
                    row['natural_mean_utility_delta'] < 0 if name == 'negative' else row['natural_mean_utility_delta'] == 0)
                    for row in histories if row['natural_mean_utility_delta'] is not None) for name in ('positive', 'negative', 'zero')},
                references={block: {name: sum((row['references'][block]['selected_utility_delta'] > 0 if name == 'positive' else
                    row['references'][block]['selected_utility_delta'] < 0 if name == 'negative' else row['references'][block]['selected_utility_delta'] == 0)
                    for row in histories if row['references'][block]['selected_utility_delta'] is not None)
                    for name in ('positive', 'negative', 'zero')} for block in ('pooled', 'A', 'B')})
    return dict(checks=checks, roots=rows, missing_or_censored_roots=missing, matched=matched,
        work=dict(**{name: dict(value) for name, value in work.items()}, trajectories=trajectories, seconds=seconds))


def analyze_training(run):
    settings = run['settings']
    checks = dict(fresh_training_allocation_rosters=True, fresh_physical_budget_accounted=True,
        complete_root_labels_match=True, whole_episode_isolation=True, both_widths_share_data_and_penalty=True,
        new_model_fits_accounted=True, shared_training_prefixes_accounted=True, deployed_models_and_hidden_work_match=True,
        frozen_recipe_roster=settings['methods'] == list(METHODS) and settings['contrasts'] == [list(pair) for pair in CONTRASTS])
    acquisition_work = {kind: {name: Counter() for name in ('ground_work', 'planning_counts', 'outcomes')}
        for kind in ('source', 'branches')}
    partition = {kind: Counter() for kind in ('training', 'heldout', 'unincorporated')}
    prefixes = {name: Counter() for name in ('model_work', 'planning_counts', 'feature_counts', 'outcomes')}
    data_counts, fit_counts, predictions = Counter(), Counter(), Counter()
    fits, stages_out, prefix_roots, prefix_trajectories, seconds = [], [], 0, 0, Counter()
    for life in run['lifecycles']:
        allocations = life['allocations']
        checks['fresh_training_allocation_rosters'] &= len(allocations) == 1 and allocations[0]['replicas'] == 4
        metadata = {}
        for allocation in allocations:
            stages = allocation['construction']
            checks['fresh_training_allocation_rosters'] &= [stage['budget'] for stage in stages] == settings['budgets']
            previous_budget = previous_cursor = used = nroots = allocation_fits = 0
            rosters = {q: {name: [] for name in ('training', 'heldout')} for q in settings['queries']}
            for stage in stages:
                budget, acquisition, data = stage['budget'], stage['acquisition'], stage['data']
                cutoff = stage['episode_cutoff']
                source = acquisition['source']['ground_work'].get('sampled_transitions', 0)
                branches = acquisition['branches']['ground_work'].get('sampled_transitions', 0)
                used += acquisition['used_transitions']
                checks['fresh_physical_budget_accounted'] &= (acquisition['budget'] == budget - previous_budget
                    and acquisition['used_transitions'] == source + branches and used == budget
                    and sum(row['total_transitions'] for row in acquisition['cost_partition'].values()) == source + branches)
                complete = acquisition['completed_roots']
                nroots += len(complete)
                for root in complete:
                    rosters[root['query']]['heldout' if root['episode'] % 5 == 4 else 'training'].append(root['episode'])
                coverage = {q: {role: sorted(values) for role, values in groups.items()} for q, groups in rosters.items()}
                checks['complete_root_labels_match'] &= (data['start_cursor'] == acquisition['start_cursor'] == previous_cursor
                    and data['next_cursor'] == acquisition['next_cursor'] and data['episode_cutoff'] == cutoff
                    and data['counts']['complete_roots'] == data['counts']['mean_roots_verified'] == len(complete)
                    and data['counts']['paired_replica_rows'] == 4 * len(complete)
                    and data['counts']['training_roots'] + data['counts']['heldout_roots'] == len(complete)
                    and data['counts']['new_environment_transitions'] == data['counts']['neural_model_fits'] == 0
                    and stage['cumulative_root_count'] == nroots and stage['cumulative_roots'] == coverage)
                train_count = sum(len(row['training']) for row in coverage.values())
                episodes = {query: row['training'] for query, row in coverage.items()}
                checks['new_model_fits_accounted'] &= set(stage['fit_logs']) == {'4', '16'}
                width_logs = []
                for hidden in settings['widths']:
                    fit = stage['fit_logs'][str(hidden)]
                    width_logs.append(fit)
                    checks['whole_episode_isolation'] &= (fit['checkpoint'] == cutoff and fit['training_episodes'] == episodes
                        and fit['training_roots'] == fit['normalization_training_roots'] == fit['conflict_mass_training_roots'] == train_count
                        and fit['heldout_roots'] == nroots - train_count and fit['total_training_pairs'] == 10 * train_count
                        and fit['training_replica_rows'] == 4 * train_count
                        and all(ep < cutoff and ep % 5 != 4 for roster in episodes.values() for ep in roster))
                    checks['both_widths_share_data_and_penalty'] &= (fit['hidden'] == hidden
                        and fit['parameter_count'] == settings['feature_dim'] * hidden + 2 * hidden
                        and fit['l2_coefficient'] == settings['l2_coefficient']
                        and fit['l2_reference_parameters'] == settings['l2_reference_parameters'] == 1968)
                    count, model = fit['counts'], fit['models'][FAMILY]
                    checks['new_model_fits_accounted'] &= (fit['family'] == FAMILY and set(fit['models']) == {FAMILY}
                        and count['neural_model_fits'] == model['counts']['neural_model_fits'] == 1
                        and count['optimizer_steps'] == model['counts']['optimizer_steps'] == settings['optimizer_steps']
                        and model['parameter_count'] == fit['parameter_count'])
                    allocation_fits += count['neural_model_fits']
                    fit_counts.update(count)
                    predictions.update({name: value for name, value in model['counts'].items()
                        if name not in ('neural_model_fits', 'optimizer_steps')})
                    fits.append(dict(life=life['id'], replicas=4, budget=budget, **fit))
                    seconds['fitting'] += fit['seconds']
                checks['both_widths_share_data_and_penalty'] &= all(width_logs[0][field] == width_logs[1][field]
                    for field in ('uniform_gamma', 'checkpoint', 'training_episodes', 'training_roots', 'heldout_roots'))
                trajectories = data['model_prefix_trajectories']
                synthetic = data['new_model_work'].get('synthetic_transitions', 0)
                checks['shared_training_prefixes_accounted'] &= (data['model_prefix_roots'] == len(complete)
                    and trajectories == len(complete) * settings['prefix_replicas'] * len(OPTIONS)
                    and sum(data['new_prefix_outcomes'].values()) == trajectories
                    and 0 <= synthetic <= settings['horizon'] * trajectories
                    and data['new_model_work'].get('spawn_uniform_draws', 0) == 2 * synthetic
                    and data['new_planning_counts'].get('model_uniform_draws', 0) == 4 * synthetic)
                for kind, grouped in acquisition_work.items():
                    for name in grouped:
                        grouped[name].update(acquisition[kind][name])
                for kind in partition:
                    partition[kind].update(acquisition['cost_partition'][kind])
                for name, key in (('model_work', 'new_model_work'), ('planning_counts', 'new_planning_counts'),
                                  ('feature_counts', 'new_feature_counts'), ('outcomes', 'new_prefix_outcomes')):
                    prefixes[name].update(data[key])
                data_counts.update(data['counts'])
                prefix_roots += data['model_prefix_roots']
                prefix_trajectories += trajectories
                seconds['acquisition'] += acquisition['seconds']
                seconds['data_and_training_prefixes'] += data['seconds']
                stages_out.append(dict(life=life['id'], budget=budget, cutoff=cutoff,
                    complete_cumulative_roots=nroots, cumulative_roots=coverage, acquisition_counts=acquisition['counts']))
                previous_budget, previous_cursor = budget, data['next_cursor']
            checks['new_model_fits_accounted'] &= allocation['new_neural_model_fits'] == allocation_fits
            checks['fresh_physical_budget_accounted'] &= allocation['new_training_environment_transitions'] == used
            metadata.update(allocation['model_metadata'])
        evaluation = life['evaluation']
        checks['deployed_models_and_hidden_work_match'] &= (metadata == evaluation['model_metadata']
            and set(metadata) == set(settings['methods']) - {'H2_ONLY', 'PREFIX_ONLY_DIRECT'})
        for method, row in metadata.items():
            hidden = int(method.split('_')[1][1:])
            budget = settings['budgets'][0] if method.endswith('_FROZEN_HALF') else settings['budgets'][-1]
            stage = next(stage for allocation in allocations for stage in allocation['construction'] if stage['budget'] == budget)
            checks['deployed_models_and_hidden_work_match'] &= (row['replicas'] == 4 and row['hidden'] == hidden
                and row['family'] == FAMILY and row['budget'] == budget
                and row['parameter_count'] == hidden * (settings['feature_dim'] + 2)
                and row['episode_cutoff'] == stage['episode_cutoff'])
            for game in evaluation['methods'][method]['games']:
                checks['deployed_models_and_hidden_work_match'] &= game['selector_checkpoint'] == row['episode_cutoff']
                if game['candidate_evaluation'] is not None:
                    checks['deployed_models_and_hidden_work_match'] &= game['candidate_evaluation']['value_counts']['neural_hidden_activations'] == 5 * hidden
    return dict(checks=checks, acquisition_work={kind: {name: dict(value) for name, value in group.items()}
            for kind, group in acquisition_work.items()}, cost_partition={kind: dict(value) for kind, value in partition.items()},
        training_prefixes=dict(roots=prefix_roots, trajectories=prefix_trajectories,
            **{name: dict(value) for name, value in prefixes.items()}), data_counts=dict(data_counts),
        fit_counts=dict(fit_counts), diagnostic_prediction_counts=dict(predictions), fit_summaries=fits,
        stages=stages_out, seconds=dict(seconds))


def analyze_run(run):
    natural, reference, training = analyze_natural(run), analyze_references(run), analyze_training(run)
    simulation = analyze_simulation(run)
    checks = dict(**natural['checks'], **reference['checks'], **training['checks'], **simulation['checks'])
    terminal = ('all_natural_games_terminal', 'all_reference_trajectories_terminal')
    complete = run['status'] == 'complete' and all(value for name, value in checks.items() if name not in terminal)
    training_transitions = sum(group['ground_work'].get('sampled_transitions', 0) for group in training['acquisition_work'].values())
    natural_transitions = natural['work']['ground_work'].get('sampled_transitions', 0)
    reference_transitions = reference['work']['ground_work'].get('sampled_transitions', 0)
    training_model_transitions = training['training_prefixes']['model_work'].get('synthetic_transitions', 0)
    deployment_model_transitions = simulation['model_work'].get('synthetic_transitions', 0)
    return dict(schema='acfqp.fresh_ranking_analysis.v105', complete=complete,
        primary_complete=complete and all(checks.values()) and not reference['missing_or_censored_roots'], checks=checks,
        natural=natural, reference=reference, training=training, simulation=simulation,
        actual_executed_work=dict(new_training_environment_transitions=training_transitions,
            new_natural_transitions=natural_transitions, new_reference_transitions=reference_transitions,
            newly_sampled_environment_transitions=training_transitions + natural_transitions + reference_transitions,
            new_neural_model_fits=training['fit_counts'].get('neural_model_fits', 0),
            new_optimizer_steps=training['fit_counts'].get('optimizer_steps', 0), new_tree_fits=0,
            new_training_model_prefix_transitions=training_model_transitions,
            new_deployment_model_prefix_transitions=deployment_model_transitions,
            new_model_prefix_transitions=training_model_transitions + deployment_model_transitions,
            new_selector_calls=simulation['decisions'], new_candidate_scoring_counts=simulation['value_counts'],
            training_diagnostic_prediction_counts=training['diagnostic_prediction_counts'],
            training_acquisition_work=training['acquisition_work'], training_cost_partition=training['cost_partition'],
            reference_work=reference['work'], actual_wall_seconds=run['actual_wall_seconds']),
        evidence_scope='Four fresh learning histories test the frozen R4/UNIFORM_SHRINK recipe at widths4/16 '
            'and both cumulative budget ages. Source, complete/heldout/incomplete branches, and new training '
            'prefixes are charged once; the loader inherited_acquisition field is an alias of current acquisition '
            'and is not historical work. Both widths are newly fitted from the fixed initialization at each age. '
            'All natural decision roots receive pool32 references and descriptive A/B16 blocks with equal root '
            'weights within each history, then equal history weights. References never choose checkpoints or '
            'change gamma. Candidate-prefix accounting is separate from H2 model computations inside reference '
            'planning, whose counters remain retained. Whole-recipe replication does not identify the isolated '
            'effect of uniform shrinkage. No efficacy interval or new scientific Gate.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    result = analyze_run(json.loads((args.directory / 'run.json').read_text()))
    (args.directory / 'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'],
        checks=result['checks'], actual_executed_work=result['actual_executed_work']), allow_nan=False))


if __name__ == '__main__':
    main()
