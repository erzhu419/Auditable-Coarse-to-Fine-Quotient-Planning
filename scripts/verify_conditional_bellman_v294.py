#!/usr/bin/env python3
"""Independent compact V294 receipts; no world, value fitting or bootstrap calls."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
from statistics import mean

from verify_cumulative_critic_v289 import close, equal_tree, json_file, require
from verify_shadow_deployment_v293 import check_games
from verify_natural_online_value_v286 import planning_counts, terminal

ARMS=('FROZEN','MC_BOARD','MC_CONDITIONED','BELLMAN_BOARD','BELLMAN_CONDITIONED')
PHASES=('A','B','A_prime')
LAWS=(.1,.5,.1)
RAW=65536


def evaluation_seed(life,phase,game):return 294900010000+life*1000000+phase*100000+game
def ranking_seed(life,phase,anchor,replica):return 294600010000+life*1000000+phase*100000+anchor*1000+replica


def add_counts(rows):
    result={}
    for row in rows:
        for key,value in row.items():
            result[key]=max(result.get(key,0),value) if key.endswith('_peak') else result.get(key,0)+value
    return result


def check_dataset(data,old):
    intervals=[];fit_steps=heldout_steps=fit_games=heldout_games=0
    require(data['snapshots']=={p:old['carrier']['phases'][p]['snapshot'] for p in PHASES},'retained carrier probability/memory prefix')
    for index,phase in enumerate(PHASES):
        item=data['phases'][phase];f,h=item['fit_games'],item['heldout_games'];games=f+h
        require(len(f)==4*len(games)//5 and f and h,'pure complete-game chronological 80/20 split')
        require([g['episode'] for g in games]==sorted(g['episode'] for g in games),'chronological pure games')
        for g in games:
            require(g['phase']==phase and g['status'] in ('WON','LOST') and g['steps']>=1
                and g['end_raw']-g['start_raw']==g['steps']+2
                and index*RAW<=g['start_raw']<g['end_raw']<=(index+1)*RAW,'whole pure-phase natural labels')
            intervals.append((g['start_raw'],g['end_raw']))
        require(len(item['anchors'])==3,'fixed three quartile ranking anchors')
        first=h[0]
        for slot,anchor in enumerate(item['anchors']):
            require(anchor['episode']==first['episode'] and anchor['phase']==phase
                and anchor['phase_index']==index and anchor['anchor_index']==slot
                and anchor['step']==int((first['steps']-1)*(.25,.5,.75)[slot])
                and 0<=anchor['model_p_four']<=1 and len(anchor['board_before_action'])==16,'first heldout-game fixed time anchors')
        fit_steps+=sum(g['steps'] for g in f);heldout_steps+=sum(g['steps'] for g in h)
        fit_games+=len(f);heldout_games+=len(h)
    costs=data['costs']
    for g in costs['excluded_games']:
        require(g['raw_tiles']==g['end_raw']-g['start_raw']==g['steps']+2,'excluded full-game raw fees')
        pure=any(i*RAW<=g['start_raw'] and g['end_raw']<=(i+1)*RAW for i in range(3))
        require((g['reason']=='MIXED_PHASE' and not pure and g['status'] in ('WON','LOST'))
            or (g['reason']=='CUTOFF' and g['status']=='CUTOFF' and g['steps']==8192),'excluded mixed/censored label reason')
        intervals.append((g['start_raw'],g['end_raw']))
    tail=costs['excluded_tail'];saved=old['carrier']['final_unfitted_game']
    require(tail==saved,'excluded final carrier tail remains unfitted')
    if tail['raw_tiles']:intervals.append((3*RAW-tail['raw_tiles'],3*RAW))
    cursor=0
    for start,end in sorted(intervals):
        require(start==cursor and end>start,'complete paid carrier inventory has a gap/overlap');cursor=end
    require(cursor==costs['reused_carrier_raw_tiles']==3*RAW and costs['new_environment_raw_tiles']==0,'retained carrier full raw/no new training')
    require((costs['fit_steps'],costs['heldout_steps'],costs['fit_games'],costs['heldout_games'])
        ==(fit_steps,heldout_steps,fit_games,heldout_games),'all pure training/heldout inventories')
    for field in ('environment','planning','learning'):
        require(costs['carrier_acquisition_counts'][field]==old['carrier']['training_counts'][field],'original carrier work was dropped')
    for field in ('raw_tiles','environment_counts','direct_counts','memory_counts'):
        require(costs['warmup_'+field]==old['warmup'][field],'original physical warmup fees')
    return fit_steps,heldout_steps


def check_fit(receipt,game,arm):
    banks=2 if arm.endswith('CONDITIONED') else 1
    mc=arm.startswith('MC');samples=game['steps']-(game['status']=='WON');c=Counter(receipt['counts'])
    require(receipt['target_kind']==('MC' if mc else 'EXPECTED_CONTROL')
        and receipt['conditioned']==(banks==2) and receipt['alpha']==.0025
        and receipt['fitted_games']==1 and receipt['fitted_steps']==game['steps']
        and receipt['trained_afterstates']==samples,'same-game method/target/sample inventory')
    require(c['td_updates']==samples and c['table_update_occurrences']==32*banks*samples
        and c['residual_error_subtractions']==samples and c['skipped_winning_afterstates']==(game['status']=='WON'),
        'winning analytic and real processed samples')
    require(c['game_sort_items']==c['address_occurrence_count_visits']==32*samples
        and c['weighted_residual_accumulations']==32*banks*samples,'original unweighted address denominator and gradients')
    unique=c['game_unique_addresses'];writes=banks*unique
    require(4<=unique<=32*samples and c['parameter_write_events']==c['normalization_divisions']==
        c['parameter_update_multiplications']==writes and c['game_parameter_commits']==1,'one consolidated commit and actual writes')
    require(receipt['learning_counts']==dict(td_updates=samples,table_updates=writes,table_update_occurrences=32*banks*samples),
        'samples distinguished from table writes')
    require(c['source_table_lookups']==32*c['value_predictions']
        and c['residual_table_lookups']==32*banks*c['value_predictions']
        and c['context_basis_calls']==(samples if banks==2 else 0),'source/residual readout and normalized observed-p basis')
    if mc:
        require(c['suffix_target_assignments']==c['suffix_reward_additions']==game['steps']
            and c['expected_control_targets']==c['expected_spawn_outcomes']==0
            and c['value_predictions']==samples,'factual suffix work excludes control enumeration')
    else:
        require(c['expected_control_targets']==samples and c['suffix_target_assignments']==c['suffix_reward_additions']==0
            and 2*samples<=c['expected_spawn_outcomes']<=32*samples
            and c['spawn_probability_products']==c['spawn_probability_sums']==c['expected_spawn_outcomes'],
            'observed-law expected control target model branches')
    for sample,step in ((receipt['first_sample'],0),(receipt['last_sample'],samples-1)):
        require(sample['step']==step and 0<=sample['model_p_four']<=1
            and close(sample['error'],sample['target']-sample['prediction_before_update']),
            'first/last precommit residual and before-action context')
    return samples,writes


def check_heldout(value,games):
    rows=value['game_metrics'];require([r['metadata'] for r in rows]==games,'complete same-game heldout labels')
    for r,g in zip(rows,games):
        require(r['count']==g['steps']-(g['status']=='WON') and r['mse']>=0 and r['mae']>=0
            and r['mae']**2<=r['mse']+1e-8 and close(r['bias'],r['mean_prediction']-r['mean_factual_future_utility']),
            'factual heldout sample/error metrics')
    metrics={key:mean(r[key] for r in rows) for key in ('bias','mse','mae')}
    equal_tree(value['metrics'],metrics,'game equal-weight factual error')
    require(value['target_counts']==dict(suffix_games=len(games),suffix_target_assignments=sum(g['steps'] for g in games),
        suffix_reward_additions=sum(g['steps'] for g in games),skipped_winning_afterstates=sum(g['status']=='WON' for g in games)),
        'full factual heldout label work')
    return metrics


def check_ranking(anchor,life,phase,slot):
    ref=anchor['reference'];p=anchor['model_p_four'];choices=anchor['choices']
    require(ref['model_p_four']==p and ref['environment_p_four']==LAWS[phase] and set(choices)==set(ARMS),
        'SOURCE continuation observed-p/environment law separation')
    legal=sorted(choices['FROZEN']['action_values']);require(legal,'ranking anchor has legal actions')
    grouped=defaultdict(list)
    for row in ref['rollouts']:grouped[row['action']].append(row)
    require(sorted(grouped)==legal,'all legal action continuation references')
    q={};steps=wins=0
    for action in legal:
        rows=grouped[action]
        require(len(rows)==32 and [r['replica_index'] for r in rows]==list(range(32))
            and [r['seed'] for r in rows]==[ranking_seed(life,phase,slot,i) for i in range(32)],'fixed all-action paired fresh reference seeds')
        for r in rows:
            require(1<=r['steps']<=8192,'reference continuation includes forced first action')
            if r['status']=='CUTOFF':
                require(r['steps']==8192 and max(r['final_board'])<11,'true reference cutoff');bonus=0.
            else:terminal(r['final_board'],r['status']);bonus=4. if r['status']=='WON' else -4.
            require(r['first_score']==choices['FROZEN']['action_values'][action]['score']
                and r['total_utility']==r['total_score']/2048.+bonus
                and r['suffix_utility']==(r['total_score']-r['first_score'])/2048.+bonus,'reference first reward and full factual suffix')
            steps+=r['steps'];wins+=r['status']=='WON'
        q[action]=mean(r['total_utility'] for r in rows)
    n=len(ref['rollouts']);env=dict(sampled_transitions=steps,environment_random_draws=2*steps,
        ground_explicit_swipe_calls=steps,ground_swipe_calls=steps+4*(steps-wins),
        ground_state_status_calls=steps,ground_status_internal_swipe_calls=4*(steps-wins))
    require(Counter(ref['counts']['environment'])==Counter(env),'actual ranking continuation transition costs')
    r=Counter(ref['counts']['rollout']);calls=steps-n
    require(r['completed_rollouts']==r['rng_streams_started']==n and r['replica_streams']==32
        and r['evaluate_calls']==1 and r['continuation_choose_calls']==calls,'forced-first SOURCE continuation planning counts')
    planning_counts(dict(ref['counts']['planning'],choose_calls=calls),calls,2)
    best=max(q.values());result={}
    for arm,choice in choices.items():
        require(sorted(choice['action_values'])==legal,'common legal ranking actions')
        action=min(legal,key=lambda a:(-choice['action_values'][a]['value'],a))
        require(choice['action']==action,'H2 action argmax and lexical ties')
        for a,item in choice['action_values'].items():
            require(item['score']==choices['FROZEN']['action_values'][a]['score']
                and item['afterstate']==choices['FROZEN']['action_values'][a]['afterstate']
                and close(item['value'],item['score']/2048.+item['tail_value']),'common deterministic actions and H2 readout units')
        result[arm]=dict(reference_utility=q[action],reference_regret=best-q[action],
            change_from_source_action=q[action]-q[choices['FROZEN']['action']],changed_action=action!=choices['FROZEN']['action'])
    return dict(anchor_id=anchor['anchor_id'],action_means=q,choices=result)


def read_canonical(d):
    lives={l['lifecycle']:l for l in d['by_lifecycle']};fits=defaultdict(list);updates=Counter();checkpoints=set();ranks=set();n=0
    for parent in d['parent_receipts']:
        pid=parent['parent'];require(parent['lifecycle_ids']==list(range(pid,16,4)),'parent/life roster')
        path=Path(parent['trace_file']);require(path.stat().st_size==parent['trace_bytes'],'new compact trace storage')
        with gzip.open(path,'rt') as stream:
            for line in stream:
                row=json.loads(line);n+=1;lid=row['lifecycle'];phase=row['phase'];life=lives[lid]
                require(row['parent']==lid%4==pid and phase in PHASES,'trace source/context identity')
                if row['kind']=='FIT_GAME':
                    arm=row['arm'];key=(lid,arm,phase);games=life['dataset']['phases'][phase]['fit_games']
                    require(arm in ARMS[1:] and len(fits[key])<len(games)
                        and row['completion']==games[len(fits[key])],'same chronological pure FIT inventory')
                    count,_=check_fit(row['fit'],row['completion'],arm);updates[lid,arm]+=count
                    require(row['value_updates']==updates[lid,arm],'persistent residual samples across phases')
                    fits[key].append(row['fit'])
                elif row['kind']=='CHECKPOINT':
                    key=(lid,row['arm'],phase);require(key not in checkpoints,'duplicate evaluation checkpoint')
                    checkpoints.add(key);saved=life['arms'][row['arm']]['phases'][phase]
                    require({k:v for k,v in row.items() if k not in ('kind','lifecycle','arm','phase','parent')}==saved,
                        'canonical heldout/science checkpoint differs from summary')
                elif row['kind']=='RANKING_ANCHOR':
                    slot=row['anchor_index'];key=(lid,phase,slot);require(key not in ranks,'duplicate fixed ranking anchor')
                    ranks.add(key);saved=life['ranking'][phase]['anchors'][slot]
                    require({k:v for k,v in row.items() if k!='kind'}==saved,'canonical ranking receipt differs from summary')
                else:raise ValueError('unexpected V294 dataflow record '+row['kind'])
    require(len(checkpoints)==16*5*3 and len(ranks)==144,'complete canonical science/ranking coverage')
    return fits,n


def check_lifecycle(life,old,fits):
    lid=life['lifecycle'];check_dataset(life['dataset'],old);result=dict(lifecycle=lid,parent=life['parent'],arms={},ranking={})
    for index,phase in enumerate(PHASES):
        rows=life['ranking'][phase]['anchors'];declared=life['dataset']['phases'][phase]['anchors']
        require(len(rows)==3,'all fixed ranking anchors retained')
        for row,anchor in zip(rows,declared):require({k:row[k] for k in anchor}==anchor,'heldout anchor/context was changed')
        checked=[check_ranking(row,lid,index,slot) for slot,row in enumerate(rows)]
        result['ranking'][phase]=dict(anchors=checked,
            arms={arm:dict(anchors=3,changed_actions=sum(r['choices'][arm]['changed_action'] for r in checked),
                **{k:mean(r['choices'][arm][k] for r in checked) for k in ('reference_utility','reference_regret','change_from_source_action')}) for arm in ARMS},
            cutoffs=sum(r['status']=='CUTOFF' for row in rows for r in row['reference']['rollouts']),
            rollouts=sum(len(row['reference']['rollouts']) for row in rows))
    def metric(g):return {k:g[k] for k in ('games','mean_game_utility','wins','losses','cutoffs','steps')}
    for arm in ARMS:
        phases={};cumulative=0
        for index,phase in enumerate(PHASES):
            row=life['arms'][arm]['phases'][phase];records=fits[lid,arm,phase];games=life['dataset']['phases'][phase]['fit_games']
            require(len(records)==(0 if arm=='FROZEN' else len(games)),'all four critics use same complete FIT games')
            total=row['fit'];cumulative+=total['trained_afterstates']
            for field in ('fitted_games','fitted_steps','trained_afterstates','seconds','cpu_seconds'):
                require(close(total[field],sum(r[field] for r in records)),'phase fit totals '+field)
            for field in ('learning_counts','target_counts','consolidation_counts','prediction_counts','setup_counts'):
                require(total[field]==add_counts(r[field] for r in records),'actual phase fit operations '+field)
            p=life['dataset']['snapshots'][phase]['estimated_p_four'];seeds=[evaluation_seed(lid,index,i) for i in range(32)]
            require(row['snapshot']==dict(estimated_p_four=p,value_updates=cumulative),'shared actual prefix p/current head samples')
            current=check_games(row['game_summaries'],seeds,row['evaluation_counts'])
            heldout=check_heldout(row['heldout'],life['dataset']['phases'][phase]['heldout_games'])
            probe=row['retention_probe'];pa=life['dataset']['snapshots']['A']['estimated_p_four']
            require(probe['model_p_four']==pa and probe['environment_p_four']==.1 and probe['depth']==2,'fixed A belief/law retention')
            if phase=='A':
                require(probe['shared_with_current'] and probe['game_summaries']==row['game_summaries']
                    and not any(probe['counts'].values()) and probe['seconds']==probe['cpu_seconds']==0.,'shared A probe charged twice')
                retention=current
            else:
                require(not probe['shared_with_current'],'new retention evaluation was marked shared')
                retention=check_games(probe['game_summaries'],[evaluation_seed(lid,0,i) for i in range(32)],probe['counts'])
            phases[phase]=dict(metric(current),heldout=dict(heldout,games=len(row['heldout']['game_metrics']),
                afterstates=sum(r['count'] for r in row['heldout']['game_metrics'])),
                ranking=result['ranking'][phase]['arms'][arm],retention_probe=metric(retention))
            if phase=='B':
                ahead=row['a_head_on_B'];require(ahead['model_p_four']==p and ahead['environment_p_four']==.5 and ahead['depth']==2,
                    'saved A residual parameters rematerialized at current B p/law')
                if arm=='FROZEN':
                    require(ahead['shared_with_current'] and ahead['game_summaries']==row['game_summaries'] and not any(ahead['counts'].values()),'shared source B reference charged twice')
                    phases[phase]['a_head_on_B']=metric(current)
                else:
                    require(not ahead['shared_with_current'],'new A-parameter/B-belief eval must be physical')
                    phases[phase]['a_head_on_B']=metric(check_games(ahead['game_summaries'],seeds,ahead['counts']))
        totals=life['arms'][arm]['fit_totals']
        for field in ('fitted_games','fitted_steps','trained_afterstates','seconds','cpu_seconds'):
            require(close(totals[field],sum(life['arms'][arm]['phases'][p]['fit'][field] for p in PHASES)),'life fit total '+field)
        for field in ('learning_counts','target_counts','consolidation_counts','prediction_counts','setup_counts'):
            require(totals[field]==add_counts(life['arms'][arm]['phases'][p]['fit'][field] for p in PHASES),'life fit count '+field)
        result['arms'][arm]=dict(mean_game_utility=mean(v['mean_game_utility'] for v in phases.values()),
            heldout={k:mean(v['heldout'][k] for v in phases.values()) for k in ('mse','mae','bias')},
            ranking={k:mean(v['ranking'][k] for v in phases.values()) for k in ('reference_utility','reference_regret','change_from_source_action')},phases=phases)
    return result


def check_head_inventory(life):
    parameters=4*11**6;weight_bytes=8*parameters;purpose={}
    require(set(life['head_setups'])==set(life['retained_A_setups'])==set(ARMS[1:]),'four learned heads and saved A banks')
    for arm in ARMS[1:]:
        banks=2 if arm.endswith('CONDITIONED') else 1
        setup=life['head_setups'][arm];copy=life['retained_A_setups'][arm]
        for row in (setup,copy):
            c=Counter(row['setup_counts'])
            require(row['residual_bytes_created']==c['allocated_residual_bytes']==banks*weight_bytes
                and c['allocated_residual_parameters']==c['zero_initialized_residual_parameters']==banks*parameters
                and c['source_parameters_shared']==parameters,'real residual bank allocation and shared immutable SOURCE')
        require(copy['setup_counts']['residual_parameters_copied']==banks*parameters
            and copy['setup_counts']['residual_bytes_copied']==banks*weight_bytes
            and copy['origin_value_updates']==life['arms'][arm]['phases']['A']['snapshot']['value_updates'],
            'saved A copies the residual banks at the A prefix')
        for phase in PHASES:purpose[arm+'_'+phase+'_CURRENT']=(arm,phase,phase)
        for phase in ('B','A_prime'):purpose[arm+'_'+phase+'_FIXED_A']=(arm,'A',phase)
        purpose[arm+'_B_A_PARAMETERS']=(arm,'B','A')
    require(len(life['materializations'])==len(purpose)==24,'all and only real learned materializations')
    seen=set()
    for row in life['materializations']:
        label=row['purpose'];require(label in purpose and label not in seen,'unique declared materialization purpose');seen.add(label)
        arm,p_phase,head_phase=purpose[label];banks=2 if arm.endswith('CONDITIONED') else 1
        require(row['model_p_four']==life['dataset']['snapshots'][p_phase]['estimated_p_four']
            and row['conditioned']==(banks==2) and row['private_weight_bytes']==weight_bytes,'current/fixed observed-p materialized readout')
        expected=life['arms'][arm]['phases'][head_phase]['snapshot']['value_updates']
        require(row['origin_residual_updates']==expected,'materialization reads correct actual head prefix')
        b=row['blending_counts'];require(b==dict(source_anchor_parameters_copied=parameters,
            source_anchor_bytes_copied=weight_bytes,effective_table_parameters_scanned=parameters*banks,
            effective_table_multiplications=parameters*banks,effective_table_additions=parameters*banks,
            effective_table_parameter_writes=parameters*banks,allocated_blending_scratch_bytes=weight_bytes),
            'real SOURCE copy, residual blending and scratch cost')
        c=Counter(row['setup_counts'])
        require(c['allocated_weight_parameters']==c['source_parameters_copied']==parameters
            and c['allocated_weight_bytes']==c['source_weight_bytes_copied']==weight_bytes,'original QueryTD initialization costs')


def check_accounting(d,old):
    lives=d['by_lifecycle'];parents=d['parent_receipts'];a=d['accounting'];kinds=('environment','planning')
    inherited=old['accounting']['inherited_costs_per_arm']['FROZEN_H2']
    carrier=sum(l['dataset']['costs']['reused_carrier_raw_tiles'] for l in lives)
    warm=sum(l['dataset']['costs']['warmup_raw_tiles'] for l in lives)
    economic=inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+carrier+warm
    require(a['new_training_environment_raw_tiles']==0 and a['reused_carrier_raw_tiles']==carrier==16*3*RAW
        and a['reused_warmup_raw_tiles']==warm==old['accounting']['physical_warmup_raw_tiles'],
        'zero new training and all original carrier/warmup observations paid')
    require(a['economic_training_raw_tiles_per_arm']==dict.fromkeys(ARMS,economic)
        and a['inherited_costs_per_arm']==dict.fromkeys(ARMS,inherited),'source-only inherited and full shared-data economic cost')
    expected={}
    expected['reused_carrier_counts']={k:add_counts(l['dataset']['costs']['carrier_acquisition_counts'][k] for l in lives)
        for k in (*kinds,'learning')}
    for scope in ('environment','direct','memory'):
        expected['reused_warmup_'+scope+'_counts']=add_counts(l['dataset']['costs']['warmup_'+scope+'_counts'] for l in lives)
    expected['processed_training_samples_per_arm']={arm:sum(l['arms'][arm]['fit_totals']['trained_afterstates'] for l in lives) for arm in ARMS}
    expected['fit_counts_per_arm']={arm:{field:add_counts(l['arms'][arm]['fit_totals'][field] for l in lives)
        for field in ('learning_counts','target_counts','consolidation_counts','prediction_counts','setup_counts')} for arm in ARMS}
    components={}
    for arm in ARMS:
        components[arm]={}
        for part in ('current','retention_probe','a_head_on_B'):
            rows=[l['arms'][arm]['phases'][p] for l in lives for p in PHASES if part!='a_head_on_B' or p=='B']
            components[arm][part]={k:add_counts(r['evaluation_counts'][k] if part=='current' else r[part]['counts'][k] for r in rows) for k in kinds}
    expected['evaluation_components_per_arm']=components
    expected['evaluation_counts_per_arm']={arm:{k:add_counts(v[k] for v in parts.values()) for k in kinds} for arm,parts in components.items()}
    expected['evaluation_counts']={k:add_counts(v[k] for v in expected['evaluation_counts_per_arm'].values()) for k in kinds}
    require(a['physical_evaluation_games']==14848 and a['logical_evaluation_game_references']==17920,
        'physical versus shared logical SCI references')
    references=[r['reference'] for l in lives for phase in l['ranking'].values() for r in phase['anchors']]
    expected['physical_ranking_anchors']=len(references)
    expected['physical_ranking_rollouts']=sum(len(r['rollouts']) for r in references)
    expected['ranking_reference_counts']={k:add_counts(r['counts'][k] for r in references) for k in (*kinds,'rollout')}
    expected['ranking_choice_counts_per_arm']={arm:add_counts(r['choice_counts'][arm] for l in lives
        for phase in l['ranking'].values() for r in phase['anchors']) for arm in ARMS}
    for scope in ('prediction','target'):
        expected['heldout_'+scope+'_counts_per_arm']={arm:add_counts(l['arms'][arm]['phases'][p]['heldout'][scope+'_counts'] for l in lives for p in PHASES) for arm in ARMS}
    expected['reconstruction_counts']=add_counts(l['dataset']['costs']['processing_counts'] for l in lives)
    expected['reconstruction_cpu_seconds']=sum(l['dataset']['costs']['processing_cpu_seconds'] for l in lives)
    expected['excluded_mixed_games']=sum(g['reason']=='MIXED_PHASE' for l in lives for g in l['dataset']['costs']['excluded_games'])
    expected['excluded_complete_game_raw_tiles']=sum(g['raw_tiles'] for l in lives for g in l['dataset']['costs']['excluded_games'])
    expected['excluded_tail_raw_tiles']=sum(l['dataset']['costs']['excluded_tail']['raw_tiles'] for l in lives)
    for scope,key,bytekey in (('residual_head','head_setups','residual_head_bytes_created'),('retained_A','retained_A_setups','retained_A_residual_bytes_created')):
        rows=[r for l in lives for r in l[key].values()]
        expected[scope+'_setup_counts']=add_counts(r['setup_counts'] for r in rows)
        expected[bytekey]=sum(r['residual_bytes_created'] for r in rows)
    rows=[r for l in lives for r in l['materializations']]
    for scope in ('setup','blending'):expected['materialization_'+scope+'_counts']=add_counts(r[scope+'_counts'] for r in rows)
    expected['materialization_count']=len(rows)
    expected['materialization_private_weight_bytes_created']=sum(r['private_weight_bytes'] for r in rows)
    expected['materialization_cpu_seconds']=sum(r['cpu_seconds'] for r in rows)
    expected['native_evaluation_setup_counts']=add_counts(p['native_evaluation_setup']['counts'] for p in parents)
    expected['native_evaluation_setup_seconds']=sum(p['native_evaluation_setup']['seconds'] for p in parents)
    expected['fit_cpu_seconds_per_arm']={arm:sum(l['arms'][arm]['fit_totals']['cpu_seconds'] for l in lives) for arm in ARMS}
    expected['ranking_reference_cpu_seconds']=sum(r['cpu_seconds'] for r in references)
    for key in ('cpu_seconds','compiler_cpu_seconds'):expected['worker_'+key if key=='cpu_seconds' else key]=sum(p[key] for p in parents)
    expected['canonical_trace_bytes']=sum(p['trace_bytes'] for p in parents)
    expected['development_reference']=dict(previous='V293',unused_validation_raw_tiles=old['accounting']['physical_validation_raw_tiles'],
        unused_deployment_raw_tiles=old['accounting']['physical_deployment_raw_tiles'],unused_scientific_evaluation_counts=old['accounting']['evaluation_counts'])
    for key,value in expected.items():equal_tree(a[key],value,'complete accounting '+key)
    require(a['coordinator_cpu_seconds']>=0 and a['wall_seconds']>0,'actual coordinator timings')


PAIRS=(('BELLMAN_CONDITIONED','FROZEN'),('MC_CONDITIONED','MC_BOARD'),
    ('BELLMAN_CONDITIONED','BELLMAN_BOARD'),('BELLMAN_BOARD','MC_BOARD'),('BELLMAN_CONDITIONED','MC_CONDITIONED'))


def check_contrast(saved,values,signed=False,lower=False):
    require(close(saved['mean'],mean(values)),'independent signed paired mean')
    equal_tree(saved['lifecycle_deltas'],{str(i):v for i,v in enumerate(values)},'all signed life effects')
    groups=[values[p::4] for p in range(4)]
    equal_tree(saved['parent_mean_deltas'],{str(p):mean(g) for p,g in enumerate(groups)},'fixed parent stratum means')
    low,high=saved['ci95']
    require(saved['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
        and mean(min(g) for g in groups)-1e-10<=low<=high<=mean(max(g) for g in groups)+1e-10,'conditional whole-life CI possible range')
    positive=sum(v>0 for v in values);zero=sum(v==0 for v in values);negative=sum(v<0 for v in values)
    if signed:
        require(saved['positive_zero_negative']==[positive,zero,negative]
            and saved['negative_lifecycles']==[i for i,v in enumerate(values) if v<0]
            and 'improved_equal_worse' not in saved,'signed diagnostic assigned benefit')
        if lower:require(saved['better_equal_worse']==[negative,zero,positive]
            and saved['worse_lifecycles']==[i for i,v in enumerate(values) if v>0],'lower error means better')
    else:
        require(saved['improved_equal_worse']==[positive,zero,negative]
            and saved['adverse_lifecycles']==[i for i,v in enumerate(values) if v<0],'all utility adverse lives retained')


def aggregate(games):
    return dict(mean_game_utility=mean(g['mean_game_utility'] for g in games),
        **{k:sum(g[k] for g in games) for k in ('games','wins','losses','cutoffs','steps')})


def check_summary(summary,records):
    equal_tree(summary['by_lifecycle'],records,'equal game/phase/life source/science diagnostics')
    arms={}
    for arm in ARMS:
        phases={}
        for phase in PHASES:
            rows=[r['arms'][arm]['phases'][phase] for r in records]
            phases[phase]=dict(aggregate(rows),heldout={k:mean(r['heldout'][k] for r in rows) for k in ('mse','mae','bias')},
                ranking={k:mean(r['ranking'][k] for r in rows) for k in ('reference_utility','reference_regret','change_from_source_action')},
                retention_probe=aggregate([r['retention_probe'] for r in rows]))
        arms[arm]=dict(mean_game_utility=mean(r['arms'][arm]['mean_game_utility'] for r in records),
            heldout={k:mean(r['arms'][arm]['heldout'][k] for r in records) for k in ('mse','mae','bias')},phases=phases,
            **{k:sum(v[k] for v in phases.values()) for k in ('games','wins','losses','cutoffs','steps')})
    equal_tree(summary['arms'],arms,'all aggregate utilities/errors and phase costs')
    for left,right in PAIRS:
        name=left+'_minus_'+right
        check_contrast(summary['paired_contrasts'][name],[r['arms'][left]['mean_game_utility']-r['arms'][right]['mean_game_utility'] for r in records])
        for phase in PHASES:check_contrast(summary['phase_contrasts'][phase][name],
            [r['arms'][left]['phases'][phase]['mean_game_utility']-r['arms'][right]['phases'][phase]['mean_game_utility'] for r in records])
        for key in ('mse','mae','bias'):check_contrast(summary['heldout_contrasts'][name][key],
            [r['arms'][left]['heldout'][key]-r['arms'][right]['heldout'][key] for r in records],True,key!='bias')
        check_contrast(summary['ranking_contrasts'][name],
            [r['arms'][left]['ranking']['reference_utility']-r['arms'][right]['ranking']['reference_utility'] for r in records])
    def interaction(r,key,phase=None):
        def value(a):
            item=r['arms'][a] if phase is None else r['arms'][a]['phases'][phase]
            return item['mean_game_utility'] if key=='utility' else item['heldout']['mse']
        return (value('BELLMAN_CONDITIONED')-value('BELLMAN_BOARD'))-(value('MC_CONDITIONED')-value('MC_BOARD'))
    check_contrast(summary['factor_interaction']['utility'],[interaction(r,'utility') for r in records])
    check_contrast(summary['factor_interaction']['heldout_mse'],[interaction(r,'mse') for r in records],True)
    for phase in PHASES:check_contrast(summary['factor_interaction']['phases'][phase],[interaction(r,'utility',phase) for r in records])
    for arm in ARMS:
        check_contrast(summary['correction_contrasts'][arm],[r['arms'][arm]['phases']['B']['mean_game_utility']-
            r['arms'][arm]['phases']['B']['a_head_on_B']['mean_game_utility'] for r in records])
        for label,left,right in (('after_B','B','A'),('restoration','A_prime','B'),('final_vs_A','A_prime','A')):
            contrast=summary['retention_contrasts'][arm][label]
            check_contrast(contrast,[r['arms'][arm]['phases'][left]['retention_probe']['mean_game_utility']-
                r['arms'][arm]['phases'][right]['retention_probe']['mean_game_utility'] for r in records])
            direction='POSITIVE_CHANGE_SUPPORTED' if contrast['ci95'][0]>0 else 'NEGATIVE_CHANGE_SUPPORTED' if contrast['ci95'][1]<0 else \
                'ZERO_OBSERVED_CHANGE' if all(v==0 for v in contrast['lifecycle_deltas'].values()) else 'CHANGE_UNCERTAIN'
            require(contrast['direction']==direction,'fixed-A preservation is not assumed from uncertainty')
    cutoffs=sum(g['cutoffs'] for arm in arms.values() for g in arm['phases'].values())
    cutoffs+=sum(r['arms'][a]['phases'][p]['retention_probe']['cutoffs'] for r in records for a in ARMS for p in ('B','A_prime'))
    cutoffs+=sum(r['arms'][a]['phases']['B']['a_head_on_B']['cutoffs'] for r in records for a in ARMS[1:])
    complete=cutoffs==0;primary=summary['paired_contrasts']['BELLMAN_CONDITIONED_minus_FROZEN']
    require(summary['science_cutoffs']==cutoffs and summary['complete_game_endpoints']==complete
        and summary['net_gain_supported']==(complete and primary['ci95'][0]>0)
        and summary['correction_supported']==(complete and summary['correction_contrasts']['BELLMAN_CONDITIONED']['ci95'][0]>0),
        'source diagnostic/MSE substituted for independent control gain')
    require(summary['ranking_cutoffs']==sum(r['ranking'][p]['cutoffs'] for r in records for p in PHASES)
        and summary['ranking_rollouts']==sum(r['ranking'][p]['rollouts'] for r in records for p in PHASES)
        and summary['physical_science_games']==14848 and summary['logical_science_game_references']==17920
        and summary['ranking_anchors']==144 and summary['bootstrap_seed']==29400001 and summary['bootstrap_draws']==20000,
        'complete frozen physical/logical/reference statistical scope')


def audit(directory):
    directory=Path(directory);d=json_file(directory/'summary.json');settings=d['settings']
    require(settings==json_file(directory/'configuration.json'),'frozen configuration changed')
    expected=dict(lifecycles=list(range(16)),parents=4,arms=list(ARMS),phases=[['A',.1],['B',.5],['A_prime',.1]],
        alpha=.0025,fit_fraction=.8,query=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.),max_steps=8192,
        evaluation_games=32,ranking_replicas=32,anchor_quartiles=[.25,.5,.75],seed_evaluation=294900010000,
        seed_ranking=294600010000,bootstrap_seed=29400001,bootstrap_draws=20000,
        scientific_games=14848,logical_scientific_game_references=17920,new_training_raw_tiles=0,
        primary='BELLMAN_CONDITIONED_minus_FROZEN_THREE_PHASE_COMPLETE_GAME_UTILITY',
        bellman='EXPECTED_MAX_CONTROL_GAME_START_FROZEN_OBSERVED_PROBABILITY',
        representation='SOURCE_PLUS_ZERO_RESIDUAL_UNIT_NORMALIZED_BARYCENTRIC_PROBABILITY_BASIS',
        split='PURE_PHASE_COMPLETE_GAMES_CHRONOLOGICAL_80_20_LABEL_HOLDOUT',
        mixed_games='EXCLUDED_WITH_ALL_ACQUISITION_COSTS_RETAINED',
        conditional_A_reference='COPY_RESIDUAL_BANKS_THEN_READ_BOTH_OLD_AND_NEW_AT_CURRENT_B_PROBABILITY')
    for key,value in expected.items():require(settings[key]==value,'registered '+key)
    old=json_file(settings['source_summary']);require(json_file(Path(settings['source_summary']).with_name('audit.json'))['independent_valid'],'previous source carrier audit')
    require(d['source_provenance']==old['source_provenance'] and d['schema']=='acfqp.conditional_bellman.v294'
        and d['status']=='EXPERIMENT_COMPLETE' and d['scientific_gate']=='NOT_A_FORMAL_GATE','immutable source and experiment scope')
    lives=d['by_lifecycle'];require([l['lifecycle'] for l in lives]==list(range(16))
        and all(l['parent']==l['lifecycle']%4 for l in lives),'complete conditional four-source cohort')
    prior={l['lifecycle']:l for l in old['by_lifecycle']};fits,rows=read_canonical(d);records=[]
    for life in lives:
        records.append(check_lifecycle(life,prior[life['lifecycle']],fits));check_head_inventory(life)
    check_summary(d['summary'],records);check_accounting(d,old);a=d['accounting'];s=d['summary']
    return dict(status='PASS',independent_valid=True,lifecycles=16,fixed_source_parents=4,canonical_rows=rows,
        new_training_environment_raw_tiles=0,reused_carrier_raw_tiles=a['reused_carrier_raw_tiles'],
        reused_warmup_raw_tiles=a['reused_warmup_raw_tiles'],economic_training_raw_tiles_per_arm=a['economic_training_raw_tiles_per_arm'],
        physical_science_games=14848,logical_science_game_references=17920,ranking_anchors=144,
        ranking_rollouts=a['physical_ranking_rollouts'],science_cutoffs=s['science_cutoffs'],ranking_cutoffs=s['ranking_cutoffs'],
        processed_training_samples_per_arm=a['processed_training_samples_per_arm'],materializations=a['materialization_count'],
        net_gain_supported=s['net_gain_supported'],correction_supported=s['correction_supported'],
        primary=s['paired_contrasts']['BELLMAN_CONDITIONED_minus_FROZEN'],errors=[],
        limitations='Compact independent accounting and statistical-input audit. No old carrier/world/source-weight replay, '
            'refitting or 20000-draw CI regeneration. Factual target construction and composite arithmetic have finite literal '
            'tests; signed effects are recomputed from all retained game metrics/rollouts. Ranking is finite SOURCE-policy '
            'continuation evidence, not optimal Q. Bellman changes objective and bootstrap. Four old sources are fixed.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True)
    directory=parser.parse_args().input
    try:result=audit(directory)
    except ValueError as error:result=dict(status='FAIL',independent_valid=False,errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False));raise SystemExit(not result['independent_valid'])


if __name__=='__main__':main()
