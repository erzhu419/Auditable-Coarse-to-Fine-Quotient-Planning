"""Jointly mutate observable conditions and two executable action continuations."""
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
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import run_controlled_predictive_program_consolidation_v161 as prior
from acfqp.science.controlled_predictive_feedback_program_v162 import run_branch
from acfqp.science.controlled_predictive_joint_feedback_generation_v169 import (
    source_candidates, mutate, executable, branch_seed, choose_parents, summarize_eval)
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics

SOURCE = ROOT/'reports/controlled_predictive_consequence_generation_v168'
OUTPUT = ROOT/'reports/controlled_predictive_joint_feedback_generation_v169'
BASE, MAX_STEPS = 16900000000, 2000
LIVES = tuple(range(4))
read, save, append = prior.read, prior.save, prior.append


def source_seed(phase, life, replica):
    return BASE+{'TRAIN_SOURCE':10000000, 'EVAL_SOURCE':90000000}[phase]+life*1000000+replica


def settings():
    return dict(lifecycles=list(LIVES), queries=['risk1'], source_replicas=4,
        source_games=32, train_roots=16, eval_roots=32, word_length=4,
        generations=2, beam=2, candidate_slots=50, generation_suffixes=1,
        final_suffixes=4, eval_suffixes=16, generation_branches=9696,
        final_branches=960, evaluation_branches=1536, physical_branches=12192,
        maximum_environment_transitions=24448000, max_steps=MAX_STEPS,
        p_four=.1, workers=4, version_base=BASE, new_parameter_updates=0,
        initial='top two V162-eligible source first-action groups from other three histories; canonical conditional modal suffixes; source returns never fitness',
        grammar='first action; after its actual spawn, legal positive-merge probe in original D4 frame selects true/false three-action suffix; at most four actions then own H2',
        mutation='two parent slots then each parent: first,probe,true0..2,false0..2, actions DOWN/LEFT/RIGHT/UP skipping original; all50slots physically costed including duplicates',
        acquisition='shared H2 plus forced A and B per candidate; both observe same first-spawn predicate and pay probe cost; no physical conditional TRAIN branch',
        fitness='select whole realized A terminal vector when predicate true/None, otherwise B; equal suffixes/root/history; no fabricated unseen-condition estimate',
        selection='conditional terminal risk1 utility; top two distinct eight-gene programs; lexical program then first slot; retain negative winners',
        final='both parents screened on four new suffixes; one conditional winner and its best same-candidate unconditional A/B, tie A; freeze before EVAL source',
        evaluation='32 new fixed roots, 16 new suffixes, H2/COND/TWIN physically executed; all entry failures/fallbacks retained',
        primary='COND-TWIN risk1 utility; adoption also requires COND-H2 positive conditional CI95 lower bound',
        uncertainty='paired suffix CI95 conditional on new frozen roots, four existing histories and teacher/program selections; crossfold TRAIN overlap',
        source_cutoffs='bounded observed windows and active quarter roots allowed; missing eligible parents or source records stops, no replacement',
        incomplete='any missing/duplicate/nonterminal/mismatched physical TRAIN pair stops downstream; absent predicate support alone allowed; EVAL cutoff blocks affected statistics',
        bank='unchanged both-query SINGLE teacher; risk8 setup/load retained with zero risk8 decisions',
        costs='branch slots and step caps frozen; actual A/B/COND/TWIN/sharedH2/source samples reported, no sampling-efficiency claim',
        frozen_policy='no extra generations, new predicates/branches/horizon/roots/budgets after outcomes, caller promotion or U006')


def extract_source():
    run, analysis, capsule = (read(SOURCE/name) for name in ('run.json', 'analysis.json', 'source_capsule.json'))
    if not (run['status'] == 'complete' and analysis['valid'] and analysis['primary_complete']):
        raise ValueError('audited V168 completion required')
    refs = deepcopy(capsule['cost_refs'])+[dict(path=str(SOURCE/'analysis.json'), fields=['costs'])]
    refs += [dict(path=str(ROOT/f'reports/v168_runtime_tmp/{name}_checks.json'), fields=['attempts'])
             for name in ('core', 'runner', 'analyzer', 'stage')]
    return dict(schema='acfqp.joint_feedback_generation.v169.source', snapshots=deepcopy(capsule['snapshots']),
        source_run_ref=str(SOURCE/'run.json'), source_analysis_ref=str(SOURCE/'analysis.json'),
        inherited_v168_environment_samples=analysis['costs']['new_environment_samples'], cost_refs=refs,
        this_stage_test_refs=[str(ROOT/f'reports/v169_runtime_tmp/{name}_checks.json') for name in ('core','runner','analyzer')])


