#!/usr/bin/env python3
"""Independent V295 compact routes, fitting inventory and scientific receipts."""
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
from statistics import mean

from verify_conditional_bellman_v294 import (add_counts, check_contrast, check_heldout,
    aggregate, check_dataset, check_fit)
from verify_cumulative_critic_v289 import close, equal_tree, json_file, require
from verify_shadow_deployment_v293 import check_games

ARMS=('FROZEN','SMOOTH_BELLMAN','ROUTED_BELLMAN')
PHASES=('A','B','A_prime')
LAWS=(.1,.5,.1)
RAW=65536
PAIRS=(('ROUTED_BELLMAN','FROZEN'),('ROUTED_BELLMAN','SMOOTH_BELLMAN'),('SMOOTH_BELLMAN','FROZEN'))


def evaluation_seed(life,phase,game):return 295900010000+life*1000000+phase*100000+game


def check_routes(data):
    modules=set(data['warmup_module_ids']);active=data['initial_active_module_id'];snapshots={};births=[]
    require(modules==set(range(len(modules))) and active in modules
        and [m['id'] for m in data['warmup_modules']]==sorted(modules),'original observed warmup modules')
    for phase_index,phase in enumerate(PHASES):
        timeline=data['routing_timeline'][phase];previous=phase_index*RAW;complete=[];completed_at=None
        for item in timeline:
            raw=item['raw_index'];require(previous<=raw<=(phase_index+1)*RAW and raw>phase_index*RAW,'causal phase raw routing timeline');previous=raw
            kind=item['kind']
            if kind in ('created','reactivated'):
                require(completed_at!=raw,'terminal observation routing must precede the same-raw game commit')
                require(item['previous_module_id']==active,'route transition uses preceding observed active module')
                module=item['module_id']
                if kind=='created':
                    require(module==len(modules),'new expert keyed to original next observed module');modules.add(module);births.append(item)
                else:require(module in modules and module!=active,'reactivation must retain an existing expert')
                active=module
            else:
                require(kind=='GAME_COMPLETE' and item['metadata']['end_raw']==raw,'route timeline completion clock')
                game=item['metadata'];pure=item['pure_phase']
                if pure is not None:
                    require(pure==phase and game in data['phases'][phase]['fit_games']+data['phases'][phase]['heldout_games']
                        and item['fit']==(game in data['phases'][phase]['fit_games'])
                        and item['exclusion_reason'] is None,'only natural pure-phase FIT-prefix games may update')
                else:require(not item['fit'] and item['exclusion_reason'] in ('MIXED_PHASE','CUTOFF'),'excluded game trained a critic')
                complete.append(game['episode'])
                completed_at=raw
        expected=data['snapshots'][phase]['memory']
        require(active==expected['active_module_id'] and modules=={m['id'] for m in expected['modules']},
            'actual observed reactivation and known module inventory at checkpoint')
        snapshots[phase]=dict(active_module_id=active,module_ids=sorted(modules))
        require(len(complete)==len(set(complete)) and all(g['episode'] in complete for g in
            data['phases'][phase]['fit_games']+data['phases'][phase]['heldout_games']),'all full factual games appear once in observed timeline')
    require(len(births)==data['costs']['routing_event_inventory'].get('created',0)
        and sum(e['kind']=='reactivated' for p in PHASES for e in data['routing_timeline'][p])
            ==data['costs']['routing_event_inventory'].get('reactivated',0)
        and sum(len(data['routing_timeline'][p]) for p in PHASES)==data['costs']['retained_route_records'],'all observed route event counts')
    return snapshots


