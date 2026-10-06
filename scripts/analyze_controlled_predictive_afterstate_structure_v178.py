"""Independent observable afterstate features and exact-vector utility search."""
from collections import Counter
from copy import deepcopy
import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(PROJECT/'src'))
from scripts import analyze_controlled_predictive_exact_h3_v177 as previous
from acfqp.science.controlled_predictive_causal_forgetting_v66 import swipe

ACTIONS, EPS = previous.ACTIONS, previous.EPS
FEATURES = 264


def vocabulary():
    rows = []
    for action in ACTIONS:
        descriptions = [dict(kind='legal', feature_id=f'{action}:legal'), dict(kind='goal_reached', feature_id=f'{action}:goal_reached')]
        descriptions.extend(dict(kind='vacancy', cell=cell, feature_id=f'{action}:vacancy:{cell}') for cell in range(16))
        for axis in ('row', 'col'):
            for line in range(4):
                for pair in range(3):
                    for kind in ('positive_equal', 'goal_pair'):
                        descriptions.append(dict(kind=kind, axis=axis, line=line, pair=pair, feature_id=f'{action}:{axis}:{line}:pair:{pair}:{kind}'))
        start = len(rows)
        rows.extend(dict(index=start+i, action=action, **description) for i, description in enumerate(descriptions))
    return rows


FEATURE_VOCABULARY = vocabulary()


def feature_from_root(root, counts=None):
    work = Counter()
    if 'structural_features' in root:
        if counts is not None:
            counts.update(structural_feature_cache_hits=1, structural_cached_feature_reads=FEATURES)
        return list(root['structural_features'])
    board = tuple(root['canonical_board']); features = []
    for action in ACTIONS:
        after, _, legal = swipe(board, action)
        work['structural_ground_swipe_calls'] += 1
        bits = [int(legal), int(legal and max(after) >= 11)]
        if legal:
            work.update(structural_goal_tile_reads=16, structural_vacancy_tile_reads=16, structural_legal_feature_values_assigned=66)
            bits.extend(int(rank == 0) for rank in after)
            lines = [after[4*r:4*r+4] for r in range(4)]+[tuple(after[4*r+c] for r in range(4)) for c in range(4)]
            for line in lines:
                work.update(structural_compressed_lines=1, structural_line_tile_reads=4)
                occupied = [rank for rank in line if rank > 0]
                for slot in range(3):
                    work['structural_adjacent_slots_inspected'] += 1
                    equal = slot+1 < len(occupied) and occupied[slot] == occupied[slot+1]
                    bits.extend([int(equal), int(equal and occupied[slot] == 10)])
                    if slot+1 < len(occupied):
                        work.update(structural_positive_equal_tests=1, structural_goal_pair_tests=1)
                    else:
                        work['structural_absent_pair_zero_assignments'] += 2
        else:
            bits.extend([0]*64)
            work['structural_illegal_feature_zero_assignments'] += 66
        features.extend(bits)
    work['structural_feature_vectors_computed'] += 1
    if counts is not None:
        counts.update(work)
    return features


