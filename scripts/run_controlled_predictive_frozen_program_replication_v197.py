"""Fresh-cohort replication with every V196 predictor and library frozen."""
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
from scripts import run_controlled_predictive_relational_programs_v196 as previous

save, utility, paired_effect = previous.save, previous.utility, previous.paired_effect
acquisition, coverage, relation = previous.acquisition, previous.coverage, previous.relation
conditional, region, trace = previous.conditional, previous.region, previous.trace
LearnedDynamics, canonical_labels = previous.LearnedDynamics, previous.canonical_labels
freeze_choices = previous.freeze_choices
projection_summary, success_diagnostics = previous.projection_summary, previous.success_diagnostics
MODEL_NAMES, MODELS = previous.MODEL_NAMES, previous.MODELS
COMPARATORS, PRIMARY, PAIR_MODES = previous.COMPARATORS, previous.PRIMARY, previous.PAIR_MODES
EPSILON = previous.EPSILON
PREVIOUS = ROOT/'reports/controlled_predictive_relational_programs_v196'
OUTPUT = ROOT/'reports/controlled_predictive_frozen_program_replication_v197'
RUNTIME = ROOT/'reports/v197_runtime_tmp'
ZERO_COUNTS = ('new_environment_samples', 'new_source_games', 'new_native_weight_updates',
    'new_predictors_fitted', 'new_tree_fits', 'new_neighbor_configurations', 'new_parameter_solves',
    'shared_library_preparations', 'new_learning_attempts', 'new_source_cache_roots',
    'new_source_evaluation_roots', 'new_source_selection_roots')


def cohort_cases():
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    cases = []
    for replica in range(4):
        for index in range(24):
            seed = 1970200+24*replica+index; rng = random.Random(seed)
            board = [rng.randint(1, 10) for _ in range(16)]
            first, second = edges[index]; board[first] = board[second] = 1+index%10
            for cell in rng.sample([cell for cell in range(16) if cell not in (first, second)], index%3):
                board[cell] = 0
            cases.append(dict(split='TARGET', replica=replica, stratum=index, horizon=3, seed=seed,
                name=f'v197_target_r{replica:02d}_{index:02d}', board=board, vacancies=index%3))
    return cases


def summarize(roots, labels, choices, retained):
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
        selected = [dict(root_id=row['root_id'], models={'PROGRAM': row['models']['PROGRAM']}) for row in rows]
        return {'PROGRAM_MINUS_'+name: paired_effect(selected,
            [dict(root_id=row['root_id'], models={'PROGRAM': row['models'][name]}) for row in rows], 'PROGRAM')
            for name in COMPARATORS}
    metrics, effects = aggregate(records), contrasts(records)
    replicas = [dict(replica=replica, roots=len(rows), models=aggregate(rows), comparisons=contrasts(rows))
        for replica in sorted({row['replica'] for row in records})
        for rows in [[row for row in records if row['replica'] == replica]]]
    cross = {'PROGRAM_MINUS_'+name: dict(
        V196_utility_delta=retained['comparisons']['PROGRAM_MINUS_'+name]['utility'],
        V197_utility_delta=effects['PROGRAM_MINUS_'+name]['utility'],
        V196_positive_replicas=sum(row['comparisons']['PROGRAM_MINUS_'+name]['utility'] > EPSILON for row in retained['replicas']),
        V197_positive_replicas=sum(row['comparisons']['PROGRAM_MINUS_'+name]['utility'] > EPSILON for row in replicas))
        for name in PRIMARY}
    headroom = metrics['ORACLE']['utility']-metrics['ONE']['utility']
    return dict(schema='acfqp.frozen_program_replication.v197.summary', complete=True, roots=len(records),
        SOURCE=deepcopy(retained['SOURCE']),
        SOURCE_reuse=dict(retained=True, summary_ref='inputs/inherited/v196_summary.json', fields=['SOURCE', 'projection_residuals.SOURCE']),
        models=metrics, comparisons=effects, replicas=replicas, root_records=records,
        projection_residuals=dict(SOURCE=deepcopy(retained['projection_residuals']['SOURCE']),
            TARGET={mode: projection_summary(choices[mode]) for mode in PAIR_MODES}),
        success_diagnostics=success_diagnostics(records, chosen), cross_cohort_comparisons=cross,
        oracle_minus_one=headroom, oracle_minus_program=metrics['ORACLE']['utility']-metrics['PROGRAM']['utility'],
        headroom_closed_fraction=effects['PROGRAM_MINUS_ONE']['utility']/headroom if headroom > EPSILON else None,
        whole_cohort_positive_vs_primary=all(effects['PROGRAM_MINUS_'+name]['utility'] > EPSILON for name in PRIMARY),
        all_replicas_positive_vs_primary=all(row['comparisons']['PROGRAM_MINUS_'+name]['utility'] > EPSILON
            for row in replicas for name in PRIMARY), **dict.fromkeys(ZERO_COUNTS, 0))