def source_lifecycle(source, phase, directory):
    started = perf_counter(); life = source['life']
    folder = directory/phase.lower()/f'life_{life}'; folder.mkdir(parents=True)
    bank, parents, leaves, records = prior.teachers(source, folder)
    environment, policy, statuses = Counter(), Counter(), Counter(); roots = []
    trace = folder/'source_games.jsonl.gz'
    with gzip.open(trace, 'wt') as output:
        for replica in range(4):
            row, _ = prior.prior.play_game(bank, 'risk1', 'H2', 0, None,
                source_seed(phase, life, replica), MAX_STEPS)
            row.update(life=life, query='risk1', replica=replica, phase=phase,
                       source_id=f'{phase}:{life}:risk1:{replica}')
            row['roots'] = prior.roots_from_source(row, phase) if phase == 'EVAL_SOURCE' or replica < 2 else []
            roots.extend(row['roots']); append(output, row)
            result = row['result']; environment.update(result['environment_counts'])
            policy.update(result['policy_counts']); statuses[result['status']] += 1
    prior.finish_teachers(bank, parents, leaves, records)
    record = dict(phase=phase, life=life, source_trace=str(trace.relative_to(directory)),
        roots=roots, physical_games=4, teacher_bank=records,
        environment_counts=dict(environment), policy_counts=dict(policy),
        statuses=dict(statuses), seconds=perf_counter()-started)
    save(folder/'lifecycle.json', record)
    print(dict(event='source_completed', phase=phase, life=life, games=4), flush=True)
    return record


def phase_cells(sources, selections, phase):
    index = {row['heldout_life']:row for row in selections or []}; cells = []
    for source in sources:
        parents = deepcopy(index[source['heldout_life']]['selected_parents'] if selections is not None else source['parents'])
        slots = ([dict(candidate_slot=i, program=deepcopy(program)) for i,program in enumerate(parents)]
                 if phase == 'FINAL' else mutate(parents))
        cells.append(dict(heldout_life=source['heldout_life'], query='risk1', phase=phase,
            parents=parents, slots=slots, complete=source['complete'], issues=deepcopy(source['issues'])))
    return cells


def branch_roster(roots, cells, phase):
    index = {row['heldout_life']:row for row in cells}; rows = []
    suffixes = {'G1':1, 'G2':1, 'FINAL':4, 'EVAL':16}[phase]
    for root in roots:
        folds = [root['life']] if phase == 'EVAL' else [life for life in LIVES if life != root['life']]
        for heldout in folds:
            cell = index[heldout]
            modes = [('H2', 'H2', None, None, 'H2')]
            if phase == 'EVAL':
                program = cell['selected_parents'][0]
                modes.extend((mode, mode, None, executable(program, forced), 'FEEDBACK')
                    for mode, forced in (('COND', None), ('TWIN', cell['selected_twin'])))
            else:
                modes.extend((f'P{item["candidate_slot"]}_{forced}', forced, item['candidate_slot'],
                              executable(item['program'], forced), 'FEEDBACK')
                    for item in cell['slots'] for forced in ('A','B'))
            for suffix in range(suffixes):
                seed = branch_seed(phase, root, suffix, heldout)
                for mode, route, candidate_slot, program, arm in modes:
                    rows.append(dict(branch_id=f'{phase}:{root["root_id"]}:fold{heldout}:{suffix}:{mode}',
                        root_id=root['root_id'], phase=phase, life=root['life'], query='risk1',
                        replica=root['replica'], slot=root['slot'], heldout_life=heldout,
                        route=route, candidate_slot=candidate_slot, mode=mode, arm=arm,
                        suffix=suffix, seed=seed, program=deepcopy(program)))
    return rows


def compact_outcome(row):
    keys = ('branch_id','root_id','phase','life','query','replica','slot',
            'heldout_life','route','candidate_slot','mode','arm','suffix','seed')
    data = {key:row[key] for key in keys}
    data.update({key:deepcopy(row['result'][key]) for key in ('score','steps','status','components','utility')})
    data['module'] = deepcopy(row['module']); return data