def check_routed_fit(fit,game,module_samples,old_updates):
    samples=game['steps']-(game['status']=='WON');c=Counter(fit['counts']);by=fit['by_module']
    require(fit['routed'] and fit['conditioned'] and fit['target_kind']=='EXPECTED_CONTROL' and fit['alpha']==.0025
        and fit['fitted_games']==1 and fit['fitted_steps']==game['steps'] and fit['trained_afterstates']==samples,
        'same complete-game frozen-context routed T* method')
    require(set(by)==set(old_updates) and sum(module_samples.values())==samples
        and fit['module_updates']==module_samples,'only actual module-assigned nonwinning samples train')
    writes=addresses=commits=0
    for module,row in by.items():
        n=module_samples[module];u=row['game_unique_addresses'];w=row['learning_counts']['table_updates']
        require(row['trained_afterstates']==n and row['old_value_updates']==old_updates[module]
            and row['new_value_updates']==old_updates[module]+n,'expert inherited parameter prefix versus new own samples')
        require((4<=u<=32*n if n else u==0) and w==2*u
            and row['learning_counts']==dict(td_updates=n,table_updates=w,table_update_occurrences=64*n),
            'module-specific actual parameter writes')
        if n:
            commits+=1
            for point in ('first_sample','last_sample'):
                item=row[point];require(0<=item['step']<samples and 0<=item['model_p_four']<=1
                    and close(item['error'],item['target']-item['prediction_before_update']),
                    'actual whole-game position and precommit expert target/residual')
        else:require(row['first_sample'] is None and row['last_sample'] is None,'inactive expert has training examples')
        writes+=w;addresses+=u
    require(c['td_updates']==c['routed_sample_expert_reads']==c['expected_control_targets']==c['residual_error_subtractions']==samples
        and c['skipped_winning_afterstates']==(game['status']=='WON'),'routed nonwinning sample counter semantics')
    require(c['game_sort_items']==c['address_occurrence_count_visits']==c['routed_gradient_expert_address_visits']==32*samples
        and c['table_update_occurrences']==c['weighted_residual_accumulations']==64*samples,'global original address denominator and isolated gradients')
    require(c['routed_expert_address_pairs']==addresses and c['routed_expert_parameter_commits']==commits
        and max(r['game_unique_addresses'] for r in by.values())<=c['game_unique_addresses']<=addresses
        and c['game_parameter_commits']==1,'global address union versus per-expert touched addresses')
    require(c['parameter_write_events']==c['normalization_divisions']==c['parameter_update_multiplications']==writes
        and fit['learning_counts']==dict(td_updates=samples,table_updates=writes,table_update_occurrences=64*samples),
        'true routed writes are summed across experts')
    require(c['routed_parameter_pointer_views']==len(by) and fit['residual_pointer_array_bytes']==8*len(by)
        and fit['dense_expert_weight_stack_bytes']==0,'pointer views avoid hidden dense expert copies')
    require(c['source_table_lookups']==32*c['value_predictions'] and c['residual_table_lookups']==64*c['value_predictions']
        and c['context_basis_calls']==samples and 2*samples<=c['expected_spawn_outcomes']<=32*samples
        and c['spawn_probability_products']==c['spawn_probability_sums']==c['expected_spawn_outcomes']
        and c['suffix_target_assignments']==c['suffix_reward_additions']==0,'same composite/control model operations')
    for point,step in (('first_sample',0),('last_sample',samples-1)):
        item=fit[point];require(item['step']==step and close(item['error'],item['target']-item['prediction_before_update']),
            'global first/last game-start residual')
    return samples,writes


def module_sample_positions(data,game):
    """Consumed-raw clocks precede the next action; terminal samples are analytic."""
    changes=[(e['raw_index'],e['module_id']) for p in PHASES for e in data['routing_timeline'][p]
        if e['kind'] in ('created','reactivated')]
    clocks=[r[0] for r in changes];positions=defaultdict(list)
    for step in range(game['steps']-(game['status']=='WON')):
        index=bisect_right(clocks,game['start_raw']+2+step)-1
        module=changes[index][1] if index>=0 else data['initial_active_module_id']
        positions[str(module)].append(step)
    return positions


def check_copy(receipt,origin):
    parameters=4*11**6;weight_bytes=8*parameters;c=Counter(receipt['setup_counts'])
    require(receipt['residual_bytes_created']==c['allocated_residual_bytes']==2*weight_bytes
        and c['allocated_residual_parameters']==c['zero_initialized_residual_parameters']==2*parameters
        and c['source_parameters_shared']==parameters,'actual two residual banks and immutable shared SOURCE')
    require(c['residual_parameters_copied']==2*parameters and c['residual_bytes_copied']==2*weight_bytes
        and receipt['origin_value_updates']==origin,'expert birth copies its own preceding parameter prefix')
    require(receipt['seconds']>=0 and receipt['cpu_seconds']>=0,'actual residual copy timing')


