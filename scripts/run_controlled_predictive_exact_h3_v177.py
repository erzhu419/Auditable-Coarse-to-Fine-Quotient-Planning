"""Fit the fixed utility partition on exact H3 vectors, then diagnose headroom."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
import importlib
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import controlled_predictive_exact_h3_v177 as core

SOURCE = ROOT/'reports/controlled_predictive_learning_v68'
TARGET = ROOT/'reports/controlled_predictive_composition_v69'
OUTPUT = ROOT/'reports/controlled_predictive_exact_h3_v177'
RUNTIME = ROOT/'reports/v177_runtime_tmp'
MODES = ('TREE', 'ONE', 'FALLBACK', 'ORACLE')
QUERY = 'goal_1_risk_1'
EPSILON = 1e-12


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def utility(vector):
    return vector[0]-vector[1]+vector[2]


def mean_vectors(vectors):
    return [sum(vector[k] for vector in vectors)/len(vectors) for k in range(3)]


def summarize(roots, labels, choices, models):
    cohorts = {}
    for cohort in ('SOURCE', 'TARGET'):
        label_index = {row['root_id']: row for row in labels[cohort]}
        selected = {(row['root_id'], row['mode']): row for row in choices[cohort]}
        records = []
        for root in roots[cohort]:
            action_vectors = label_index[root['root_id']]['action_components']
            oracle_action = root['legal_actions'][0]
            for action in root['legal_actions'][1:]:
                if utility(action_vectors[action]) > utility(action_vectors[oracle_action])+EPSILON:
                    oracle_action = action
            modes = {}
            for mode in MODES:
                action = oracle_action if mode == 'ORACLE' else selected[root['root_id'], mode]['canonical_action']
                vector = action_vectors[action]
                modes[mode] = dict(action=action, components=vector, utility=utility(vector),
                    regret=utility(action_vectors[oracle_action])-utility(vector),
                    fallback=False if mode in ('ORACLE', 'FALLBACK') else selected[root['root_id'], mode]['fallback'])
            records.append(dict(root_id=root['root_id'], source_id=root['source_id'], modes=modes,
                headroom=modes['ORACLE']['utility']-modes['ONE']['utility'],
                tree_minus_one=modes['TREE']['utility']-modes['ONE']['utility']))
        grouped = defaultdict(list)
        for row in records:
            grouped[row['source_id']].append(row)
        groups = []
        for source_id, rows in sorted(grouped.items()):
            groups.append(dict(source_id=source_id, roots=len(rows), metrics={
                mode: dict(components=mean_vectors([row['modes'][mode]['components'] for row in rows])) for mode in MODES}))
        aggregates = {}
        for weighting in ('ROOT_MEAN', 'DESIGN_GROUP_MEAN'):
            metrics = {}
            for mode in MODES:
                vectors = ([row['modes'][mode]['components'] for row in records] if weighting == 'ROOT_MEAN'
                    else [row['metrics'][mode]['components'] for row in groups])
                vector = mean_vectors(vectors)
                metrics[mode] = dict(components=vector, utility=utility(vector))
            headroom = metrics['ORACLE']['utility']-metrics['ONE']['utility']
            improvement = metrics['TREE']['utility']-metrics['ONE']['utility']
            aggregates[weighting] = dict(metrics=metrics, headroom=headroom, tree_minus_one=improvement,
                oracle_minus_tree=metrics['ORACLE']['utility']-metrics['TREE']['utility'],
                informative=headroom > EPSILON,
                headroom_closed_fraction=improvement/headroom if headroom > EPSILON else None)
        cohorts[cohort] = dict(roots=len(records), design_groups=len(groups), primary_weighting=(
            'DESIGN_GROUP_MEAN' if cohort == 'SOURCE' else 'ROOT_MEAN'), aggregates=aggregates,
            diagnostics=dict(headroom_roots=sum(row['headroom'] > EPSILON for row in records),
                tree_improved_roots=sum(row['tree_minus_one'] > EPSILON for row in records),
                tree_worsened_roots=sum(row['tree_minus_one'] < -EPSILON for row in records),
                tree_same_value_roots=sum(abs(row['tree_minus_one']) <= EPSILON for row in records),
                tree_one_action_changes=sum(row['modes']['TREE']['action'] != row['modes']['ONE']['action'] for row in records),
                fallback_counts={mode: sum(row['modes'][mode]['fallback'] for row in records) for mode in ('TREE', 'ONE')},
                oracle_action_disagreements={mode: sum(row['modes'][mode]['action'] != row['modes']['ORACLE']['action'] for row in records) for mode in ('TREE', 'ONE')},
                positive_regret_roots={mode: sum(row['modes'][mode]['regret'] > EPSILON for row in records) for mode in ('TREE', 'ONE')}),
            groups=groups, root_records=records)
    return dict(schema='acfqp.exact_h3.v177.summary', complete=True, cohorts=cohorts,
        learned_splits=sum(node['kind'] == 'split' for node in models['TREE']['nodes']),
        candidate_reasons=dict(Counter(row['reason'] for row in models['TREE']['candidate_records'])),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0)


def canonical_labels(root, native, provenance):
    if native['status'] != 'ACTIVE' or native['horizon'] != 3:
        raise ValueError('required exact root must be ACTIVE H3')
    if set(native['legal_actions']) != set(root['action_map'].values()):
        raise ValueError('kernel and observed root actions differ')
    components = {}
    for canonical, actual in root['action_map'].items():
        if abs(root['immediate_rewards'][canonical]-native['immediate_rewards'][actual]) > EPSILON:
            raise ValueError('kernel reward differs from observed immediate merge reward')
        components[canonical] = list(native['action_components'][actual])
    result = dict(deepcopy(root), action_components=components, kernel_root=native['root_cell'],
        kernel_root_index=native['root_index'], provenance=provenance,
        teacher_action_native=native['teacher_action'])
    if 'action_component_fractions' in native:
        result['action_component_fractions'] = {canonical: native['action_component_fractions'][actual]
            for canonical, actual in root['action_map'].items()}
    return result


def freeze_choices(roots, models):
    rows, work = [], Counter()
    for root in roots:
        for mode in ('TREE', 'ONE'):
            decision = core.choose_action(models[mode], root)
            work.update(decision['work'])
            rows.append(dict(root_id=root['root_id'], mode=mode, canonical_action=decision['canonical_action'],
                actual_action=decision['actual_action'], fallback=decision['fallback'], decision=decision))
        action = root['fallback_action']
        rows.append(dict(root_id=root['root_id'], mode='FALLBACK', canonical_action=action,
            actual_action=root['action_map'][action], fallback=False, decision=dict(reason='observable_immediate_reward')))
    return rows, dict(work)


def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_exact_h3_v177')
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
        if getattr(module, '__file__', None) and Path(module.__file__).suffix == '.py'
        and any(str(Path(module.__file__).resolve()).startswith(str(ROOT/folder)+'/')
            for folder in ('src', 'scripts'))}
    paths.update(ROOT/relative for relative in (
        'scripts/run_controlled_predictive_exact_h3_v177.py',
        'scripts/analyze_controlled_predictive_exact_h3_v177.py',
        'specs/EXACT_H3_LEARNING_V177.md',
        'tests/test_exact_h3_core_v177.py', 'tests/test_exact_h3_runner_v177.py',
        'tests/test_exact_h3_analysis_v177.py',
        'reports/v177_runtime_tmp/run_checks.py', 'reports/v177_runtime_tmp/run_stage.py'))
    records = []
    for path in sorted(paths):
        destination = output/'source_code'/path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        records.append(str(path.relative_to(ROOT)))
    save(output/'source_manifest.json', dict(files=records))
    return records


def run(output=OUTPUT):
    started = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    run_record = dict(schema='acfqp.exact_h3.v177.run', status='preparing', phase_history=[],
        runtime=dict(python=sys.version.split()[0], executable=sys.executable,
            numpy=core.estimation.np.__version__),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0,
        costs={}, inherited_cost_refs=[dict(path=str(SOURCE/'manifest.json'), fields=['source', 'models']),
            dict(path=str(TARGET/'manifest.json'), fields=['acquisition', 'source_semantics_reference']),
            dict(path=str(TARGET/'targets.jsonl'), fields=['arms.*.costs', 'ground', 'portable', 'case_seconds']),
            dict(path=str(RUNTIME/'readonly_preflight.json'), fields=['costs'])],
        test_refs=[str(RUNTIME/f'{kind}_checks.json') for kind in ('core', 'runner', 'analyzer')])
    inputs = []; work = Counter()
    def read_input(path, destination):
        raw = path.read_bytes(); saved = output/'inputs'/destination
        saved.parent.mkdir(parents=True, exist_ok=True); saved.write_bytes(raw)
        work.update(json_read_operations=1, input_bytes_read=len(raw))
        inputs.append(dict(path=str(path), saved_ref=str(saved.relative_to(output)), bytes=len(raw),
            phase=run_record['status']))
        save(output/'input_manifest.json', inputs)
        return json.loads(raw)
    def phase(name):
        run_record['status'] = name
        run_record['phase_history'].append(dict(phase=name, seconds_since_start=perf_counter()-started,
            input_reads=work['json_read_operations']))
        save(output/'run.json', run_record)
        print(json.dumps(dict(event=name, seconds=perf_counter()-started)), flush=True)
    try:
        capture_code(output)
        source_roster = read_input(SOURCE/'roster.json', 'source/roster.json')
        target_roster = read_input(TARGET/'roster.json', 'target/roster.json')
        query = read_input(SOURCE/'queries.json', 'source/queries.json')[QUERY]
        if query != dict(reward_weight=1., failure_penalty=1., goal_bonus=1.):
            raise ValueError('required complete vector utility query differs')
        roots = {'SOURCE': [], 'TARGET': [], 'excluded': []}
        for ordinal, case in enumerate(source_roster['source']):
            if case['horizon'] != 3:
                roots['excluded'].append(dict(cohort='SOURCE', ordinal=ordinal, case=case, reason='horizon_not_three'))
                continue
            roots['SOURCE'].append(core.root_from_case(case, ordinal, 'SOURCE', work))
        for ordinal, case in enumerate(target_roster['target']):
            if case['horizon'] == 3:
                roots['TARGET'].append(core.root_from_case(case, ordinal, 'TARGET', work))
        if len(roots['SOURCE']) != 47 or len(roots['TARGET']) != 24 or len(roots['excluded']) != 1:
            raise ValueError('fixed 47 H3 source / 24 H3 target roster differs')
        if len({root['root_id'] for cohort in ('SOURCE', 'TARGET') for root in roots[cohort]}) != 71:
            raise ValueError('distinct source and target roots required')
        save(output/'roots.json', roots)
        phase('source_labels')
        tick = perf_counter()
        source_kernel = read_input(SOURCE/'RAW/kernel.json', 'source/RAW.kernel.json')
        source_plans = read_input(SOURCE/'RAW/plans.json', 'source/RAW.plans.json')
        cells = {row[0]: row[1:] for row in source_kernel['cells']}
        if len(source_kernel['roots']) != len(source_roster['source']):
            raise ValueError('source roots cannot bind to original roster order')
        for ordinal, case in enumerate(source_roster['source']):
            if cells[source_kernel['roots'][ordinal]][0] != case['horizon']:
                raise ValueError('source horizon does not match original root identity')
        source_result = core.evaluate_payload(source_kernel, source_plans[QUERY],
            [root['ordinal'] for root in roots['SOURCE']])
        index = {label['root_index']: label for label in source_result['labels']}
        labels = {'SOURCE': [canonical_labels(root, index[root['ordinal']],
            dict(kernel_ref='inputs/source/RAW.kernel.json', plans_ref='inputs/source/RAW.plans.json', query=QUERY))
            for root in roots['SOURCE']], 'TARGET': []}
        run_record['costs']['source_evaluation'] = dict(counts=source_result['counts'], seconds=perf_counter()-tick)
        save(output/'source_labels.json', labels['SOURCE'])
        tick = perf_counter()
        models = {'ONE': core.fit_exact_one(labels['SOURCE'], 0),
                  'TREE': core.fit_exact_partition(labels['SOURCE'], 0)}
        run_record['costs']['learning'] = dict(seconds=perf_counter()-tick,
            one_fit_counts=models['ONE']['fit_counts'], one_node_fit_counts=models['ONE']['node_fit_counts'],
            tree_fit_counts=models['TREE']['fit_counts'],
            tree_search_counts=models['TREE']['utility_search_counts'], tree_node_fit_counts=models['TREE']['node_fit_counts'])
        save(output/'models.json', models)
        phase('models_frozen')
        choices = {}; decision_counts = {}
        for cohort in ('SOURCE', 'TARGET'):
            choices[cohort], decision_counts[cohort] = freeze_choices(roots[cohort], models)
        run_record['costs']['decision_counts'] = decision_counts
        save(output/'choices.json', choices)
        phase('target_choices_frozen')
        phase('target_labels')
        target_costs = []
        for root in roots['TARGET']:
            tick = perf_counter(); name = root['root_id']
            kernel = read_input(TARGET/name/'FULL.model.json', f'target/{name}/FULL.model.json')
            plans = read_input(TARGET/name/'FULL.plans.json', f'target/{name}/FULL.plans.json')
            if kernel['variant'] != 'FULL' or kernel['rule']['goal_rank'] != 11:
                raise ValueError('fixed target FULL goal rank eleven required')
            literals = {(h, tuple(board)): state for h, board, state in kernel['literal_boards']}
            if len(kernel['roots']) != 1 or literals[3, tuple(root['board'])] != kernel['roots'][0]:
                raise ValueError('target literal root is not the observed board')
            result = core.evaluate_payload(kernel, plans[QUERY], [0])
            labels['TARGET'].append(canonical_labels(root, result['labels'][0], dict(
                kernel_ref=f'inputs/target/{name}/FULL.model.json', plans_ref=f'inputs/target/{name}/FULL.plans.json', query=QUERY)))
            target_costs.append(dict(root_id=name, counts=result['counts'], seconds=perf_counter()-tick))
        run_record['costs']['target_evaluations'] = target_costs
        save(output/'labels.json', labels)
        summary = summarize(roots, labels, choices, models)
        save(output/'summary.json', summary)
        run_record['costs']['preparation_and_input_counts'] = dict(work)
        run_record['seconds'] = perf_counter()-started
        phase('complete')
        save(output/'run.json', run_record)
        print(json.dumps(dict(learned_splits=summary['learned_splits'], target=summary['cohorts']['TARGET']['aggregates']['ROOT_MEAN'])), flush=True)
        return run_record
    except Exception as error:
        run_record.update(status='failed', seconds=perf_counter()-started,
            failure=dict(type=type(error).__name__, message=str(error)))
        run_record['costs']['preparation_and_input_counts'] = dict(work)
        save(output/'run.json', run_record)
        raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args(); run(args.output)


if __name__ == '__main__':
    main()