def branch_lifecycle(source, phase, roots, cells, directory):
    started = perf_counter(); life = source['life']
    folder = directory/phase.lower()/f'life_{life}'; folder.mkdir(parents=True)
    bank, parents, leaves, records = prior.teachers(source, folder)
    rule = LearnedDynamics.from_payload(source['rule']); before = rule.to_payload()
    rootmap = {root['root_id']:root for root in roots if root['life'] == life}
    trace = folder/'branches.jsonl.gz'; outcomes = []
    environment, policy, setup, statuses = Counter(), Counter(), Counter(), Counter()
    with gzip.open(trace, 'wt') as output:
        for item in branch_roster(roots, cells, phase):
            root = rootmap.get(item['root_id'])
            if root is None: continue
            row = run_branch(root['board'], bank, rule, 'risk1', item['program'],
                             item['arm'], item['seed'], MAX_STEPS, .1)
            row.update({key:value for key,value in item.items() if key != 'program'})
            append(output, row); outcomes.append(compact_outcome(row)); result = row['result']
            environment.update(result['environment_counts']); policy.update(result['policy_counts'])
            setup.update(result['program_setup_counts']); statuses[result['status']] += 1
    prior.finish_teachers(bank, parents, leaves, records); save(folder/'outcomes.json', outcomes)
    record = dict(phase=phase, life=life, branch_trace=str(trace.relative_to(directory)),
        outcomes_ref=str((folder/'outcomes.json').relative_to(directory)), teacher_bank=records,
        rule_before=before, rule_after=rule.to_payload(), physical_branches=len(outcomes),
        environment_counts=dict(environment), policy_counts=dict(policy),
        program_setup_counts=dict(setup), statuses=dict(statuses), seconds=perf_counter()-started)
    save(folder/'lifecycle.json', record)
    print(dict(event='branches_completed', phase=phase, life=life, branches=len(outcomes)), flush=True)
    return record


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_joint_feedback_generation_v169')
    files = {Path(__file__).resolve(), ROOT/'specs/CONSEQUENCE_FEEDBACK_GENERATION_V169.md',
             ROOT/'reports/v169_runtime_tmp/run_stage.py'}
    files.update((ROOT/'tests').glob('*joint_feedback_generation*v169.py'))
    for module in list(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name:
            path = Path(name).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'): files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    for path in sorted(files):
        target = directory/'source'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    return len(files)


def run(directory=OUTPUT):
    started = perf_counter(); directory = directory.resolve(); directory.mkdir(parents=True, exist_ok=False)
    capsule = extract_source(); save(directory/'source_capsule.json', capsule)
    data = dict(schema='acfqp.joint_feedback_generation.v169.run', status='frozen', settings=settings(),
        phases={}, phase_order=[], inherited_cost_refs=capsule['cost_refs'],
        frozen_source_files=snapshot_code(directory), new_parameter_updates=0)
    source_roster = [dict(phase=phase, life=life, query='risk1', replica=replica,
                         seed=source_seed(phase, life, replica))
        for phase in ('TRAIN_SOURCE','EVAL_SOURCE') for life in LIVES for replica in range(4)]
    save(directory/'frozen_inputs.json', dict(**deepcopy(data), source_roster=source_roster))
    data['phase_order'] = ['INPUTS_FROZEN']; save(directory/'run.json', data)

    def execute(phase, function, *args):
        data['status'] = phase.lower(); save(directory/'run.json', data)
        data['phases'][phase] = prior.parallel_phase(function, capsule['snapshots'], phase, *args, directory)
        data['phase_order'].append(phase); save(directory/'run.json', data)

    def stop():
        data.update(status='incomplete_training', seconds=perf_counter()-started)
        save(directory/'run.json', data)
        print(dict(status='incomplete_training', phase_order=data['phase_order']), flush=True)

    execute('TRAIN_SOURCE', source_lifecycle)
    roots = [root for life in data['phases']['TRAIN_SOURCE']['lifecycles'] for root in life['roots']]
    save(directory/'train_roots.json', roots)
    source_rows = [row for life in data['phases']['TRAIN_SOURCE']['lifecycles']
                   for row in prior.read_rows(directory/life['source_trace'])]
    rules = {source['life']:LearnedDynamics.from_payload(source['rule']) for source in capsule['snapshots']}
    generation_started = perf_counter()
    sources = [source_candidates(source_rows, rules, heldout) for heldout in LIVES]
    save(directory/'source_candidates.json', sources)
    data['generation_seconds'] = perf_counter()-generation_started; del source_rows, rules
    if not all(cell['complete'] for cell in sources): stop(); return
    selections = None
    for phase in ('G1','G2','FINAL'):
        cells = phase_cells(sources, selections, phase)
        save(directory/f'inputs_{phase.lower()}.json', dict(roots=roots,cells=cells,branch_roster=branch_roster(roots,cells,phase)))
        execute(phase, branch_lifecycle, roots, cells)
        outcomes = [row for life in data['phases'][phase]['lifecycles'] for row in read(directory/life['outcomes_ref'])]
        selection_started = perf_counter(); selections = choose_parents(cells, roots, outcomes, phase)
        save(directory/f'selections_{phase.lower()}.json', selections)
        data.setdefault('selection_seconds', {})[phase] = perf_counter()-selection_started
        if not all(cell['complete'] for cell in selections): stop(); return
        data['phase_order'].append('PROGRAMS_FROZEN' if phase == 'FINAL' else f'{phase}_SELECTED')
        if phase == 'FINAL': save(directory/'frozen_programs.json', selections)
        save(directory/'run.json', data)
    execute('EVAL_SOURCE', source_lifecycle)
    roots = [root for life in data['phases']['EVAL_SOURCE']['lifecycles'] for root in life['roots']]
    save(directory/'eval_roots.json', roots)
    save(directory/'inputs_eval.json', dict(roots=roots,cells=selections,branch_roster=branch_roster(roots,selections,'EVAL')))
    execute('EVAL', branch_lifecycle, roots, selections)
    outcomes = [row for life in data['phases']['EVAL']['lifecycles'] for row in read(directory/life['outcomes_ref'])]
    save(directory/'summary.json', summarize_eval(roots, outcomes))
    data.update(status='complete', seconds=perf_counter()-started); save(directory/'run.json', data)
    print(dict(status='complete', seconds=data['seconds']), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)