def read_canonical(d):
    lives={l['lifecycle']:l for l in d['by_lifecycle']};fits=defaultdict(list);snapshots={};n=0
    for parent in d['parent_receipts']:
        pid=parent['parent'];require(parent['lifecycle_ids']==list(range(pid,16,4)),'parent/life roster')
        path=Path(parent['trace_file']);require(path.stat().st_size==parent['trace_bytes'],'compact physical trace bytes')
        states={life:dict(experts={str(m):0 for m in lives[life]['dataset']['warmup_module_ids']},smooth=0,own=0,
            positions=Counter(),pending=[],births=[],counter_births=[],counter=None,checkpoints=set()) for life in parent['lifecycle_ids']}
        with gzip.open(path,'rt') as stream:
            for line in stream:
                row=json.loads(line);n+=1;lid=row['lifecycle'];phase=row['phase'];life=lives[lid];state=states[lid]
                require(row['parent']==lid%4==pid and phase in PHASES,'canonical source/context identity')
                if phase=='B' and state['counter'] is None:
                    require((lid,'A') in snapshots,'counterfactual library copied before any B observation')
                    state['counter']=dict(snapshots[lid,'A']['experts'])
                if state['pending']:
                    require(row['kind']=='FIT_GAME' and row['arm']==state['pending'][0],
                        'all game-start target reads must commit at this factual completion before later routing')
                if row['kind']=='ROUTE_EVENT':
                    pos=state['positions'][phase];timeline=life['dataset']['routing_timeline'][phase]
                    require(pos<len(timeline) and row['original_event']==timeline[pos],'all observed routes in original causal order')
                    event=timeline[pos];state['positions'][phase]+=1
                    if event['kind']=='created':
                        module,previous=str(event['module_id']),str(event['previous_module_id'])
                        born=row['current_birth'];require(born is not None and born['event']==event and born['phase']==phase,
                            'created observed module missing its parameter copy')
                        check_copy(born['receipt'],state['experts'][previous]);state['experts'][module]=state['experts'][previous]
                        state['births'].append(born)
                        if phase=='B':
                            counter=row['no_update_birth'];require(counter is not None and counter['event']==event and counter['phase']==phase,
                                'no-B-update library must follow exactly the same observed B creation')
                            check_copy(counter['receipt'],state['counter'][previous]);state['counter'][module]=state['counter'][previous]
                            state['counter_births'].append(counter)
                        else:require(row['no_update_birth'] is None,'no-update library exists only during B')
                    else:require(row['current_birth'] is None and row['no_update_birth'] is None,'reactivation/completion cannot replace an expert')
                    if event['kind']=='GAME_COMPLETE' and event['fit']:
                        state['pending']=list(ARMS[1:]);state['game']=event['metadata']
                elif row['kind']=='FIT_GAME':
                    arm=row['arm'];require(state['pending'] and row['completion']==state['game'],'FIT label was not just completed')
                    game=row['completion'];key=(lid,arm,phase);declared=life['dataset']['phases'][phase]['fit_games']
                    require(len(fits[key])<len(declared) and game==declared[len(fits[key])],'unchanged chronological FIT game inventory')
                    if arm=='SMOOTH_BELLMAN':
                        count,_=check_fit(row['fit'],game,'BELLMAN_CONDITIONED');state['smooth']+=count
                        require(row['value_updates']==state['smooth'],'smooth own processed samples')
                    else:
                        positions=module_sample_positions(life['dataset'],game)
                        assigned={m:len(positions[m]) for m in state['experts']}
                        count,_=check_routed_fit(row['fit'],game,assigned,state['experts'])
                        for module,value in row['fit']['by_module'].items():
                            if positions[module]:
                                require(value['first_sample']['step']==positions[module][0]
                                    and value['last_sample']['step']==positions[module][-1],
                                    'routed examples use actual before-action observed module positions')
                            state['experts'][module]=value['new_value_updates']
                        state['own']+=count;require(row['value_updates']==state['own'],'copied expert history credited as new own learning')
                    fits[key].append(row['fit']);state['pending'].pop(0)
                elif row['kind']=='CHECKPOINT':
                    key=(row['arm'],phase);require(key not in state['checkpoints']
                        and state['positions'][phase]==len(life['dataset']['routing_timeline'][phase]),'checkpoint before all actual route events')
                    state['checkpoints'].add(key);saved=life['arms'][row['arm']]['phases'][phase]
                    require({k:v for k,v in row.items() if k not in ('kind','lifecycle','arm','phase','parent')}==saved,
                        'canonical physical science/holdout checkpoint differs from summary')
                    if row['arm']=='ROUTED_BELLMAN':
                        require(saved['snapshot']['expert_value_updates']==state['experts']
                            and saved['snapshot']['value_updates']==state['own'],'expert inherited and global own update inventories')
                        snapshots[lid,phase]=dict(experts=dict(state['experts']),counter=dict(state['counter']) if phase=='B' else None)
                else:raise ValueError('unexpected V295 record '+row['kind'])
        for lid,state in states.items():
            life=lives[lid]
            require(not state['pending'] and len(state['checkpoints'])==9,'complete routed three-phase canonical endpoints')
            require(state['births']==life['expert_births'] and state['counter_births']==life['no_update_births'],
                'all actual expert copies retained once')
    return fits,snapshots,n


