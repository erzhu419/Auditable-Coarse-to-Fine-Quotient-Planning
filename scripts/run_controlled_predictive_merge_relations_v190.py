"""SOURCE-trained shared merge relations on a frozen fresh H3 cohort."""
import argparse
from collections import Counter
from copy import deepcopy
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
from acfqp.science import controlled_predictive_merge_relations_v190 as core
from acfqp.science import controlled_predictive_merge_relation_learning_v190 as learning
from acfqp.science import controlled_predictive_mechanism_interactions_v188 as old_dense
from acfqp.science import controlled_predictive_source_coverage_v185 as coverage
from acfqp.science import controlled_predictive_fresh_h3_confirmation_v184 as acquisition
from acfqp.science import controlled_predictive_shared_consequences_v179 as shared
from acfqp.science import controlled_predictive_rank_layout_consequences_v182 as layout
from acfqp.science import controlled_predictive_exact_h3_v177 as exact
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from scripts.run_controlled_predictive_exact_h3_v177 import canonical_labels
from scripts.run_controlled_predictive_source_coverage_v185 import paired_effect

PREVIOUS = ROOT/'reports/controlled_predictive_feature_conflicts_v189'
LEARNED = ROOT/'reports/controlled_predictive_mechanism_interactions_v188'
OUTPUT = ROOT/'reports/controlled_predictive_merge_relations_v190'
RUNTIME = ROOT/'reports/v190_runtime_tmp'
CONTROLS = ('LINEAR','INTERACT','RIDGE','LAYOUT','SHARED','OLD_SHARED','ONE')
MODEL_NAMES = ('RELATION',*CONTROLS)
MODELS = (*MODEL_NAMES,'FALLBACK','ORACLE')
EPSILON = 1e-12


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def utility(vector):
    return vector[0]-vector[1]+vector[2]


def same_features(first,second):
    return max(abs(a-b) for a,b in zip(first,second,strict=True)) <= EPSILON


def development_diagnostics(roots,labels,previous,certificate):
    """Check known counterexamples; no fitting or new capacity search."""
    work=Counter(); labeled={row['root_id']:row for row in labels}
    old_alias={row['root_id']:row for row in previous['alias']['root_records']}
    roots_index={row['root_id']:row for row in roots}
    rows=[]
    for root in roots:
        groups=[]
        for action in exact.ACTIONS:
            if action not in root['legal_actions']:
                continue
            feature=root['relation_features'][action]
            group=None
            for candidate in groups:
                work.update(development_vector_comparisons=1,development_feature_values_read=196)
                if same_features(feature,root['relation_features'][candidate[0]]):
                    group=candidate; break
            if group is None:
                group=[]; groups.append(group)
            group.append(action)
        representatives=[]
        for group in groups:
            best=group[0]
            for action in group[1:]:
                work['development_alias_reward_comparisons']+=1
                if root['immediate_rewards'][action] > root['immediate_rewards'][best]+EPSILON:
                    best=action
            representatives.append(best)
        vectors=labeled[root['root_id']]['action_components']
        actual_best=max(utility(vectors[action]) for action in root['legal_actions'])
        accessible=max(utility(vectors[action]) for action in representatives)
        floor=actual_best-accessible
        before=old_alias[root['root_id']]['within_root_regret']
        rows.append(dict(root_id=root['root_id'],old_floor=before,new_floor=floor,
            old_loss=before>EPSILON,new_loss=floor>EPSILON,representatives=representatives,
            groups=groups,oracle_utility=actual_best,accessible_utility=accessible))
        work.update(development_roots=1,development_complete_vector_reads=len(vectors)+len(representatives),
            development_component_reads=3*(len(vectors)+len(representatives)),
            development_utility_evaluations=len(vectors)+len(representatives))
    occurrences={}
    for item in previous['problem']['roots']:
        for group in item['classes']:
            occurrences.setdefault(group['vertex_id'],[]).append((item['root_id'],group['representative']))
    cycle_vertices=[]
    for vertex,items in sorted(occurrences.items()):
        first=roots_index[items[0][0]]['relation_features'][items[0][1]]
        equal=True
        for root_id,action in items[1:]:
            work.update(development_vertex_vector_comparisons=1,development_feature_values_read=196)
            equal=same_features(first,roots_index[root_id]['relation_features'][action]) and equal
        cycle_vertices.append(dict(vertex_id=vertex,occurrences=len(items),still_equal=equal))
    certified_occurrences={}
    for node in certificate['dual_explanations']:
        for edge in node['edges']:
            for role in ('best','bad'):
                endpoint=edge[role]
                certified_occurrences.setdefault(endpoint['vertex_id'],[]).append((edge['root_id'],endpoint['action']))
    selected=[]
    for vertex,items in sorted(certified_occurrences.items()):
        first=roots_index[items[0][0]]['relation_features'][items[0][1]]
        equal=True
        for root_id,action in items[1:]:
            work.update(development_certificate_vector_comparisons=1,development_feature_values_read=196)
            equal=same_features(first,roots_index[root_id]['relation_features'][action]) and equal
        selected.append(dict(vertex_id=vertex,occurrences=[list(item) for item in items],still_equal=equal))
    metrics=dict(roots=len(rows),old_loss_roots=sum(row['old_loss'] for row in rows),
        new_loss_roots=sum(row['new_loss'] for row in rows),
        old_loss_roots_now_accessible=sum(row['old_loss'] and not row['new_loss'] for row in rows),
        old_floor_mean=math.fsum(row['old_floor'] for row in rows)/len(rows),
        new_floor_mean=math.fsum(row['new_floor'] for row in rows)/len(rows),
        old_cycle_vertices=len(selected),old_cycle_vertices_split=sum(not row['still_equal'] for row in selected))
    return dict(root_records=rows,vertex_records=cycle_vertices,certified_vertex_records=selected,metrics=metrics,work=dict(work))


