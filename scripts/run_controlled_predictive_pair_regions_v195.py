"""SOURCE-learned joint applicability regions on fresh H3 boards."""
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
from acfqp.science import controlled_predictive_pair_regions_v195 as core
from acfqp.science import controlled_predictive_conditional_pairs_v194 as conditional
from scripts import run_controlled_predictive_nonlinear_relations_v192 as previous

save, utility, paired_effect = previous.save, previous.utility, previous.paired_effect
acquisition, coverage, relation = previous.acquisition, previous.coverage, previous.relation
LearnedDynamics, canonical_labels = previous.LearnedDynamics, previous.canonical_labels
PREVIOUS = ROOT/'reports/controlled_predictive_conditional_pairs_v194'
OUTPUT = ROOT/'reports/controlled_predictive_pair_regions_v195'
RUNTIME = ROOT/'reports/v195_runtime_tmp'
NEW_MODES = ('TREE32', 'RAW32')
PAIR_MODES = (*NEW_MODES, 'CONDITIONAL', 'PAIR98')
OLD_MODES = ('CONDITIONAL', 'PAIR98', 'NONLINEAR', 'RELATION', 'LINEAR', 'INTERACT', 'RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE')
MODEL_NAMES = (*NEW_MODES, *OLD_MODES)
MODELS = (*MODEL_NAMES, 'FALLBACK', 'ORACLE')
COMPARATORS = ('RAW32', *OLD_MODES, 'FALLBACK')
PRIMARY = ('RAW32', 'CONDITIONAL', 'LINEAR', 'NONLINEAR', 'OLD_SHARED')
EPSILON = 1e-12


def observable(root):
    return {key: root[key] for key in ('root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
        'immediate_rewards', 'fallback_action', 'action_map', 'layout_features', 'action_features',
        'relation_features', 'conditional_features', 'raw_afterstates')}


def source_diagnostics(roots, model, library):
    rows, work = [], Counter()
    for root in sorted(roots, key=lambda row: row['root_id']):
        decision = core.choose_action(model, observable(root), library, work)
        if model['mode'] == 'RAW32':
            for pair in decision['estimated_pairs'].values():
                del pair['forward']['neighbors']
                del pair['reverse']['neighbors']
        legal = [action for action in previous.exact.ACTIONS if action in root['legal_actions']]
        vectors = root['action_components']; values = {action: utility(vectors[action]) for action in legal}
        best = max(values.values()); oracle = next(action for action in legal if values[action] >= best-EPSILON)
        action = decision['canonical_action']; regret = best-values[action]
        rows.append(dict(root_id=root['root_id'], source_id=root['source_id'], decision=decision,
            action=action, components=list(vectors[action]), utility=values[action], oracle_action=oracle,
            oracle_components=list(vectors[oracle]), oracle_utility=best, regret=regret, positive_regret=regret > EPSILON))
        work.update(source_observable_root_preparations=1, source_complete_component_reads=3*len(legal),
            source_action_utility_evaluations=len(legal), source_selected_component_reads=3,
            source_oracle_component_reads=3, source_regret_subtractions=1,
            source_oracle_action_comparisons=legal.index(oracle)+1, source_diagnostic_root_records=1)
    n = len(rows)
    metrics = dict(roots=n, components=[math.fsum(row['components'][i] for row in rows)/n for i in range(3)],
        utility=math.fsum(row['utility'] for row in rows)/n,
        oracle_components=[math.fsum(row['oracle_components'][i] for row in rows)/n for i in range(3)],
        oracle_utility=math.fsum(row['oracle_utility'] for row in rows)/n,
        regret_mean=math.fsum(row['regret'] for row in rows)/n,
        positive_regret_roots=sum(row['positive_regret'] for row in rows),
        fallback_roots=sum(row['decision']['fallback'] for row in rows))
    work.update(source_summary_component_reads=6*n, source_summary_scalar_reads=3*n, source_summary_flag_reads=2*n)
    return dict(root_records=rows, metrics=metrics, projection_residuals=projection_summary(rows), work=dict(work))