def check_lifecycle(life,old,fits,routed_states,previous):
    lid=life['lifecycle'];data=life['dataset'];check_dataset(data,old);routes=check_routes(data)
    result=dict(lifecycle=lid,parent=life['parent'],arms={},actual_A_prime_module=routes['A_prime']['active_module_id'],
        saved_A_module=routes['A']['active_module_id'],
        A_prime_same_observed_module=routes['A_prime']['active_module_id']==routes['A']['active_module_id'])
    for p in PHASES:
        require(data['phases'][p]['fit_games']==previous['dataset']['phases'][p]['fit_games']
            and data['phases'][p]['heldout_games']==previous['dataset']['phases'][p]['heldout_games'],
            'same V294 pure-phase FIT/heldout history')
        timeline=data['routing_timeline'][p]
        require(life['phase_route_counts'][p]==dict(created=sum(e['kind']=='created' for e in timeline),
            reactivated=sum(e['kind']=='reactivated' for e in timeline),game_complete=sum(e['kind']=='GAME_COMPLETE' for e in timeline),
            fit_game_complete=sum(e['kind']=='GAME_COMPLETE' and e['fit'] for e in timeline)),
            'actual observed phase route inventory')
    def metric(value):return {k:value[k] for k in ('games','mean_game_utility','wins','losses','cutoffs','steps')}
    for arm in ARMS:
        phases={};cumulative=0
        for index,phase in enumerate(PHASES):
            row=life['arms'][arm]['phases'][phase];records=fits[lid,arm,phase];games=data['phases'][phase]['fit_games']
            require(len(records)==(0 if arm=='FROZEN' else len(games)),'both learners receive all and only identical FIT games')
            for key in ('fitted_games','fitted_steps','trained_afterstates','seconds','cpu_seconds'):
                require(close(row['fit'][key],sum(r[key] for r in records)),'phase actual fit total '+key)
            for key in ('learning_counts','target_counts','consolidation_counts','prediction_counts','setup_counts'):
                equal_tree(row['fit'][key],add_counts(r[key] for r in records),'phase actual fit operations '+key)
            cumulative+=row['fit']['trained_afterstates'];snap=row['snapshot'];p=data['snapshots'][phase]['estimated_p_four']
            module=routes[phase]['active_module_id'];selected=module if arm=='ROUTED_BELLMAN' else None
            require(snap['estimated_p_four']==p and snap['active_module_id']==module and snap['selected_value_module_id']==selected
                and snap['value_updates']==cumulative,'science uses actual learned p/observed active module and own prefix')
            require(snap['routed_expert_module_ids']==(routes[phase]['module_ids'] if arm=='ROUTED_BELLMAN' else [])
                and snap['expert_value_updates']==(routed_states[lid,phase]['experts'] if arm=='ROUTED_BELLMAN' else {}),
                'science expert roster never selected by phase truth')
            current=check_games(row['game_summaries'],[evaluation_seed(lid,index,i) for i in range(32)],row['evaluation_counts'])
            heldout=check_heldout(row['heldout'],data['phases'][phase]['heldout_games'])
            if arm in ('FROZEN','SMOOTH_BELLMAN'):
                prior=previous['arms']['FROZEN' if arm=='FROZEN' else 'BELLMAN_CONDITIONED']['phases'][phase]
                for key in ('game_metrics','metrics','prediction_counts','target_counts'):
                    require(row['heldout'][key]==prior['heldout'][key],'unchanged SOURCE/smooth full factual heldout '+key)
            else:
                counts=Counter(row['heldout']['prediction_counts']);samples=sum(r['count'] for r in row['heldout']['game_metrics'])
                require(row['heldout']['routing_prediction_samples']==counts['value_predictions']==samples
                    and counts['source_table_lookups']==32*samples and counts['residual_table_lookups']==64*samples,
                    'routed heldout only factual sample prediction work')
                expected_batches=sum(len(module_sample_positions(data,g)) for g in data['phases'][phase]['heldout_games'])
                require(row['heldout']['routing_prediction_batches']==expected_batches,'all heldout module prediction batches billed')
            probe=row['retention_probe'];pa=data['snapshots']['A']['estimated_p_four'];ma=routes['A']['active_module_id']
            require(probe['model_p_four']==pa and probe['environment_p_four']==.1 and probe['depth']==2
                and probe['selected_value_module_id']==(ma if arm=='ROUTED_BELLMAN' else None),
                'known A context and actual A-prime route must remain distinct')
            if phase=='A':
                require(probe['shared_with_current'] and probe['game_summaries']==row['game_summaries']
                    and not any(probe['counts'].values()) and probe['seconds']==probe['cpu_seconds']==0.,'shared A probe counted twice')
                retention=current
            else:
                require(not probe['shared_with_current'],'new fixed-A physical probe marked shared')
                retention=check_games(probe['game_summaries'],[evaluation_seed(lid,0,i) for i in range(32)],probe['counts'])
            phases[phase]=dict(metric(current),heldout=heldout,retention_probe=metric(retention))
            if phase=='B':
                ahead=row['a_head_on_B'];require(ahead['model_p_four']==p and ahead['environment_p_four']==.5 and ahead['depth']==2
                    and ahead['selected_value_module_id']==selected,'B counterpart same observed route/law/belief')
                if arm=='FROZEN':
                    require(ahead['shared_with_current'] and ahead['game_summaries']==row['game_summaries']
                        and not any(ahead['counts'].values()) and ahead['seconds']==ahead['cpu_seconds']==0.,'SOURCE B reference charged twice')
                    comparison=current
                else:
                    require(not ahead['shared_with_current'],'learned no-B-update counterpart must have actual games')
                    comparison=check_games(ahead['game_summaries'],[evaluation_seed(lid,1,i) for i in range(32)],ahead['counts'])
                phases[phase]['a_head_on_B']=metric(comparison)
        totals=life['arms'][arm]['fit_totals']
        for key in ('fitted_games','fitted_steps','trained_afterstates','seconds','cpu_seconds'):
            require(close(totals[key],sum(life['arms'][arm]['phases'][p]['fit'][key] for p in PHASES)),'life fit total '+key)
        for key in ('learning_counts','target_counts','consolidation_counts','prediction_counts','setup_counts'):
            equal_tree(totals[key],add_counts(life['arms'][arm]['phases'][p]['fit'][key] for p in PHASES),'life fit work '+key)
        result['arms'][arm]=dict(mean_game_utility=mean(r['mean_game_utility'] for r in phases.values()),
            heldout={k:mean(r['heldout'][k] for r in phases.values()) for k in ('mse','mae','bias')},phases=phases)
    for p in PHASES:
        prior=previous['arms']['BELLMAN_CONDITIONED']['phases'][p]['fit'];now=life['arms']['SMOOTH_BELLMAN']['phases'][p]['fit']
        for key in ('fitted_games','fitted_steps','trained_afterstates','learning_counts','target_counts','consolidation_counts','prediction_counts'):
            require(now[key]==prior[key],'smooth learning remains exact V294 baseline '+key)
    return result


