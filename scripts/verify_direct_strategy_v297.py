#!/usr/bin/env python3
"""Independent direct-program search, terminal reward and physical cost audit."""
import argparse
from collections import Counter
import gzip
import json
from math import sqrt
from pathlib import Path
import random
from statistics import mean

from verify_cumulative_critic_v289 import close, equal_tree, json_file, require
from verify_conditional_bellman_v294 import add_counts, check_contrast
from verify_shadow_deployment_v293 import check_games

ARMS=('SOURCE','CEM','RANDOM_SEARCH')
METHODS=ARMS[1:]
PAIRS=(('CEM','SOURCE'),('CEM','RANDOM_SEARCH'),('RANDOM_SEARCH','SOURCE'))
ZERO=[0.,0.,0.,0.]


def training_seed(life,round_index,replica):return 297200010000+life*1000000+round_index*1000+replica
def proposal_seed(life,round_index):return 297300010000+life*1000000+round_index
def science_seed(life,game):return 297900010000+life*1000000+game


def proposals(incumbent,mu,sigma,seed):
    candidates=[tuple(ZERO)]
    if list(incumbent)!=ZERO:candidates.append(tuple(incumbent))
    rng=random.Random(seed);draws=0
    while len(candidates)<8:
        candidate=tuple(max(-1.,min(1.,m+s*rng.gauss(0.,1.))) for m,s in zip(mu,sigma));draws+=1
        if candidate not in candidates:candidates.append(candidate)
    return [list(t) for t in candidates],draws


def decision(method,candidates,fitnesses,mu,sigma):
    ranked=sorted(range(8),key=lambda i:(-fitnesses[i],i));elite=ranked[:2]
    if method=='CEM':
        center=[mean(candidates[i][j] for i in elite) for j in range(4)]
        spread=[sqrt(mean((candidates[i][j]-center[j])**2 for i in elite)) for j in range(4)]
        updated_mu=[.5*a+.5*b for a,b in zip(mu,center)]
        updated_sigma=[max(.025,min(.5,.5*a+.5*b)) for a,b in zip(sigma,spread)]
    else:updated_mu,updated_sigma=[0.]*4,[.25]*4
    return dict(winner_index=ranked[0],winner_theta=candidates[ranked[0]],elite_indices=elite,
        mean_after=updated_mu,sigma_after=updated_sigma)


def check_batch(receipt,seeds,p,theta):
    require(receipt['theta']==list(theta) and receipt['model_p_four']==p and receipt['environment_p_four']==.1,
        'frozen program and SOURCE learned probability; ground law is execution only')
    result=check_games(receipt['game_summaries'],seeds,receipt['counts']);zero=list(theta)==ZERO
    for game in receipt['game_summaries']:
        c=Counter(game['strategy_counts']);steps=game['steps']
        require(c['active_choices']+c['source_fallback_choices']==steps and c['action_changes']<=c['active_choices'],
            'actual direct-policy and fallback action selections')
        if zero:
            require(c==Counter(zero_source_games=1,source_fallback_choices=steps),'zero program must be exact original SOURCE without extra features')
        else:
            entries,exits,active,features=(c[k] for k in ('mode_entries','mode_exits','active_choices','feature_evaluations'))
            require(c['zero_source_games']==0 and c['game_memory_resets']==1 and c['mode_guard_checks']==steps
                and entries>=1 and entries-exits in (0,1),'game-local mode and reset accounting')
            require(active<=features<=4*active and c['feature_cell_reads']==c['feature_distance_evaluations']==16*features
                and c['feature_normalization_divisions']==3*features
                and c['dot_product_multiplications']==c['dot_product_additions']==4*features
                and c['strategy_score_additions']==features,'real legal-action feature and score work')
            require(c['corner_rank_checks']==16*entries and c['corner_distance_evaluations']==4*entries
                and c['strategy_memory_writes']==3+3*(entries+exits)+active,'actual locked corner/previous BUILD action state writes')
    require(Counter(receipt['counts']['strategy'])==sum((Counter(g['strategy_counts']) for g in receipt['game_summaries']),Counter()),
        'batch strategy counts are sums of actual games')
    return result