def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_frozen_program_replication_v197')
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
        if getattr(module, '__file__', None) and Path(module.__file__).suffix == '.py'
        and any(str(Path(module.__file__).resolve()).startswith(str(ROOT/folder)+'/') for folder in ('src', 'scripts'))}
    paths.update(ROOT/relative for relative in ('scripts/run_controlled_predictive_frozen_program_replication_v197.py',
        'scripts/analyze_controlled_predictive_frozen_program_replication_v197.py', 'specs/FROZEN_PROGRAM_REPLICATION_V197.md',
        'tests/test_frozen_program_replication_runner_v197.py', 'tests/test_frozen_program_replication_analysis_v197.py',
        'reports/v197_runtime_tmp/run_checks.py', 'reports/v197_runtime_tmp/run_stage.py'))
    for path in sorted(paths):
        target = output/'source_code'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    save(output/'source_manifest.json', dict(files=[str(path.relative_to(ROOT)) for path in sorted(paths)]))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='acfqp.frozen_program_replication.v197.run', status='preparing', phase_history=[], costs={},
        runtime=dict(python=sys.version.split()[0], executable=sys.executable), **dict.fromkeys(ZERO_COUNTS, 0),
        new_boards_generated=0, new_reference_kernel_attempts=0, new_reference_kernels=0,
        new_teacher_plans=0, new_exact_label_roots=0, completed_roots=0, resource_cap_per_board=200000,
        library_refs=dict(program='inputs/inherited/program_libraries.json', region='inputs/inherited/region_libraries.json'),
        inherited_cost_refs=[dict(path=str(PREVIOUS/'run.json'), fields=['costs', 'inherited_cost_refs']),
            dict(path=str(PREVIOUS/'analysis.json'), fields=['costs'])],
        test_refs=[str(RUNTIME/f'{kind}_checks.json') for kind in ('runner', 'analyzer')])
    inputs, input_work, label_work = [], Counter(), Counter()
    labels, native_labels, label_costs = [], [], []
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
        stage = read(ROOT/'reports/v196_runtime_tmp/stage_checks.json', 'v196_stage_checks.json')
        prior = read(PREVIOUS/'run.json', 'v196_run.json')
        if not stage['valid'] or prior['status'] != 'complete':
            raise ValueError('settled V196 stage is incomplete')
        retained = read(PREVIOUS/'summary.json', 'v196_summary.json')
        programs = read(PREVIOUS/'models.json', 'program_models.json')
        libraries = read(PREVIOUS/'libraries.json', 'program_libraries.json')
        inherited = PREVIOUS/'inputs/inherited'
        old_regions = read(inherited/'region_models.json', 'region_models.json')
        region_libraries = read(inherited/'region_libraries.json', 'region_libraries.json')
        old_pairs = read(inherited/'conditional_models.json', 'conditional_models.json')
        nonlinear = read(inherited/'nonlinear_model.json', 'nonlinear_model.json')
        retained_relation = read(inherited/'relation_model.json', 'relation_model.json')
        expanded = read(inherited/'expanded_models.json', 'expanded_models.json')
        old = read(inherited/'baseline_models.json', 'baseline_models.json')
        rule = LearnedDynamics.from_payload(read(inherited/'learned_rule.json', 'learned_rule.json'))
        dense = read(inherited/'dense_models.json', 'dense_models.json')
        all_models = dict(expanded, **dense, **programs, **old_regions, **old_pairs, NONLINEAR=nonlinear, RELATION=retained_relation,
            OLD_SHARED=old['SHARED'], ONE=old['ONE'])
        save(output/'models.json', all_models); phase('models_frozen'); phase('target_roots'); tick = perf_counter()
        cases = cohort_cases(); save(output/'target_cases.json', cases); record['new_boards_generated'] = len(cases)
        target, observation_work = acquisition.observe_roots(cases)
        feature_work = coverage.cache_roots(target); relation_work = relation.cache_roots(target)
        conditional_work = conditional.cache_roots(target); raw_work = region.cache_roots(target)
        program_work = trace.cache_roots(target, rule)
        record['costs']['observations'] = dict(seconds=perf_counter()-tick, counts=observation_work,
            feature_counts=feature_work, relation_counts=relation_work, conditional_counts=conditional_work,
            raw_counts=raw_work, program_counts=program_work)
        roots = dict(TARGET=target); save(output/'roots.json', roots)
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
        save(output/'summary.json', summarize(roots, labels, choices, retained))
        record['costs']['input_counts'] = dict(input_work); record['seconds'] = perf_counter()-begun
        phase('complete'); save(output/'run.json', record); return record
    except Exception as error:
        record.update(status='failed', seconds=perf_counter()-begun,
            failure=dict(type=type(error).__name__, message=str(error), counts=getattr(error, 'counts', {}),
                label_seconds=getattr(error, 'elapsed_seconds', 0.)))
        record['costs']['input_counts'] = dict(input_work); save(output/'run.json', record); raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
