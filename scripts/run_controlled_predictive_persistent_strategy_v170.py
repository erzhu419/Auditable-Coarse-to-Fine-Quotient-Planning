"""Learn persistent two-node strategies with paid, full-episode consequences."""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import importlib
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import run_controlled_predictive_program_consolidation_v161 as prior
from acfqp.science.controlled_predictive_persistent_strategy_v170 import (
    source_candidates, mutate, episode_seed, run_episode, choose_parents, summarize_eval)
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics

SOURCE = ROOT/'reports/controlled_predictive_joint_feedback_generation_v169'
OUTPUT = ROOT/'reports/controlled_predictive_persistent_strategy_v170'
BASE, MAX_STEPS = 17000000000, 8192
LIVES = tuple(range(4))
read, save, append = prior.read, prior.save, prior.append


def source_seed(life,replica):
    return BASE+10000000+life*1000000+replica


def settings():
    return dict(lifecycles=list(LIVES),queries=['risk1'],source_replicas=4,source_games=16,
        control_nodes=2,initial_node=0,generations=2,beam=2,candidate_slots=54,
        generation_episodes_per_history=2,final_episodes_per_history=4,eval_episodes_per_history=32,
        generation_games=5232,final_games=240,evaluation_games=384,controlled_games=5856,total_games=5872,
        maximum_environment_transitions=48103424,max_steps=MAX_STEPS,p_four=.1,workers=4,
        version_base=BASE,new_parameter_updates=0,execution_unit='complete episode from two initial random tiles',
        grammar='two control nodes, each current-board D4-frame merge probe, true/false direct action or own-H2 call and true/false next-node0/1',
        source='all current predecision source boards/actions in other three histories; four probes; conditional action modes; top two fit-count probes; empty branch H2',
        initialization='source-modal two-node program and exact-H2 action-leaf incumbent; same source probes; true edge to other node and false edge to self',
        mutation='parents first, then parent/node/field probe,true_action,false_action,true_next,false_next; action alternatives DOWN/LEFT/RIGHT/UP then H2; next0/1; all54slots costed',
        runtime='reobserve current board every decision; execute one action or H2 call, advance graph even after same-step illegal-action H2 fallback; keep controller active',
        ablation='same-candidate LATCHED remembers first predicate per node but still computes/pays current probe each decision; no independent control selection',
        acquisition='physically run COND/LATCHED complete episodes for every candidate and shared H2 on other three histories; candidate/mode excluded from environment seed',
        fitness='actual terminal reward/failure/success vector; COND whole-episode utility; equal episodes/history then three TRAIN histories; no off-policy vector composition',
        selection='two distinct programs for G1/G2, one FINAL; highest complete COND utility, lexical program then first slot; retain negative winners',
        final='two parents on four fresh episodes/history; freeze four programs before EVAL, matched LATCHED uses same selected program',
        primary='COND-LATCHED risk1 whole-episode utility; progression also requires COND-H2 conditional CI95 lower bound>0',
        uncertainty='paired whole-episode CI95;32new games/history then four fixed existing histories; conditional on frozen teachers/programs; overlapping crossfold TRAIN',
        incomplete='source cutoff retains observed labels; missing source roster/parents or any missing,duplicate,cutoff,null,mismatched TRAIN game stops downstream; no replacements; EVAL cutoff blocks affected statistics',
        bank='both-query SINGLE teachers unchanged; risk8 loads/setup counted with zero decisions',
        costs='source,COND,LATCHED,sharedH2,per-decision observation,graph,teacher,fallback,selection,test and inherited costs retained; no efficiency claim',
        frozen_policy='no outcome-dependent extra generations,graph capacity,seeds,games,horizon,caller promotion or U006')


def extract_source():
    run,analysis,capsule=(read(SOURCE/name) for name in ('run.json','analysis.json','source_capsule.json'))
    if not(run['status']=='complete' and analysis['valid'] and analysis['primary_complete']):
        raise ValueError('audited V169 completion required')
    refs=deepcopy(capsule['cost_refs'])+[dict(path=str(SOURCE/'analysis.json'),fields=['costs'])]
    refs += [dict(path=str(ROOT/f'reports/v169_runtime_tmp/{name}_checks.json'),fields=['attempts'])
             for name in ('core','runner','analyzer','stage')]
    return dict(schema='acfqp.persistent_strategy.v170.source',snapshots=deepcopy(capsule['snapshots']),
        source_run_ref=str(SOURCE/'run.json'),source_analysis_ref=str(SOURCE/'analysis.json'),
        inherited_v169_environment_samples=analysis['costs']['new_environment_samples'],cost_refs=refs,
        this_stage_test_refs=[str(ROOT/f'reports/v170_runtime_tmp/{name}_checks.json') for name in ('core','runner','analyzer')])