def reconstruct_search(life):
    """Only training receipts enter proposal/ranking arithmetic; science is excluded."""
    lid=life['lifecycle'];references=life['training_references'];states={m:dict(incumbent=list(ZERO),mu=[0.]*4,sigma=[.25]*4) for m in METHODS}
    logical={m:[] for m in METHODS};used={};require(len(life['search_rounds'])==4,'four frozen search rounds')
    for round_index,row in enumerate(life['search_rounds']):
        seeds=[training_seed(lid,round_index,i) for i in range(4)]
        require(row['round_index']==round_index and row['training_seeds']==seeds
            and row['proposal_seed']==proposal_seed(lid,round_index),'fresh training/proposal family and round order')
        cache={}
        for method in METHODS:
            state=states[method];detail=row['arms'][method]
            require(detail['incumbent_before']==state['incumbent'] and detail['mean_before']==state['mu']
                and detail['sigma_before']==state['sigma'],'literal preceding search state, not a science or older-round winner')
            candidates,draws=proposals(state['incumbent'],state['mu'],state['sigma'],row['proposal_seed'])
            require(detail['candidates']==candidates and detail['proposal_draw_vectors']==draws,
                'paired Gaussian/clipping/uniqueness proposals exactly reconstructed')
            fitnesses=[];ids=[]
            for theta in candidates:
                key=tuple(theta)
                if key not in cache:
                    ref_id=f'L{lid:02d}-T{len(used):03d}';require(ref_id in references,'physical candidate batch absent')
                    receipt=references[ref_id]
                    require(receipt['reference_id']==ref_id and receipt['theta']==theta and receipt['round_index']==round_index
                        and [g['seed'] for g in receipt['game_summaries']]==seeds,
                        'exact program and four-game seed bundle for each shared physical batch')
                    cache[key]=ref_id;used[ref_id]=receipt
                ref_id=cache[key];ids.append(ref_id)
                fitnesses.append(mean(g['utility'] for g in references[ref_id]['game_summaries']))
            require(detail['reference_ids']==ids and detail['fitnesses']==fitnesses,
                'training utility alone ranks candidates; repeated programs share their batch')
            chosen=decision(method,candidates,fitnesses,state['mu'],state['sigma'])
            for key,value in chosen.items():require(detail[key]==value,'literal top-two/population-spread update '+key)
            states[method]=dict(incumbent=chosen['winner_theta'],mu=chosen['mean_after'],sigma=chosen['sigma_after'])
            logical[method].extend(ids)
    require(used==references,'every physical training batch is used once in the complete search inventory')
    return states,logical


def merge_counts(receipts):
    return {kind:dict(sum((Counter(r['counts'][kind]) for r in receipts),Counter())) for kind in ('environment','planning','strategy')}


def check_training_costs(life,logical):
    for method in METHODS:
        refs=[life['training_references'][i] for i in logical[method]]
        expected=dict(game_references=sum(len(r['game_summaries']) for r in refs),
            cutoff_games=sum(g['status']=='CUTOFF' for r in refs for g in r['game_summaries']),counts=merge_counts(refs),
            evaluation_cpu_seconds=sum(r['cpu_seconds'] for r in refs),
            proposal_draw_vectors=sum(r['arms'][method]['proposal_draw_vectors'] for r in life['search_rounds']),
            program_fitness_evaluations=32,incumbent_parameter_assignments=16,
            proposal_distribution_parameter_updates=32 if method=='CEM' else 0)
        require(expected['game_references']==128,'same candidate/game slot budget for both search methods')
        equal_tree(life['training_costs_per_arm'][method],expected,'complete logical training cost')
        require(life['arms'][method]['training']==life['training_costs_per_arm'][method],'arm training accounting differs')
    require(life['arms']['SOURCE']['training']==dict(game_references=0,cutoff_games=0),'SOURCE has no new search or policy learning')