def cohort_cases():
    edges=[(4*r+c,4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c,4*(r+1)+c) for r in range(3) for c in range(4)]
    result=[]
    for replica in range(4):
        for index in range(24):
            seed=1900200+24*replica+index; rng=random.Random(seed)
            board=[rng.randint(1,10) for _ in range(16)]
            first,second=edges[index]; board[first]=board[second]=1+index%10
            for cell in rng.sample([cell for cell in range(16) if cell not in (first,second)],index%3):
                board[cell]=0
            result.append(dict(split='TARGET',replica=replica,stratum=index,horizon=3,seed=seed,
                name=f'v190_target_r{replica:02d}_{index:02d}',board=board,vacancies=index%3))
    return result


def freeze_choices(roots,models):
    result={name:[] for name in (*MODEL_NAMES,'FALLBACK')}; work=Counter()
    for root in roots:
        observable={key:root[key] for key in ('root_id','source_id','life','canonical_board',
            'legal_actions','immediate_rewards','fallback_action','action_map','layout_features','action_features','relation_features')}
        for mode in MODEL_NAMES:
            chooser=(learning.choose_action if mode=='RELATION' else old_dense.choose_action if mode in ('LINEAR','INTERACT')
                else shared.choose_action if mode in ('SHARED','OLD_SHARED') else exact.choose_action if mode=='ONE' else layout.choose_action)
            choice=chooser(models[mode],observable)
            work.update(choice['work']); work.update(choice.get('feature_work',{})); work['frozen_model_choices']+=1
            result[mode].append(dict(root_id=root['root_id'],mode=mode,canonical_action=choice['canonical_action'],
                actual_action=choice['actual_action'],fallback=choice['fallback'],decision=choice))
        action=root['fallback_action']; work['frozen_fallback_choices']+=1
        result['FALLBACK'].append(dict(root_id=root['root_id'],mode='FALLBACK',canonical_action=action,
            actual_action=root['action_map'][action],fallback=False,
            decision=dict(reason='observable_immediate_reward',work={'frozen_fallback_choices':1})))
    return result,dict(work)


def summarize(roots, labels, choices, selection, model, development):
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
        ranked = [dict(root_id=row['root_id'], models={'RELATION': row['models']['RELATION']}) for row in rows]
        return {'RELATION_MINUS_'+name: paired_effect(ranked,
            [dict(root_id=row['root_id'], models={'RELATION': row['models'][name]}) for row in rows], 'RELATION')
            for name in CONTROLS}

    metrics, effects = aggregate(records), contrasts(records)
    replicas = [dict(replica=replica, roots=len(rows), models=aggregate(rows), comparisons=contrasts(rows))
        for replica in sorted({row['replica'] for row in records})
        for rows in [[row for row in records if row['replica'] == replica]]]
    headroom = metrics['ORACLE']['utility']-metrics['ONE']['utility']
    return dict(schema='acfqp.merge_relations.v190.summary', complete=True, roots=len(records),
        SOURCE=dict(roots=len(roots['SOURCE']), design_groups=len({row['source_id'] for row in roots['SOURCE']}),
            selected_lambda=selection['selected_lambda'], source_heldout_utility=selection['selected_utility'],
            source_selection=[dict(lambda_value=row['lambda_value'], utility=row['utility']) for row in selection['candidates']],
            columns=model['constants']['columns'], source_rank=model['rank'], source_root_mean_loss=model['root_mean_loss']),
        development=development['metrics'],
        models=metrics, comparisons=effects, replicas=replicas, root_records=records,
        oracle_minus_one=headroom, oracle_minus_relation=metrics['ORACLE']['utility']-metrics['RELATION']['utility'],
        headroom_closed_fraction=effects['RELATION_MINUS_ONE']['utility']/headroom if headroom > EPSILON else None,
        whole_cohort_positive_vs_linear_ridge_old_shared=all(effects['RELATION_MINUS_'+name]['utility'] > EPSILON
            for name in ('LINEAR', 'RIDGE', 'OLD_SHARED')),
        all_replicas_positive_vs_linear_ridge_old_shared=all(row['comparisons']['RELATION_MINUS_'+name]['utility'] > EPSILON
            for row in replicas for name in ('LINEAR', 'RIDGE', 'OLD_SHARED')),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=13)



