"""Increase SOURCE coverage, then compare frozen learners on unopened targets."""
import argparse
from collections import Counter
from copy import deepcopy
import importlib
import json
import math
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import controlled_predictive_source_coverage_v185 as core
from acfqp.science import controlled_predictive_fresh_h3_confirmation_v184 as acquisition
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from scripts import run_controlled_predictive_fresh_h3_confirmation_v184 as statistics
from scripts.run_controlled_predictive_exact_h3_v177 import canonical_labels

PREVIOUS = ROOT/'reports/controlled_predictive_fresh_h3_confirmation_v184'
OUTPUT = ROOT/'reports/controlled_predictive_source_coverage_v185'
RUNTIME = ROOT/'reports/v185_runtime_tmp'
EPSILON = 1e-12


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def paired_effect(new_rows, old_rows, name):
    """Paired effect of changing only the declared learner's training dataset."""
    old = {row['root_id']: row for row in old_rows}
    pairs = []
    for row in new_rows:
        new, original = row['models'][name], old[row['root_id']]['models'][name]
        pairs.append(dict(root_id=row['root_id'],
            components=[new['components'][k]-original['components'][k] for k in range(3)],
            utility=new['utility']-original['utility'], action_changed=new['action'] != original['action'],
            new_error=new['regret'] > EPSILON and original['regret'] <= EPSILON,
            resolved_error=new['regret'] <= EPSILON and original['regret'] > EPSILON))
    gains = [row for row in pairs if row['utility'] > EPSILON]
    losses = [row for row in pairs if row['utility'] < -EPSILON]
    positive, negative = math.fsum(row['utility'] for row in gains), math.fsum(row['utility'] for row in losses)
    best = max(gains, key=lambda row: row['utility']) if gains else None
    worst = min(losses, key=lambda row: row['utility']) if losses else None
    mean = [math.fsum(row['components'][k] for row in pairs)/len(pairs) for k in range(3)]
    return dict(components=mean, utility=statistics.utility(mean), improved_roots=len(gains),
        worsened_roots=len(losses), equal_value_roots=len(pairs)-len(gains)-len(losses),
        action_changes=sum(row['action_changed'] for row in pairs),
        new_error_roots=sum(row['new_error'] for row in pairs), resolved_error_roots=sum(row['resolved_error'] for row in pairs),
        positive_gain_sum=positive, negative_gain_sum=negative,
        largest_gain_root=best['root_id'] if best else None, largest_gain=best['utility'] if best else 0.,
        largest_gain_share_of_positive=best['utility']/positive if best else None,
        largest_loss_root=worst['root_id'] if worst else None, largest_loss=worst['utility'] if worst else 0., root_records=pairs)


def summarize(roots, labels, choices, selection):
    new_choices = {name: choices[name] for name in ('RIDGE', 'LAYOUT', 'SHARED', 'ONE', 'FALLBACK')}
    old_choices = {name: choices['OLD_'+name] if name in ('RIDGE', 'LAYOUT', 'SHARED') else choices[name]
        for name in ('RIDGE', 'LAYOUT', 'SHARED', 'ONE', 'FALLBACK')}
    expanded = statistics.summarize(roots['TARGET'], labels, new_choices)
    original = statistics.summarize(roots['TARGET'], labels, old_choices)
    new_rows, old_rows = expanded['root_records'], original['root_records']
    effects = {name+'_MINUS_OLD_'+name: paired_effect(new_rows, old_rows, name)
        for name in ('RIDGE', 'LAYOUT', 'SHARED')}
    replicas = [dict(replica=replica, roots=len(new), effects={name+'_MINUS_OLD_'+name: paired_effect(new, old, name)
        for name in ('RIDGE', 'LAYOUT', 'SHARED')}) for replica in sorted({row['replica'] for row in new_rows})
        for new, old in [([row for row in new_rows if row['replica'] == replica], [row for row in old_rows if row['replica'] == replica])]]
    return dict(schema='acfqp.source_coverage.v185.summary', complete=True,
        SOURCE=dict(roots=len(roots['SOURCE']), old=47, new=96,
            design_groups=len({row['source_id'] for row in roots['SOURCE']}), selected_lambda=selection['selected_lambda'],
            source_selection=[dict(lambda_value=row['lambda_value'], utility=row['utility']) for row in selection['candidates']]),
        expanded=expanded, original=original, coverage_effects=effects, replica_coverage_effects=replicas,
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=15)


