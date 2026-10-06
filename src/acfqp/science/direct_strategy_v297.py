"""Search stateful executable programs using complete-game rewards only."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import json
from math import sqrt
from pathlib import Path
import random
import resource
from statistics import mean
from time import perf_counter, process_time

from .natural_model_revision_v281 import load_leaf, QUERY, MAX_STEPS

METHODS = ('CEM', 'RANDOM_SEARCH')
ARMS = ('SOURCE',) + METHODS
ZERO = (0., 0., 0., 0.)
ROUNDS, CANDIDATES, REPLICAS, SCIENCE_GAMES = 4, 8, 4, 32


def training_seed(life, round_index, replica):
    return 297200010000+life*1000000+round_index*1000+replica


def proposal_seed(life, round_index):
    return 297300010000+life*1000000+round_index


def science_seed(life, game):
    return 297900010000+life*1000000+game


def learned_probability(source):
    return sum(numerator/denominator for rank,numerator,denominator in
               source['rule']['spawn_distribution'] if rank==2)


def propose(incumbent, mu, sigma, seed):
    """SOURCE and incumbent plus unique paired Gaussian program proposals."""
    candidates = [ZERO]
    incumbent = tuple(incumbent)
    if incumbent != ZERO:
        candidates.append(incumbent)
    rng = random.Random(seed); draws = 0
    while len(candidates)<CANDIDATES:
        candidate = tuple(max(-1., min(1., m+s*rng.gauss(0.,1.))) for m,s in zip(mu,sigma))
        draws += 1
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates, draws


def decide(method, candidates, fitnesses, mu, sigma):
    order = sorted(range(len(candidates)), key=lambda i:(-fitnesses[i],i))
    winner = order[0]; elite = order[:2]
    if method=='CEM':
        center = [mean(candidates[i][j] for i in elite) for j in range(4)]
        spread = [sqrt(mean((candidates[i][j]-center[j])**2 for i in elite)) for j in range(4)]
        new_mu = [.5*a+.5*b for a,b in zip(mu,center)]
        new_sigma = [max(.025,min(.5,.5*a+.5*b)) for a,b in zip(sigma,spread)]
    else:
        new_mu, new_sigma = [0.]*4, [.25]*4
    return dict(winner_index=winner,winner_theta=list(candidates[winner]),elite_indices=elite,
                mean_after=new_mu,sigma_after=new_sigma)


def _merge_counts(evaluations):
    return {kind:dict(sum((Counter(r['counts'][kind]) for r in evaluations),Counter()))
            for kind in ('environment','planning','strategy')}


def _train(engine, life, p, emit):
    states = {m:dict(incumbent=ZERO,mu=[0.]*4,sigma=[.25]*4) for m in METHODS}
    references = {}; rounds = []; logical_ids = {m:[] for m in METHODS}
    for round_index in range(ROUNDS):
        seeds = [training_seed(life,round_index,i) for i in range(REPLICAS)]
        cached = {}; arms = {}
        for method in METHODS:
            state = states[method]
            candidates, draws = propose(state['incumbent'],state['mu'],state['sigma'],
                                        proposal_seed(life,round_index))
            ids = []; fitnesses = []
            for theta in candidates:
                if theta not in cached:
                    receipt_id = f'L{life:02d}-T{len(references):03d}'
                    evaluated = engine.evaluate(theta,p,.1,seeds,max_steps=MAX_STEPS)
                    receipt = dict(evaluated,theta=list(theta),reference_id=receipt_id,
                        model_p_four=p,environment_p_four=.1,round_index=round_index)
                    references[receipt_id] = receipt; cached[theta] = receipt_id
                    emit(dict(kind='TRAIN_EVALUATION',lifecycle=life,**receipt))
                receipt_id = cached[theta]; ids.append(receipt_id)
                fitnesses.append(mean(g['utility'] for g in references[receipt_id]['game_summaries']))
            chosen = decide(method,candidates,fitnesses,state['mu'],state['sigma'])
            arms[method] = dict(candidates=[list(t) for t in candidates],reference_ids=ids,
                fitnesses=fitnesses,incumbent_before=list(state['incumbent']),
                mean_before=list(state['mu']),sigma_before=list(state['sigma']),
                proposal_draw_vectors=draws,**chosen)
            logical_ids[method].extend(ids)
            states[method] = dict(incumbent=tuple(chosen['winner_theta']),
                                 mu=chosen['mean_after'],sigma=chosen['sigma_after'])
        row = dict(round_index=round_index,training_seeds=seeds,
                   proposal_seed=proposal_seed(life,round_index),arms=arms)
        rounds.append(row); emit(dict(kind='SEARCH_ROUND',lifecycle=life,**row))
    costs = {m:dict(game_references=ROUNDS*CANDIDATES*REPLICAS,
        cutoff_games=sum(g['status']=='CUTOFF' for i in logical_ids[m] for g in references[i]['game_summaries']),
        counts=_merge_counts([references[i] for i in logical_ids[m]]),
        evaluation_cpu_seconds=sum(references[i]['cpu_seconds'] for i in logical_ids[m]),
        proposal_draw_vectors=sum(r['arms'][m]['proposal_draw_vectors'] for r in rounds),
        program_fitness_evaluations=ROUNDS*CANDIDATES,
        incumbent_parameter_assignments=ROUNDS*4,
        proposal_distribution_parameter_updates=ROUNDS*8 if m=='CEM' else 0) for m in METHODS}
    return states,rounds,references,costs


def _run_parent(source, output):
    from .native_strategy_v297 import NativeStrategy
    started,cpu = perf_counter(),process_time(); child=resource.getrusage(resource.RUSAGE_CHILDREN)
    output=Path(output); parent=source['parent']; runtime=output/'runtime'/f'parent_{parent}'
    runtime.mkdir(parents=True,exist_ok=True)
    leaf,setup=load_leaf(source,runtime); engine=NativeStrategy(leaf,runtime)
    p=learned_probability(source); lives=[]; trace=output/f'parent_{parent}_records.jsonl.gz'
    with gzip.open(trace,'xt',encoding='utf-8') as stream:
        def emit(row):
            stream.write(json.dumps(row,separators=(',',':'),allow_nan=False)+'\n')
        for life in range(parent,16,4):
            states,rounds,training,costs=_train(engine,life,p,emit)
            cached={}; science={}; arms={}
            for method in ARMS:
                theta=ZERO if method=='SOURCE' else states[method]['incumbent']
                if theta not in cached:
                    receipt_id=f'L{life:02d}-S{len(science)}'
                    receipt=dict(engine.evaluate(theta,p,.1,
                        [science_seed(life,i) for i in range(SCIENCE_GAMES)],max_steps=MAX_STEPS),
                        theta=list(theta),reference_id=receipt_id,model_p_four=p,environment_p_four=.1)
                    science[receipt_id]=receipt; cached[theta]=receipt_id
                    emit(dict(kind='SCIENCE_EVALUATION',lifecycle=life,**receipt))
                arms[method]=dict(science[cached[theta]],training=costs[method] if method in METHODS
                                  else dict(game_references=0,cutoff_games=0))
            row=dict(lifecycle=life,parent=parent,model_p_four=p,search_rounds=rounds,
                     training_references=training,science_references=science,training_costs_per_arm=costs,arms=arms)
            lives.append(row); emit(dict(kind='LIFECYCLE_COMPLETE',lifecycle=life,parent=parent,
                final_thetas={m:a['theta'] for m,a in arms.items()})); stream.flush()
            print(json.dumps(dict(event='direct_strategy_lifecycle_complete',lifecycle=life,parent=parent)),flush=True)
    if leaf.updates!=0 or leaf.weights.flags.writeable:
        raise ValueError('Direct program search must not update SOURCE values')
    after=resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent,lifecycles=lives,source_setup=setup,
        native_setup_counts=dict(engine.setup_counts),native_setup_seconds=engine.setup_seconds,
        source_updates_after=leaf.updates,source_weights_readonly=not leaf.weights.flags.writeable,
        trace_file=str(trace.resolve()),trace_bytes=trace.stat().st_size,
        worker_cpu_seconds=process_time()-cpu,wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=after.ru_utime+after.ru_stime-child.ru_utime-child.ru_stime)


def configuration(source_summary,finite_test_passes):
    return dict(schema='acfqp.direct_strategy_freeze.v297',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/DIRECT_STRATEGY_V297.md'),
        source_summary=str(Path(source_summary).resolve()),lifecycles=list(range(16)),parents=4,
        arms=ARMS,rounds=ROUNDS,candidates=CANDIDATES,replicas=REPLICAS,science_games=SCIENCE_GAMES,
        theta_bounds=[-1.,1.],initial_mean=[0.]*4,initial_sigma=[.25]*4,elite_count=2,
        sigma_bounds=[.025,.5],smoothing=.5,model_probability='SOURCE_LEARNED_SPAWN_DISTRIBUTION',
        environment_p_four=.1,query=QUERY,max_steps=MAX_STEPS,
        training_seed_base=297200010000,proposal_seed_base=297300010000,science_seed_base=297900010000,
        bootstrap_seed=29700001,bootstrap_draws=20000,primary='CEM_minus_SOURCE',
        finite_test_passes=finite_test_passes)


def build_accounting(lives,parents,inherited,cpu,wall):
    training=[r for l in lives for r in l['training_references'].values()]
    science=[r for l in lives for r in l['science_references'].values()]
    logical={m:_merge_counts([dict(counts=l['training_costs_per_arm'][m]['counts']) for l in lives]) for m in METHODS}
    return dict(new_source_value_updates=0,physical_training_evaluations=len(training),
        physical_training_games=sum(len(r['game_summaries']) for r in training),
        physical_science_evaluations=len(science),physical_science_games=sum(len(r['game_summaries']) for r in science),
        logical_training_games_per_arm={m:16*ROUNDS*CANDIDATES*REPLICAS for m in METHODS},
        logical_science_games_per_arm={m:16*SCIENCE_GAMES for m in ARMS},
        physical_training_counts=_merge_counts(training),physical_science_counts=_merge_counts(science),
        logical_training_counts_per_arm=logical,
        training_cutoffs=sum(g['status']=='CUTOFF' for r in training for g in r['game_summaries']),
        science_cutoffs=sum(g['status']=='CUTOFF' for r in science for g in r['game_summaries']),
        inherited_source_costs=inherited,
        economic_training_raw_tiles_per_arm={m:inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+
            (logical[m]['environment'].get('raw_tile_productions',0) if m in METHODS else 0) for m in ARMS},
        source_setup_cpu_seconds=sum(p['source_setup']['cpu_seconds'] for p in parents),
        native_setup_seconds=sum(p['native_setup_seconds'] for p in parents),
        worker_cpu_seconds=sum(p['worker_cpu_seconds'] for p in parents),
        compiler_cpu_seconds=sum(p['compiler_cpu_seconds'] for p in parents),
        coordinator_cpu_seconds=cpu,wall_seconds=wall,
        canonical_trace_bytes=sum(p['trace_bytes'] for p in parents),
        cost_scope='Physical identical-program/seed receipts are shared. Both search arms have the same '
            'candidate and complete-game slot budget; actual raw observations and CPU are not matched. '
            'SOURCE pays no new search. Source training and learned dynamics are inherited once; '
            'old carrier, V296 discovery and validation are unused development cost, not training inputs.')


def run(source_summary,output,finite_test_passes):
    from .direct_strategy_analysis_v297 import analyze
    started,cpu=perf_counter(),process_time(); output=Path(output); output.mkdir(parents=True,exist_ok=True)
    if any((output/n).exists() for n in ('configuration.json','summary.json')):
        raise FileExistsError('V297 frozen configuration or results already exist')
    old=json.loads(Path(source_summary).read_text()); provenance=deepcopy(old['source_provenance'])
    settings=configuration(source_summary,finite_test_passes)
    (output/'configuration.json').write_text(json.dumps(settings,indent=2)+'\n')
    parents=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(_run_parent,source,output) for source in provenance['parents']]
        for job in as_completed(jobs):parents.append(job.result())
    parents.sort(key=lambda p:p['parent'])
    lives=sorted([l for p in parents for l in p['lifecycles']],key=lambda l:l['lifecycle'])
    inherited={k:deepcopy(v) for k,v in old['accounting']['inherited_costs_per_arm']['FROZEN'].items()}
    summary=analyze(lives)
    result=dict(schema='acfqp.direct_strategy.v297',status='EXPERIMENT_COMPLETE',settings=settings,
        source_provenance=provenance,by_lifecycle=lives,
        parent_receipts=[{k:v for k,v in p.items() if k!='lifecycles'} for p in parents],summary=summary,
        accounting=build_accounting(lives,parents,inherited,process_time()-cpu,perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(event='direct_strategy_complete',primary=summary['paired_contrasts']['CEM_minus_SOURCE'])),flush=True)
    return result