def source_lifecycle(source,phase,directory):
    started=perf_counter();life=source['life'];folder=directory/'source'/f'life_{life}';folder.mkdir(parents=True)
    bank,parents,leaves,records=prior.teachers(source,folder)
    environment,policy,statuses=Counter(),Counter(),Counter();trace=folder/'source_games.jsonl.gz'
    with gzip.open(trace,'wt') as output:
        for replica in range(4):
            row,_=prior.prior.play_game(bank,'risk1','H2',0,None,source_seed(life,replica),MAX_STEPS)
            row.update(life=life,query='risk1',replica=replica,phase=phase,source_id=f'{phase}:{life}:risk1:{replica}')
            append(output,row);result=row['result'];environment.update(result['environment_counts'])
            policy.update(result['policy_counts']);statuses[result['status']]+=1
    prior.finish_teachers(bank,parents,leaves,records)
    data=dict(phase=phase,life=life,source_trace=str(trace.relative_to(directory)),physical_games=4,
        teacher_bank=records,environment_counts=dict(environment),policy_counts=dict(policy),
        statuses=dict(statuses),seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data);print(dict(event='source_completed',life=life,games=4),flush=True)
    return data


def phase_cells(sources,previous,phase):
    index={c['heldout_life']:c for c in previous or []};cells=[]
    for source in sources:
        parents=deepcopy(index[source['heldout_life']]['selected_parents'] if previous is not None else source['parents'])
        slots=([dict(candidate_slot=i,program=deepcopy(p)) for i,p in enumerate(parents)] if phase=='FINAL' else mutate(parents))
        cells.append(dict(heldout_life=source['heldout_life'],query='risk1',phase=phase,parents=parents,
            slots=slots,complete=source['complete'],issues=deepcopy(source['issues'])))
    return cells


def branch_roster(cells,phase):
    index={cell['heldout_life']:cell for cell in cells};rows=[]
    episodes={'G1':2,'G2':2,'FINAL':4,'EVAL':32}[phase]
    for life in LIVES:
        for heldout in ([life] if phase=='EVAL' else [fold for fold in LIVES if fold!=life]):
            cell=index[heldout];modes=[('H2','H2',None,None)]
            if phase=='EVAL':
                modes += [(arm,arm,None,cell['selected_parents'][0]) for arm in ('COND','LATCHED')]
            else:
                modes += [(f'P{item["candidate_slot"]}_{arm}',arm,item['candidate_slot'],item['program'])
                          for item in cell['slots'] for arm in ('COND','LATCHED')]
            for episode in range(episodes):
                seed=episode_seed(phase,life,episode,heldout)
                for mode,arm,slot,program in modes:
                    rows.append(dict(branch_id=f'{phase}:{life}:fold{heldout}:{episode}:{mode}',
                        phase=phase,life=life,query='risk1',heldout_life=heldout,episode=episode,
                        mode=mode,route=arm,arm=arm,candidate_slot=slot,seed=seed,program=deepcopy(program)))
    return rows


def compact_outcome(row):
    keys=('branch_id','phase','life','query','heldout_life','episode','mode','route','arm','candidate_slot','seed')
    return dict(**{k:row[k] for k in keys},
        **{k:deepcopy(row['result'][k]) for k in ('score','steps','status','components','utility')},
        module=deepcopy(row['module']))