def check_head_inventory(life,routed_states):
    lid=life['lifecycle'];parameters=4*11**6;weight_bytes=8*parameters
    initial=life['head_initializations'];require([(r['arm'],r['module_id']) for r in initial]
        ==[('SMOOTH_BELLMAN',None)]+[('ROUTED_BELLMAN',m) for m in life['dataset']['warmup_module_ids']],
        'initialize exactly original known warmup modules')
    for r in initial:
        c=Counter(r['setup_counts']);require(r['residual_bytes_created']==c['allocated_residual_bytes']==2*weight_bytes
            and c['allocated_residual_parameters']==c['zero_initialized_residual_parameters']==2*parameters
            and c['source_parameters_shared']==parameters and c['residual_parameters_copied']==0
            and r['cpu_seconds']>=0,'zero initial residuals share actual SOURCE and bill allocation')
    ma=life['dataset']['snapshots']['A']['memory']['active_module_id'];a=routed_states[lid,'A']['experts']
    copies=life['retained_A_copies'];require([(r['arm'],r['module_id']) for r in copies]
        ==[('SMOOTH_BELLMAN',None)]+[('ROUTED_BELLMAN',int(m)) for m in a],
        'copy complete A library for identical B routing')
    for r in copies:check_copy(r['receipt'],life['arms']['SMOOTH_BELLMAN']['phases']['A']['snapshot']['value_updates']
        if r['arm']=='SMOOTH_BELLMAN' else a[str(r['module_id'])])
    purposes={}
    for arm in ARMS[1:]:
        for phase in PHASES:
            snapshot=life['arms'][arm]['phases'][phase]['snapshot']
            current=(snapshot['value_updates'] if arm=='SMOOTH_BELLMAN' else snapshot['expert_value_updates'][str(snapshot['active_module_id'])])
            purposes[arm+'_'+phase+'_CURRENT']=(phase,current)
        for phase in ('B','A_prime'):
            snapshot=life['arms'][arm]['phases'][phase]['snapshot']
            current=snapshot['value_updates'] if arm=='SMOOTH_BELLMAN' else snapshot['expert_value_updates'][str(ma)]
            purposes[arm+'_'+phase+'_FIXED_A']=('A',current)
        reference=life['arms'][arm]['phases']['A']['snapshot']['value_updates'] if arm=='SMOOTH_BELLMAN' else \
            routed_states[lid,'B']['counter'][str(life['dataset']['snapshots']['B']['memory']['active_module_id'])]
        purposes[arm+'_B_NO_VALUE_UPDATES']=('B',reference)
    require(len(life['materializations'])==12 and {r['purpose'] for r in life['materializations']}==set(purposes),
        'all actual current/retention/no-update materializations')
    for r in life['materializations']:
        phase,updates=purposes[r['purpose']]
        require(r['conditioned'] and r['model_p_four']==life['dataset']['snapshots'][phase]['estimated_p_four']
            and r['origin_residual_updates']==updates and r['private_weight_bytes']==weight_bytes,
            'materialization uses exact selected expert parameter prefix and observed p')
        require(r['blending_counts']==dict(source_anchor_parameters_copied=parameters,source_anchor_bytes_copied=weight_bytes,
            effective_table_parameters_scanned=2*parameters,effective_table_multiplications=2*parameters,
            effective_table_additions=2*parameters,effective_table_parameter_writes=2*parameters,allocated_blending_scratch_bytes=weight_bytes),
            'real SOURCE anchor and two-bank blend cost')
        c=Counter(r['setup_counts']);require(c['allocated_weight_parameters']==c['source_parameters_copied']==parameters
            and c['allocated_weight_bytes']==c['source_weight_bytes_copied']==weight_bytes,'actual immutable QueryTD setup cost')


