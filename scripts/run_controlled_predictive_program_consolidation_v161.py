"""Generate four-action programs from fresh TRAIN experience; test heldout histories."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import importlib
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import run_controlled_predictive_policy_modules_v151 as prior
from acfqp.science.controlled_predictive_program_consolidation_v161 import generate_candidates,run_branch
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics

SOURCE=ROOT/'reports/controlled_predictive_module_mobility_v160'
LIVES,QUERIES=prior.LIVES,prior.QUERIES
BASE,MAX_STEPS,WORKERS=161*100000000,2000,4
SOURCE_REPLICAS,TRAIN_SUFFIXES,EVAL_SUFFIXES=4,4,16
MODES=('H2','FREQ','BEST')
read,save,append,read_rows=prior.read,prior.save,prior.append,prior.read_rows
load_teacher,leaf_state=prior.load_teacher,prior.leaf_state


def source_seed(phase,life,query,replica):
    offset={'TRAIN_SOURCE':10000000,'EVAL_SOURCE':90000000}[phase]
    return BASE+offset+life*1000000+list(QUERIES).index(query)*100000+replica


def branch_seed(phase,root,suffix,heldout_life=None):
    q=list(QUERIES).index(root['query'])
    if phase=='SCREEN':
        return BASE+20000000+heldout_life*1000000+root['life']*100000+q*10000+root['replica']*1000+root['slot']*100+suffix
    if phase=='EVAL':
        return BASE+50000000+root['life']*1000000+q*100000+root['replica']*1000+root['slot']*100+suffix
    raise ValueError(phase)


def roots_from_source(row,phase):
    n=len(row['actions']);roots=[]
    for slot in range(2):
        step=((2*slot+1)*n)//4
        board=list(row['initial_board'] if step==0 else row['choices'][step-1]['afterstate'])
        if step:board[row['spawned_cells'][step-1]]=row['spawned_ranks'][step-1]
        roots.append(dict(root_id=f'{phase}:{row["life"]}:{row["query"]}:{row["replica"]}:{slot}',
            phase=phase,life=row['life'],query=row['query'],replica=row['replica'],slot=slot,
            source_id=row['source_id'],source_seed=row['seed'],source_step=step,source_steps=n,board=board))
    return roots


def screening_roster(roots,candidates):
    cells={(c['heldout_life'],c['query']):c for c in candidates};rows=[]
    for life in LIVES:
        for heldout in LIVES:
            if heldout==life:continue
            for query in QUERIES:
                modes=['H2']+[p['candidate_id'] for p in cells[heldout,query]['candidates']]
                for root in roots:
                    if (root['life'],root['query'])!=(life,query):continue
                    for suffix in range(TRAIN_SUFFIXES):
                        for mode in modes:
                            rows.append(dict(branch_id=f'{root["root_id"]}:fold{heldout}:{suffix}:{mode}',
                                root_id=root['root_id'],heldout_life=heldout,suffix=suffix,mode=mode,
                                seed=branch_seed('SCREEN',root,suffix,heldout)))
    return rows


def eval_roster(roots):
    return [dict(branch_id=f'{r["root_id"]}:{suffix}:{mode}',root_id=r['root_id'],
        heldout_life=r['life'],suffix=suffix,mode=mode,seed=branch_seed('EVAL',r,suffix))
        for r in roots for suffix in range(EVAL_SUFFIXES) for mode in MODES]


def settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,source_replicas=4,source_games=64,
        train_roots=32,eval_roots=64,word_length=4,candidate_limit=4,train_suffixes=4,eval_suffixes=16,
        screening_branch_cap=1920,evaluation_branches=3072,physical_branch_cap=4992,
        maximum_environment_transitions=10112000,max_steps=2000,p_four=.1,workers=4,version_base=BASE,
        generation='all contiguous length4 words from new TRAIN own-query H2 games in other three histories; no terminal-outcome filtering',
        normalization='lexicographically least D4 board at fragment/root start; first transform breaks ties; fixed orientation for whole word',
        grammar='four primitive swipes; exit at illegal next action, terminal, or four executed actions; then own H2 permanently',
        candidates='top four canonical words by occurrence count; lexical word tie; no manual added candidate',
        root_selection='floor(n/4),floor(3*n/4) active predecision states; TRAIN only source replicas0/1; EVAL all four',
        screening='each heldout-history/query cell uses only three other histories; equal four roots/history and four paired suffixes',
        selection='highest complete TRAIN paired terminal utility mean vs H2; frequency order breaks ties; retain and force candidate even if mean<=0',
        evaluation='freeze all programs before generating any EVAL source; H2 vs frequency-top FREQ vs TRAIN-screened BEST',
        primary='BEST-H2 terminal utility per query; average16pairedsuffixes/root, equal roots/history, equal four heldout histories',
        secondary='BEST-FREQ and FREQ-H2, component reward/failure/success, prefix exposure, per-history effects',
        uncertainty='pointwise conditional paired-suffix intervals; fixed roots, histories and trained selections; cross-fold training overlaps',
        costs='all natural source games, every physically executed screening/control branch, generation/transport work and frozen teacher loads',
        incomplete='retain cutoffs and all costs; any incomplete TRAIN cell stops before EVAL; affected EVAL statistics incomplete; no replacements',
        new_parameter_updates=0,frozen_policy='no outcome-dependent grammar, length, top-k, seed cap, extra fitting, caller learning or U006')


def extract_source():
    run,analysis,capsule=(read(SOURCE/name) for name in ('run.json','analysis.json','source_capsule.json'))
    if not(run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('audited V160 completion required')
    return dict(schema='acfqp.program_consolidation.v161.source',snapshots=deepcopy(capsule['snapshots']),
        source_run_ref=str(SOURCE/'run.json'),source_analysis_ref=str(SOURCE/'analysis.json'),
        inherited_v160_environment_samples=analysis['costs']['new_environment_samples'],
        inherited_v158_environment_samples=capsule['inherited_new_environment_samples'],
        cost_refs=deepcopy(capsule['cost_refs'])+[dict(path=str(SOURCE/'analysis.json'),fields=['costs'])]+[
            dict(path=str(ROOT/f'reports/v160_runtime_tmp/{name}_checks.json'),fields=['attempts'])
            for name in ('core','runner','analyzer')])


def teachers(source,folder):
    bank,parents,leaves,records={},{},{},{}
    for query in QUERIES:
        qfolder=folder/query;qfolder.mkdir()
        parent,leaf,teacher,loads=load_teacher(source,'SINGLE',query,qfolder)
        bank[query],parents[query],leaves[query]=teacher,parent,leaf
        records[query]=dict(loads=loads,parent_before=leaf_state(parent,True),leaf_before=leaf_state(leaf))
    return bank,parents,leaves,records


def finish_teachers(bank,parents,leaves,records):
    for query in QUERIES:
        records[query].update(parent_after=leaf_state(parents[query],True),leaf_after=leaf_state(leaves[query]),total_counts=dict(bank[query].counts))


def source_lifecycle(source,phase,directory):
    started=perf_counter();life=source['life'];stem='train' if phase=='TRAIN_SOURCE' else 'eval_sources'
    folder=directory/stem/f'life_{life}';folder.mkdir(parents=True)
    bank,parents,leaves,records=teachers(source,folder)
    trace=folder/'source_games.jsonl.gz';environment,policy,statuses=Counter(),Counter(),Counter();roots=[]
    with gzip.open(trace,'wt') as output:
        for query in QUERIES:
            for replica in range(SOURCE_REPLICAS):
                row,_=prior.play_game(bank,query,'H2',0,None,source_seed(phase,life,query,replica),MAX_STEPS)
                row.update(life=life,replica=replica,phase=phase,source_id=f'{phase}:{life}:{query}:{replica}')
                row['roots']=roots_from_source(row,phase) if phase=='EVAL_SOURCE' or replica<2 else []
                roots.extend(row['roots']);append(output,row);result=row['result']
                environment.update(result['environment_counts']);policy.update(result['policy_counts']);statuses[result['status']]+=1
    finish_teachers(bank,parents,leaves,records)
    data=dict(phase=phase,life=life,source_trace=str(trace.relative_to(directory)),roots=roots,physical_games=8,
        teacher_bank=records,environment_counts=dict(environment),policy_counts=dict(policy),statuses=dict(statuses),seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data);print(dict(event='source_completed',phase=phase,life=life,games=8),flush=True);return data


def compact_outcome(row):
    data={key:row[key] for key in ('branch_id','root_id','phase','life','query','replica','slot','heldout_life','mode','suffix','seed')}
    data.update({key:deepcopy(row['result'][key]) for key in ('score','steps','status','components','utility')})
    data['module']=deepcopy(row['module']);return data


def branch_lifecycle(source,phase,roots,programs,directory):
    started=perf_counter();life=source['life'];stem='screening' if phase=='SCREEN' else 'eval'
    folder=directory/stem/f'life_{life}';folder.mkdir(parents=True)
    bank,parents,leaves,records=teachers(source,folder);rule=LearnedDynamics.from_payload(source['rule']);before=rule.to_payload()
    roster=screening_roster(roots,programs) if phase=='SCREEN' else eval_roster(roots)
    rootmap={r['root_id']:r for r in roots};cells={(c['heldout_life'],c['query']):c for c in programs}
    trace=folder/'branches.jsonl.gz';environment,policy,setup,statuses=Counter(),Counter(),Counter(),Counter();outcomes=[]
    with gzip.open(trace,'wt') as output:
        for item in roster:
            root=rootmap[item['root_id']]
            if root['life']!=life:continue
            cell=cells[item['heldout_life'],root['query']];mode=item['mode']
            if mode=='H2':word=None
            elif phase=='SCREEN':word=next(p['word'] for p in cell['candidates'] if p['candidate_id']==mode)
            else:word=cell['frequency_program' if mode=='FREQ' else 'selected_program']['word']
            row=run_branch(root['board'],bank,rule,root['query'],word,item['seed'],MAX_STEPS,.1)
            row.update(**item,phase=phase,life=life,replica=root['replica'],slot=root['slot'])
            append(output,row);outcomes.append(compact_outcome(row));result=row['result']
            environment.update(result['environment_counts']);policy.update(result['policy_counts'])
            setup.update(result['program_setup_counts']);statuses[result['status']]+=1
            if item['suffix']==(TRAIN_SUFFIXES-1 if phase=='SCREEN' else EVAL_SUFFIXES-1) and mode==(cell['candidates'][-1]['candidate_id'] if phase=='SCREEN' else 'BEST'):
                print(dict(event='root_completed',phase=phase,life=life,heldout_life=item['heldout_life'],root_id=root['root_id']),flush=True)
    finish_teachers(bank,parents,leaves,records);save(folder/'outcomes.json',outcomes)
    data=dict(phase=phase,life=life,branch_trace=str(trace.relative_to(directory)),outcomes_ref=str((folder/'outcomes.json').relative_to(directory)),
        teacher_bank=records,rule_before=before,rule_after=rule.to_payload(),physical_branches=len(outcomes),
        environment_counts=dict(environment),policy_counts=dict(policy),program_setup_counts=dict(setup),statuses=dict(statuses),seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data);return data


def parallel_phase(function,snapshots,*args):
    started=perf_counter();lifecycles=[]
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks=[pool.submit(function,source,*args) for source in snapshots]
        for task in as_completed(tasks):lifecycles.append(task.result())
    lifecycles.sort(key=lambda row:row['life']);return dict(lifecycles=lifecycles,seconds=perf_counter()-started)


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_program_consolidation_v161')
    files={Path(__file__).resolve(),ROOT/'specs/PROGRAM_CONSOLIDATION_V161.md',ROOT/'reports/v161_runtime_tmp/run_stage.py'}
    for module in list(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*program_consolidation*v161.py'))
    for path in sorted(files):
        target=directory/'source'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)


def run(directory):
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    capsule=extract_source();save(directory/'source_capsule.json',capsule);snapshot_code(directory)
    data=dict(schema='acfqp.program_consolidation.v161.run',status='frozen',settings=settings(),phases={},phase_order=[],inherited_cost_refs=capsule['cost_refs'])
    source_roster=[dict(phase=p,life=l,query=q,replica=r,seed=source_seed(p,l,q,r))
        for p in ('TRAIN_SOURCE','EVAL_SOURCE') for l in LIVES for q in QUERIES for r in range(4)]
    save(directory/'frozen_inputs.json',dict(**deepcopy(data),source_roster=source_roster));save(directory/'run.json',data)
    def execute(name,function,*args):
        data['status']=name.lower();save(directory/'run.json',data)
        data['phases'][name]=parallel_phase(function,capsule['snapshots'],name,*args,directory)
        data['phase_order'].append(name);save(directory/'run.json',data)
    execute('TRAIN_SOURCE',source_lifecycle)
    train=data['phases']['TRAIN_SOURCE'];roots=[r for life in train['lifecycles'] for r in life['roots']]
    save(directory/'train_roots.json',roots)
    rows=[row for life in train['lifecycles'] for row in read_rows(directory/life['source_trace'])]
    candidates=[generate_candidates(rows,heldout,query,4) for heldout in LIVES for query in QUERIES]
    save(directory/'generated_candidates.json',candidates);del rows
    save(directory/'screening_inputs.json',dict(roots=roots,candidates=candidates,branch_roster=screening_roster(roots,candidates)))
    execute('SCREEN',branch_lifecycle,roots,candidates)
    from scripts.analyze_controlled_predictive_program_consolidation_v161 import select_programs,summarize_eval
    outcomes=[row for life in data['phases']['SCREEN']['lifecycles'] for row in read(directory/life['outcomes_ref'])]
    programs=select_programs(candidates,roots,outcomes)
    save(directory/'frozen_programs.json',programs);data['phase_order'].append('PROGRAMS_FROZEN')
    data['status']='programs_frozen';save(directory/'run.json',data)
    if not all(p['complete'] for p in programs):
        data.update(status='incomplete_training',seconds=perf_counter()-started);save(directory/'run.json',data);return
    execute('EVAL_SOURCE',source_lifecycle)
    roots=[r for life in data['phases']['EVAL_SOURCE']['lifecycles'] for r in life['roots']];save(directory/'eval_roots.json',roots)
    save(directory/'evaluation_inputs.json',dict(roots=roots,programs=programs,branch_roster=eval_roster(roots)))
    execute('EVAL',branch_lifecycle,roots,programs)
    outcomes=[row for life in data['phases']['EVAL']['lifecycles'] for row in read(directory/life['outcomes_ref'])]
    save(directory/'summary.json',summarize_eval(roots,outcomes))
    data.update(status='complete',seconds=perf_counter()-started,new_parameter_updates=0);save(directory/'run.json',data)
    print(dict(status='complete',seconds=data['seconds']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_program_consolidation_v161')
    run(parser.parse_args().output)
