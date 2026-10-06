"""Learn shared mechanism interactions with a matched linear selection control."""
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
from acfqp.science import controlled_predictive_mechanism_interactions_v188 as core
from acfqp.science import controlled_predictive_fresh_h3_confirmation_v184 as acquisition
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from scripts.run_controlled_predictive_exact_h3_v177 import canonical_labels
from scripts.run_controlled_predictive_source_coverage_v185 import paired_effect

PREVIOUS = ROOT/'reports/controlled_predictive_position_shared_v187'
OUTPUT = ROOT/'reports/controlled_predictive_mechanism_interactions_v188'
RUNTIME = ROOT/'reports/v188_runtime_tmp'
MODELS = (*core.MODEL_NAMES, 'FALLBACK', 'ORACLE')
CONTROLS = ('LINEAR', 'RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE')
EPSILON = 1e-12


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def utility(vector):
    return vector[0]-vector[1]+vector[2]


def summarize(roots, labels, choices, selection, models):
    label_index = {row['root_id']: row for row in labels}
    choice_index = {name: {row['root_id']: row for row in rows} for name, rows in choices.items()}
    records = []
    for root in roots['TARGET']:
        vectors = label_index[root['root_id']]['action_components']
        oracle = root['legal_actions'][0]
        for action in root['legal_actions'][1:]:
            if utility(vectors[action]) > utility(vectors[oracle])+EPSILON:
                oracle = action
        root_models = {}
        for name in MODELS:
            decision = None if name == 'ORACLE' else choice_index[name][root['root_id']]
            action = oracle if decision is None else decision['canonical_action']
            vector = vectors[action]
            root_models[name] = dict(action=action, components=vector, utility=utility(vector),
                regret=utility(vectors[oracle])-utility(vector),
                fallback=False if decision is None else decision['fallback'])
        records.append(dict(root_id=root['root_id'], replica=root['replica'], stratum=root['stratum'], models=root_models))

    def aggregate(rows):
        result = {}
        for name in MODELS:
            mean = [math.fsum(row['models'][name]['components'][k] for row in rows)/len(rows) for k in range(3)]
            result[name] = dict(components=mean, utility=utility(mean),
                positive_regret_roots=sum(row['models'][name]['regret'] > EPSILON for row in rows),
                fallback_roots=sum(row['models'][name]['fallback'] for row in rows))
        return result

    def contrasts(rows):
        ranked = [dict(root_id=row['root_id'], models={'INTERACT': row['models']['INTERACT']}) for row in rows]
        return {'INTERACT_MINUS_'+name: paired_effect(ranked,
            [dict(root_id=row['root_id'], models={'INTERACT': row['models'][name]}) for row in rows], 'INTERACT')
            for name in CONTROLS}

    metrics, effects = aggregate(records), contrasts(records)
    replicas = [dict(replica=replica, roots=len(rows), models=aggregate(rows), comparisons=contrasts(rows))
        for replica in sorted({row['replica'] for row in records})
        for rows in [[row for row in records if row['replica'] == replica]]]
    headroom = metrics['ORACLE']['utility']-metrics['ONE']['utility']
    return dict(schema='acfqp.mechanism_interactions.v188.summary', complete=True, roots=len(records),
        SOURCE=dict(roots=len(roots['SOURCE']), design_groups=len({row['source_id'] for row in roots['SOURCE']}),
            learners={name: dict(selected_lambda=selection[name]['selected_lambda'],
                source_heldout_utility=selection[name]['selected_utility'],
                source_selection=[dict(lambda_value=row['lambda_value'], utility=row['utility']) for row in selection[name]['candidates']],
                columns=models[name]['constants']['columns'], source_rank=models[name]['rank'],
                source_root_mean_loss=models[name]['root_mean_loss']) for name in ('LINEAR', 'INTERACT')}),
        models=metrics, comparisons=effects, replicas=replicas, root_records=records,
        oracle_minus_one=headroom, oracle_minus_interact=metrics['ORACLE']['utility']-metrics['INTERACT']['utility'],
        headroom_closed_fraction=effects['INTERACT_MINUS_ONE']['utility']/headroom if headroom > EPSILON else None,
        whole_cohort_positive_vs_linear_ridge_old_shared=all(effects['INTERACT_MINUS_'+name]['utility'] > EPSILON
            for name in ('LINEAR', 'RIDGE', 'OLD_SHARED')),
        all_replicas_positive_vs_linear_ridge_old_shared=all(row['comparisons']['INTERACT_MINUS_'+name]['utility'] > EPSILON
            for row in replicas for name in ('LINEAR', 'RIDGE', 'OLD_SHARED')),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=26)


