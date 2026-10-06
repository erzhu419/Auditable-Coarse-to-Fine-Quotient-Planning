#!/usr/bin/env python3
"""Independent compact checks for the unchanged chronological MC replay."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from math import isclose
from pathlib import Path
from statistics import mean


def require(condition,message):
    if not condition:raise ValueError(message)


def close(a,b):
    return isclose(a,b,rel_tol=1e-10,abs_tol=1e-10)


def anchor_positions(nonwinning_count):
    require(nonwinning_count>0,'heldout game requires a nonwinning afterstate')
    return sorted({k*(nonwinning_count-1)//3 for k in range(4)})


def fixed_prefixes(fit_games):
    return [0,(fit_games+3)//4,(fit_games+1)//2,(3*fit_games+3)//4,fit_games]


def factual_targets(scores,status):
    require(status in ('WON','LOST'),'factual complete-game targets require a terminal receipt')
    suffix=4. if status=='WON' else -4.
    values=[]
    for score in reversed(scores):
        values.append(suffix)
        suffix+=score/2048.
    values.reverse()
    return values[:-1] if status=='WON' else values


def panel_metrics(anchors,predictions):
    """Each heldout game has equal weight regardless of its anchor count."""
    require(len(anchors)==len(predictions),'fixed panel prediction count')
    games=defaultdict(list)
    for anchor,prediction in zip(anchors,predictions):
        error=prediction-anchor['target']
        games[anchor['episode']].append(dict(bias=error,mse=error*error,mae=abs(error)))
    return {key:mean(mean(row[key] for row in rows) for rows in games.values())
        for key in ('bias','mse','mae')}


def panel_game_metrics(anchors,predictions):
    require(len(anchors)==len(predictions),'fixed panel prediction count')
    games=defaultdict(list)
    for anchor,prediction in zip(anchors,predictions):
        error=prediction-anchor['target']
        games[anchor['episode']].append(dict(bias=error,mse=error*error,mae=abs(error)))
    return [dict(episode=episode,count=len(rows),
        **{key:mean(row[key] for row in rows) for key in ('bias','mse','mae')})
        for episode,rows in sorted(games.items())]


def h2_reference(action,queries):
    require(action in queries,'H2 recommendation absent from fixed all-action reference')
    query=queries[action]
    require(len(query['validation'])==32,'fixed validation batch size')
    return query['first_score']/2048.+mean(query['validation'])


def positive_run_description(values):
    runs=[];start=None
    for index,value in enumerate(values):
        if value>0 and start is None:start=index
        if value<=0 and start is not None:runs.append([start,index-1]);start=None
    if start is not None:runs.append([start,len(values)-1])
    return dict(first_positive_index=runs[0][0] if runs else None,
        positive_runs=runs,final_positive_run=runs[-1] if runs and runs[-1][1]==len(values)-1 else None)


def compare_metrics(saved,expected,message):
    require(set(saved)==set(expected),message+' fields')
    require(all(close(saved[key],value) for key,value in expected.items()),message)


def h2_board_metrics(row,queries):
    frozen,current=row['frozen_action_values'],row['mc_action_values']
    require(set(frozen)==set(current)==set(queries),'same legal H2/reference actions')
    old_action=min(frozen,key=lambda action:(-frozen[action],action))
    new_action=min(current,key=lambda action:(-current[action],action))
    require(row['frozen_action']==old_action and row['mc_action']==new_action,'H2 argmax/tie direction')
    reference={action:h2_reference(action,queries) for action in queries}
    compare_metrics(row['reference_q'],reference,'fixed validation reference')
    old,new,best=reference[old_action],reference[new_action],max(reference.values())
    return dict(action_disagreement=int(old_action!=new_action),validation_utility_delta=new-old,
        frozen_reference_regret=best-old,mc_reference_regret=best-new,
        predicted_frozen_action_margin=current[old_action]-max(value for action,value in current.items() if action!=old_action))


def read_retained_scores(original):
    """Only canonical factual scores; no board, router or learner replay."""
    scores={life:defaultdict(list) for life in range(16)}
    for parent in original['parent_receipts']:
        with gzip.open(parent['trace_file'],'rt') as stream:
            for line in stream:
                if '"arm":"FROZEN","phase":"A"' not in line[:200]:continue
                row=json.loads(line)
                if row['kind']!='TRAIN':continue
                values=iter(row['scores'])
                for spawn in row['raw_spawns']:
                    if spawn['kind']=='POST_ACTION':scores[row['lifecycle']][spawn['episode']].append(next(values))
    return scores


def json_file(path):
    return json.loads(Path(path).read_text())


def equal_tree(saved,expected,message):
    if isinstance(expected,dict):
        require(set(saved)==set(expected),message+' fields')
        for key,value in expected.items():equal_tree(saved[key],value,message+'.'+key)
    elif isinstance(expected,list):
        require(len(saved)==len(expected),message+' length')
        for actual,value in zip(saved,expected):equal_tree(actual,value,message)
    elif isinstance(expected,float):require(close(saved,expected),message)
    else:require(saved==expected,message)


def check_contrast(saved,values,direction=None):
    require(close(saved['mean'],mean(values)),'signed endpoint mean')
    equal_tree(saved['lifecycle_values'],{str(i):value for i,value in enumerate(values)},'signed life inputs')
    require(saved['negative_equal_positive']==[sum(v<0 for v in values),sum(v==0 for v in values),sum(v>0 for v in values)],
        'signed endpoint inventory')
    groups=[values[p::4] for p in range(4)]
    equal_tree(saved['parent_means'],{str(p):mean(g) for p,g in enumerate(groups)},'fixed parent means')
    require(saved['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS','CI source scope')
    low,high=saved['ci95']
    require(mean(min(g) for g in groups)-1e-10<=low<=high<=mean(max(g) for g in groups)+1e-10,
        'CI possible conditional resampling range')
    if direction:
        losses=values if direction=='negative_is_better' else [-v for v in values]
        require(saved['quality_direction']==direction
            and saved['improved_equal_worse']==[sum(v<0 for v in losses),sum(v==0 for v in losses),sum(v>0 for v in losses)]
            and saved['adverse_lifecycles']==[i for i,v in enumerate(losses) if v>0],'quality direction/adverse lives')
    else:require('quality_direction' not in saved,'unordered endpoint assigned a quality direction')


def sum_counts(rows):
    return dict(sum((Counter(row) for row in rows),Counter()))


def check_dataset(saved,previous):
    require({k:v for k,v in saved.items() if k!='costs'}=={k:v for k,v in previous.items() if k!='costs'},
        'same full retained dataset')
    require({k:v for k,v in saved['costs'].items() if k!='processing_cpu_seconds'}
        =={k:v for k,v in previous['costs'].items() if k!='processing_cpu_seconds'},'same retained acquisition/work costs')
    require(saved['costs']['processing_cpu_seconds']>=0,'actual reconstruction CPU')


def audit(directory):
    directory=Path(directory);d=json_file(directory/'summary.json');settings=d['settings']
    require(settings==json_file(directory/'configuration.json'),'frozen configuration changed')
    require(d['schema']=='acfqp.cumulative_critic.v289' and d['status']=='DIAGNOSTIC_COMPLETE'
        and d['scientific_gate']=='NOT_A_FORMAL_GATE','diagnostic status')
    settings_expected=dict(lifecycles=list(range(16)),parents=4,alpha=.0025,
        fit='ORIGINAL_COMPLETE_GAME_MC_CHRONOLOGY',anchors_per_heldout_game=4,
        anchor_selection='EQUALLY_SPACED_NONWINNING_TIME_INDICES',snapshots='ZERO_AND_EVERY_FIT_GAME_END',
        h2_fractions=[0.,.25,.5,.75,1.],h2_cohort='V288_UNIFORM_A_PREACTION_BOARDS',h2_boards_per_lifecycle=4,
        h2_belief='FIXED_V287_FIT_PREFIX_MEMORY',reference='IMMEDIATE_SCORE_PLUS_V285_VALIDATION_ORACLE_H2_SUFFIX_MEAN',
        primary='FINAL_MINUS_SOURCE_ANCHOR_MSE',bootstrap_draws=20000,bootstrap_seed=28900001,
        new_environment_observations=0)
    for key,value in settings_expected.items():require(settings[key]==value,'registered '+key)
    old=json_file(settings['source_summary']);suffix=json_file(Path(settings['query_trace']).with_name('summary.json'))
    for path in (Path(settings['source_summary']),Path(settings['query_trace']).with_name('summary.json')):
        require(json_file(path.with_name('audit.json'))['independent_valid'],'existing source audit')
    require(d['source_provenance']==old['source_provenance'],'source provenance changed')
    lives=d['by_lifecycle'];old_lives={life['lifecycle']:life for life in old['by_lifecycle']}
    require([life['lifecycle'] for life in lives]==list(range(16))
        and all(life['parent']==life['lifecycle']%4 for life in lives),'complete fixed cohort')
    original=json_file(old['settings']['source_summary'])
    scores=read_retained_scores(original)
    query_boards=defaultdict(dict);panel_counts=Counter()
    with gzip.open(settings['query_trace'],'rt') as stream:
        for line in stream:
            q=json.loads(line);panel_counts['compact_queries_read']+=1
            if q['group']!='uniform':continue
            board=query_boards[q['lifecycle']].setdefault(q['state_id'],dict(board=q['board'],queries={}))
            require(board['board']==q['board'] and q['action'] not in board['queries'],'fixed H2 query inventory')
            board['queries'][q['action']]=q
            panel_counts.update(reference_action_means=1,reused_validation_labels=len(q['validation']))
    panels={};snapshots={};traces=0
    require([p['parent'] for p in d['parent_receipts']]==list(range(4)),'one source parent receipt')
    for parent in d['parent_receipts']:
        require(parent['lifecycle_ids']==list(range(parent['parent'],16,4)),'parent life inventory')
        trace=Path(parent['trace_file']);require(trace.stat().st_size==parent['trace_bytes'],'prediction trace storage')
        traces+=parent['trace_bytes']
        with gzip.open(trace,'rt') as stream:
            for line in stream:
                row=json.loads(line);life=row['lifecycle']
                require(life in parent['lifecycle_ids'],'trace life/source assignment')
                if row['kind']=='PANEL':
                    require(life not in panels,'duplicated panel');panels[life]=row['anchors']
                else:
                    require(row['kind']=='SNAPSHOT','unsupported trace record')
                    key=(life,row['completed_fit_games']);require(key not in snapshots,'duplicated snapshot')
                    snapshots[key]=row
    records=[];total_anchors=total_updates=full_heldout_games=0
    for life in lives:
        lid=life['lifecycle'];ds=life['dataset'];previous=old_lives[lid];n=ds['fit_game_count']
        require(life['fit_game_count']==n,'fit game count');check_dataset(ds,previous['dataset'])
        require(life['estimated_p_four']==previous['evaluation_snapshot']['estimated_p_four'], 'fixed fit-prefix belief')
        anchors=life['anchor_panel']['rows'];require(panels[lid]==anchors,'compact fixed panel changed')
        expected_anchors=[];fit_steps=0;anchor_steps=0;counts=Counter()
        for episode,game in enumerate(ds['games']):
            values=scores[lid][game['episode']]
            require(len(values)==game['steps'] and sum(values)==game['score'],'canonical complete-game scores')
            if episode>=n:
                targets=factual_targets(values,game['status'])
                for index in anchor_positions(len(targets)):
                    expected_anchors.append((episode,anchor_steps+index,targets[index]))
                counts.update(suffix_games=1,suffix_target_assignments=game['steps'],suffix_reward_additions=game['steps'])
                counts['target_buffer_doubles_peak']=max(counts['target_buffer_doubles_peak'],game['steps'])
            else:fit_steps+=game['steps']
            anchor_steps+=game['steps']
        require([(a['episode'],a['step'],a['target']) for a in anchors]==expected_anchors,
            'fixed time anchors or factual after-current-action labels')
        require(all(len(a['afterstate'])==16 and max(a['afterstate'])<11 for a in anchors),'nonwinning anchor boards')
        counts['selected_anchors']=len(anchors)
        require(life['anchor_panel']['counts']==dict(counts),'anchor label work/peak costs')
        total_anchors+=len(anchors)
        replay=life['replay'];old_fit=previous['arms']['EPISODIC_MC']['fit']
        require(replay['method']=='MC' and replay['alpha']==.0025 and replay['initial_updates']==0
            and replay['fitted_games']==n and replay['fitted_steps']==fit_steps
            and replay['trained_afterstates']==old_fit['trained_afterstates'],'same MC fit inventory')
        for key in ('learning_counts','first_update','last_update'):require(replay[key]==old_fit[key],'original MC '+key)
        require({k:v for k,v in replay['target_counts'].items() if k!='target_buffer_doubles_peak'}
            =={k:v for k,v in old_fit['target_counts'].items() if k!='target_buffer_doubles_peak'},'original MC target work')
        require(replay['target_counts']['target_buffer_doubles_peak']>=max(g['steps'] for g in ds['games'][:n]),'fit target buffer')
        require(replay['callback_calls']==n+1,'complete chronological snapshot callbacks')
        require(replay['anchor_scoring_counts']==dict(snapshots=n+1,value_predictions=len(anchors)*(n+1),
            table_lookups=32*len(anchors)*(n+1),prediction_shift_additions=2*len(anchors)*(n+1)),'snapshot physical work')
        require([s['completed_fit_games'] for s in life['snapshots']]==list(range(n+1)),'complete snapshot chronology')
        steps=updates=0;trajectory=[]
        for completed,saved in enumerate(life['snapshots']):
            if completed:
                game=ds['games'][completed-1];steps+=game['steps'];updates+=game['steps']-(game['status']=='WON')
            trace=snapshots.pop((lid,completed))
            require(saved['cumulative_fit_steps']==trace['cumulative_fit_steps']==steps
                and saved['cumulative_updates']==trace['cumulative_updates']==updates,'prefix sample/update inventory')
            predictions=trace['predictions'];metrics=panel_metrics(anchors,predictions)
            compare_metrics(saved['metrics'],metrics,'fixed panel error weighting')
            equal_tree(saved['game_metrics'],panel_game_metrics(anchors,predictions),'per-game fixed panel errors')
            if completed==0:baseline=metrics
            trajectory.append(dict(completed_fit_games=completed,cumulative_updates=updates,cumulative_fit_steps=steps,
                metrics=metrics,delta_from_frozen={key:metrics[key]-baseline[key] for key in metrics}))
        total_updates+=updates
        for arm in ('FROZEN','EPISODIC_MC'):
            saved=life['full_heldout'][arm];expected=previous['arms'][arm]['heldout']
            for key in ('game_metrics','metrics','prediction_counts','target_counts'):
                require(saved[key]==expected[key],'original full heldout '+arm+' '+key)
            full_heldout_games+=len(saved['game_metrics'])
        require(all(life['reproduction'].values()),'producer reproduction receipt')
        boards=query_boards[lid];require(len(boards)==4,'all four uniform H2 boards')
        frozen_rows={row['state_id']:row for row in life['frozen_h2_costs']['rows']}
        require(set(frozen_rows)==set(boards),'frozen H2 cohort')
        require([p['completed_fit_games'] for p in life['h2_probes']]==fixed_prefixes(n),'predeclared H2 prefixes')
        probes=[]
        for probe in life['h2_probes']:
            require(probe['model_p_four']==life['estimated_p_four'],'H2 model p changed by prefix')
            require({r['state_id'] for r in probe['board_rows']}==set(boards)
                and len(probe['board_rows'])==4,'same ordered fixed H2 boards')
            board_metrics=[]
            for row in probe['board_rows']:
                board=boards[row['state_id']];frozen=frozen_rows[row['state_id']]
                require(row['board']==board['board'] and row['frozen_action_values']==frozen['action_values']
                    and row['frozen_action']==frozen['action'],'frozen H2 original-board readout')
                computed=h2_board_metrics(row,board['queries'])
                compare_metrics({key:row[key] for key in computed},computed,'H2 reference/quality direction')
                board_metrics.append(computed)
                if probe['completed_fit_games']==0:
                    require(row['mc_action_values']==row['frozen_action_values'],'zero-prefix source head identity')
            metrics={key:mean(row[key] for row in board_metrics) for key in board_metrics[0]}
            compare_metrics(probe['metrics'],metrics,'H2 equal-board metrics')
            probes.append(dict(completed_fit_games=probe['completed_fit_games'],metrics=metrics))
        run=positive_run_description([point['delta_from_frozen']['mse'] for point in trajectory])
        records.append(dict(lifecycle=lid,parent=lid%4,fit_game_count=n,anchor_trajectory=trajectory,h2_probes=probes,
            first_above_baseline_game=run['first_positive_index'],
            final_above_baseline_run_start_game=run['final_positive_run'][0] if run['final_positive_run'] else None))
    require(not snapshots and set(panels)==set(range(16)),'extra or missing compact snapshots')
    summary=d['summary'];equal_tree(summary['by_lifecycle'],records,'retained signed trajectories')
    require(summary['primary_endpoint']=='FINAL_ANCHOR_MC_MINUS_FROZEN_MSE'
        and summary['bootstrap_draws']==20000 and summary['bootstrap_seed']==28900001
        and summary['estimator']=='ANCHOR_WITHIN_GAME_THEN_HELDOUT_GAME_THEN_LIFECYCLE'
        and summary['h2_reference']=='OLD_ORACLE_H2_CONTINUATION_READOUT_NOT_NEW_POLICY_RETURN','endpoint/scientific scope')
    for key in ('bias','mse','mae'):
        check_contrast(summary['final_anchor_contrasts'][key],
            [r['anchor_trajectory'][-1]['delta_from_frozen'][key] for r in records],
            None if key=='bias' else 'negative_is_better')
    require(summary['primary_final_anchor_mse_delta']==summary['final_anchor_contrasts']['mse'],'primary final endpoint')
    for key in ('validation_utility_delta','action_disagreement'):
        check_contrast(summary['final_h2_diagnostics'][key],[r['h2_probes'][-1]['metrics'][key] for r in records],
            'positive_is_better' if key=='validation_utility_delta' else None)
    for checkpoint,prefix_index in enumerate(range(5)):
        prefixes=[fixed_prefixes(r['fit_game_count'])[prefix_index] for r in records]
        counts={str(r['lifecycle']):prefix for r,prefix in zip(records,prefixes)}
        anchors=[r['anchor_trajectory'][prefix] for r,prefix in zip(records,prefixes)]
        probes=[next(p for p in r['h2_probes'] if p['completed_fit_games']==prefix) for r,prefix in zip(records,prefixes)]
        fraction=checkpoint/4.
        equal_tree(summary['anchor_checkpoints'][checkpoint],dict(fraction=fraction,lifecycle_fit_games=counts,
            metrics={key:mean(point['metrics'][key] for point in anchors) for key in ('bias','mse','mae')},
            delta_from_frozen={key:mean(point['delta_from_frozen'][key] for point in anchors) for key in ('bias','mse','mae')},
            mean_cumulative_updates=mean(point['cumulative_updates'] for point in anchors),
            mean_cumulative_fit_steps=mean(point['cumulative_fit_steps'] for point in anchors)),'fixed anchor checkpoint')
        equal_tree(summary['h2_checkpoints'][checkpoint],dict(fraction=fraction,lifecycle_fit_games=counts,
            metrics={key:mean(point['metrics'][key] for point in probes) for key in probes[0]['metrics']}),'fixed H2 checkpoint')
    account=d['accounting']
    require(account['new_environment_observations']==account['new_evaluation_games']==0
        and account['replay_value_updates']==total_updates,'actual replay/zero environment budget')
    for field,values in (
        ('fit_counts',[l['replay']['learning_counts'] for l in lives]),
        ('anchor_prediction_counts',[l['replay']['anchor_scoring_counts'] for l in lives]),
        ('anchor_label_counts',[{k:v for k,v in l['anchor_panel']['counts'].items() if not k.endswith('_peak')} for l in lives]),
        ('h2_planning_counts',[l['frozen_h2_costs']['counts'] for l in lives]+[p['planning_counts'] for l in lives for p in l['h2_probes']]),
        ('full_heldout_prediction_counts',[score['prediction_counts'] for l in lives for score in l['full_heldout'].values()])):
        require(account[field]==sum_counts(values),'aggregate '+field)
    for name,values in (('fit',[l['replay']['target_counts'] for l in lives]),
        ('full_heldout',[score['target_counts'] for l in lives for score in l['full_heldout'].values()]),
        ('anchor_label',[l['anchor_panel']['counts'] for l in lives])):
        if name!='anchor_label':require(account[name+'_target_counts']==sum_counts(
            [{k:v for k,v in value.items() if k!='target_buffer_doubles_peak'} for value in values]),'target work aggregate')
        require(account[name+'_target_buffer_doubles_peak']==max(v.get('target_buffer_doubles_peak',0) for v in values),
            'buffer peak incorrectly accumulated')
    require(account['private_head_weight_bytes_created']==sum(l['head_setup']['private_weight_bytes'] for l in lives),
        'private critic allocation costs')
    require(account['inherited_retained_actor_acquisition']==old['accounting']['inherited_costs_per_arm']['FROZEN']
        and account['inherited_retained_actor_economic_raw_tiles']==old['accounting']['economic_training_raw_tiles_per_arm']['FROZEN']
        and account['inherited_suffix_costs']==suffix['accounting']['inherited_costs'],'complete historical acquisition ledger')
    require(account['compact_panel_read_counts']==dict(panel_counts) and account['prediction_trace_bytes']==traces,
        'compact read/storage costs')
    require('not additive' in account['historical_scope'],'historical cost duplication scope')
    for key in ('worker_cpu_seconds','compiler_cpu_seconds'):
        require(close(account[key],sum(p['cpu_seconds' if key=='worker_cpu_seconds' else key] for p in d['parent_receipts'])),
            'actual process CPU aggregate')
    return dict(status='PASS',independent_valid=True,lifecycles=16,fixed_source_parents=4,
        fixed_anchors=total_anchors,chronological_game_snapshots=sum(len(l['snapshots']) for l in lives),
        h2_board_readouts=320,full_heldout_scored_games=full_heldout_games,replay_value_updates=total_updates,
        new_environment_observations=0,new_evaluation_games=0,
        primary_final_anchor_mse_delta=summary['primary_final_anchor_mse_delta'],
        final_h2_diagnostics=summary['final_h2_diagnostics'],
        first_above_baseline_games={str(r['lifecycle']):r['first_above_baseline_game'] for r in records},
        final_above_baseline_run_start_games={str(r['lifecycle']):r['final_above_baseline_run_start_game'] for r in records},
        actual_processing_costs={key:account[key] for key in ('fit_counts','fit_target_counts','anchor_prediction_counts',
            'anchor_label_counts','h2_planning_counts','full_heldout_prediction_counts','full_heldout_target_counts',
            'private_head_weight_bytes_created','worker_cpu_seconds','compiler_cpu_seconds','coordinator_cpu_seconds',
            'wall_seconds','prediction_trace_bytes')},
        method='Canonical factual score suffixes, fixed time anchors and chronology, all compact prediction errors, '
            'original whole heldout/fit receipts, fixed H2 argmax/reference directions, equal-game/life signed endpoints and costs.',
        limitations='No source checkpoint reload, board/weight replay, planning recomputation or new observations. '
            'Existing 20000-draw bootstrap not regenerated; inputs, source grouping and interval bounds checked. '
            'H2 reference uses the old ORACLE continuation and is not new-policy return.',errors=[])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True)
    directory=parser.parse_args().input
    try:result=audit(directory)
    except ValueError as error:result=dict(status='FAIL',independent_valid=False,errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False));raise SystemExit(not result['independent_valid'])


if __name__=='__main__':main()
