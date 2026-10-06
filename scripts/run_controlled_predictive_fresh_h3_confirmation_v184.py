"""Confirm frozen SOURCE models on an unopened, predeclared H3 board cohort."""
import argparse
from collections import Counter
import importlib
import json
import math
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import controlled_predictive_fresh_h3_confirmation_v184 as core
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from scripts.run_controlled_predictive_exact_h3_v177 import canonical_labels

OUTPUT = ROOT/'reports/controlled_predictive_fresh_h3_confirmation_v184'
RUNTIME = ROOT/'reports/v184_runtime_tmp'
PREVIOUS = ROOT/'reports/controlled_predictive_source_regularization_v183'
BASELINES = ROOT/'reports/controlled_predictive_rank_layout_consequences_v182'
MODELS = ('RIDGE', 'LAYOUT', 'SHARED', 'ONE', 'FALLBACK', 'ORACLE')
EPSILON = 1e-12


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def utility(vector):
    return vector[0]-vector[1]+vector[2]


def summarize(roots, labels, choices):
    """Report every root and replica, retaining both outcome gains and losses."""
    label_index = {row['root_id']: row for row in labels}
    choice_index = {name: {row['root_id']: row for row in rows} for name, rows in choices.items()}
    records = []
    for root in roots:
        vectors = label_index[root['root_id']]['action_components']
        oracle = root['legal_actions'][0]
        for action in root['legal_actions'][1:]:
            if utility(vectors[action]) > utility(vectors[oracle])+EPSILON:
                oracle = action
        modes = {}
        for name in MODELS:
            decision = None if name == 'ORACLE' else choice_index[name][root['root_id']]
            action = oracle if decision is None else decision['canonical_action']
            vector = vectors[action]
            modes[name] = dict(action=action, components=vector, utility=utility(vector),
                regret=utility(vectors[oracle])-utility(vector),
                fallback=False if decision is None else decision['fallback'])
        records.append(dict(root_id=root['root_id'], replica=root['replica'], stratum=root['stratum'],
            models=modes))

    def aggregate(rows):
        result = {}
        for name in MODELS:
            vectors = [row['models'][name]['components'] for row in rows]
            mean = [math.fsum(vector[k] for vector in vectors)/len(rows) for k in range(3)]
            result[name] = dict(components=mean, utility=utility(mean),
                positive_regret_roots=sum(row['models'][name]['regret'] > EPSILON for row in rows),
                fallback_roots=sum(row['models'][name]['fallback'] for row in rows))
        return result

    def contrasts(rows):
        result = {}
        for baseline in ('ONE', 'LAYOUT', 'SHARED'):
            paired = []
            for row in rows:
                ridge, other = row['models']['RIDGE'], row['models'][baseline]
                paired.append(dict(root_id=row['root_id'],
                    components=[ridge['components'][k]-other['components'][k] for k in range(3)],
                    utility=ridge['utility']-other['utility'],
                    action_changed=ridge['action'] != other['action'],
                    new_error=ridge['regret'] > EPSILON and other['regret'] <= EPSILON,
                    resolved_error=ridge['regret'] <= EPSILON and other['regret'] > EPSILON))
            gains = [row for row in paired if row['utility'] > EPSILON]
            losses = [row for row in paired if row['utility'] < -EPSILON]
            positive = math.fsum(row['utility'] for row in gains)
            negative = math.fsum(row['utility'] for row in losses)
            largest = max(gains, key=lambda row: row['utility']) if gains else None
            worst = min(losses, key=lambda row: row['utility']) if losses else None
            mean = [math.fsum(row['components'][k] for row in paired)/len(rows) for k in range(3)]
            result['RIDGE_MINUS_'+baseline] = dict(components=mean, utility=utility(mean),
                improved_roots=len(gains), worsened_roots=len(losses), equal_value_roots=len(rows)-len(gains)-len(losses),
                action_changes=sum(row['action_changed'] for row in paired),
                new_error_roots=sum(row['new_error'] for row in paired),
                resolved_error_roots=sum(row['resolved_error'] for row in paired),
                positive_gain_sum=positive, negative_gain_sum=negative,
                largest_gain_root=largest['root_id'] if largest else None,
                largest_gain=largest['utility'] if largest else 0.,
                largest_gain_share_of_positive=largest['utility']/positive if largest else None,
                largest_loss_root=worst['root_id'] if worst else None,
                largest_loss=worst['utility'] if worst else 0., root_records=paired)
        return result

    replicas = [dict(replica=replica, roots=len(rows), models=aggregate(rows), comparisons=contrasts(rows))
        for replica in sorted({row['replica'] for row in records})
        for rows in [[row for row in records if row['replica'] == replica]]]
    model_metrics, comparisons = aggregate(records), contrasts(records)
    headroom = model_metrics['ORACLE']['utility']-model_metrics['ONE']['utility']
    coverage = [item for row in choices['RIDGE'] for item in row['decision']['coverage'].values()]
    return dict(schema='acfqp.fresh_h3_confirmation.v184.summary', complete=True, roots=len(records),
        models=model_metrics, comparisons=comparisons, replicas=replicas, root_records=records,
        oracle_minus_one=headroom,
        oracle_minus_ridge=model_metrics['ORACLE']['utility']-model_metrics['RIDGE']['utility'],
        headroom_closed_fraction=comparisons['RIDGE_MINUS_ONE']['utility']/headroom if headroom > EPSILON else None,
        feature_coverage=dict(total_tokens=sum(row['total_tokens'] for row in coverage),
            known_tokens=sum(row['known_tokens'] for row in coverage),
            unknown_tokens=sum(row['unknown_tokens'] for row in coverage)),
        whole_cohort_positive_vs_one_and_shared=all(comparisons['RIDGE_MINUS_'+name]['utility'] > EPSILON
            for name in ('ONE', 'SHARED')),
        all_replicas_positive_vs_one_and_shared=all(row['comparisons']['RIDGE_MINUS_'+name]['utility'] > EPSILON
            for row in replicas for name in ('ONE', 'SHARED')),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=0)