def check_lifecycle(life,p):
    lid=life['lifecycle'];require(life['model_p_four']==p,'planning probability must come from source fitted distribution')
    states,logical=reconstruct_search(life);check_training_costs(life,logical)
    for receipt in life['training_references'].values():
        check_batch(receipt,[training_seed(lid,receipt['round_index'],i) for i in range(4)],p,receipt['theta'])
    cache={};used={};arms={}
    for method in ARMS:
        theta=ZERO if method=='SOURCE' else states[method]['incumbent'];key=tuple(theta)
        if key not in cache:
            rid=f'L{lid:02d}-S{len(used)}';require(rid in life['science_references'],'frozen final actor science batch absent')
            receipt=life['science_references'][rid];require(receipt['reference_id']==rid,'actual science batch identity')
            used[rid]=receipt;cache[key]=rid
        row=life['arms'][method];receipt=used[cache[key]]
        require({k:v for k,v in row.items() if k!='training'}==receipt and row['theta']==theta,
            'science must use final round-four actor and shared exact native receipt')
        result=check_batch(receipt,[science_seed(lid,i) for i in range(32)],p,theta)
        arms[method]=dict({k:result[k] for k in ('games','mean_game_utility','wins','losses','cutoffs','steps')},
            theta=theta,model_p_four=p,training_game_references=row['training']['game_references'],
            training_cutoff_references=row['training']['cutoff_games'])
    require(used==life['science_references'],'no extra science samples or duplicate shared actor batches')
    return dict(lifecycle=lid,parent=life['parent'],arms=arms,unique_science_actors=len(used),
        physical_science_games=32*len(used),logical_science_game_references=96)


def read_canonical(d):
    lives={l['lifecycle']:l for l in d['by_lifecycle']};rows=0
    for parent in d['parent_receipts']:
        pid=parent['parent'];expected_lives=list(range(pid,16,4));seen_refs=set();seen_rounds=set();complete=set()
        path=Path(parent['trace_file']);require(path.stat().st_size==parent['trace_bytes'],'actual canonical gzip storage')
        with gzip.open(path,'rt') as stream:
            for line in stream:
                row=json.loads(line);rows+=1;lid=row['lifecycle'];life=lives[lid]
                require(lid in expected_lives and lid not in complete,'canonical source/life identity or post-completion observation')
                kind=row['kind']
                if kind in ('TRAIN_EVALUATION','SCIENCE_EVALUATION'):
                    science=kind=='SCIENCE_EVALUATION';rid=row['reference_id'];key=(lid,rid)
                    require(key not in seen_refs,'same native batch was emitted twice');seen_refs.add(key)
                    expected=life['science_references' if science else 'training_references'][rid]
                    require({k:v for k,v in row.items() if k not in ('kind','lifecycle')}==expected,'canonical native receipt differs from summary')
                    if science:require(all((lid,r) in seen_rounds for r in range(4)),'science leaked before final parameter selection')
                elif kind=='SEARCH_ROUND':
                    ri=row['round_index'];require((lid,ri) not in seen_rounds and all((lid,r) in seen_rounds for r in range(ri)),
                        'causal complete search round order')
                    require({k:v for k,v in row.items() if k not in ('kind','lifecycle')}==life['search_rounds'][ri],
                        'actual search round metadata differs from summary')
                    require(all((lid,rid) in seen_refs for detail in row['arms'].values() for rid in detail['reference_ids']),
                        'candidate scores preceded their actual training execution')
                    seen_rounds.add((lid,ri))
                elif kind=='LIFECYCLE_COMPLETE':
                    require(row['parent']==pid and row['final_thetas']=={m:a['theta'] for m,a in life['arms'].items()}
                        and all((lid,r) in seen_rounds for r in range(4))
                        and all((lid,rid) in seen_refs for rid in life['training_references']|life['science_references']),
                        'life completed without all frozen search/science results')
                    complete.add(lid)
                else:raise ValueError('unexpected V297 record '+kind)
        require(complete==set(expected_lives) and len(seen_rounds)==16
            and len(seen_refs)==sum(len(lives[l]['training_references'])+len(lives[l]['science_references']) for l in expected_lives),
            'all physical batches and sixteen source-specific rounds retained')
    return rows


