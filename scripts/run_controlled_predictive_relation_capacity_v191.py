"""Retained-root capacity of the frozen V190 shared 98-feature scorer."""
import argparse
from collections import Counter
from copy import deepcopy
import importlib
import json
from math import fsum
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import controlled_predictive_relation_capacity_v191 as core
from acfqp.science import controlled_predictive_merge_relations_v190 as relation
from acfqp.science import controlled_predictive_merge_relation_learning_v190 as learning

PREVIOUS = ROOT/'reports/controlled_predictive_merge_relations_v190'
OUTPUT = ROOT/'reports/controlled_predictive_relation_capacity_v191'
RUNTIME = ROOT/'reports/v191_runtime_tmp'
SCOPES = ('SOURCE', 'TARGET', 'JOINT')
SCHEMA = 'acfqp.relation_capacity.v191'
ACTIONS, EPSILON = learning.ACTIONS, learning.EPSILON


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def utility(vector):
    return vector[0]-vector[1]+vector[2]


def source_diagnostics(roots, model):
    """Run only the retained full R/F/S chooser on label-free SOURCE views."""
    rows, work = [], Counter()
    keys = ('root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
            'immediate_rewards', 'fallback_action', 'action_map', 'layout_features',
            'action_features', 'relation_features')
    for root in sorted(roots, key=lambda row: row['root_id']):
        observable = {key: root[key] for key in keys}
        decision = learning.choose_action(model, observable, work)
        legal = [action for action in ACTIONS if action in root['legal_actions']]
        vectors = root['action_components']
        values = {action: utility(vectors[action]) for action in legal}
        best = max(values.values())
        oracle = next(action for action in legal if values[action] >= best-EPSILON)
        action = decision['canonical_action']
        vector = list(vectors[action]); regret = best-values[action]
        rows.append(dict(root_id=root['root_id'], source_id=root['source_id'], decision=decision,
            action=action, components=vector, utility=values[action], oracle_action=oracle,
            oracle_components=list(vectors[oracle]), oracle_utility=best, regret=regret,
            positive_regret=regret > EPSILON))
        work.update(source_observable_root_preparations=1, source_complete_component_reads=3*len(legal),
            source_action_utility_evaluations=len(legal), source_selected_component_reads=3,
            source_oracle_component_reads=3, source_regret_subtractions=1,
            source_oracle_action_comparisons=legal.index(oracle)+1, source_diagnostic_root_records=1)
    n = len(rows)
    metrics = dict(roots=n, components=[fsum(row['components'][i] for row in rows)/n for i in range(3)],
        utility=fsum(row['utility'] for row in rows)/n,
        oracle_components=[fsum(row['oracle_components'][i] for row in rows)/n for i in range(3)],
        oracle_utility=fsum(row['oracle_utility'] for row in rows)/n,
        regret_mean=fsum(row['regret'] for row in rows)/n,
        positive_regret_roots=sum(row['positive_regret'] for row in rows),
        fallback_roots=sum(row['decision']['fallback'] for row in rows))
    work.update(source_summary_component_reads=6*n, source_summary_scalar_reads=3*n,
                source_summary_flag_reads=2*n)
    return dict(root_records=rows, metrics=metrics, work=dict(work))


def retained_target_metrics(roots, choices, summary):
    """Bind retained decisions, without re-running any TARGET chooser."""
    selected = {row['root_id']: row for row in choices['RELATION']}
    retained = {row['root_id']: row for row in summary['root_records']}
    ids = {root['root_id'] for root in roots}
    if (len(ids) != len(roots) or len(selected) != len(choices['RELATION'])
            or len(retained) != len(summary['root_records']) or ids != set(selected) or ids != set(retained)):
        raise ValueError('retained TARGET roots and RELATION choices must bind once each')
    for root in roots:
        action = selected[root['root_id']]['canonical_action']
        if action not in root['legal_actions'] or action != retained[root['root_id']]['models']['RELATION']['action']:
            raise ValueError('retained TARGET choice differs from its complete V190 summary')
    n, chosen, oracle = len(roots), summary['models']['RELATION'], summary['models']['ORACLE']
    result = dict(roots=n, components=deepcopy(chosen['components']), utility=chosen['utility'],
        oracle_components=deepcopy(oracle['components']), oracle_utility=oracle['utility'],
        regret_mean=oracle['utility']-chosen['utility'], positive_regret_roots=chosen['positive_regret_roots'],
        fallback_roots=chosen['fallback_roots'])
    return result, dict(retained_target_root_bindings=n, retained_target_choice_bindings=n,
                        retained_target_summary_root_bindings=n, retained_target_aggregate_reads=12)