def cohort_cases():
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    cases = []
    for replica in range(4):
        for index in range(24):
            seed = 1950200+24*replica+index; rng = random.Random(seed)
            board = [rng.randint(1, 10) for _ in range(16)]
            first, second = edges[index]; board[first] = board[second] = 1+index%10
            for cell in rng.sample([cell for cell in range(16) if cell not in (first, second)], index%3):
                board[cell] = 0
            cases.append(dict(split='TARGET', replica=replica, stratum=index, horizon=3, seed=seed,
                name=f'v195_target_r{replica:02d}_{index:02d}', board=board, vacancies=index%3))
    return cases


def freeze_choices(roots, models, libraries):
    choices = {name: [] for name in (*MODEL_NAMES, 'FALLBACK')}; work = Counter()
    for root in roots:
        seen = observable(root)
        for mode in MODEL_NAMES:
            if mode in NEW_MODES:
                decision = core.choose_action(models[mode], seen, libraries['FULL'])
            else:
                chooser = (conditional.choose_action if mode in ('CONDITIONAL', 'PAIR98')
                    else previous.core.choose_action if mode == 'NONLINEAR'
                    else previous.old_relation.choose_action if mode == 'RELATION'
                    else previous.old_dense.choose_action if mode in ('LINEAR', 'INTERACT')
                    else previous.shared.choose_action if mode in ('SHARED', 'OLD_SHARED')
                    else previous.exact.choose_action if mode == 'ONE' else previous.layout.choose_action)
                decision = chooser(models[mode], seen)
            work.update(decision['work']); work.update(decision.get('feature_work', {})); work['frozen_model_choices'] += 1
            choices[mode].append(dict(root_id=root['root_id'], mode=mode, canonical_action=decision['canonical_action'],
                actual_action=decision['actual_action'], fallback=decision['fallback'], decision=decision))
        action = root['fallback_action']; work['frozen_fallback_choices'] += 1
        choices['FALLBACK'].append(dict(root_id=root['root_id'], mode='FALLBACK', canonical_action=action,
            actual_action=root['action_map'][action], fallback=False,
            decision=dict(reason='observable_immediate_reward', work={'frozen_fallback_choices': 1})))
    return choices, dict(work)


def projection_summary(rows):
    pairs = [pair for row in rows for pair in row['decision']['estimated_pairs'].values()]
    residuals = [pair['projection_residual'] for pair in pairs]
    n = len(residuals)
    utilities = [(utility(pair['estimated_tail_delta']), utility(pair['projected_tail_delta'])) for pair in pairs]
    return dict(roots=len(rows), pairs=n,
        max_abs_components=[max((abs(vector[i]) for vector in residuals), default=0.) for i in range(3)],
        mean_abs_components=[math.fsum(abs(vector[i]) for vector in residuals)/n if n else 0. for i in range(3)],
        utility_sign_flips=sum(abs(raw) > EPSILON and abs(projected) > EPSILON and (raw > 0) != (projected > 0)
            for raw, projected in utilities))


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
            first, second = sorted((actual['action'], oracle['action']), key=previous.exact.ACTIONS.index)
            pair = chosen[mode][row['root_id']]['decision']['estimated_pairs'][first+'|'+second]
            estimate = pair['estimated_tail_delta'][2]*(1. if pair['actions'][0] == actual['action'] else -1.)
            if abs(estimate) <= EPSILON:
                missed.append(row['root_id'])
            elif (true_delta > 0) != (estimate > 0):
                wrong.append(row['root_id'])
        result[mode] = dict(eligible_roots=eligible, missed=len(missed), wrong_direction=len(wrong),
            missed_root_ids=missed, wrong_direction_root_ids=wrong)
    return result