def branch_lifecycle(source,phase,cells,directory):
    started=perf_counter();life=source['life'];folder=directory/phase.lower()/f'life_{life}';folder.mkdir(parents=True)
    bank,parents,leaves,records=prior.teachers(source,folder)
    rule=LearnedDynamics.from_payload(source['rule']);before=rule.to_payload()
    trace=folder/'branches.jsonl.gz';outcomes=[];environment,policy,setup,statuses=Counter(),Counter(),Counter(),Counter()
    with gzip.open(trace,'wt') as output:
        for plan in branch_roster(cells,phase):
            if plan['life']!=life:continue
            row=run_episode(bank,rule,'risk1',plan['program'],plan['arm'],plan['seed'],MAX_STEPS,.1)
            row.update({k:v for k,v in plan.items() if k!='program'})
            append(output,row);outcomes.append(compact_outcome(row));result=row['result']
            environment.update(result['environment_counts']);policy.update(result['policy_counts'])
            setup.update(result['program_setup_counts']);statuses[result['status']]+=1
    prior.finish_teachers(bank,parents,leaves,records);save(folder/'outcomes.json',outcomes)
    data=dict(phase=phase,life=life,branch_trace=str(trace.relative_to(directory)),
        outcomes_ref=str((folder/'outcomes.json').relative_to(directory)),teacher_bank=records,
        rule_before=before,rule_after=rule.to_payload(),physical_branches=len(outcomes),
        environment_counts=dict(environment),policy_counts=dict(policy),program_setup_counts=dict(setup),
        statuses=dict(statuses),seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data);print(dict(event='games_completed',phase=phase,life=life,games=len(outcomes)),flush=True)
    return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_persistent_strategy_v170')
    files={Path(__file__).resolve(),ROOT/'specs/PERSISTENT_STRATEGY_PROGRAM_V170.md',ROOT/'reports/v170_runtime_tmp/run_stage.py'}
    files.update((ROOT/'tests').glob('*persistent_strategy*v170.py'))
    for module in list(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    for path in sorted(files):
        dest=directory/'source_code'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    return len(files)


def run(directory=OUTPUT):
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    capsule=extract_source();save(directory/'source_capsule.json',capsule)
    data=dict(schema='acfqp.persistent_strategy.v170.run',status='frozen',settings=settings(),phases={},phase_order=[],
        generation_seconds=0.,selection_seconds={},new_parameter_updates=0,inherited_cost_refs=capsule['cost_refs'],
        frozen_source_files=snapshot_code(directory))
    source_roster=[dict(phase='SOURCE',life=life,query='risk1',replica=r,seed=source_seed(life,r)) for life in LIVES for r in range(4)]
    save(directory/'frozen_inputs.json',dict(**deepcopy(data),source_roster=source_roster))
    data['phase_order']=['INPUTS_FROZEN'];save(directory/'run.json',data)

    def execute(phase,function,*args):
        data['status']=phase.lower();save(directory/'run.json',data)
        data['phases'][phase]=prior.parallel_phase(function,capsule['snapshots'],phase,*args,directory)
        data['phase_order'].append(phase);save(directory/'run.json',data)

    def stop():
        data.update(status='incomplete_training',seconds=perf_counter()-started);save(directory/'run.json',data)
        print(dict(status='incomplete_training',phase_order=data['phase_order']),flush=True)

    execute('SOURCE',source_lifecycle)
    rows=[row for lc in data['phases']['SOURCE']['lifecycles'] for row in prior.read_rows(directory/lc['source_trace'])]
    rules={s['life']:LearnedDynamics.from_payload(s['rule']) for s in capsule['snapshots']}
    generation_started=perf_counter();sources=[source_candidates(rows,rules,heldout) for heldout in LIVES]
    data['generation_seconds']=perf_counter()-generation_started;save(directory/'source_candidates.json',sources);del rows,rules
    if not all(c['complete'] for c in sources):stop();return
    selections=None
    for phase in ('G1','G2','FINAL'):
        cells=phase_cells(sources,selections,phase);save(directory/f'inputs_{phase.lower()}.json',dict(cells=cells,branch_roster=branch_roster(cells,phase)))
        execute(phase,branch_lifecycle,cells)
        outcomes=[row for lc in data['phases'][phase]['lifecycles'] for row in read(directory/lc['outcomes_ref'])]
        selection_started=perf_counter();selections=choose_parents(cells,outcomes,phase)
        save(directory/f'selections_{phase.lower()}.json',selections);data['selection_seconds'][phase]=perf_counter()-selection_started
        if not all(c['complete'] for c in selections):stop();return
        data['phase_order'].append('PROGRAMS_FROZEN' if phase=='FINAL' else f'{phase}_SELECTED')
        if phase=='FINAL':save(directory/'frozen_programs.json',selections)
        save(directory/'run.json',data)
    save(directory/'inputs_eval.json',dict(cells=selections,branch_roster=branch_roster(selections,'EVAL')))
    execute('EVAL',branch_lifecycle,selections)
    outcomes=[row for lc in data['phases']['EVAL']['lifecycles'] for row in read(directory/lc['outcomes_ref'])]
    save(directory/'summary.json',summarize_eval(outcomes))
    data.update(status='complete',seconds=perf_counter()-started);save(directory/'run.json',data)
    print(dict(status='complete',seconds=data['seconds']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=OUTPUT)
    run(parser.parse_args().output)