def summarize(problems, capacities, source, target):
    learned = {'SOURCE': source['metrics'], 'TARGET': target}
    total = source['metrics']['roots']+target['roots']
    joint = dict(roots=total)
    for key in ('components', 'oracle_components'):
        joint[key] = [fsum(row['roots']*row[key][i] for row in learned.values())/total for i in range(3)]
    for key in ('utility', 'oracle_utility', 'regret_mean'):
        joint[key] = fsum(row['roots']*row[key] for row in learned.values())/total
    for key in ('positive_regret_roots', 'fallback_roots'):
        joint[key] = sum(row[key] for row in learned.values())
    learned['JOINT'] = joint
    scopes = {}
    for scope in SCOPES:
        capacity = capacities[scope]
        weak, witness = capacity.get('weak_witness'), capacity.get('witness')
        weak_actual = weak is not None and weak['evaluation']['all_optimal']
        if capacity['status'] == 'strict_feasible':
            attainability = 'attained_by_retained_strict_witness'
        elif capacity['status'] == 'weak_infeasible':
            attainability = 'impossible_on_retained_roots'
        else:
            attainability = 'attained_by_retained_weak_witness' if weak_actual else 'unknown'
        scopes[scope] = dict(roots=len(problems[scope]['roots']), status=capacity['status'],
            upper_bound=capacity['upper_bound'], strict_witness_margin=None if witness is None else witness['margin'],
            solver_nodes=len(capacity['nodes']), lp_solves=capacity['costs'].get('lp_solves', 0),
            native_lp_status_counts=dict(Counter(str(node['native_lp']['status']) for node in capacity['nodes'])),
            strict_witness_actual_all_optimal=None if witness is None else witness['evaluation']['all_optimal'],
            strict_witness_rational_all_optimal=None if witness is None else witness['evaluation']['rational_all_optimal'],
            actual_tie_policy_attainability=attainability,
            weak_witness_all_optimal=None if weak is None else weak['evaluation']['all_optimal'], learned=learned[scope])
    return dict(schema=SCHEMA+'.summary', complete=all(capacities[scope]['status'] in
        ('strict_feasible', 'weak_infeasible', 'no_positive_margin') for scope in SCOPES), scopes=scopes,
        new_environment_samples=0, new_fits=0, new_labels=0, new_capacity_scopes=len(capacities),
        work=dict(summary_scope_records=len(SCOPES), summary_learned_weighted_component_products=12,
                  summary_learned_weighted_scalar_products=6, summary_learned_count_reads=4))