def summarize(roots, labels, choices, selections, models, source):
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
        new = [dict(root_id=row['root_id'], models={'TREE32': row['models']['TREE32']}) for row in rows]
        return {'TREE32_MINUS_'+name: paired_effect(new,
            [dict(root_id=row['root_id'], models={'TREE32': row['models'][name]}) for row in rows], 'TREE32')
            for name in COMPARATORS}
    metrics, effects = aggregate(records), contrasts(records)
    replicas = [dict(replica=replica, roots=len(rows), models=aggregate(rows), comparisons=contrasts(rows))
        for replica in sorted({row['replica'] for row in records})
        for rows in [[row for row in records if row['replica'] == replica]]]
    source_modes = {}
    for mode in NEW_MODES:
        selection, model = selections[mode], models[mode]
        configuration = (dict(selected_depth=selection['selected_depth'], selected_min_leaf_roots=selection['selected_min_leaf_roots'])
            if mode == 'TREE32' else dict(selected_k=selection['selected_k']))
        source_modes[mode] = dict(**configuration, source_heldout_utility=selection['selected_utility'],
            feature_columns=model['constants']['columns'], actual=deepcopy(source[mode]['metrics']))
    headroom = metrics['ORACLE']['utility']-metrics['ONE']['utility']
    return dict(schema='acfqp.pair_regions.v195.summary', complete=True, roots=len(records),
        SOURCE=dict(roots=len(roots['SOURCE']), design_groups=len({row['source_id'] for row in roots['SOURCE']}), modes=source_modes),
        models=metrics, comparisons=effects, replicas=replicas, root_records=records,
        projection_residuals=dict(SOURCE={mode: projection_summary(source[mode]['root_records']) for mode in NEW_MODES},
            TARGET={mode: projection_summary(choices[mode]) for mode in PAIR_MODES}),
        success_diagnostics=success_diagnostics(records, chosen),
        oracle_minus_one=headroom, oracle_minus_tree=metrics['ORACLE']['utility']-metrics['TREE32']['utility'],
        headroom_closed_fraction=effects['TREE32_MINUS_ONE']['utility']/headroom if headroom > EPSILON else None,
        whole_cohort_positive_vs_primary=all(effects['TREE32_MINUS_'+name]['utility'] > EPSILON for name in PRIMARY),
        all_replicas_positive_vs_primary=all(row['comparisons']['TREE32_MINUS_'+name]['utility'] > EPSILON
            for row in replicas for name in PRIMARY), new_environment_samples=0, new_source_games=0,
        new_native_weight_updates=0, new_predictors_fitted=24, new_tree_fits=17, new_raw_configurations=7, new_parameter_solves=0)