def fit_partition(examples, life=0):
    fit_work, search_work, node_work, feature_work = Counter(), Counter(), Counter(), Counter()
    examples, folds, labels = previous.prepare_exact(examples, life, fit_work)
    originals = deepcopy(examples)
    for i, example in enumerate(examples):
        features = feature_from_root(example, feature_work)
        originals[i]['structural_features'] = features
        example['canonical_board'] = features
    sources = dict(Counter(row['source_id'] for row in examples)); nodes = [dict(node_id=0, kind='leaf', leaf_id=0)]
    active = {0: list(range(len(examples)))}; members = {0: list(active[0])}; records = []
    def search(node, indices):
        search_work['utility_search_nodes_evaluated'] += 1
        if any(sum(examples[i]['fold'] == fold for i in indices) < 16 for fold in range(2)):
            search_work['utility_nodes_without_two_fit_children'] += 1; return None
        best = None
        for feature in range(FEATURES):
            candidate = previous.exact_candidate(examples, indices, node, feature, 0, folds, sources, search_work)
            candidate['feature_id'] = FEATURE_VOCABULARY[feature]['feature_id']
            records.append(candidate)
            if candidate['score'] is None or candidate['score'] <= EPS:
                continue
            search_work['utility_positive_candidate_comparisons'] += 1
            if best is None or candidate['score'] > best['score']+EPS:
                best = candidate
        return best
    candidates = {0: search(0, active[0])}
    while len(active) < 16:
        best = None
        for node in sorted(candidates):
            candidate = candidates[node]
            if candidate is None:
                continue
            search_work['utility_global_candidate_comparisons'] += 1
            if best is None or candidate['score'] > best['score']+EPS:
                best = candidate
        if best is None:
            break
        node, first, second = best['node_id'], len(nodes), len(nodes)+1; best['selected'] = True
        left = [i for i in active[node] if examples[i]['canonical_board'][best['cell']] == 0]
        right = [i for i in active[node] if examples[i]['canonical_board'][best['cell']] == 1]
        nodes[node] = dict(node_id=node, kind='split', cell=best['cell'], threshold=0, feature_id=best['feature_id'], left=first, right=second, utility_gain=best['score'])
        del active[node], candidates[node]
        for child, indices in ((first, left), (second, right)):
            nodes.append(dict(node_id=child, kind='leaf', leaf_id=child)); active[child] = indices; members[child] = indices
        search_work['utility_splits_applied'] += 1
        if len(active) < 16:
            for child in (first, second):
                candidates[child] = search(child, active[child])
    fits = {}
    for node in nodes:
        index = node['node_id']; fits[str(index)] = dict(leaf_id=index, **previous.exact_leaf_fit([originals[i] for i in members[index]], node_work))
        node_work['full_discovery_node_fits'] += 1
    training = [{key: deepcopy(row[key]) for key in ('root_id', 'source_id', 'life', 'fold', 'canonical_board', 'legal_actions', 'immediate_rewards', 'action_components', 'structural_features')} | dict(provenance=deepcopy(row.get('provenance', {}))) for row in originals]
    return dict(schema='acfqp.afterstate_structure.v178', life=life, query='risk1', native_teacher_query='goal_1_risk_1', horizon=3,
        mode='PART_UNPRUNED', label_kind='exact_enumerated_vector',
        constants=dict(min_child_roots=8, min_child_sources=2, min_action_roots=4, max_leaves=16, epsilon=EPS, discovery_design_groups=12,
                       feature_count=FEATURES, features_per_action=66, feature_thresholds=[0], goal_rank=11),
        root_ids=[row['root_id'] for row in originals], source_ids=sorted(sources), source_folds=folds, source_root_counts=sources,
        nodes=nodes, groups={}, leaves=[deepcopy(fits[str(node)]) for node in sorted(active)], node_fits=fits, fit_labels=labels,
        training_outcomes=training, candidate_records=records, fit_counts=dict(fit_work), utility_search_counts=dict(search_work), node_fit_counts=dict(node_work),
        feature_vocabulary=deepcopy(FEATURE_VOCABULARY), feature_counts=dict(feature_work))


def choose_action(payload, root, counts=None):
    work = Counter(); observed = dict(root, canonical_board=feature_from_root(root, work))
    decision = previous.choose_action(payload, observed, counts); decision['feature_work'] = dict(work)
    if counts is not None:
        counts.update(work)
    return decision


def structure_choices(roots, model, inherited):
    choices, work = {}, Counter()
    for cohort in ('SOURCE', 'TARGET'):
        rows = []
        for root in roots[cohort]:
            decision = choose_action(model, root); work.update(decision['work']); work.update(decision['feature_work'])
            rows.append(dict(root_id=root['root_id'], mode='TREE', canonical_action=decision['canonical_action'], actual_action=decision['actual_action'],
                             fallback=decision['fallback'], decision=decision))
        rows.extend(deepcopy(row) for row in inherited[cohort] if row['mode'] in ('ONE', 'FALLBACK'))
        choices[cohort] = rows
    return choices, dict(work)