def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_relation_capacity_v191')
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
        if getattr(module, '__file__', None) and Path(module.__file__).suffix == '.py'
        and any(str(Path(module.__file__).resolve()).startswith(str(ROOT/folder)+'/')
            for folder in ('src', 'scripts'))}
    paths.update(ROOT/relative for relative in (
        'scripts/run_controlled_predictive_relation_capacity_v191.py',
        'scripts/analyze_controlled_predictive_relation_capacity_v191.py',
        'specs/RELATION_CAPACITY_V191.md', 'tests/test_relation_capacity_core_v191.py',
        'tests/test_relation_capacity_runner_v191.py', 'tests/test_relation_capacity_analysis_v191.py',
        'reports/v191_runtime_tmp/run_checks.py', 'reports/v191_runtime_tmp/run_stage.py'))
    for path in sorted(paths):
        target = output/'source_code'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    save(output/'source_manifest.json', dict(files=[str(path.relative_to(ROOT)) for path in sorted(paths)]))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema=SCHEMA+'.run', status='preparing', phase_history=[], costs={},
        runtime=dict(python=sys.version.split()[0], executable=sys.executable),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=0,
        new_reference_kernels=0, new_exact_label_roots=0, new_boards_generated=0,
        new_capacity_attempts=0, new_capacity_scopes=0, new_lp_solves=0,
        inherited_cost_refs=[dict(path=str(PREVIOUS/'run.json'), fields=['costs', 'inherited_cost_refs']),
            dict(path=str(PREVIOUS/'analysis.json'), fields=['costs']),
            dict(path=str(PREVIOUS/'metadata_binding_amendment/result.json'), fields=['costs'])],
        test_refs=[str(RUNTIME/f'{kind}_checks.json') for kind in ('core', 'runner', 'analyzer')])
    inputs, input_work, capacities, active_scope = [], Counter(), {}, None
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
        stage = read(ROOT/'reports/v190_runtime_tmp/stage_checks.json', 'v190_stage_checks.json')
        amendment = read(PREVIOUS/'metadata_binding_amendment/result.json', 'v190_metadata_amendment.json')
        prior = read(PREVIOUS/'run.json', 'v190_run.json')
        if (not amendment['corrected_valid'] or not stage['frozen_source_same']
                or not stage['frozen_inputs_same'] or prior['status'] != 'complete'):
            raise ValueError('settled amended V190 stage is incomplete')
        retained_roots = read(PREVIOUS/'roots.json', 'v190_roots.json')
        labels = read(PREVIOUS/'labels.json', 'v190_labels.json')
        model = read(PREVIOUS/'model.json', 'v190_model.json')
        choices = read(PREVIOUS/'choices.json', 'v190_choices.json')
        inherited_summary = read(PREVIOUS/'summary.json', 'v190_summary.json')
        source, target = deepcopy(retained_roots['SOURCE']), retained_roots['TARGET']
        if (len(source) != 143 or len({row['source_id'] for row in source}) != 36 or len(target) != 96
                or len(labels) != 96):
            raise ValueError('fixed SOURCE143/36 and retained TARGET96 differ')
        tick = perf_counter(); cache_work = relation.cache_roots(source)
        record['costs']['source_cache'] = dict(seconds=perf_counter()-tick, counts=cache_work)
        roots = dict(SOURCE=source, TARGET=target); save(output/'roots.json', roots)
        source_labels = [dict(root_id=root['root_id'], action_components=deepcopy(root['action_components'])) for root in source]
        scope_inputs = dict(SOURCE=(source, source_labels), TARGET=(target, labels),
                            JOINT=(source+target, source_labels+labels))
        problems = {}
        for scope in SCOPES:
            tick = perf_counter(); problems[scope] = core.build_problem(*scope_inputs[scope])
            record['costs']['problem_'+scope] = dict(seconds=perf_counter()-tick, counts=problems[scope]['work'])
        save(output/'problems.json', problems)
        tick = perf_counter(); learned_source = source_diagnostics(source, model)
        record['costs']['source_evaluation'] = dict(seconds=perf_counter()-tick, counts=learned_source['work'])
        save(output/'learned_source_diagnostics.json', learned_source)
        tick = perf_counter(); learned_target, binding_work = retained_target_metrics(target, choices, inherited_summary)
        record['costs']['retained_target_bindings'] = dict(seconds=perf_counter()-tick, counts=binding_work)
        phase('problems_frozen')
        for scope in SCOPES:
            active_scope = scope; phase('capacity_'+scope); tick = perf_counter()
            record['new_capacity_attempts'] += 1
            capacity = core.solve_capacity(problems[scope]); capacities[scope] = capacity
            record['new_capacity_scopes'] += 1; record['new_lp_solves'] += capacity['costs'].get('lp_solves', 0)
            record['costs']['capacity_'+scope] = dict(seconds=perf_counter()-tick, counts=capacity['costs'])
            save(output/'capacities.json', capacities); save(output/'run.json', record)
        active_scope = None; tick = perf_counter(); summary = summarize(problems, capacities, learned_source, learned_target)
        record['costs']['summary'] = dict(seconds=perf_counter()-tick, counts=summary['work'])
        save(output/'summary.json', summary)
        record['costs']['input_counts'] = dict(input_work); record['seconds'] = perf_counter()-begun
        phase('complete'); save(output/'run.json', record); return record
    except Exception as error:
        record.update(status='failed', seconds=perf_counter()-begun,
            failure=dict(type=type(error).__name__, message=str(error), capacity_scope=active_scope))
        if hasattr(error, 'record'):
            save(output/'failed_capacity.json', error.record)
            paid = error.record.get('costs', {})
            record['costs']['failed_capacity'] = dict(scope=active_scope, counts=paid)
            record['new_lp_solves'] += paid.get('lp_solves', 0)
        record['costs']['input_counts'] = dict(input_work); save(output/'run.json', record); raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
