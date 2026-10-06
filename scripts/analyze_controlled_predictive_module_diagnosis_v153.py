"""Audit four paired module/continuation interventions on frozen roots."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import analyze_controlled_predictive_policy_modules_v151 as prior

LIVES,QUERIES=prior.LIVES,prior.QUERIES
SOURCES=('H2','LEARN8');MODES=('H_H2','M_H2','H_GATE','M_GATE')
BASE,SUFFIXES,MAX_STEPS,WORKERS=153*100000000,16,2000,4
METRICS=('delta_h2','delta_gate','continuation_shift','error_h2','error_gate',
    'policy_gain_h2','policy_gain_gate','mse_excess_h2','mse_excess_gate')
mean,close,add_checks,read=prior.mean,prior.close,prior.add_checks,prior.read


def expected_settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,source_methods=list(SOURCES),modes=list(MODES),
        checkpoint=4,duration=8,source_replicas=[0,4,8,12],roots_per_source_cell=4,roots=64,suffixes=SUFFIXES,
        physical_branches=4096,max_steps=MAX_STEPS,p_four=.1,workers=WORKERS,version_base=BASE,
        root_selection='replica=4*slot; boundary index=floor((2*slot+1)*boundary_count/8); slot=0..3',
        seeds='BASE+20000000+life*1000000+query_index*100000+source_index*10000+slot*100+suffix; shared across modes',
        continuation='H_H2: own forever; M_H2: other8 then own; H_GATE: own1 then gate; M_GATE: other8 then gate',
        gate='unchanged frozen cp4 LEARN8; fresh gate at prefix end; branch absolute step; own query for each teacher',
        horizon='2000 transitions from each root for all modes; no initial spawns; winning swipe spawns',
        prediction='all root components, utility advantages and strict-positive decisions frozen before sampling',
        new_training_updates=0,primary='equal four roots within history then equal four histories; separate query/source',
        estimands=['delta_h2','delta_gate','continuation_shift','error_h2','error_gate','mse_excess_h2','mse_excess_gate','policy_gain_h2','policy_gain_gate'],
        intervals='pointwise conditional seed CI: mean +/-1.96*sqrt(sum_root(weight_root^2*sample_variance(metric_suffix)/16)); fixed histories and roots',
        accepted_subset='equal accepted roots within history then equal four histories; empty-history subset incomplete',
        blocks=[[0,3],[4,7],[8,11],[12,15]],
        mse='mse_excess=p^2-2*p*delta; plug-in squared error of root mean includes Monte Carlo variance',
        incomplete='retain cutoff branches and all costs; incomplete root/comparison excluded from complete-cohort claims; no replacements',
        frozen_policy='no fitting, checkpoint selection, extra favorable suffixes, or gate changes')


def branch_seed(root,suffix):
    return BASE+20000000+root['life']*1000000+list(QUERIES).index(root['query'])*100000+SOURCES.index(root['source_method'])*10000+root['slot']*100+suffix


def moments(values):
    complete=bool(values) and all(value is not None for value in values);average=mean(values)
    variance=sum((value-average)**2 for value in values)/(len(values)-1) if complete and len(values)>1 else (0. if complete else None)
    return dict(n=len(values),complete=complete,mean=average,sample_variance=variance,
        mean_variance=variance/len(values) if complete else None)


def root_diagnostics(root,branches):
    prediction=root['prediction']['advantage'];accept=root['prediction']['accept'];samples=[]
    for suffix in range(SUFFIXES):
        rows=branches.get(suffix,{})
        usable=lambda names:all(mode in rows and rows[mode]['valid'] and rows[mode]['result']['status'] in ('WON','LOST') for mode in names)
        delta_h2=(rows['M_H2']['result']['utility']-rows['H_H2']['result']['utility']) if usable(('M_H2','H_H2')) else None
        delta_gate=(rows['M_GATE']['result']['utility']-rows['H_GATE']['result']['utility']) if usable(('M_GATE','H_GATE')) else None
        samples.append(dict(delta_h2=delta_h2,delta_gate=delta_gate,continuation_shift=None if delta_h2 is None or delta_gate is None else delta_gate-delta_h2,
            error_h2=None if delta_h2 is None else prediction-delta_h2,error_gate=None if delta_gate is None else prediction-delta_gate,
            policy_gain_h2=delta_h2 if accept else 0.,policy_gain_gate=delta_gate if accept else 0.,
            mse_excess_h2=None if delta_h2 is None else prediction**2-2*prediction*delta_h2,
            mse_excess_gate=None if delta_gate is None else prediction**2-2*prediction*delta_gate))
    summaries={key:moments([row[key] for row in samples]) for key in METRICS}
    plug_in={}
    for condition in ('h2','gate'):
        value=summaries[f'delta_{condition}']['mean']
        plug_in[condition]=dict(prediction_mse=None if value is None else (prediction-value)**2,
            zero_mse=None if value is None else value**2,mc_mean_variance=summaries[f'delta_{condition}']['mean_variance'])
    return dict(root_id=root['root_id'],life=root['life'],query=root['query'],source_method=root['source_method'],slot=root['slot'],
        prediction=prediction,accept=accept,complete=all(row['complete'] for row in summaries.values()),
        metrics=summaries,plug_in_mse=plug_in,blocks=[{key:moments([r[key] for r in samples[start:start+4]])
            for key in METRICS} for start in range(0,16,4)])


def history_summary(rows,block=None):
    stats=[row['metrics'] if block is None else row['blocks'][block] for row in rows]
    metrics={}
    for name in METRICS:
        complete=bool(stats) and all(row[name]['complete'] for row in stats);average=mean(row[name]['mean'] for row in stats)
        variance=sum(row[name]['mean_variance'] for row in stats)/len(stats)**2 if complete else None
        se=math.sqrt(variance) if complete else None
        metrics[name]=dict(complete=complete,mean=average,conditional_suffix_se=se,
            conditional_suffix_ci95=None if se is None else [average-1.96*se,average+1.96*se])
    return dict(roots=len(rows),accepted_roots=sum(r['accept'] for r in rows),complete=bool(stats) and all(
        stat[name]['complete'] for stat in stats for name in METRICS),metrics=metrics)


def combine_histories(cells):
    metrics={}
    for name in METRICS:
        average=mean(c['metrics'][name]['mean'] for c in cells)
        complete=all(c['metrics'][name]['complete'] for c in cells)
        se=math.sqrt(sum(c['metrics'][name]['conditional_suffix_se']**2 for c in cells)/len(LIVES)**2) if complete else None
        metrics[name]=dict(complete=complete,mean=average,conditional_suffix_se=se,
            conditional_suffix_ci95=None if se is None else [average-1.96*se,average+1.96*se],
            positive_histories=sum(c['metrics'][name]['mean'] is not None and c['metrics'][name]['mean']>0 for c in cells))
    return metrics


def aggregate(rows,accepted_only=False):
    output={}
    for source in SOURCES:
        output[source]={}
        for query in QUERIES:
            selected=[r for r in rows if r['source_method']==source and r['query']==query and (not accepted_only or r['accept'])]
            cells=[dict(life=life,**history_summary([r for r in selected if r['life']==life])) for life in LIVES]
            metrics=combine_histories(cells)
            blocks=[]
            for block in range(4):
                histories=[dict(life=life,**history_summary([r for r in selected if r['life']==life],block)) for life in LIVES]
                blocks.append(dict(suffix_start=block*4,suffix_end=block*4+3,complete=all(h['complete'] for h in histories),
                    lifecycles=histories,metrics=combine_histories(histories)))
            plug_in={condition:{metric:mean(mean(r['plug_in_mse'][condition][metric] for r in selected if r['life']==life) for life in LIVES)
                for metric in ('prediction_mse','zero_mse','mc_mean_variance')} for condition in ('h2','gate')}
            output[source][query]=dict(roots=len(selected),accepted_roots=sum(r['accept'] for r in selected),
                complete=all(c['complete'] for c in cells),lifecycles=cells,metrics=metrics,blocks=blocks,plug_in_mse=plug_in)
    return output


def replay_branch(row,weights,max_steps=MAX_STEPS):
    result=row['result'];n=result['steps'];query=row['query'];mode=row['mode'];other='risk8' if query=='risk1' else 'risk1'
    prefix_steps=8 if mode.startswith('M_') else 1;prefix_policy=other if mode.startswith('M_') else query
    checks=dict(branch_arrays=n>0 and all(len(row[k])==n for k in ('actions','choices','scores','spawned_cells','spawned_ranks')),
        branch_settings=row['p_four']==.1 and row['max_steps']==max_steps,branch_actions=True,branch_rng=True,branch_terminal=True,
        branch_returns=True,branch_environment=True,branch_phases=True,branch_forced_query=True,branch_policy_totals=True,
        branch_no_learning=not any(result['learning_counts'].values()),branch_seconds=math.isfinite(result['seconds']) and 0<=result['decision_seconds']<=result['seconds'])
    if not checks['branch_arrays']:return checks,0
    board=tuple(row['root_board']);status,exits,swipes=prior.previous.legal_exits(board);replayed=swipes
    checks['branch_terminal'] &= status=='ACTIVE'
    environment=Counter(ground_state_status_calls=1,ground_status_internal_swipe_calls=swipes,ground_swipe_calls=swipes)
    phases={p:Counter() for p in ('prefix','continuation')};teachers={q:Counter() for q in QUERIES};remaining=0
    rng=random.Random(row['seed']);score_total=0
    for step,choice in enumerate(row['choices']):
        phase='prefix' if step<prefix_steps else 'continuation';work=Counter(choice['work']);phases[phase].update(work)
        checks['branch_phases'] &= choice['step']==step and choice['phase']==phase
        if phase=='continuation' and mode.endswith('_GATE'):
            local_checks,remaining=prior.gate_checks(board,choice,query,'LEARN8',weights,remaining,step,8,exits);add_checks(checks,local_checks)
            checks['branch_phases'] &= choice['policy_key']==choice['module_decision']['policy_key']
        else:
            policy=prefix_policy if phase=='prefix' else query
            native={k[len(f'policy_{policy}_'):]:v for k,v in work.items() if k.startswith(f'policy_{policy}_')}
            expected=Counter(forced_decisions=1);expected.update({f'policy_{policy}_{k}':v for k,v in native.items()})
            checks['branch_forced_query'] &= choice['policy_key']==policy and choice['module_decision'] is None and work==expected
            checks['branch_forced_query'] &= prior.planning.planning_counts_valid(native,'H2','SINGLE',1,len(exits)) and prior.local.compact_choice_valid(choice,exits,policy)
            add_checks(checks,prior.h1.root_choice_checks(board,choice,policy))
        replayed+=4;prior.add_policy_work(teachers,work)
        action=choice['action'];checks['branch_actions'] &= status=='ACTIVE' and action in exits and row['actions'][step]==action
        if action not in exits:return checks,replayed
        after,score=exits[action];score_total+=score;checks['branch_actions'] &= row['scores'][step]==score
        empty=[i for i,v in enumerate(after) if not v];cell=empty[int(rng.random()*len(empty))];rank=1 if rng.random()<.9 else 2
        checks['branch_rng'] &= (row['spawned_cells'][step],row['spawned_ranks'][step])==(cell,rank)
        board=list(after);board[cell]=rank;status,exits,swipes=prior.previous.legal_exits(tuple(board));replayed+=swipes
        environment.update(ground_explicit_swipe_calls=1,ground_swipe_calls=1+swipes,environment_random_draws=2,sampled_transitions=1,
            ground_state_status_calls=1,ground_status_internal_swipe_calls=swipes)
    final='CUTOFF' if status=='ACTIVE' else status;components=[score_total/2048.,float(final=='LOST'),float(final=='WON')]
    checks['branch_terminal'] &= row['final_board']==board and result['status']==final and n<=row['max_steps'] and (final!='CUTOFF' or n==row['max_steps'])
    checks['branch_returns'] &= result['score']==score_total and result['components']==components and result['utility']==(None if final=='CUTOFF' else prior.utility(components,query))
    checks['branch_environment'] &= Counter(result['environment_counts'])==environment
    checks['branch_policy_totals'] &= Counter(result['prefix_counts'])==phases['prefix'] and Counter(result['continuation_counts'])==phases['continuation'] and Counter(result['policy_counts'])==sum(phases.values(),Counter())
    checks['branch_policy_totals'] &= set(result['policy_counts_by_query'])==set(QUERIES) and all(Counter(result['policy_counts_by_query'][q])==teachers[q] for q in QUERIES)
    return checks,replayed


def model_setup(n):
    return Counter(topology_integer_cells=64,bias_integer_cells=1,loaded_weight_addresses=n,
        loaded_weight_parameters=3*n,loaded_numeric_weight_bytes=24*n)


def source_models(capsule,directory):
    origin=Path(capsule['source_run_ref']).parent;run=read(capsule['source_run_ref']);analysis=read(origin/'analysis.json');original=read(origin/'source_capsule.json')
    source={(r['life'],r['query']):r for r in original['models'] if r['checkpoint']==4 and r['duration']==8}
    checks=dict(source_complete=run['status']=='complete' and analysis['complete'] and analysis['primary_complete'],
        source_bindings=capsule['snapshots']==original['snapshots'] and capsule['source_traces']==[
            dict(life=r['life'],path=str(origin/r['control_trace'])) for r in run['lifecycles']],model_copies=True,model_roster=True)
    models={}
    for item in capsule['models']:
        key=item['life'],item['query'];reference=source[key];path=directory/item['model_ref'];payload=read(path);old=read(item['source_model_ref'])
        checks['model_roster'] &= key not in models and item['checkpoint']==4 and item['duration']==8
        checks['model_copies'] &= Path(item['source_model_ref'])==origin/reference['model_ref'] and payload==old and item['model_bytes']==path.stat().st_size
        checks['model_copies'] &= prior.local.prior.state(payload)==item['frozen_state']==reference['frozen_state'] and payload['frozen']
        models[key]=dict(metadata=item,weights={int(row[0]):tuple(row[1:]) for row in payload['weights']})
    checks['model_roster'] &= len(capsule['models'])==len(models)==8 and set(models)=={(l,q) for l in LIVES for q in QUERIES}
    return models,checks


def source_roots(capsule):
    roots=[];read_rows=0;selected=0
    for trace in capsule['source_traces']:
        wanted={(q,m,4*slot) for q in QUERIES for m in SOURCES for slot in range(4)};found={}
        for row in prior.old.read_rows(trace['path']):
            read_rows+=1;key=row['query'],row['method'],row['replica']
            if key not in wanted or row['checkpoint']!=(-1 if row['method']=='H2' else 4):continue
            life=trace['life'];query,method,replica=key;slot=replica//4
            candidates=[step for step,choice in enumerate(row['choices']) if choice['module_decision']['boundary']]
            ordinal=(2*slot+1)*len(candidates)//8;step=candidates[ordinal]
            board=list(row['initial_board']) if not step else list(row['choices'][step-1]['afterstate'])
            if step:board[row['spawned_cells'][step-1]]=row['spawned_ranks'][step-1]
            found[key]=dict(root_id=f'{life}:{query}:{method}:{slot}',life=life,query=query,source_method=method,slot=slot,
                replica=replica,source_ref=trace['path'],source_physical_id=row['physical_id'],source_seed=row['seed'],source_step=step,
                source_boundary_count=len(candidates),selected_boundary_index=ordinal,board=board)
            if set(found)==wanted:break
        roots.extend(found.values());selected+=len(found)
    roots.sort(key=lambda r:(r['life'],list(QUERIES).index(r['query']),SOURCES.index(r['source_method']),r['slot']))
    return roots,dict(source_rows_read=read_rows,source_games_selected=selected)


def preparation_checks(capsule,frozen,models):
    expected,source_work=source_roots(capsule);roots=frozen['roots'];records=frozen['preparation'];prediction_counts={key:Counter() for key in models}
    checks=dict(root_roster=len(roots)==len(expected)==64,root_source_identity=True,root_predictions=True,
        root_prediction_counts=True,preparation_models=True,preparation_accounting=all(records[k]==v for k,v in source_work.items()),branch_roster=True)
    for actual,reference in zip(roots,expected):
        checks['root_source_identity'] &= all(actual[k]==v for k,v in reference.items())
        key=reference['life'],reference['query'];model=models[key];prediction=prior.predict(reference['board'],model['weights']);value=prior.utility(prediction,reference['query'])
        checks['root_predictions'] &= actual['model_ref']==model['metadata']['model_ref'] and len(actual['prediction']['components'])==3 and all(
            close(a,b) for a,b in zip(actual['prediction']['components'],prediction)) and close(actual['prediction']['advantage'],value) and actual['prediction']['accept']==(value>0)
        work=prior.prediction_work(reference['board']);prediction_counts[key].update(work)
        checks['root_prediction_counts'] &= Counter(actual['prediction_counts'])==work
    seen=[]
    for record in records['prediction_models']:
        key=record['life'],record['query'];seen.append(key);model=models[key]
        checks['preparation_models'] &= record['model_ref']==model['metadata']['model_ref'] and record['before']==record['after']==model['metadata']['frozen_state']
        checks['preparation_accounting'] &= Counter(record['counts'])==prediction_counts[key] and Counter(record['setup_counts'])==model_setup(len(model['weights']))
    checks['preparation_models'] &= len(seen)==len(set(seen))==8 and set(seen)==set(models)
    roster=[dict(branch_id=f'{r["root_id"]}:{suffix}:{mode}',root_id=r['root_id'],suffix=suffix,mode=mode,seed=branch_seed(r,suffix)) for r in roots for suffix in range(16) for mode in MODES]
    checks['branch_roster'] &= frozen['branch_roster']==roster and len(roster)==4096
    return checks,dict(**source_work,root_prediction_counts=dict(sum(prediction_counts.values(),Counter())))


def audit_lifecycle(lifecycle,source,models,roots,directory):
    directory=Path(directory);life=lifecycle['life'];root_map={r['root_id']:r for r in roots};seen=[]
    outcomes={r['root_id']:{} for r in roots};teacher_counts={q:Counter() for q in QUERIES};model_counts={q:Counter() for q in QUERIES}
    checks=dict(branch_identity=True,branch_roster=True,physical_accounting=True,teacher_bank=True,teacher_totals=True,models_frozen=True,model_counts=True,model_roster=True)
    costs=dict(physical_branches=0,environment_counts=Counter(),policy_counts=Counter(),statuses=Counter(),decision_seconds=0.,
        analysis_replay_swipes=0,physical_cells={},model_accounting=[],teacher_accounting=[])
    for row in prior.old.read_rows(directory/lifecycle['branch_trace']):
        root=root_map[row['root_id']];query=root['query'];mode=row['mode'];suffix=row['suffix'];seen.append(row['branch_id'])
        checks['branch_identity'] &= all(row[k]==v for k,v in dict(branch_id=f'{root["root_id"]}:{suffix}:{mode}',life=life,
            query=query,source_method=root['source_method'],slot=root['slot'],root_board=root['board'],seed=branch_seed(root,suffix)).items())
        local_checks,swipes=replay_branch(row,models[query]['weights']);add_checks(checks,local_checks);costs['analysis_replay_swipes']+=swipes
        result=row['result'];outcomes[row['root_id']].setdefault(suffix,{})[mode]=dict(valid=all(local_checks.values()),result={k:result[k] for k in ('status','utility','components')})
        costs['physical_branches']+=1;costs['decision_seconds']+=result['decision_seconds'];costs['statuses'][result['status']]+=1
        for name in ('environment_counts','policy_counts'):costs[name].update(result[name])
        for q in QUERIES:teacher_counts[q].update(result['policy_counts_by_query'][q])
        model_counts[query].update({k[len('learner_'):]:v for k,v in result['policy_counts'].items() if k.startswith('learner_')})
        cell=costs['physical_cells'].setdefault(f'{query}:{root["source_method"]}:{mode}',dict(query=query,source_method=root['source_method'],mode=mode,
            physical_branches=0,statuses=Counter(),environment_counts=Counter(),policy_counts=Counter(),decision_seconds=0.))
        cell['physical_branches']+=1;cell['statuses'][result['status']]+=1;cell['decision_seconds']+=result['decision_seconds']
        for name in ('environment_counts','policy_counts'):cell[name].update(result[name])
    checks['branch_roster'] &= seen==[f'{r["root_id"]}:{suffix}:{mode}' for r in roots for suffix in range(16) for mode in MODES] and len(seen)==1024
    checks['physical_accounting'] &= lifecycle['physical_branches']==costs['physical_branches'] and all(Counter(lifecycle[k])==costs[k] for k in ('environment_counts','policy_counts','statuses'))
    loaded=[]
    for record in lifecycle['models']:
        query=record['query'];loaded.append(query);model=models[query]
        checks['models_frozen'] &= record['model_ref']==model['metadata']['model_ref'] and record['before']==record['after']==model['metadata']['frozen_state']
        checks['model_counts'] &= Counter(record['counts'])==model_counts[query] and Counter(record['setup_counts'])==model_setup(len(model['weights']))
        costs['model_accounting'].append(dict(life=life,**record))
    checks['model_roster'] &= len(loaded)==len(set(loaded))==2 and set(loaded)==set(QUERIES)
    for query in QUERIES:
        teacher=lifecycle['teacher_bank'][query]
        checks['teacher_bank'] &= prior.h1.teacher_analysis.teacher_loads_valid(teacher['loads'],source,'SINGLE',query)
        checks['teacher_bank'] &= teacher['parent_before']==teacher['parent_after']==prior.planning.previous.model_state(source,query,'PARENT',0)
        checks['teacher_bank'] &= teacher['leaf_before']==teacher['leaf_after']==prior.planning.expected_model_state(source,query,'SINGLE')
        checks['teacher_totals'] &= Counter(teacher['total_counts'])==teacher_counts[query]
        costs['teacher_accounting'].append(dict(life=life,query=query,**teacher))
    diagnostics=[root_diagnostics(root,outcomes[root['root_id']]) for root in roots]
    print(json.dumps(dict(event='audited_lifecycle',life=life,physical_branches=costs['physical_branches'],replayed_swipes=costs['analysis_replay_swipes'])),flush=True)
    return dict(life=life,checks=checks,costs=costs,diagnostics=diagnostics)


def analyze(directory):
    started=perf_counter();directory=Path(directory).resolve()
    run,capsule,frozen=(read(directory/name) for name in ('run.json','source_capsule.json','frozen_inputs.json'))
    checks=dict(settings=run['settings']==expected_settings(),frozen_inputs=frozen['status']=='frozen' and not frozen['lifecycles'] and
        all(frozen[k]==run[k] for k in ('settings','inherited_cost_refs')),inherited_costs=run['inherited_cost_refs']==capsule['cost_refs'],
        lifecycle_roster=len(run['lifecycles'])==4 and {r['life'] for r in run['lifecycles']}==set(LIVES))
    models,source_checks=source_models(capsule,directory);add_checks(checks,source_checks)
    local_checks,preparation_work=preparation_checks(capsule,frozen,models);add_checks(checks,local_checks)
    inherited={path:read(path) for path in {ref['path'] for ref in capsule['cost_refs']}}
    checks['inherited_fields']=all(all(field in inherited[ref['path']] for field in ref['fields']) for ref in capsule['cost_refs'])
    sources={s['life']:s for s in capsule['snapshots']};results=[]
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks=[pool.submit(audit_lifecycle,lifecycle,sources[lifecycle['life']],
            {q:models[lifecycle['life'],q] for q in QUERIES},[r for r in frozen['roots'] if r['life']==lifecycle['life']],directory)
            for lifecycle in run['lifecycles']]
        for task in as_completed(tasks):results.append(task.result())
    results.sort(key=lambda r:r['life']);diagnostics=[]
    costs=dict(physical_branches=0,environment_counts=Counter(),policy_counts=Counter(),statuses=Counter(),decision_seconds=0.,
        analysis_replay_swipes=0,physical_cells={},model_accounting=[],teacher_accounting=[],
        preparation=frozen['preparation'],analysis_preparation=preparation_work,analysis_model_files_read=16,
        runtime_model_loads=len(frozen['preparation']['prediction_models'])+sum(len(l['models']) for l in run['lifecycles']),
        frozen_model_copies=dict(files=len(capsule['models']),bytes=sum(m['model_bytes'] for m in capsule['models'])),
        analysis_inherited_files_read=len(inherited),new_training_updates=0,new_training_environment_samples=0)
    for result in results:
        add_checks(checks,result['checks']);diagnostics.extend(result['diagnostics']);local_costs=result['costs']
        for name in ('physical_branches','decision_seconds','analysis_replay_swipes'):costs[name]+=local_costs[name]
        for name in ('environment_counts','policy_counts','statuses'):costs[name].update(local_costs[name])
        for name in ('model_accounting','teacher_accounting'):costs[name].extend(local_costs[name])
        for key,cell in local_costs['physical_cells'].items():
            target=costs['physical_cells'].setdefault(key,dict(query=cell['query'],source_method=cell['source_method'],mode=cell['mode'],
                physical_branches=0,statuses=Counter(),environment_counts=Counter(),policy_counts=Counter(),decision_seconds=0.))
            for name in ('physical_branches','decision_seconds'):target[name]+=cell[name]
            for name in ('statuses','environment_counts','policy_counts'):target[name].update(cell[name])
    checks['full_branch_roster']=costs['physical_branches']==4096 and len(diagnostics)==64
    complete=run['status']=='complete' and all(checks.values());costs['new_environment_samples']=costs['environment_counts'].get('sampled_transitions',0)
    return dict(schema='acfqp.module_diagnosis.v153.analysis',complete=complete,primary_complete=complete and all(r['complete'] for r in diagnostics),
        checks=checks,all_roots=aggregate(diagnostics),accepted_roots=aggregate(diagnostics,True),root_diagnostics=diagnostics,costs=costs,
        inherited_cost_refs=run['inherited_cost_refs'],seconds=perf_counter()-started,
        estimand='Paired interventions at fixed roots: delta_h2=M_H2-H_H2; delta_gate=M_GATE-H_GATE; continuation_shift=delta_gate-delta_h2.',
        uncertainty='Pointwise intervals condition on fixed histories, roots and predictions; root mean labels retain Monte Carlo uncertainty. MSE excess p^2-2*p*delta is linear and avoids squared-label noise bias.',
        limitations='Root-source differences are descriptive. Accepted subsets need at least one root from every history; all-root policy gains retain declined roots as exact zero. Cutoffs and costs remain in the record.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input','--directory',dest='input',type=Path,default=ROOT/'reports/controlled_predictive_module_diagnosis_v153')
    args=parser.parse_args();result=analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=len(result['checks']),
        failed=[k for k,v in result['checks'].items() if not v],seconds=result['seconds'])),flush=True)
    raise SystemExit(0 if result['complete'] else 1)