def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_source_coverage_v185')
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
        if getattr(module, '__file__', None) and Path(module.__file__).suffix == '.py'
        and any(str(Path(module.__file__).resolve()).startswith(str(ROOT/folder)+'/') for folder in ('src', 'scripts'))}
    paths.update(ROOT/relative for relative in (
        'scripts/run_controlled_predictive_source_coverage_v185.py',
        'scripts/analyze_controlled_predictive_source_coverage_v185.py',
        'specs/SOURCE_COVERAGE_V185.md',
        'tests/test_source_coverage_core_v185.py', 'tests/test_source_coverage_runner_v185.py',
        'tests/test_source_coverage_analysis_v185.py',
        'reports/v185_runtime_tmp/run_checks.py', 'reports/v185_runtime_tmp/run_stage.py'))
    for path in sorted(paths):
        target = output/'source_code'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    save(output/'source_manifest.json', dict(files=[str(path.relative_to(ROOT)) for path in sorted(paths)]))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='acfqp.source_coverage.v185.run', status='preparing', phase_history=[], costs={},
        runtime=dict(python=sys.version.split()[0], executable=sys.executable),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=0,
        new_boards_generated=0, new_reference_kernel_attempts=0, new_reference_kernels=0, new_teacher_plans=0,
        new_exact_label_roots=0, completed_roots=0, resource_cap_per_board=200000,
        inherited_cost_refs=[dict(path=str(PREVIOUS/'run.json'), fields=['costs', 'inherited_cost_refs']),
            dict(path=str(PREVIOUS/'analysis.json'), fields=['costs'])],
        test_refs=[str(RUNTIME/f'{kind}_checks.json') for kind in ('core', 'runner', 'analyzer')])
    inputs, input_work, label_work = [], Counter(), Counter()
    native_labels, label_costs = dict(SOURCE=[], TARGET=[]), []
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
    def acquire(cases, observed, cohort):
        labels = []; tick = perf_counter()
        for case, root in zip(cases, observed, strict=True):
            record['new_reference_kernel_attempts'] += 1
            result = acquisition.exact_labels(case, rule)
            native = dict(result['native'], root_id=root['root_id']); native_labels[cohort].append(native)
            labels.append(canonical_labels(root, native, dict(kind='new_exact_V69_FULL',
                teacher_query='goal_1_risk_1', teacher_policy_ref='teacher_policy/'+root['root_id']+'.json')))
            save(output/'teacher_policy'/f"{root['root_id']}.json", result['teacher_policy'])
            label_costs.append(dict(root_id=root['root_id'], cohort=cohort, costs=result['costs']))
            for kind in ('construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation'):
                label_work.update({kind+'.'+key: value for key, value in result['costs'][kind].items() if type(value) is int})
            record['completed_roots'] += 1; record['new_reference_kernels'] += 1
            record['new_teacher_plans'] += 1; record['new_exact_label_roots'] += 1
            record['costs']['labels'] = dict(counts=dict(label_work))
            record['costs'].setdefault('label_seconds', {})[cohort] = perf_counter()-tick
            save(output/f'{cohort.lower()}_new_labels.json', labels)
            save(output/'native_labels.json', native_labels); save(output/'label_costs.json', label_costs)
            save(output/'run.json', record)
            print(json.dumps(dict(event='label_complete', cohort=cohort, root=root['root_id'],
                completed=record['completed_roots'], seconds=perf_counter()-begun)), flush=True)
        return labels
    try:
        capture_code(output); phase('protocol_frozen')
        stage = read(ROOT/'reports/v184_runtime_tmp/stage_checks.json', 'stage_checks.json')
        prior = read(PREVIOUS/'run.json', 'v184_run.json')
        if not stage['valid'] or prior['status'] != 'complete':
            raise ValueError('settled V184 stage is incomplete')
        old_ridge = read(PREVIOUS/'inputs/inherited/ridge_models.json', 'ridge_models.json')['RIDGE']
        old_baselines = read(PREVIOUS/'inputs/inherited/baseline_models.json', 'baseline_models.json')
        rule = LearnedDynamics.from_payload(read(PREVIOUS/'inputs/inherited/learned_rule.json', 'learned_rule.json'))
        original_source = deepcopy(old_ridge['training_outcomes'])
        if len(original_source) != 47 or len({row['source_id'] for row in original_source}) != 12:
            raise ValueError('fixed original SOURCE roster differs')
        phase('source_roots'); tick = perf_counter()
        source_cases = core.cohort_cases('SOURCE'); save(output/'source_cases.json', source_cases)
        fresh_source, source_observation = core.observe_roots(source_cases)
        record['new_boards_generated'] += len(source_cases)
        source_features = core.cache_roots(original_source+fresh_source)
        record['costs']['source_observations'] = dict(seconds=perf_counter()-tick, counts=source_observation, feature_counts=source_features)
        phase('source_labels'); source_labels = original_source+acquire(source_cases, fresh_source, 'SOURCE')
        save(output/'source_labels.json', source_labels)
        roots = dict(SOURCE=source_labels, TARGET=[]); save(output/'roots.json', roots)
        phase('source_selection'); tick = perf_counter(); result = core.fit_expanded(source_labels)
        selection, new_models = result['selection'], result['models']
        selection.pop('model')
        record['new_predictors_fitted'] = 15
        record['costs']['learning'] = dict(seconds=perf_counter()-tick, counts=result['costs'])
        save(output/'selection.json', selection); save(output/'models.json', new_models)
        phase('models_frozen'); phase('target_roots'); tick = perf_counter()
        target_cases = core.cohort_cases('TARGET'); save(output/'target_cases.json', target_cases)
        target_roots, target_observation = core.observe_roots(target_cases)
        record['new_boards_generated'] += len(target_cases)
        target_features = core.cache_roots(target_roots)
        roots['TARGET'] = target_roots; save(output/'roots.json', roots)
        record['costs']['target_observations'] = dict(seconds=perf_counter()-tick, counts=target_observation, feature_counts=target_features)
        models = dict(new_models, OLD_RIDGE=old_ridge, OLD_LAYOUT=old_baselines['LAYOUT'],
            OLD_SHARED=old_baselines['SHARED'], ONE=old_baselines['ONE'])
        tick = perf_counter(); choices, choice_work = core.freeze_choices(target_roots, models)
        record['costs']['choices'] = dict(seconds=perf_counter()-tick, counts=choice_work)
        save(output/'choices.json', choices); phase('target_choices_frozen'); phase('target_labels')
        labels = acquire(target_cases, target_roots, 'TARGET'); save(output/'labels.json', labels)
        save(output/'summary.json', summarize(roots, labels, choices, selection))
        record['costs']['input_counts'] = dict(input_work)
        record['seconds'] = perf_counter()-begun; phase('complete'); save(output/'run.json', record)
        return record
    except Exception as error:
        record.update(status='failed', seconds=perf_counter()-begun,
            failure=dict(type=type(error).__name__, message=str(error), counts=getattr(error, 'counts', {}),
                label_seconds=getattr(error, 'elapsed_seconds', 0.)))
        if hasattr(error, 'record'):
            save(output/'failed_learning.json', error.record)
            record['costs']['failed_learning'] = error.record.get('costs', {})
            paid = record['costs']['failed_learning']
            record['new_predictors_fitted'] = paid.get('ridge_predictors_fitted', 0)+paid.get('shared_predictors_fitted', 0)
        record['costs']['input_counts'] = dict(input_work); save(output/'run.json', record); raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