def check_summary(summary,records):
    equal_tree(summary['by_lifecycle'],records,'independent equal-game/whole-life actor outcomes')
    arms={m:dict(mean_game_utility=mean(r['arms'][m]['mean_game_utility'] for r in records),
        **{k:sum(r['arms'][m][k] for r in records) for k in ('games','wins','losses','cutoffs','steps',
            'training_game_references','training_cutoff_references')}) for m in ARMS}
    equal_tree(summary['arms'],arms,'all signed actor outcomes and logical training budgets')
    for left,right in PAIRS:check_contrast(summary['paired_contrasts'][left+'_minus_'+right],
        [r['arms'][left]['mean_game_utility']-r['arms'][right]['mean_game_utility'] for r in records])
    training=sum(a['training_cutoff_references'] for a in arms.values())
    physical=sum(r['physical_science_games'] for r in records)
    cutoffs=0
    for record in records:
        seen=set()
        for method in ARMS:
            theta=tuple(record['arms'][method]['theta'])
            if theta not in seen:cutoffs+=record['arms'][method]['cutoffs'];seen.add(theta)
    complete=training+cutoffs==0
    require(summary['complete_natural_games']==complete and summary['training_cutoff_references']==training
        and summary['physical_science_cutoffs']==cutoffs and summary['physical_science_games']==physical
        and summary['logical_science_game_references']==1536 and summary['training_game_references_per_search_arm']==2048,
        'physical shared evaluations versus complete logical candidate/science slots')
    require(summary['stable_task_policy_gain_supported']==(complete and summary['paired_contrasts']['CEM_minus_SOURCE']['ci95'][0]>0)
        and summary['optimizer_contribution_supported']==(complete and summary['paired_contrasts']['CEM_minus_RANDOM_SEARCH']['ci95'][0]>0),
        'training maxima or optimizer comparison substituted for independent primary benefit')
    require(summary['primary_contrast']=='CEM_minus_SOURCE' and summary['bootstrap_seed']==29700001
        and summary['bootstrap_draws']==20000 and summary['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
        and summary['estimator']=='EQUAL_SCIENCE_GAMES_THEN_LIFECYCLES','stable-A fixed-parent whole-life statistical scope')


def check_accounting(d,old):
    lives=d['by_lifecycle'];parents=d['parent_receipts'];a=d['accounting']
    train=[r for l in lives for r in l['training_references'].values()]
    science=[r for l in lives for r in l['science_references'].values()]
    inherited=old['accounting']['inherited_costs_per_arm']['FROZEN']
    logical={m:merge_counts([dict(counts=l['training_costs_per_arm'][m]['counts']) for l in lives]) for m in METHODS}
    expected=dict(new_source_value_updates=0,physical_training_evaluations=len(train),
        physical_training_games=sum(len(r['game_summaries']) for r in train),
        physical_science_evaluations=len(science),physical_science_games=sum(len(r['game_summaries']) for r in science),
        logical_training_games_per_arm=dict.fromkeys(METHODS,2048),logical_science_games_per_arm=dict.fromkeys(ARMS,512),
        physical_training_counts=merge_counts(train),physical_science_counts=merge_counts(science),logical_training_counts_per_arm=logical,
        training_cutoffs=sum(g['status']=='CUTOFF' for r in train for g in r['game_summaries']),
        science_cutoffs=sum(g['status']=='CUTOFF' for r in science for g in r['game_summaries']),inherited_source_costs=inherited,
        economic_training_raw_tiles_per_arm={m:inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+
            (logical[m]['environment']['raw_tile_productions'] if m in METHODS else 0) for m in ARMS},
        source_setup_cpu_seconds=sum(p['source_setup']['cpu_seconds'] for p in parents),
        native_setup_seconds=sum(p['native_setup_seconds'] for p in parents),
        worker_cpu_seconds=sum(p['worker_cpu_seconds'] for p in parents),compiler_cpu_seconds=sum(p['compiler_cpu_seconds'] for p in parents),
        canonical_trace_bytes=sum(p['trace_bytes'] for p in parents))
    for key,value in expected.items():equal_tree(a[key],value,'all physical/shared/logical direct strategy costs '+key)
    require(a['coordinator_cpu_seconds']>=0 and a['wall_seconds']>0,'actual run wall/CPU scope')
    for p in parents:
        setup=p['source_setup'];require(setup['new_leaf_updates']==p['source_updates_after']==0 and p['source_weights_readonly']
            and setup['checkpoint_loads']==1 and setup['leaf_weight_bytes']==8*4*11**6
            and setup['cpu_seconds']>=0 and setup['wall_seconds']>=0,'actual unchanged source setup and immutable value parameters')
    return dict(source_setup_counts=add_counts(p['source_setup']['setup_counts'] for p in parents),
        native_setup_counts=add_counts(p['native_setup_counts'] for p in parents),
        physical_training_evaluation_cpu_seconds=sum(r['cpu_seconds'] for r in train),
        physical_science_evaluation_cpu_seconds=sum(r['cpu_seconds'] for r in science))


def audit(directory):
    directory=Path(directory);d=json_file(directory/'summary.json');settings=d['settings']
    require(settings==json_file(directory/'configuration.json'),'frozen configuration changed')
    expected=dict(lifecycles=list(range(16)),parents=4,arms=list(ARMS),rounds=4,candidates=8,replicas=4,science_games=32,
        theta_bounds=[-1.,1.],initial_mean=[0.]*4,initial_sigma=[.25]*4,elite_count=2,
        sigma_bounds=[.025,.5],smoothing=.5,model_probability='SOURCE_LEARNED_SPAWN_DISTRIBUTION',
        environment_p_four=.1,query=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.),max_steps=8192,
        training_seed_base=297200010000,proposal_seed_base=297300010000,science_seed_base=297900010000,
        bootstrap_seed=29700001,bootstrap_draws=20000,primary='CEM_minus_SOURCE')
    for key,value in expected.items():require(settings[key]==value,'registered '+key)
    source_path=Path(settings['source_summary']);old=json_file(source_path)
    require(json_file(source_path.with_name('audit.json'))['independent_valid'],'retained frozen source evidence')
    require(d['schema']=='acfqp.direct_strategy.v297' and d['status']=='EXPERIMENT_COMPLETE'
        and d['source_provenance']==old['source_provenance'],'same four frozen sources and direct stable-A experiment scope')
    lives=d['by_lifecycle'];require([l['lifecycle'] for l in lives]==list(range(16))
        and all(l['parent']==l['lifecycle']%4 for l in lives) and [p['parent'] for p in d['parent_receipts']]==list(range(4)),
        'sixteen whole lives under four fixed source parents')
    probabilities={s['parent']:sum(numerator/denominator for rank,numerator,denominator in s['rule']['spawn_distribution'] if rank==2)
        for s in d['source_provenance']['parents']}
    rows=read_canonical(d);records=[check_lifecycle(life,probabilities[life['parent']]) for life in lives]
    check_summary(d['summary'],records);setup=check_accounting(d,old);s=d['summary'];a=d['accounting']
    return dict(status='PASS',independent_valid=True,lifecycles=16,fixed_source_parents=4,canonical_rows=rows,
        search_rounds=64,logical_training_games_per_search_arm=2048,logical_science_games_per_arm=512,
        physical_training_games=a['physical_training_games'],physical_science_games=a['physical_science_games'],
        training_raw_tiles=a['physical_training_counts']['environment']['raw_tile_productions'],
        science_raw_tiles=a['physical_science_counts']['environment']['raw_tile_productions'],
        training_cutoffs=a['training_cutoffs'],science_cutoffs=a['science_cutoffs'],new_source_value_updates=0,
        source_model_probabilities=probabilities,economic_training_raw_tiles_per_arm=a['economic_training_raw_tiles_per_arm'],
        stable_task_policy_gain_supported=s['stable_task_policy_gain_supported'],optimizer_contribution_supported=s['optimizer_contribution_supported'],
        primary=s['paired_contrasts']['CEM_minus_SOURCE'],**setup,canonical_trace_bytes=a['canonical_trace_bytes'],errors=[],
        limitations='Independent literal Gaussian/CEM/ranking reconstruction, canonical execution, terminal/utility, signed mean '
            'and physical/logical cost audit. No source-weight/world replay, additional games, value fitting, or 20000-draw '
            'CI regeneration. Setup and evaluator CPU subscopes are already included in worker CPU. Stable-A independent '
            'program utility is separate from optimizer contribution, continual learning or a persistent strategy library; four sources are fixed.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True)
    directory=parser.parse_args().input
    try:result=audit(directory)
    except ValueError as error:result=dict(status='FAIL',independent_valid=False,errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False));raise SystemExit(not result['independent_valid'])


if __name__=='__main__':main()
