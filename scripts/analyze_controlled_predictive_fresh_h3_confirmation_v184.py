"""Independent fresh observations, frozen-policy exact integration and contrasts."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(PROJECT/'src'))
from scripts import analyze_controlled_predictive_rank_layout_consequences_v182 as layout
from acfqp.science.controlled_predictive_causal_forgetting_v66 import swipe

exact, shared = layout.exact, layout.previous
ACTIONS, EPS = exact.ACTIONS, exact.EPS
MODEL_NAMES = ('RIDGE', 'LAYOUT', 'SHARED', 'ONE')
MODES = (*MODEL_NAMES, 'FALLBACK', 'ORACLE')
OUTPUT = PROJECT/'reports/controlled_predictive_fresh_h3_confirmation_v184'


def same(actual, expected):
    return exact._equal(actual, expected) and exact._equal(expected, actual)


def fresh_cases():
    """Called only by the post-run audit, not during import or pure tests."""
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c, 4*r+c+4) for r in range(3) for c in range(4)]
    result = []
    for replica in range(4):
        for index, (first, second) in enumerate(edges):
            seed = 1840200+24*replica+index; rng = random.Random(seed)
            board = [rng.randint(1, 10) for _ in range(16)]
            board[first] = board[second] = 1+index % 10
            for cell in rng.sample([cell for cell in range(16) if cell not in (first, second)], index % 3):
                board[cell] = 0
            result.append(dict(name=f'v184_h3_r{replica:02d}_{index:02d}', horizon=3,
                seed=seed, replica=replica, stratum=index, board=board, vacancies=index % 3))
    return result


def observe_roots(cases):
    work, roots = Counter(), []
    for ordinal, case in enumerate(cases):
        root = exact.root_from_case(case, ordinal, 'FRESH', work)
        root.update(source_id=f"FRESH_REPLICA:{case['replica']:02d}", replica=case['replica'],
                    stratum=case['stratum'], seed=case['seed'])
        roots.append(root)
    return roots, dict(work)


def freeze_choices(roots, models):
    choices, work = {name: [] for name in (*MODEL_NAMES, 'FALLBACK')}, Counter()
    keys = ('root_id', 'source_id', 'life', 'canonical_board', 'legal_actions', 'immediate_rewards',
            'fallback_action', 'action_map', 'layout_features', 'action_features')
    for root in roots:
        root['layout_features'] = layout.action_features_from_root(root, work)
        root['action_features'] = {action: list(record['aggregate']) for action, record in root['layout_features'].items()}
        work.update(shared_feature_maps_derived=1, shared_aggregate_cache_values_copied=6*len(root['action_features']))
        observed = {key: root[key] for key in keys}
        for name in MODEL_NAMES:
            chooser = layout.choose_action if name in ('RIDGE', 'LAYOUT') else shared.choose_action if name == 'SHARED' else exact.choose_action
            decision = chooser(models[name], observed)
            work.update(decision['work']); work.update(decision.get('feature_work', {})); work['fresh_model_choices'] += 1
            choices[name].append(dict(root_id=root['root_id'], mode=name, canonical_action=decision['canonical_action'],
                actual_action=decision['actual_action'], fallback=decision['fallback'], decision=decision))
        action = root['fallback_action']; work['fresh_fallback_choices'] += 1
        choices['FALLBACK'].append(dict(root_id=root['root_id'], mode='FALLBACK', canonical_action=action,
            actual_action=root['action_map'][action], fallback=False,
            decision=dict(reason='observable_immediate_reward', work=dict(fresh_fallback_choices=1))))
    return choices, dict(work)


class FrozenTeacherEvaluator:
    """V66 mechanics and exact spawn probabilities; no teacher optimization."""
    def __init__(self, teacher_policy):
        self.work, self.policy, self.boards, self.values, self.actions = Counter(), {}, {}, {}, {}
        for row in teacher_policy:
            board, horizon = tuple(row['board']), row['horizon']; key = board, horizon
            self.work.update(teacher_records_read=1, teacher_board_tile_reads=16)
            if key in self.policy:
                raise ValueError('Duplicate frozen teacher observation')
            if horizon not in (1, 2, 3) or row['action'] not in ACTIONS:
                raise ValueError('Frozen teacher has an invalid horizon/action')
            self.policy[key] = row['action']

    def classify(self, board):
        board = tuple(board)
        if board not in self.boards:
            self.work.update(board_classifications=1, goal_tile_reads=16)
            if max(board) >= 11:
                status, moves = 'WON', {}
            else:
                moves = {}
                for action in ACTIONS:
                    after, score, legal = swipe(board, action, self.work)
                    if legal:
                        moves[action] = after, score
                status = 'ACTIVE' if moves else 'LOST'
            self.boards[board] = status, moves
        return self.boards[board]

    def value(self, board, horizon):
        board = tuple(board); key = board, horizon
        if key not in self.values:
            status, _ = self.classify(board)
            if status != 'ACTIVE' or horizon == 0:
                self.values[key] = (Fraction(0), Fraction(status == 'LOST'), Fraction(status == 'WON'))
                self.work['terminal_vector_initializations'] += 1
            else:
                if key not in self.policy:
                    raise ValueError('A fixed-policy continuation observation is missing')
                self.work['teacher_policy_reads'] += 1
                self.values[key] = self.action_value(board, horizon, self.policy[key])
        return self.values[key]

    def action_value(self, board, horizon, action):
        board = tuple(board); key = board, horizon, action
        if key not in self.actions:
            status, moves = self.classify(board)
            if horizon <= 0 or status != 'ACTIVE' or action not in moves:
                raise ValueError('Exact first/continuation action must be legal and ACTIVE')
            after, score = moves[action]; empty = [cell for cell, rank in enumerate(after) if rank == 0]
            reward, vector = Fraction(score, 2048), [Fraction(0)]*3
            self.work.update(action_rows_integrated=1, empty_cell_reads=16)
            for cell in empty:
                for rank, mass in ((1, Fraction(9, 10)), (2, Fraction(1, 10))):
                    child = list(after); child[cell] = rank; probability = mass/len(empty)
                    tail = self.value(tuple(child), horizon-1)
                    vector[0] += probability*(reward+tail[0])
                    vector[1] += probability*tail[1]; vector[2] += probability*tail[2]
                    self.work.update(spawn_outcomes_enumerated=1, component_accumulations=3)
            self.actions[key] = tuple(vector)
        return self.actions[key]

    def root_label(self, board, horizon, root_cell=None):
        board = tuple(board); status, moves = self.classify(board)
        if status != 'ACTIVE' or (board, horizon) not in self.policy:
            raise ValueError('The root must bind to the frozen ACTIVE teacher')
        legal = [action for action in ACTIONS if action in moves]
        vectors = {action: self.action_value(board, horizon, action) for action in legal}
        oracle = legal[0]
        for action in legal[1:]:
            if exact.utility(vectors[action]) > exact.utility(vectors[oracle])+Fraction(1, 10**12):
                oracle = action
        return dict(root_index=0, root_cell=root_cell, horizon=horizon, status=status, legal_actions=legal,
            immediate_rewards={action: moves[action][1]/2048. for action in legal},
            action_components={action: list(map(float, vector)) for action, vector in vectors.items()},
            action_component_fractions={action: [[value.numerator, value.denominator] for value in vector] for action, vector in vectors.items()},
            continuation_components=list(map(float, self.value(board, horizon))), oracle_action=oracle,
            oracle_components=list(map(float, vectors[oracle])), teacher_action=self.policy[board, horizon])


def summarize(roots, labels, choices):
    labels = {row['root_id']: row for row in labels}
    selected = {name: {row['root_id']: row for row in rows} for name, rows in choices.items()}
    records = []
    for root in roots:
        vectors = labels[root['root_id']]['action_components']; oracle = root['legal_actions'][0]
        for action in root['legal_actions'][1:]:
            if exact.utility(vectors[action]) > exact.utility(vectors[oracle])+EPS:
                oracle = action
        models = {}
        for name in MODES:
            choice = None if name == 'ORACLE' else selected[name][root['root_id']]
            action = oracle if choice is None else choice['canonical_action']; vector = vectors[action]
            models[name] = dict(action=action, components=vector, utility=exact.utility(vector),
                regret=exact.utility(vectors[oracle])-exact.utility(vector), fallback=False if choice is None else choice['fallback'])
        records.append(dict(root_id=root['root_id'], replica=root['replica'], stratum=root['stratum'], models=models))

    def model_means(rows):
        return {name: dict(components=exact.mean_vectors([row['models'][name]['components'] for row in rows]),
            utility=exact.utility(exact.mean_vectors([row['models'][name]['components'] for row in rows])),
            positive_regret_roots=sum(row['models'][name]['regret'] > EPS for row in rows),
            fallback_roots=sum(row['models'][name]['fallback'] for row in rows)) for name in MODES}

    def contrasts(rows):
        result = {}
        for baseline in ('ONE', 'LAYOUT', 'SHARED'):
            paired = []
            for row in rows:
                first, second = row['models']['RIDGE'], row['models'][baseline]
                paired.append(dict(root_id=row['root_id'], components=[a-b for a, b in zip(first['components'], second['components'])],
                    utility=first['utility']-second['utility'], action_changed=first['action'] != second['action'],
                    new_error=first['regret'] > EPS and second['regret'] <= EPS,
                    resolved_error=first['regret'] <= EPS and second['regret'] > EPS))
            gains = [row for row in paired if row['utility'] > EPS]; losses = [row for row in paired if row['utility'] < -EPS]
            positive, negative = math.fsum(row['utility'] for row in gains), math.fsum(row['utility'] for row in losses)
            best, worst = (max(gains, key=lambda row: row['utility']) if gains else None), (min(losses, key=lambda row: row['utility']) if losses else None)
            mean = exact.mean_vectors([row['components'] for row in paired])
            result['RIDGE_MINUS_'+baseline] = dict(components=mean, utility=exact.utility(mean), improved_roots=len(gains),
                worsened_roots=len(losses), equal_value_roots=len(rows)-len(gains)-len(losses),
                action_changes=sum(row['action_changed'] for row in paired), new_error_roots=sum(row['new_error'] for row in paired),
                resolved_error_roots=sum(row['resolved_error'] for row in paired), positive_gain_sum=positive, negative_gain_sum=negative,
                largest_gain_root=best['root_id'] if best else None, largest_gain=best['utility'] if best else 0.,
                largest_gain_share_of_positive=best['utility']/positive if best else None,
                largest_loss_root=worst['root_id'] if worst else None, largest_loss=worst['utility'] if worst else 0., root_records=paired)
        return result

    replicas = [dict(replica=replica, roots=len(rows), models=model_means(rows), comparisons=contrasts(rows))
        for replica in sorted({row['replica'] for row in records}) for rows in [[row for row in records if row['replica'] == replica]]]
    means, comparisons = model_means(records), contrasts(records)
    headroom = means['ORACLE']['utility']-means['ONE']['utility']
    coverage = [entry for row in choices['RIDGE'] for entry in row['decision']['coverage'].values()]
    return dict(schema='acfqp.fresh_h3_confirmation.v184.summary', complete=True, roots=len(records), models=means,
        comparisons=comparisons, replicas=replicas, root_records=records, oracle_minus_one=headroom,
        oracle_minus_ridge=means['ORACLE']['utility']-means['RIDGE']['utility'],
        headroom_closed_fraction=comparisons['RIDGE_MINUS_ONE']['utility']/headroom if headroom > EPS else None,
        feature_coverage=dict(total_tokens=sum(row['total_tokens'] for row in coverage), known_tokens=sum(row['known_tokens'] for row in coverage), unknown_tokens=sum(row['unknown_tokens'] for row in coverage)),
        whole_cohort_positive_vs_one_and_shared=all(comparisons['RIDGE_MINUS_'+name]['utility'] > EPS for name in ('ONE', 'SHARED')),
        all_replicas_positive_vs_one_and_shared=all(row['comparisons']['RIDGE_MINUS_'+name]['utility'] > EPS for row in replicas for name in ('ONE', 'SHARED')),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=0)


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, io = [], Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); io.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    names = ('stage_checks.json', 'v183_run.json', 'ridge_models.json', 'baseline_models.json', 'learned_rule.json')
    check('five_frozen_model_and_rule_inputs', [(row['saved_ref'], row['phase']) for row in inputs] ==
        [(f'inputs/inherited/{name}', 'protocol_frozen') for name in names])
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        io.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        if 'selected_models' in row:
            original_payload = json.loads(original); expected = {name: original_payload[name] for name in row['selected_models']}
            retained_same = row['selected_models'] == ['LAYOUT', 'SHARED', 'ONE'] and json.loads(saved) == expected
        else:
            retained_same = saved == original
        check('retained_input:'+row['saved_ref'], retained_same and len(original) == row['bytes'] and len(saved) == row['saved_bytes'])
    stage, old_run = read('inputs/inherited/stage_checks.json'), read('inputs/inherited/v183_run.json')
    check('settled_V183_stage_and_run', stage['valid'] and old_run['status'] == 'complete')
    models = dict(read('inputs/inherited/baseline_models.json'), RIDGE=read('inputs/inherited/ridge_models.json')['RIDGE'])
    check('frozen_lambda_and_model_refs', models['RIDGE']['constants']['lambda_value'] == .1 and read('models.json') ==
        {name: dict(saved_ref='inputs/inherited/'+('ridge_models.json' if name == 'RIDGE' else 'baseline_models.json'), model_key=name) for name in MODEL_NAMES})
    rule = read('inputs/inherited/learned_rule.json')
    check('fixed_standard_swipe_spawn_reward_rule', rule['program'] == dict(pack=True, merge_relation='equal', rank_increment=1, consumption='once', reward_rule='output_value') and
        rule['goal_rank'] == 11 and rule['spawn_location'] == 'uniform' and {rank: Fraction(p, q) for rank, p, q in rule['spawn_distribution']} == {1: Fraction(9, 10), 2: Fraction(1, 10)})
    cases = fresh_cases(); check('new_96_seeded_board_roster_without_replacement', read('cases.json') == cases)
    roots, observation_work = observe_roots(cases); choices, choice_work = freeze_choices(roots, models)
    check('independent_observable_roots_native_transport_and_cached_features', same(read('roots.json'), roots))
    check('four_frozen_models_and_immediate_reward_fallback_choices', same(read('choices.json'), choices))
    check('observation_and_choice_costs', run['costs']['observations']['counts'] == observation_work and run['costs']['choices']['counts'] == choice_work)
    native, saved_labels, label_costs = read('native_labels.json'), read('labels.json'), read('label_costs.json')
    ids = [root['root_id'] for root in roots]
    check('complete_ordered_native_canonical_and_cost_rosters', all([row['root_id'] for row in rows] == ids for rows in (native, saved_labels, label_costs)))
    labels, integration_work, label_work = [], Counter(), Counter()
    for case, root, saved_native, cost_row in zip(cases, roots, native, label_costs, strict=True):
        policy = read(f"teacher_policy/{root['root_id']}.json")
        try:
            evaluator = FrozenTeacherEvaluator(policy)
            expected_native = dict(evaluator.root_label(case['board'], 3, saved_native['root_cell']), root_id=root['root_id'])
            # Compiler cell IDs are provenance; the complete physical vectors are recomputed.
            check('exact_saved_teacher_RFS:'+root['root_id'], same(saved_native, expected_native) and
                saved_native['action_component_fractions'] == expected_native['action_component_fractions'])
            labels.append(exact.canonical_labels(root, expected_native, dict(kind='new_exact_V69_FULL',
                teacher_query='goal_1_risk_1', teacher_policy_ref='teacher_policy/'+root['root_id']+'.json')))
            integration_work.update(evaluator.work)
        except ValueError as error:
            checks.append(dict(name='exact_saved_teacher_RFS:'+root['root_id'], passed=False, issue=str(error)))
            labels.append(saved_labels[len(labels)])
        costs = cost_row['costs']; construction, compilation, export = costs['construction'], costs['compilation'], costs['teacher_export']
        n = len(policy)
        check('new_FULL_cap_teacher_export_and_label_accounting:'+root['root_id'], construction['concrete_states'] <= 200000 and
            construction['concrete_active_states'] == construction['active_states'] == n and
            compilation['model_payload_calls'] == compilation['model_reload_calls'] == 1 and
            compilation['payload_cells'] == construction['registered_states'] == costs['label_evaluation']['kernel_cells_read'] and
            compilation['payload_rows'] == costs['label_evaluation']['kernel_rows_read'] and
            compilation['payload_outcomes'] == costs['label_evaluation']['kernel_outcomes_read'] and
            costs['label_evaluation']['root_labels_emitted'] == 1 and
            export == dict(teacher_encoding_records_read=construction['concrete_states'], teacher_policy_records=n,
                teacher_policy_action_reads=n, teacher_policy_tile_reads=16*n))
        for kind in ('construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation'):
            label_work.update({kind+'.'+key: value for key, value in costs[kind].items() if type(value) is int})
    check('independent_canonical_full_vectors_and_exact_fractions', same(saved_labels, labels) and
        all(actual['action_component_fractions'] == expected['action_component_fractions'] for actual, expected in zip(saved_labels, labels, strict=True)))
    summary = summarize(roots, labels, choices)
    check('full_vector_regret_replica_effect_and_gain_concentration_summary', same(read('summary.json'), summary))
    check('paid_input_and_all_five_label_cost_groups', run['costs']['input_counts'] == dict(json_read_operations=5,
        input_bytes_read=sum(row['bytes'] for row in inputs), input_bytes_retained=sum(row['saved_bytes'] for row in inputs)) and run['costs']['labels']['counts'] == dict(label_work))
    check('protocol_models_all_choices_then_new_labels_freeze', [(row['phase'], row['input_reads']) for row in run['phase_history']] ==
        [('protocol_frozen', 0), ('models_frozen', 5), ('target_choices_frozen', 5), ('target_labels', 5), ('complete', 5)])
    check('96_new_boards_kernels_plans_exact_labels_without_fitting_or_sampling', all(run[key] == 96 for key in
        ('new_boards_generated', 'new_reference_kernel_attempts', 'new_reference_kernels', 'new_teacher_plans', 'new_exact_label_roots', 'completed_roots')) and
        run['resource_cap_per_board'] == 200000 and all(run[key] == 0 for key in ('new_environment_samples', 'new_source_games', 'new_native_weight_updates', 'new_predictors_fitted')))
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and summary['complete']
    return dict(schema='acfqp.fresh_h3_confirmation.v184.analysis', valid=valid, complete=complete, primary_complete=complete,
        passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), checks=checks, summary=summary,
        costs=dict(new_environment_samples=0, physical_branches_replayed=0, old_kernels_reevaluated=0, old_models_refitted=0,
            independent_new_root_label_integrations=len(labels), independent_label_integration_counts=dict(integration_work),
            independent_observation_counts=observation_work, independent_choice_counts=choice_work,
            independent_input_counts=dict(io), original_run_costs=run['costs'], reconstructed_label_cost_counts=dict(label_work),
            inherited_cost_refs=run['inherited_cost_refs'], test_refs=run['test_refs'], seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    args = parser.parse_args(); result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'], new_environment_samples=0)))


if __name__ == '__main__':
    main()