def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_pair_regions_v195')
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
        if getattr(module, '__file__', None) and Path(module.__file__).suffix == '.py'
        and any(str(Path(module.__file__).resolve()).startswith(str(ROOT/folder)+'/') for folder in ('src', 'scripts'))}
    paths.update(ROOT/relative for relative in ('scripts/run_controlled_predictive_pair_regions_v195.py',
        'scripts/analyze_controlled_predictive_pair_regions_v195.py', 'specs/PAIR_REGIONS_V195.md',
        'tests/test_pair_regions_core_v195.py', 'tests/test_pair_regions_runner_v195.py',
        'tests/test_pair_regions_analysis_v195.py', 'reports/v195_runtime_tmp/run_checks.py', 'reports/v195_runtime_tmp/run_stage.py'))
    for path in sorted(paths):
        target = output/'source_code'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    save(output/'source_manifest.json', dict(files=[str(path.relative_to(ROOT)) for path in sorted(paths)]))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='acfqp.pair_regions.v195.run', status='preparing', phase_history=[], costs={},
        runtime=dict(python=sys.version.split()[0], executable=sys.executable), new_environment_samples=0,
        new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=0, new_tree_fits=0,
        new_raw_configurations=0, new_parameter_solves=0, shared_library_preparations=0,
        new_learning_attempts=0, new_boards_generated=0, new_reference_kernel_attempts=0,
        new_reference_kernels=0, new_teacher_plans=0, new_exact_label_roots=0, completed_roots=0,
        resource_cap_per_board=200000,
        inherited_cost_refs=[dict(path=str(PREVIOUS/'run.json'), fields=['costs', 'inherited_cost_refs']),
            dict(path=str(PREVIOUS/'analysis.json'), fields=['costs'])],
        test_refs=[str(RUNTIME/f'{kind}_checks.json') for kind in ('core', 'runner', 'analyzer')])
    inputs, input_work, label_work = [], Counter(), Counter()
    labels, native_labels, label_costs, source_actual = [], [], [], {}
    learning_in_progress = False
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
        stage = read(ROOT/'reports/v194_runtime_tmp/stage_checks.json', 'v194_stage_checks.json')
        prior = read(PREVIOUS/'run.json', 'v194_run.json')
        if not stage['valid'] or prior['status'] != 'complete':
            raise ValueError('settled V194 stage is incomplete')
        source = read(PREVIOUS/'roots.json', 'v194_roots.json')['SOURCE']
        old_pairs = read(PREVIOUS/'models.json', 'conditional_models.json')
        inherited = PREVIOUS/'inputs/inherited'
        nonlinear = read(inherited/'nonlinear_model.json', 'nonlinear_model.json')
        retained_relation = read(inherited/'relation_model.json', 'relation_model.json')
        expanded = read(inherited/'expanded_models.json', 'expanded_models.json')
        old = read(inherited/'baseline_models.json', 'baseline_models.json')
        rule = LearnedDynamics.from_payload(read(inherited/'learned_rule.json', 'learned_rule.json'))
        dense = read(inherited/'dense_models.json', 'dense_models.json')
        if len(source) != 143 or len({row['source_id'] for row in source}) != 36:
            raise ValueError('fixed SOURCE143/36 differs')
        phase('source_selection'); tick = perf_counter(); source_features = core.cache_roots(source)
        record['costs']['source_features'] = dict(seconds=perf_counter()-tick, counts=source_features)
        roots = dict(SOURCE=source, TARGET=[]); save(output/'roots.json', roots)
        tick = perf_counter(); record['new_learning_attempts'] += 1; learning_in_progress = True
        fitted = core.fit_models(source)
        models, selections, libraries = fitted['models'], fitted['selection'], fitted['libraries']
        counts = fitted['costs']; learning_in_progress = False
        record['new_predictors_fitted'] = counts['new_predictors_fitted']
        record['new_tree_fits'] = counts['tree_predictors_fitted']
        record['new_raw_configurations'] = counts['raw_predictor_configurations']
        record['shared_library_preparations'] = counts['shared_library_preparations']
        record['costs']['learning'] = dict(seconds=perf_counter()-tick, counts=counts)
        save(output/'models.json', models); save(output/'selection.json', selections); save(output/'libraries.json', libraries)
        for mode in NEW_MODES:
            tick = perf_counter(); source_actual[mode] = source_diagnostics(source, models[mode], libraries['FULL'])
            record['costs']['source_evaluation_'+mode] = dict(seconds=perf_counter()-tick, counts=source_actual[mode]['work'])
            save(output/'source_diagnostics.json', source_actual); save(output/'run.json', record)
        phase('models_frozen'); phase('target_roots'); tick = perf_counter()
        cases = cohort_cases(); save(output/'target_cases.json', cases)
        target, observation_work = acquisition.observe_roots(cases)
        feature_work = coverage.cache_roots(target); relation_work = relation.cache_roots(target)
        conditional_work = conditional.cache_roots(target); raw_work = core.cache_roots(target)
        record['new_boards_generated'] = len(cases)
        record['costs']['observations'] = dict(seconds=perf_counter()-tick, counts=observation_work,
            feature_counts=feature_work, relation_counts=relation_work, conditional_counts=conditional_work, raw_counts=raw_work)
        roots['TARGET'] = target; save(output/'roots.json', roots)
        all_models = dict(expanded, **dense, **models, **old_pairs, NONLINEAR=nonlinear, RELATION=retained_relation,
            OLD_SHARED=old['SHARED'], ONE=old['ONE'])
        tick = perf_counter(); choices, choice_work = freeze_choices(target, all_models, libraries)
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
        save(output/'summary.json', summarize(roots, labels, choices, selections, models, source_actual))
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
            record['new_raw_configurations'] = paid.get('raw_predictor_configurations', 0)
            record['shared_library_preparations'] = paid.get('shared_library_preparations', 0)
        record['costs']['input_counts'] = dict(input_work); save(output/'run.json', record); raise

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