def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_mechanism_interactions_v188')
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
        if getattr(module, '__file__', None) and Path(module.__file__).suffix == '.py'
        and any(str(Path(module.__file__).resolve()).startswith(str(ROOT/folder)+'/') for folder in ('src', 'scripts'))}
    paths.update(ROOT/relative for relative in (
        'scripts/run_controlled_predictive_mechanism_interactions_v188.py',
        'scripts/analyze_controlled_predictive_mechanism_interactions_v188.py',
        'specs/MECHANISM_INTERACTIONS_V188.md', 'tests/test_mechanism_interactions_core_v188.py',
        'tests/test_mechanism_interactions_runner_v188.py', 'tests/test_mechanism_interactions_analysis_v188.py',
        'reports/v188_runtime_tmp/run_checks.py', 'reports/v188_runtime_tmp/run_stage.py'))
    for path in sorted(paths):
        target = output/'source_code'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    save(output/'source_manifest.json', dict(files=[str(path.relative_to(ROOT)) for path in sorted(paths)]))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='acfqp.mechanism_interactions.v188.run', status='preparing', phase_history=[], costs={},
        runtime=dict(python=sys.version.split()[0], executable=sys.executable),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=0,
        new_learning_attempts=0, new_boards_generated=0, new_reference_kernel_attempts=0,
        new_reference_kernels=0, new_teacher_plans=0, new_exact_label_roots=0, completed_roots=0,
        resource_cap_per_board=200000,
        inherited_cost_refs=[dict(path=str(PREVIOUS/'run.json'), fields=['costs', 'inherited_cost_refs']),
            dict(path=str(PREVIOUS/'analysis.json'), fields=['costs']),
            dict(path=str(PREVIOUS/'posthoc_feature_aliases.json'), fields=['seconds', 'new_fits', 'new_labels'])],
        test_refs=[str(RUNTIME/f'{kind}_checks.json') for kind in ('core', 'runner', 'analyzer')])
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
        stage = read(ROOT/'reports/v187_runtime_tmp/stage_checks.json', 'stage_checks.json')
        prior = read(PREVIOUS/'run.json', 'v187_run.json')
        if not stage['valid'] or prior['status'] != 'complete':
            raise ValueError('settled V187 stage is incomplete')
        source = read(PREVIOUS/'source_labels.json', 'source_labels.json')
        expanded = read(PREVIOUS/'inputs/inherited/expanded_models.json', 'expanded_models.json')
        old = read(PREVIOUS/'inputs/inherited/baseline_models.json', 'baseline_models.json')
        rule = LearnedDynamics.from_payload(read(PREVIOUS/'inputs/inherited/learned_rule.json', 'learned_rule.json'))
        if len(source) != 143 or len({row['source_id'] for row in source}) != 36:
            raise ValueError('fixed SOURCE143/36 groups differ')
        if expanded['RIDGE']['constants']['lambda_value'] != .1:
            raise ValueError('frozen SOURCE strength differs')
        save(output/'source_labels.json', source)
        roots = dict(SOURCE=source, TARGET=[]); save(output/'roots.json', roots)
        phase('source_selection'); tick = perf_counter(); record['new_learning_attempts'] += 1
        fitted = core.fit_models(source)
        new_models, selection = fitted['models'], dict(fitted['selections'], costs=fitted['costs'])
        record['new_predictors_fitted'] = fitted['costs']['ridge_predictors_fitted']
        record['costs']['learning'] = dict(seconds=perf_counter()-tick, counts=fitted['costs'])
        save(output/'selection.json', selection); save(output/'models.json', new_models)
        phase('models_frozen'); phase('target_roots'); tick = perf_counter()
        cases = core.cohort_cases(); save(output/'target_cases.json', cases)
        target, observation_work = core.observe_roots(cases); feature_work = core.cache_roots(target)
        record['new_boards_generated'] = len(cases)
        record['costs']['observations'] = dict(seconds=perf_counter()-tick, counts=observation_work, feature_counts=feature_work)
        roots['TARGET'] = target; save(output/'roots.json', roots)
        models = dict(expanded, **new_models, OLD_SHARED=old['SHARED'], ONE=old['ONE'])
        tick = perf_counter(); choices, choice_work = core.freeze_choices(target, models)
        record['costs']['choices'] = dict(seconds=perf_counter()-tick, counts=choice_work)
        save(output/'choices.json', choices); phase('target_choices_frozen'); phase('target_labels')
        label_start = perf_counter()
        for case, root in zip(cases, target, strict=True):
            record['new_reference_kernel_attempts'] += 1
            result = acquisition.exact_labels(case, rule)
            native = dict(result['native'], root_id=root['root_id']); native_labels.append(native)
            labels.append(canonical_labels(root, native, dict(kind='new_exact_V69_FULL',
                teacher_query='goal_1_risk_1', teacher_policy_ref='teacher_policy/'+root['root_id']+'.json')))
            save(output/'teacher_policy'/f"{root['root_id']}.json", result['teacher_policy'])
            label_costs.append(dict(root_id=root['root_id'], costs=result['costs']))
            for kind in ('construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation'):
                label_work.update({kind+'.'+key: value for key, value in result['costs'][kind].items() if type(value) is int})
            record['completed_roots'] += 1; record['new_reference_kernels'] += 1
            record['new_teacher_plans'] += 1; record['new_exact_label_roots'] += 1
            record['costs']['labels'] = dict(seconds=perf_counter()-label_start, counts=dict(label_work))
            save(output/'labels.json', labels); save(output/'native_labels.json', native_labels)
            save(output/'label_costs.json', label_costs); save(output/'run.json', record)
            print(json.dumps(dict(event='label_complete', root=root['root_id'], completed=record['completed_roots'],
                seconds=perf_counter()-begun)), flush=True)
        save(output/'summary.json', summarize(roots, labels, choices, selection, new_models))
        record['costs']['input_counts'] = dict(input_work); record['seconds'] = perf_counter()-begun
        phase('complete'); save(output/'run.json', record); return record
    except Exception as error:
        record.update(status='failed', seconds=perf_counter()-begun,
            failure=dict(type=type(error).__name__, message=str(error), counts=getattr(error, 'counts', {}),
                label_seconds=getattr(error, 'elapsed_seconds', 0.)))
        if hasattr(error, 'record'):
            save(output/'failed_learning.json', error.record)
            record['costs']['failed_learning'] = error.record.get('costs', {})
            record['new_predictors_fitted'] = record['costs']['failed_learning'].get('ridge_predictors_fitted', 0)
        record['costs']['input_counts'] = dict(input_work); save(output/'run.json', record); raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
