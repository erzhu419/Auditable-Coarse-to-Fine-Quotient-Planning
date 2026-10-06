"""SOURCE action-utility partitions over the frozen V196 program representation."""
from collections import Counter
from copy import deepcopy
import argparse
import importlib
import json
import math
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import controlled_predictive_utility_program_partition_v198 as core
from scripts import run_controlled_predictive_relational_programs_v196 as previous

save, utility, paired_effect = previous.save, previous.utility, previous.paired_effect
acquisition, coverage, relation = previous.acquisition, previous.coverage, previous.relation
conditional, region, trace = previous.conditional, previous.region, previous.trace
LearnedDynamics, canonical_labels = previous.LearnedDynamics, previous.canonical_labels
source_diagnostics, projection_summary = previous.source_diagnostics, previous.projection_summary
MODEL_NAMES = ('UTILITY', *previous.MODEL_NAMES)
MODELS = (*MODEL_NAMES, 'FALLBACK', 'ORACLE')
COMPARATORS = (*previous.MODEL_NAMES, 'FALLBACK')
PRIMARY = ('PROGRAM', 'PROGRAM_NEIGHBOR', 'TERMINAL', 'TREE32', 'LINEAR', 'NONLINEAR', 'OLD_SHARED')
PAIR_MODES = ('UTILITY', *previous.PAIR_MODES)
EPSILON = previous.EPSILON
PREVIOUS = ROOT/'reports/controlled_predictive_frozen_program_replication_v197'
SOURCE_PREVIOUS = ROOT/'reports/controlled_predictive_relational_programs_v196'
OUTPUT = ROOT/'reports/controlled_predictive_utility_program_partition_v198'
RUNTIME = ROOT/'reports/v198_runtime_tmp'
ZERO_COUNTS = ('new_environment_samples', 'new_source_games', 'new_native_weight_updates',
    'new_neighbor_configurations', 'new_parameter_solves', 'shared_library_preparations', 'new_source_cache_roots')


def cohort_cases():
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    cases = []
    for replica in range(4):
        for index in range(24):
            seed = 1980200+24*replica+index; rng = random.Random(seed)
            board = [rng.randint(1, 10) for _ in range(16)]
            first, second = edges[index]; board[first] = board[second] = 1+index%10
            for cell in rng.sample([cell for cell in range(16) if cell not in (first, second)], index%3):
                board[cell] = 0
            cases.append(dict(split='TARGET', replica=replica, stratum=index, horizon=3, seed=seed,
                name=f'v198_target_r{replica:02d}_{index:02d}', board=board, vacancies=index%3))
    return cases


def freeze_choices(roots, models, libraries, region_libraries):
    choices, old_work = previous.freeze_choices(roots,
        {name: models[name] for name in previous.MODEL_NAMES}, libraries, region_libraries)
    work = Counter(old_work); rows = []
    for root in roots:
        decision = core.choose_action(models['UTILITY'], previous.observable(root), libraries['FULL'])
        work.update(decision['work']); work.update(decision.get('feature_work', {})); work['frozen_model_choices'] += 1
        rows.append(dict(root_id=root['root_id'], mode='UTILITY', canonical_action=decision['canonical_action'],
            actual_action=decision['actual_action'], fallback=decision['fallback'], decision=decision))
    return dict(UTILITY=rows, **choices), dict(work)


def success_diagnostics(records, chosen):
    result = {}
    for mode in PAIR_MODES:
        eligible, missed, wrong = 0, [], []
        for row in records:
            actual, oracle = row['models'][mode], row['models']['ORACLE']
            true_delta = actual['components'][2]-oracle['components'][2]
            if actual['regret'] <= EPSILON or abs(true_delta) <= EPSILON:
                continue
            eligible += 1
            first, second = sorted((actual['action'], oracle['action']), key=core.ACTIONS.index)
            pair = chosen[mode][row['root_id']]['decision']['estimated_pairs'][first+'|'+second]
            estimate = pair['estimated_tail_delta'][2]*(1. if pair['actions'][0] == actual['action'] else -1.)
            if abs(estimate) <= EPSILON:
                missed.append(row['root_id'])
            elif (true_delta > 0) != (estimate > 0):
                wrong.append(row['root_id'])
        result[mode] = dict(eligible_roots=eligible, missed=len(missed), wrong_direction=len(wrong),
            missed_root_ids=missed, wrong_direction_root_ids=wrong)
    return result