def summarize(roots, labels, choices, models):
    summaries = {name: previous.summarize(roots, labels, choices[name], {'TREE': models[name]}) for name in ('STRUCTURE', 'RAW')}
    contrasts = {}
    for cohort in ('SOURCE', 'TARGET'):
        index = {name: {row['root_id']: row for row in summaries[name]['cohorts'][cohort]['root_records']} for name in summaries}
        records, groups = [], {}
        for root in roots[cohort]:
            a, b = [index[name][root['root_id']]['modes']['TREE'] for name in ('STRUCTURE', 'RAW')]
            vector = [x-y for x, y in zip(a['components'], b['components'])]
            records.append(dict(root_id=root['root_id'], source_id=root['source_id'], components=vector, utility=previous.utility(vector),
                                structure_action=a['action'], raw_action=b['action'], structure_regret=a['regret'], raw_regret=b['regret']))
            groups.setdefault(root['source_id'], []).append(vector)
        group_rows = [dict(source_id=source, roots=len(vectors), components=previous.mean_vectors(vectors), utility=previous.utility(previous.mean_vectors(vectors))) for source, vectors in sorted(groups.items())]
        aggregates = {}
        for weighting in ('ROOT_MEAN', 'DESIGN_GROUP_MEAN'):
            selected = records if weighting == 'ROOT_MEAN' else group_rows; vector = previous.mean_vectors([row['components'] for row in selected])
            aggregates[weighting] = dict(components=vector, utility=previous.utility(vector))
        contrasts[cohort] = dict(roots=len(records), primary_weighting='DESIGN_GROUP_MEAN' if cohort == 'SOURCE' else 'ROOT_MEAN', aggregates=aggregates,
            diagnostics=dict(improved_roots=sum(row['utility'] > EPS for row in records), worsened_roots=sum(row['utility'] < -EPS for row in records),
                             equal_value_roots=sum(abs(row['utility']) <= EPS for row in records), action_changes=sum(row['structure_action'] != row['raw_action'] for row in records),
                             new_positive_regret_roots=sum(row['raw_regret'] <= EPS < row['structure_regret'] for row in records),
                             resolved_positive_regret_roots=sum(row['structure_regret'] <= EPS < row['raw_regret'] for row in records)), groups=group_rows, root_records=records)
    return dict(schema='acfqp.afterstate_structure.v178.summary', complete=True, **summaries, structure_minus_raw=contrasts,
                new_environment_samples=0, new_source_games=0, new_native_weight_updates=0)


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, work = [], Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); work.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run = read('run.json'); inputs = read('input_manifest.json')
    expected_names = ['stage_checks.json', 'run.json', 'roots.json', 'source_labels.json', 'models.json', 'choices.json', 'labels.json']
    check('fixed_input_order_and_label_freeze', [(row['saved_ref'], row['phase']) for row in inputs] ==
          [(f'inputs/inherited/{name}', 'preparing' if i < 6 else 'target_labels') for i, name in enumerate(expected_names)])
    for row in inputs:
        raw, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        work.update(input_byte_comparisons=1, input_comparison_bytes_read=len(raw)+len(original))
        check('retained_input_bytes:'+row['saved_ref'], raw == original and len(raw) == row['bytes'])
    check('input_costs', run['costs']['input_counts'] == dict(json_read_operations=7, input_bytes_read=sum(row['bytes'] for row in inputs)))
    stage = read('inputs/inherited/stage_checks.json'); inherited_run = read('inputs/inherited/run.json')
    check('inherited_V177_settled_complete', stage['valid'] and inherited_run['status'] == 'complete')
    roots = read('inputs/inherited/roots.json'); labels = read('inputs/inherited/labels.json'); source_labels = read('inputs/inherited/source_labels.json')
    old_models = read('inputs/inherited/models.json'); old_choices = read('inputs/inherited/choices.json')
    check('fixed47_SOURCE24_TARGET', len(roots['SOURCE']) == 47 and len(roots['TARGET']) == 24)
    check('unchanged_source_and_target_labels', read('labels.json') == labels and labels['SOURCE'] == source_labels)
    feature_work = Counter()
    for cohort in ('SOURCE', 'TARGET'):
        for root in roots[cohort]:
            root['structural_features'] = feature_from_root(root, feature_work)
    check('independent_local_swipe_observable_feature_cache', read('roots.json') == roots)
    check('one_feature_construction_per_root', run['costs']['feature_construction']['counts'] == dict(feature_work) and feature_work['structural_ground_swipe_calls'] == 284)
    features = {root['root_id']: root['structural_features'] for cohort in ('SOURCE', 'TARGET') for root in roots[cohort]}
    examples = [dict(deepcopy(row), structural_features=features[row['root_id']]) for row in source_labels]
    model = fit_partition(examples); models = dict(STRUCTURE=model, RAW=old_models['TREE'], ONE=old_models['ONE']); saved_models = read('models.json')
    check('old_ONE_and_RAW_fixed_without_refit', saved_models['ONE'] == models['ONE'] and saved_models['RAW'] == models['RAW'])
    check('independent_structure_candidates_and_nodes', previous._equal(saved_models['STRUCTURE'], model) and previous._equal(model, saved_models['STRUCTURE']))
    for key, field in (('fit_counts', 'fit_counts'), ('search_counts', 'utility_search_counts'), ('node_fit_counts', 'node_fit_counts'), ('feature_counts', 'feature_counts')):
        check('new_fit_costs:'+key, run['costs']['learning'][key] == model[field])
    structure, choice_work = structure_choices(roots, model, old_choices); choices = dict(STRUCTURE=structure, RAW=old_choices); saved_choices = read('choices.json')
    check('inherited_choices_unchanged', saved_choices['RAW'] == old_choices)
    check('new_frozen_choices_without_target_labels', previous._equal(saved_choices['STRUCTURE'], structure) and previous._equal(structure, saved_choices['STRUCTURE']))
    check('new_decision_cache_and_policy_costs', run['costs']['choice_counts'] == choice_work)
    summary = summarize(roots, labels, choices, models); saved_summary = read('summary.json')
    check('independent_headroom_and_structure_minus_RAW', previous._equal(saved_summary, summary) and previous._equal(summary, saved_summary))
    check('target_choice_freeze_precedes_target_label_read', [row['phase'] for row in run['phase_history']] ==
          ['source_fit', 'models_frozen', 'target_choices_frozen', 'target_labels', 'complete'] and [row['input_reads'] for row in run['phase_history']] == [6, 6, 6, 6, 7])
    check('no_new_physical_samples_or_native_updates', all(run[key] == 0 for key in ('new_environment_samples', 'new_source_games', 'new_native_weight_updates')))
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and summary['complete']
    return dict(schema='acfqp.afterstate_structure.v178.analysis', valid=valid, complete=complete, primary_complete=complete, checks=checks,
                passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=summary,
                costs=dict(new_environment_samples=0, physical_branches_replayed=0, old_kernels_reevaluated=0, old_models_refitted=0,
                           inherited_cost_refs=run['inherited_cost_refs'], test_refs=run['test_refs'], original_run_costs=run['costs'],
                           independent_input_counts=dict(work), independent_feature_counts=dict(feature_work),
                           independent_fit_counts={key: model[key] for key in ('fit_counts', 'utility_search_counts', 'node_fit_counts', 'feature_counts')},
                           independent_choice_counts=choice_work, seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=PROJECT/'reports/controlled_predictive_afterstate_structure_v178')
    args = parser.parse_args(); result = analyze(args.directory); (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'], new_environment_samples=0)))


if __name__ == '__main__':
    main()