def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_merge_relations_v190')
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
        if getattr(module, '__file__', None) and Path(module.__file__).suffix == '.py'
        and any(str(Path(module.__file__).resolve()).startswith(str(ROOT/folder)+'/') for folder in ('src', 'scripts'))}
    paths.update(ROOT/relative for relative in (
        'scripts/run_controlled_predictive_merge_relations_v190.py',
        'scripts/analyze_controlled_predictive_merge_relations_v190.py',
        'specs/MERGE_RELATIONS_V190.md', 'tests/test_merge_relations_core_v190.py',
        'tests/test_merge_relations_runner_v190.py', 'tests/test_merge_relations_analysis_v190.py',
        'tests/test_merge_relation_learning_v190.py', 'reports/v190_runtime_tmp/run_checks.py', 'reports/v190_runtime_tmp/run_stage.py'))
    for path in sorted(paths):
        target = output/'source_code'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    save(output/'source_manifest.json', dict(files=[str(path.relative_to(ROOT)) for path in sorted(paths)]))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='acfqp.merge_relations.v190.run', status='preparing', phase_history=[], costs={},
        runtime=dict(python=sys.version.split()[0], executable=sys.executable),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=0,
        new_learning_attempts=0, new_boards_generated=0, new_reference_kernel_attempts=0,
        new_reference_kernels=0, new_teacher_plans=0, new_exact_label_roots=0, completed_roots=0,
        resource_cap_per_board=200000,
        inherited_cost_refs=[dict(path=str(PREVIOUS/'run.json'), fields=['costs', 'inherited_cost_refs']),
            dict(path=str(PREVIOUS/'analysis.json'), fields=['costs']),
            dict(path=str(LEARNED/'run.json'), fields=['costs', 'inherited_cost_refs'])],
        test_refs=[str(RUNTIME/f'{kind}_checks.json') for kind in ('core', 'learning', 'runner', 'analyzer')])
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
        stage = read(ROOT/'reports/v189_runtime_tmp/stage_checks.json', 'v189_stage_checks.json')
        prior = read(PREVIOUS/'run.json', 'v189_run.json')
        if not stage['valid'] or prior['status'] != 'complete':
            raise ValueError('settled V189 stage is incomplete')
        old_diagnostics = read(PREVIOUS/'diagnostics.json', 'v189_diagnostics.json')
        old_summary = read(PREVIOUS/'summary.json', 'v189_summary.json')
        inherited_roots = read(LEARNED/'roots.json', 'v188_roots.json')
        inherited_labels = read(LEARNED/'labels.json', 'v188_labels.json')
        expanded = read(LEARNED/'inputs/inherited/expanded_models.json', 'expanded_models.json')
        old = read(LEARNED/'inputs/inherited/baseline_models.json', 'baseline_models.json')
        rule = LearnedDynamics.from_payload(read(LEARNED/'inputs/inherited/learned_rule.json', 'learned_rule.json'))
        dense = read(LEARNED/'models.json', 'v188_models.json')
        source = inherited_roots['SOURCE']
        if len(source) != 143 or len({row['source_id'] for row in source}) != 36 or len(inherited_roots['TARGET']) != 96:
            raise ValueError('fixed SOURCE143/36 and development TARGET96 differ')
        phase('development_diagnostics'); tick = perf_counter()
        development_roots = deepcopy(inherited_roots['TARGET'])
        development_features = core.cache_roots(development_roots)
        development = development_diagnostics(development_roots,inherited_labels,old_diagnostics,old_summary)
        record['costs']['development'] = dict(seconds=perf_counter()-tick, feature_counts=development_features, counts=development['work'])
        save(output/'development.json', development)
        save(output/'source_labels.json', source)
        roots = dict(SOURCE=source, TARGET=[]); save(output/'roots.json', roots)
        phase('source_selection'); tick = perf_counter(); record['new_learning_attempts'] += 1
        fitted = learning.fit_model(source)
        new_model, selection = fitted['model'], fitted['selection']
        record['new_predictors_fitted'] = fitted['costs']['ridge_predictors_fitted']
        record['costs']['learning'] = dict(seconds=perf_counter()-tick, counts=fitted['costs'])
        save(output/'selection.json', selection); save(output/'model.json', new_model)
        phase('models_frozen'); phase('target_roots'); tick = perf_counter()
        cases = cohort_cases(); save(output/'target_cases.json', cases)
        target, observation_work = acquisition.observe_roots(cases)
        feature_work = coverage.cache_roots(target); relation_work = core.cache_roots(target)
        record['new_boards_generated'] = len(cases)
        record['costs']['observations'] = dict(seconds=perf_counter()-tick, counts=observation_work, feature_counts=feature_work, relation_counts=relation_work)
        roots['TARGET'] = target; save(output/'roots.json', roots)
        models = dict(expanded, **dense, RELATION=new_model, OLD_SHARED=old['SHARED'], ONE=old['ONE'])
        tick = perf_counter(); choices, choice_work = freeze_choices(target, models)
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
        save(output/'summary.json', summarize(roots, labels, choices, selection, new_model, development))
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