def summarize(roots, labels, choices, selections, models, source, retained, old_selections):
    labeled = {row['root_id']: row for row in labels}
    chosen = {name: {row['root_id']: row for row in rows} for name, rows in choices.items()}
    records = []
    for root in roots['TARGET']:
        vectors = labeled[root['root_id']]['action_components']; oracle = root['legal_actions'][0]
        for action in root['legal_actions'][1:]:
            if utility(vectors[action]) > utility(vectors[oracle])+EPSILON:
                oracle = action
        metrics = {}
        for name in MODELS:
            decision = None if name == 'ORACLE' else chosen[name][root['root_id']]
            action = oracle if decision is None else decision['canonical_action']; vector = vectors[action]
            metrics[name] = dict(action=action, components=vector, utility=utility(vector),
                regret=utility(vectors[oracle])-utility(vector), fallback=False if decision is None else decision['fallback'])
        records.append(dict(root_id=root['root_id'], replica=root['replica'], stratum=root['stratum'], models=metrics))
    def aggregate(rows):
        result = {}
        for name in MODELS:
            mean = [math.fsum(row['models'][name]['components'][k] for row in rows)/len(rows) for k in range(3)]
            result[name] = dict(components=mean, utility=utility(mean),
                positive_regret_roots=sum(row['models'][name]['regret'] > EPSILON for row in rows),
                fallback_roots=sum(row['models'][name]['fallback'] for row in rows))
        return result
    def contrasts(rows):
        selected = [dict(root_id=row['root_id'], models={'UTILITY': row['models']['UTILITY']}) for row in rows]
        return {'UTILITY_MINUS_'+name: paired_effect(selected,
            [dict(root_id=row['root_id'], models={'UTILITY': row['models'][name]}) for row in rows], 'UTILITY')
            for name in COMPARATORS}
    metrics, effects = aggregate(records), contrasts(records)
    replicas = [dict(replica=replica, roots=len(rows), models=aggregate(rows), comparisons=contrasts(rows))
        for replica in sorted({row['replica'] for row in records})
        for rows in [[row for row in records if row['replica'] == replica]]]
    selection = selections['UTILITY']; modes = deepcopy(retained['SOURCE']['modes'])
    modes['UTILITY'] = dict(selected_depth=selection['selected_depth'], selected_min_leaf_roots=selection['selected_min_leaf_roots'],
        source_heldout_utility=selection['selected_utility'], feature_columns=models['UTILITY']['constants']['columns'],
        actual=deepcopy(source['UTILITY']['metrics']))
    old_utility = old_selections['PROGRAM']['selected_utility']; headroom = metrics['ORACLE']['utility']-metrics['ONE']['utility']
    return dict(schema='acfqp.utility_program_partition.v198.summary', complete=True, roots=len(records),
        SOURCE=dict(roots=len(roots['SOURCE']), design_groups=len({row['source_id'] for row in roots['SOURCE']}), modes=modes,
            heldout_comparison=dict(UTILITY_utility=selection['selected_utility'], PROGRAM_utility=old_utility,
                UTILITY_MINUS_PROGRAM=selection['selected_utility']-old_utility)),
        SOURCE_reuse=dict(retained_modes=list(previous.NEW_MODES), summary_ref='inputs/inherited/v197_summary.json',
            selection_ref='inputs/inherited/v196_selection.json', fields=['SOURCE.modes', 'projection_residuals.SOURCE']),
        models=metrics, comparisons=effects, replicas=replicas, root_records=records,
        projection_residuals=dict(SOURCE=dict(deepcopy(retained['projection_residuals']['SOURCE']),
            UTILITY=deepcopy(source['UTILITY']['projection_residuals'])),
            TARGET={mode: projection_summary(choices[mode]) for mode in PAIR_MODES}),
        success_diagnostics=success_diagnostics(records, chosen),
        oracle_minus_one=headroom, oracle_minus_utility=metrics['ORACLE']['utility']-metrics['UTILITY']['utility'],
        headroom_closed_fraction=effects['UTILITY_MINUS_ONE']['utility']/headroom if headroom > EPSILON else None,
        whole_cohort_positive_vs_primary=all(effects['UTILITY_MINUS_'+name]['utility'] > EPSILON for name in PRIMARY),
        all_replicas_positive_vs_primary=all(row['comparisons']['UTILITY_MINUS_'+name]['utility'] > EPSILON
            for row in replicas for name in PRIMARY), new_predictors_fitted=17, new_tree_fits=17,
        new_learning_attempts=1, new_source_selection_roots=len(roots['SOURCE']),
        new_source_evaluation_roots=len(roots['SOURCE']), **dict.fromkeys(ZERO_COUNTS, 0))