def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_fresh_h3_confirmation_v184')
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
        if getattr(module, '__file__', None) and Path(module.__file__).suffix == '.py'
        and any(str(Path(module.__file__).resolve()).startswith(str(ROOT/folder)+'/')
            for folder in ('src', 'scripts'))}
    paths.update(ROOT/relative for relative in (
        'scripts/run_controlled_predictive_fresh_h3_confirmation_v184.py',
        'scripts/analyze_controlled_predictive_fresh_h3_confirmation_v184.py',
        'specs/FRESH_H3_CONFIRMATION_V184.md',
        'tests/test_fresh_h3_confirmation_core_v184.py',
        'tests/test_fresh_h3_confirmation_runner_v184.py',
        'tests/test_fresh_h3_confirmation_analysis_v184.py',
        'reports/v184_runtime_tmp/run_checks.py', 'reports/v184_runtime_tmp/run_stage.py'))
    for path in sorted(paths):
        target = output/'source_code'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    save(output/'source_manifest.json', dict(files=[str(path.relative_to(ROOT)) for path in sorted(paths)]))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='acfqp.fresh_h3_confirmation.v184.run', status='preparing', phase_history=[],
        runtime=dict(python=sys.version.split()[0], executable=sys.executable), costs={},
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0,
        new_predictors_fitted=0, new_reference_kernel_attempts=0, new_reference_kernels=0, new_teacher_plans=0, new_exact_label_roots=0,
        completed_roots=0, resource_cap_per_board=200000,
        inherited_cost_refs=[dict(path=str(PREVIOUS/'run.json'), fields=['costs', 'inherited_cost_refs']),
            dict(path=str(PREVIOUS/'analysis.json'), fields=['costs']),
            dict(path=str(BASELINES/'run.json'), fields=['costs', 'inherited_cost_refs']),
            dict(path=str(ROOT/'reports/controlled_predictive_composition_v69/manifest.json'), fields=['acquisition', 'rule'])],
        test_refs=[str(RUNTIME/f'{kind}_checks.json') for kind in ('core', 'runner', 'analyzer')])
    inputs, input_work, label_work = [], Counter(), Counter()
    label_costs, labels, native_labels = [], [], []
    def phase(name):
        record['status'] = name
        record['phase_history'].append(dict(phase=name, seconds_since_start=perf_counter()-begun,
            input_reads=input_work['json_read_operations']))
        save(output/'run.json', record)
        print(json.dumps(dict(event=name, seconds=perf_counter()-begun)), flush=True)
    def read(path, name, selected_models=None):
        raw = path.read_bytes(); payload = json.loads(raw)
        saved = raw if selected_models is None else (json.dumps(
            {key: payload[key] for key in selected_models}, indent=2, allow_nan=False)+'\n').encode()
        target = output/'inputs/inherited'/name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(saved)
        input_work.update(json_read_operations=1, input_bytes_read=len(raw), input_bytes_retained=len(saved))
        row = dict(path=str(path), saved_ref=str(target.relative_to(output)), bytes=len(raw),
            saved_bytes=len(saved), phase=record['status'])
        if selected_models is not None:
            row['selected_models'] = list(selected_models)
        inputs.append(row); save(output/'input_manifest.json', inputs)
        return json.loads(saved)
    try:
        capture_code(output); phase('protocol_frozen')
        stage = read(ROOT/'reports/v183_runtime_tmp/stage_checks.json', 'stage_checks.json')
        prior = read(PREVIOUS/'run.json', 'v183_run.json')
        if not stage['valid'] or prior['status'] != 'complete':
            raise ValueError('settled V183 stage is incomplete')
        ridge = read(PREVIOUS/'models.json', 'ridge_models.json')['RIDGE']
        baselines = read(BASELINES/'models.json', 'baseline_models.json', ('LAYOUT', 'SHARED', 'ONE'))
        rule = LearnedDynamics.from_payload(read(ROOT/'reports/controlled_predictive_composition_v69/learned_rule.json', 'learned_rule.json'))
        if ridge['constants']['lambda_value'] != .1:
            raise ValueError('V183 selected lambda differs from frozen 0.1')
        models = dict(baselines, RIDGE=ridge)
        save(output/'models.json', {name: dict(saved_ref='inputs/inherited/'+(
            'ridge_models.json' if name == 'RIDGE' else 'baseline_models.json'), model_key=name) for name in models})
        phase('models_frozen'); tick = perf_counter()
        cases = core.fresh_cases(); save(output/'cases.json', cases)
        roots, observation_work = core.observe_roots(cases)
        record['new_boards_generated'] = len(cases)
        record['costs']['observations'] = dict(seconds=perf_counter()-tick, counts=observation_work)
        tick = perf_counter(); choices, choice_work = core.freeze_choices(roots, models)
        save(output/'roots.json', roots); save(output/'choices.json', choices)
        record['costs']['choices'] = dict(seconds=perf_counter()-tick, counts=choice_work)
        phase('target_choices_frozen'); phase('target_labels'); label_begun = perf_counter()
        for case, root in zip(cases, roots, strict=True):
            record['new_reference_kernel_attempts'] += 1
            result = core.exact_labels(case, rule)
            native = dict(result['native'], root_id=root['root_id'])
            native_labels.append(native)
            labels.append(canonical_labels(root, native, dict(kind='new_exact_V69_FULL',
                teacher_query='goal_1_risk_1', teacher_policy_ref='teacher_policy/'+root['root_id']+'.json')))
            save(output/'teacher_policy'/f"{root['root_id']}.json", result['teacher_policy'])
            label_costs.append(dict(root_id=root['root_id'], costs=result['costs']))
            for kind in ('construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation'):
                label_work.update({kind+'.'+key: value for key, value in result['costs'][kind].items()
                    if type(value) is int})
            record['completed_roots'] += 1
            record['new_reference_kernels'] += 1; record['new_teacher_plans'] += 1; record['new_exact_label_roots'] += 1
            record['costs']['labels'] = dict(seconds=perf_counter()-label_begun, counts=dict(label_work))
            save(output/'labels.json', labels); save(output/'native_labels.json', native_labels)
            save(output/'label_costs.json', label_costs); save(output/'run.json', record)
            print(json.dumps(dict(event='label_complete', root=root['root_id'], completed=record['completed_roots'],
                seconds=perf_counter()-begun)), flush=True)
        save(output/'summary.json', summarize(roots, labels, choices))
        record['costs']['input_counts'] = dict(input_work)
        record['seconds'] = perf_counter()-begun; phase('complete'); save(output/'run.json', record)
        return record
    except Exception as error:
        record.update(status='failed', seconds=perf_counter()-begun,
            failure=dict(type=type(error).__name__, message=str(error), counts=getattr(error, 'counts', {}),
                label_seconds=getattr(error, 'elapsed_seconds', 0.)))
        record['costs']['input_counts'] = dict(input_work)
        save(output/'run.json', record); raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