def check_summary(summary,records):
    equal_tree(summary['by_lifecycle'],records,'equal game then phase then life diagnostics')
    arms={}
    for arm in ARMS:
        phases={p:dict(aggregate([r['arms'][arm]['phases'][p] for r in records]),
            heldout={k:mean(r['arms'][arm]['phases'][p]['heldout'][k] for r in records) for k in ('mse','mae','bias')},
            retention_probe=aggregate([r['arms'][arm]['phases'][p]['retention_probe'] for r in records])) for p in PHASES}
        arms[arm]=dict(mean_game_utility=mean(r['arms'][arm]['mean_game_utility'] for r in records),phases=phases,
            heldout={k:mean(r['arms'][arm]['heldout'][k] for r in records) for k in ('mse','mae','bias')},
            **{k:sum(v[k] for v in phases.values()) for k in ('games','wins','losses','cutoffs','steps')})
    equal_tree(summary['arms'],arms,'all independent utility/error aggregation')
    for left,right in PAIRS:
        name=left+'_minus_'+right
        check_contrast(summary['paired_contrasts'][name],[r['arms'][left]['mean_game_utility']-r['arms'][right]['mean_game_utility'] for r in records])
        for p in PHASES:check_contrast(summary['phase_contrasts'][p][name],[r['arms'][left]['phases'][p]['mean_game_utility']-
            r['arms'][right]['phases'][p]['mean_game_utility'] for r in records])
    for arm in ARMS:
        check_contrast(summary['correction_contrasts'][arm],[r['arms'][arm]['phases']['B']['mean_game_utility']-
            r['arms'][arm]['phases']['B']['a_head_on_B']['mean_game_utility'] for r in records])
        for label,p,q in (('after_B','B','A'),('restoration','A_prime','B'),('final_vs_A','A_prime','A')):
            c=summary['retention_contrasts'][arm][label]
            check_contrast(c,[r['arms'][arm]['phases'][p]['retention_probe']['mean_game_utility']-
                r['arms'][arm]['phases'][q]['retention_probe']['mean_game_utility'] for r in records])
            direction='POSITIVE_CHANGE_SUPPORTED' if c['ci95'][0]>0 else 'NEGATIVE_CHANGE_SUPPORTED' if c['ci95'][1]<0 else \
                'ZERO_OBSERVED_CHANGE' if all(v==0 for v in c['lifecycle_deltas'].values()) else 'CHANGE_UNCERTAIN'
            require(c['direction']==direction,'known-A stored context does not prove actual behavioral preservation')
    cutoffs=sum(v['cutoffs'] for v in arms.values())
    cutoffs+=sum(r['arms'][a]['phases'][p]['retention_probe']['cutoffs'] for r in records for a in ARMS for p in ('B','A_prime'))
    cutoffs+=sum(r['arms'][a]['phases']['B']['a_head_on_B']['cutoffs'] for r in records for a in ARMS[1:])
    require(summary['science_cutoffs']==cutoffs and summary['complete_game_endpoints']==(cutoffs==0)
        and summary['net_gain_supported']==(cutoffs==0 and summary['paired_contrasts']['ROUTED_BELLMAN_minus_FROZEN']['ci95'][0]>0)
        and summary['correction_supported']==(cutoffs==0 and summary['correction_contrasts']['ROUTED_BELLMAN']['ci95'][0]>0),
        'secondary sharing or stored-A diagnostic substituted for independent primary benefit')
    require(summary['actual_A_prime_same_observed_module']==sum(r['A_prime_same_observed_module'] for r in records)
        and summary['physical_science_games']==8704 and summary['logical_science_game_references']==10752
        and summary['bootstrap_seed']==29500001 and summary['bootstrap_draws']==20000
        and summary['primary_contrast']=='ROUTED_BELLMAN_minus_FROZEN'
        and summary['estimator']=='EQUAL_GAMES_THEN_PHASES_THEN_LIFECYCLES'
        and summary['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS','actual roster and frozen statistical evidence scope')


def check_accounting(d,old):
    lives=d['by_lifecycle'];parents=d['parent_receipts'];a=d['accounting'];kinds=('environment','planning')
    inherited=old['accounting']['inherited_costs_per_arm']['FROZEN_H2']
    carrier=sum(l['dataset']['costs']['reused_carrier_raw_tiles'] for l in lives)
    warm=sum(l['dataset']['costs']['warmup_raw_tiles'] for l in lives)
    economic=inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+carrier+warm
    require(a['new_training_environment_raw_tiles']==a['new_ranking_rollouts']==0
        and a['reused_carrier_raw_tiles']==carrier==16*3*RAW
        and a['reused_warmup_raw_tiles']==warm==old['accounting']['physical_warmup_raw_tiles'],
        'zero new training/ranking; all original carrier/warmup fees retained')
    require(a['economic_training_raw_tiles_per_arm']==dict.fromkeys(ARMS,economic)
        and a['inherited_costs_per_arm']==dict.fromkeys(ARMS,inherited),'source-only fees plus same paid original carrier history')
    expected=dict(reused_carrier_counts={k:add_counts(l['dataset']['costs']['carrier_acquisition_counts'][k] for l in lives)
        for k in (*kinds,'learning')},reused_warmup_counts={k:add_counts(l['dataset']['costs']['warmup_'+k+'_counts'] for l in lives)
        for k in ('environment','direct','memory')})
    expected['processed_training_samples_per_arm']={arm:sum(l['arms'][arm]['fit_totals']['trained_afterstates'] for l in lives) for arm in ARMS}
    expected['fit_counts_per_arm']={arm:{k:add_counts(l['arms'][arm]['fit_totals'][k] for l in lives)
        for k in ('learning_counts','target_counts','consolidation_counts','prediction_counts','setup_counts')} for arm in ARMS}
    components={}
    physical=logical=0
    for arm in ARMS:
        components[arm]={}
        for part in ('current','retention_probe','a_head_on_B'):
            rows=[l['arms'][arm]['phases'][p] for l in lives for p in PHASES if part!='a_head_on_B' or p=='B']
            components[arm][part]={k:add_counts(r['evaluation_counts'][k] if part=='current' else r[part]['counts'][k] for r in rows) for k in kinds}
            for r in rows:
                n=len(r['game_summaries']) if part=='current' else len(r[part]['game_summaries'])
                logical+=n;physical+=n if part=='current' or not r[part]['shared_with_current'] else 0
    require(a['physical_evaluation_games']==physical==8704 and a['logical_evaluation_game_references']==logical==10752,
        'all physical science and shared logical references counted once')
    expected['evaluation_components_per_arm']=components
    expected['evaluation_counts_per_arm']={arm:{k:add_counts(v[k] for v in parts.values()) for k in kinds} for arm,parts in components.items()}
    expected['evaluation_counts']={k:add_counts(v[k] for v in expected['evaluation_counts_per_arm'].values()) for k in kinds}
    for scope in ('prediction','target'):
        expected['heldout_'+scope+'_counts_per_arm']={arm:add_counts(l['arms'][arm]['phases'][p]['heldout'][scope+'_counts'] for l in lives for p in PHASES) for arm in ARMS}
    expected['routed_heldout_prediction_batches']=sum(l['arms']['ROUTED_BELLMAN']['phases'][p]['heldout']['routing_prediction_batches'] for l in lives for p in PHASES)
    for name,field in (('reconstruction_counts','processing_counts'),('reconstruction_memory_counts','processing_memory_counts'),
        ('observed_route_counts','routing_event_inventory')):expected[name]=add_counts(l['dataset']['costs'][field] for l in lives)
    expected['observed_phase_route_counts']={p:add_counts(l['phase_route_counts'][p] for l in lives) for p in PHASES}
    expected['reconstruction_cpu_seconds']=sum(l['dataset']['costs']['processing_cpu_seconds'] for l in lives)
    expected['excluded_mixed_games']=sum(g['reason']=='MIXED_PHASE' for l in lives for g in l['dataset']['costs']['excluded_games'])
    expected['excluded_complete_game_raw_tiles']=sum(g['raw_tiles'] for l in lives for g in l['dataset']['costs']['excluded_games'])
    expected['excluded_tail_raw_tiles']=sum(l['dataset']['costs']['excluded_tail']['raw_tiles'] for l in lives)
    initial=[r for l in lives for r in l['head_initializations']]
    births=[r['receipt'] for l in lives for r in l['expert_births']]
    copies=[r['receipt'] for l in lives for r in l['retained_A_copies']]
    counter=[r['receipt'] for l in lives for r in l['no_update_births']]
    expected.update(actual_experts_created=len(births),initial_residual_heads=len(initial),no_update_experts_created=len(counter))
    for scope,rows in (('initial_residual',initial),('expert_birth',births),('retained_A',copies),('no_update_birth',counter)):
        expected[scope+'_setup_counts']=add_counts(r['setup_counts'] for r in rows)
        expected[scope+'_residual_bytes_created']=sum(r['residual_bytes_created'] for r in rows)
        expected[scope+'_cpu_seconds']=sum(r['cpu_seconds'] for r in rows)
    rows=[r for l in lives for r in l['materializations']]
    for scope in ('setup','blending'):expected['materialization_'+scope+'_counts']=add_counts(r[scope+'_counts'] for r in rows)
    expected['materialization_count']=len(rows)
    expected['materialization_private_weight_bytes_created']=sum(r['private_weight_bytes'] for r in rows)
    expected['materialization_cpu_seconds']=sum(r['cpu_seconds'] for r in rows)
    expected['native_evaluation_setup_counts']=add_counts(p['native_evaluation_setup']['counts'] for p in parents)
    expected['native_evaluation_setup_seconds']=sum(p['native_evaluation_setup']['seconds'] for p in parents)
    expected['fit_cpu_seconds_per_arm']={arm:sum(l['arms'][arm]['fit_totals']['cpu_seconds'] for l in lives) for arm in ARMS}
    for name,field in (('worker_cpu_seconds','cpu_seconds'),('compiler_cpu_seconds','compiler_cpu_seconds'),('canonical_trace_bytes','trace_bytes')):
        expected[name]=sum(p[field] for p in parents)
    for key,value in expected.items():equal_tree(a[key],value,'full actual accounting '+key)
    for parent in parents:
        setup=parent['source_setup'];require(setup['new_leaf_updates']==0 and setup['checkpoint_loads']==1
            and setup['leaf_weight_bytes']==8*4*11**6 and setup['cpu_seconds']>=0 and setup['wall_seconds']>=0,
            'actual source reconstruction retained and no new SOURCE updates')
    require(a['materialization_count']==192 and a['coordinator_cpu_seconds']>=0 and a['wall_seconds']>0,
        'all real materializations and process timings')


def audit(directory):
    directory=Path(directory);d=json_file(directory/'summary.json');settings=d['settings']
    require(settings==json_file(directory/'configuration.json'),'frozen settings changed')
    expected=dict(lifecycles=list(range(16)),parents=4,arms=list(ARMS),phases=[['A',.1],['B',.5],['A_prime',.1]],
        alpha=.0025,fit_fraction=.8,query=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.),max_steps=8192,
        evaluation_games=32,seed_evaluation=295900010000,bootstrap_seed=29500001,bootstrap_draws=20000,
        scientific_games=8704,logical_scientific_game_references=10752,new_training_raw_tiles=0,new_ranking_rollouts=0,
        primary='ROUTED_BELLMAN_minus_FROZEN_THREE_PHASE_COMPLETE_GAME_UTILITY',
        target='EXPECTED_MAX_CONTROL_GAME_START_FROZEN_OBSERVED_PROBABILITY',
        representation='SOURCE_PLUS_UNIT_NORMALIZED_TWO_BANK_RESIDUAL_PER_OBSERVED_LIBRARY_MODULE',
        denominator='WHOLE_GAME_ORIGINAL_ADDRESS_OCCURRENCES_ACROSS_ALL_MODULES',
        expert_birth='COPY_PREVIOUS_EXPERT_AT_OBSERVED_CREATION_BEFORE_CURRENT_GAME_COMMIT',
        correction_reference='A_LIBRARY_FOLLOWS_SAME_B_OBSERVED_BIRTHS_WITHOUT_B_VALUE_UPDATES',
        split='V294_PURE_PHASE_COMPLETE_GAMES_CHRONOLOGICAL_80_20_LABEL_HOLDOUT')
    for key,value in expected.items():require(settings[key]==value,'registered '+key)
    old_path=Path(settings['source_summary']);old=json_file(old_path)
    require(json_file(old_path.with_name('audit.json'))['independent_valid'],'valid previous carrier evidence')
    previous_path=directory.parent/'conditional_bellman_v294'/'summary.json';previous=json_file(previous_path)
    require(json_file(previous_path.with_name('audit.json'))['independent_valid']
        and previous['settings']['source_summary']==str(old_path),'valid unchanged V294 smooth comparator')
    require(d['source_provenance']==old['source_provenance']==previous['source_provenance']
        and d['schema']=='acfqp.routed_bellman.v295' and d['status']=='EXPERIMENT_COMPLETE'
        and d['scientific_gate']=='NOT_A_FORMAL_GATE','immutable source and exploratory scientific scope')
    lives=d['by_lifecycle'];require([l['lifecycle'] for l in lives]==list(range(16))
        and all(l['parent']==l['lifecycle']%4 for l in lives),'complete four-source 16-life cohort')
    prior={l['lifecycle']:l for l in old['by_lifecycle']};smooth={l['lifecycle']:l for l in previous['by_lifecycle']}
    fits,states,rows=read_canonical(d);records=[]
    for life in lives:
        records.append(check_lifecycle(life,prior[life['lifecycle']],fits,states,smooth[life['lifecycle']]))
        check_head_inventory(life,states)
    check_summary(d['summary'],records);check_accounting(d,old);a=d['accounting'];s=d['summary']
    return dict(status='PASS',independent_valid=True,lifecycles=16,fixed_source_parents=4,canonical_rows=rows,
        new_training_environment_raw_tiles=0,new_ranking_rollouts=0,reused_carrier_raw_tiles=a['reused_carrier_raw_tiles'],
        reused_warmup_raw_tiles=a['reused_warmup_raw_tiles'],economic_training_raw_tiles_per_arm=a['economic_training_raw_tiles_per_arm'],
        physical_science_games=8704,logical_science_game_references=10752,science_cutoffs=s['science_cutoffs'],
        processed_training_samples_per_arm=a['processed_training_samples_per_arm'],actual_experts_created=a['actual_experts_created'],
        no_update_experts_created=a['no_update_experts_created'],materializations=192,
        source_setup_counts=add_counts(p['source_setup']['setup_counts'] for p in d['parent_receipts']),
        source_setup_cpu_seconds=sum(p['source_setup']['cpu_seconds'] for p in d['parent_receipts']),
        source_setup_cpu_scope='Already included in worker CPU; separate operation receipt, not additional process time.',
        net_gain_supported=s['net_gain_supported'],correction_supported=s['correction_supported'],
        actual_A_prime_same_observed_module=s['actual_A_prime_same_observed_module'],
        primary=s['paired_contrasts']['ROUTED_BELLMAN_minus_FROZEN'],errors=[],
        limitations='Independent compact route/sample/copy, terminal game, signed mean and accounting audit. No old carrier/world '
            'or SOURCE-weight replay, refitting, or 20000-draw CI regeneration. Before-action module counts use the actual carrier '
            'protocol which stops at every memory-block boundary. Target/normalization mathematics have finite literal tests. '
            'Known-A context probes are separate from actual A-prime routing and independent net control. Four source parents are fixed.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True)
    directory=parser.parse_args().input
    try:result=audit(directory)
    except ValueError as error:result=dict(status='FAIL',independent_valid=False,errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False));raise SystemExit(not result['independent_valid'])


if __name__=='__main__':main()