def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_utility_program_partition_v198')
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
        if getattr(module, '__file__', None) and Path(module.__file__).suffix == '.py'
        and any(str(Path(module.__file__).resolve()).startswith(str(ROOT/folder)+'/') for folder in ('src', 'scripts'))}
    paths.update(ROOT/relative for relative in ('scripts/run_controlled_predictive_utility_program_partition_v198.py',
        'scripts/analyze_controlled_predictive_utility_program_partition_v198.py', 'specs/UTILITY_PROGRAM_PARTITION_V198.md',
        'tests/test_utility_program_partition_core_v198.py', 'tests/test_utility_program_partition_runner_v198.py',
        'tests/test_utility_program_partition_analysis_v198.py', 'reports/v198_runtime_tmp/run_checks.py', 'reports/v198_runtime_tmp/run_stage.py'))
    for path in sorted(paths):
        target = output/'source_code'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    save(output/'source_manifest.json', dict(files=[str(path.relative_to(ROOT)) for path in sorted(paths)]))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='acfqp.utility_program_partition.v198.run', status='preparing', phase_history=[], costs={},
        runtime=dict(python=sys.version.split()[0], executable=sys.executable), **dict.fromkeys(ZERO_COUNTS, 0),
        new_predictors_fitted=0, new_tree_fits=0, new_learning_attempts=0, new_source_selection_roots=0, new_source_evaluation_roots=0,
        new_boards_generated=0, new_reference_kernel_attempts=0, new_reference_kernels=0,
        new_teacher_plans=0, new_exact_label_roots=0, completed_roots=0, resource_cap_per_board=200000,
        library_refs=dict(program='inputs/inherited/program_libraries.json', region='inputs/inherited/region_libraries.json'),
        inherited_cost_refs=[dict(path=str(path/filename), fields=fields) for path in (PREVIOUS, SOURCE_PREVIOUS)
            for filename, fields in (('run.json', ['costs', 'inherited_cost_refs']), ('analysis.json', ['costs']))],
        test_refs=[str(RUNTIME/f'{kind}_checks.json') for kind in ('core', 'runner', 'analyzer')])
    inputs, input_work, label_work = [], Counter(), Counter()
    labels, native_labels, label_costs = [], [], []; learning_in_progress = False
    def phase(name):
        record['status'] = name
        record['phase_history'].append(dict(phase=name, seconds_since_start=perf_counter()-begun,
            input_reads=input_work['json_read_operations']))
        save(output/'run.json', record)
        print(json.dumps(dict(event=name, seconds=perf_counter()-begun)), flush=True)
    def read(path, name):
        raw = path.read_bytes(); target = output/'inputs/inherited'/name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        input_work.update(json_read_operations=1, input_bytes_read=len(raw), input_bytes_retained=len(raw))
        inputs.append(dict(path=str(path), saved_ref=str(target.relative_to(output)), bytes=len(raw), phase=record['status']))
        save(output/'input_manifest.json', inputs); return json.loads(raw)
    try:
        capture_code(output); phase('protocol_frozen')
        stage = read(ROOT/'reports/v197_runtime_tmp/stage_checks.json', 'v197_stage_checks.json')
        prior = read(PREVIOUS/'run.json', 'v197_run.json')
        if not stage['valid'] or prior['status'] != 'complete':
            raise ValueError('settled V197 stage is incomplete')
        retained = read(PREVIOUS/'summary.json', 'v197_summary.json')
        source = read(SOURCE_PREVIOUS/'roots.json', 'v196_roots.json')['SOURCE']
        inherited = PREVIOUS/'inputs/inherited'
        programs = read(inherited/'program_models.json', 'program_models.json')
        libraries = read(inherited/'program_libraries.json', 'program_libraries.json')
        old_regions = read(inherited/'region_models.json', 'region_models.json')
        region_libraries = read(inherited/'region_libraries.json', 'region_libraries.json')
        old_pairs = read(inherited/'conditional_models.json', 'conditional_models.json')
        nonlinear = read(inherited/'nonlinear_model.json', 'nonlinear_model.json')
        retained_relation = read(inherited/'relation_model.json', 'relation_model.json')
        expanded = read(inherited/'expanded_models.json', 'expanded_models.json')
        old = read(inherited/'baseline_models.json', 'baseline_models.json')
        rule = LearnedDynamics.from_payload(read(inherited/'learned_rule.json', 'learned_rule.json'))
        dense = read(inherited/'dense_models.json', 'dense_models.json')
        old_selections = read(SOURCE_PREVIOUS/'selection.json', 'v196_selection.json')
        if len(source) != 143 or len({row['source_id'] for row in source}) != 36:
            raise ValueError('fixed SOURCE143/36 differs')
        roots = dict(SOURCE=source, TARGET=[]); save(output/'roots.json', roots)
        phase('source_selection'); tick = perf_counter(); learning_in_progress = True
        record['new_learning_attempts'] += 1; record['new_source_selection_roots'] = len(source)
        fitted = core.fit_models(source, libraries); learning_in_progress = False
        selections, counts = fitted['selection'], fitted['costs']
        record['new_predictors_fitted'] = counts['new_predictors_fitted']; record['new_tree_fits'] = counts['tree_predictors_fitted']
        record['costs']['learning'] = dict(seconds=perf_counter()-tick, counts=counts)
        all_models = dict(expanded, **dense, **programs, **old_regions, **old_pairs, **fitted['models'], NONLINEAR=nonlinear,
            RELATION=retained_relation, OLD_SHARED=old['SHARED'], ONE=old['ONE'])
        save(output/'models.json', all_models); save(output/'selection.json', selections)
        tick = perf_counter(); source_actual = {'UTILITY': source_diagnostics(source, all_models['UTILITY'], libraries['FULL'])}
        record['new_source_evaluation_roots'] = len(source)
        record['costs']['source_evaluation_UTILITY'] = dict(seconds=perf_counter()-tick, counts=source_actual['UTILITY']['work'])
        save(output/'source_diagnostics.json', source_actual)
        phase('models_frozen'); phase('target_roots'); tick = perf_counter()
        cases = cohort_cases(); save(output/'target_cases.json', cases); record['new_boards_generated'] = len(cases)
        target, observation_work = acquisition.observe_roots(cases)
        feature_work = coverage.cache_roots(target); relation_work = relation.cache_roots(target)
        conditional_work = conditional.cache_roots(target); raw_work = region.cache_roots(target)
        program_work = trace.cache_roots(target, rule)
        record['costs']['observations'] = dict(seconds=perf_counter()-tick, counts=observation_work,
            feature_counts=feature_work, relation_counts=relation_work, conditional_counts=conditional_work,
            raw_counts=raw_work, program_counts=program_work)
        roots['TARGET'] = target; save(output/'roots.json', roots)
        tick = perf_counter(); choices, choice_work = freeze_choices(target, all_models, libraries, region_libraries)
        record['costs']['choices'] = dict(seconds=perf_counter()-tick, counts=choice_work)
        save(output/'choices.json', choices); phase('target_choices_frozen'); phase('target_labels')
        label_start = perf_counter()
        for case, root in zip(cases, target, strict=True):
            record['new_reference_kernel_attempts'] += 1
            result = acquisition.exact_labels(case, rule)
            native = dict(result['native'], root_id=root['root_id']); native_labels.append(native)
            labels.append(canonical_labels(root, native, dict(kind='new_exact_V69_FULL', teacher_query='goal_1_risk_1',
                teacher_policy_ref='teacher_policy/'+root['root_id']+'.json')))
            save(output/'teacher_policy'/f"{root['root_id']}.json", result['teacher_policy'])
            label_costs.append(dict(root_id=root['root_id'], costs=result['costs']))
            for kind in ('construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation'):
                label_work.update({kind+'.'+key: value for key, value in result['costs'][kind].items() if type(value) is int})
            record['completed_roots'] += 1; record['new_reference_kernels'] += 1
            record['new_teacher_plans'] += 1; record['new_exact_label_roots'] += 1
            record['costs']['labels'] = dict(seconds=perf_counter()-label_start, counts=dict(label_work))
            save(output/'labels.json', labels); save(output/'native_labels.json', native_labels)
            save(output/'label_costs.json', label_costs); save(output/'run.json', record)
            print(json.dumps(dict(event='label_complete', root=root['root_id'], completed=record['completed_roots'], seconds=perf_counter()-begun)), flush=True)
        save(output/'summary.json', summarize(roots, labels, choices, selections, all_models, source_actual, retained, old_selections))
        record['costs']['input_counts'] = dict(input_work); record['seconds'] = perf_counter()-begun
        phase('complete'); save(output/'run.json', record); return record
    except Exception as error:
        record.update(status='failed', seconds=perf_counter()-begun,
            failure=dict(type=type(error).__name__, message=str(error), counts=getattr(error, 'counts', {}),
                label_seconds=getattr(error, 'elapsed_seconds', 0.)))
        if learning_in_progress and hasattr(error, 'record'):
            save(output/'failed_learning.json', error.record)
            paid = error.record.get('costs', {}); record['costs']['failed_learning'] = dict(counts=paid)
            record['new_predictors_fitted'] = paid.get('new_predictors_fitted', 0)
            record['new_tree_fits'] = paid.get('tree_predictors_fitted', 0)
        record['costs']['input_counts'] = dict(input_work); save(output/'run.json', record); raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
