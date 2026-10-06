"""Two frozen mutation generations driven by cross-history terminal outcomes."""
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
from acfqp.science.controlled_predictive_program_consolidation_v161 import run_branch
from acfqp.science.controlled_predictive_consequence_generation_v168 import (
    source_frequencies, mutate, choose_parents, summarize_eval)
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics

SOURCE = ROOT/'reports/controlled_predictive_fixed_program_v167'
OUTPUT = ROOT/'reports/controlled_predictive_consequence_generation_v168'
BASE, MAX_STEPS = 16800000000, 2000
ROUTES, LIVES = ('FREQ', 'CONS'), tuple(range(4))
read, save, append = prior.read, prior.save, prior.append


def source_seed(phase, life, replica):
    return BASE+{'TRAIN_SOURCE':10000000, 'EVAL_SOURCE':90000000}[phase]+life*1000000+replica


def branch_seed(phase, root, suffix, heldout=None):
    if phase == 'EVAL':
        return BASE+50000000+root['life']*1000000+root['replica']*1000+root['slot']*100+suffix
    return BASE+{'G1':20000000, 'G2':30000000, 'FINAL':40000000}[phase]+heldout*1000000+root['life']*100000+root['replica']*1000+root['slot']*100+suffix


def settings():
    return dict(lifecycles=list(LIVES), queries=['risk1'], source_replicas=4,
        source_games=32, train_roots=16, eval_roots=32, word_length=4,
        generations=2, beam=2, candidate_slots=26, generation_suffixes=2,
        final_suffixes=4, eval_suffixes=16, generation_branches=10176,
        final_branches=960, evaluation_branches=1536, physical_branches=12672,
        maximum_environment_transitions=25408000, max_steps=MAX_STEPS,
        p_four=.1, workers=4, version_base=BASE, new_parameter_updates=0,
        parent_prior='top two full-frequency source TRAIN canonical words in the other three histories; outcome-independent',
        mutation='parents slots0/1; then parent order, positions0..3, DOWN/LEFT/RIGHT/UP skipping original; all26slots physically executed including duplicates',
        feedback='CONS terminal paired risk1 utility selects two distinct next-generation parents; FREQ original source word frequency; lexical word then slot tie',
        final='both routes terminal-screen their two parents on four fresh suffixes, select one distinct word including negative winner',
        weighting='two/four paired suffixes per root, four TRAIN roots per other history, three TRAIN histories equally',
        evaluation='freeze all final fold programs before new EVAL source games; H2/FREQ/CONS on32roots16new suffixes',
        primary='CONS-FREQ risk1 terminal utility; adoption also requires CONS-H2 positive conditional CI95',
        uncertainty='paired suffix CI95 conditional on new frozen roots, four existing histories, teachers and trained programs; fold TRAIN overlap',
        source_cutoffs='bounded observed source windows and active quarter roots allowed; source returns never fitness',
        incomplete='missing initial words or any incomplete generation/final cohort stops all downstream phases; no replacements; EVAL cutoff blocks affected statistics',
        bank='unchanged both-query SINGLE teacher; risk8 loads/setup retained with zero risk8 decisions',
        costs='match branch slots/caps, report actual draws per route plus shared H2 and source; no equal realized-draw or sampling-efficiency claim',
        frozen_policy='no extra generations, changed words/grammar/roots/suffix budgets after outcomes, caller promotion or U006')


def extract_source():
    run, analysis, capsule = (read(SOURCE/name) for name in ('run.json', 'analysis.json', 'source_capsule.json'))
    if not (run['status'] == 'complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('audited V167 completion required')
    refs = deepcopy(capsule['cost_refs'])+[dict(path=str(SOURCE/'analysis.json'), fields=['costs'])]
    refs += [dict(path=str(ROOT/f'reports/v167_runtime_tmp/{name}_checks.json'), fields=['attempts'])
             for name in ('core', 'runner', 'analyzer', 'stage')]
    return dict(schema='acfqp.consequence_generation.v168.source', snapshots=deepcopy(capsule['snapshots']),
        source_run_ref=str(SOURCE/'run.json'), source_analysis_ref=str(SOURCE/'analysis.json'),
        inherited_v167_environment_samples=analysis['costs']['new_environment_samples'], cost_refs=refs,
        this_stage_test_refs=[str(ROOT/f'reports/v168_runtime_tmp/{name}_checks.json')
                              for name in ('core', 'runner', 'analyzer')])


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


def phase_cells(frequencies, selections, phase):
    index = {(row['heldout_life'], row['route']):row for row in selections or []}
    cells = []
    for source in frequencies:
        for route in ROUTES:
            parents = (deepcopy(index[source['heldout_life'], route]['selected_parents']) if selections is not None
                       else [deepcopy(row['word']) for row in source['source_frequencies'][:2]])
            slots = ([dict(candidate_slot=i, word=deepcopy(word)) for i, word in enumerate(parents)]
                     if phase == 'FINAL' else mutate(parents))
            cells.append(dict(heldout_life=source['heldout_life'], route=route, phase=phase,
                source_frequencies=deepcopy(source['source_frequencies']), parents=parents,
                slots=slots, complete=source['complete'], issues=deepcopy(source['issues'])))
    return cells


def branch_roster(roots, cells, phase):
    index = {(row['heldout_life'], row['route']):row for row in cells}; rows = []
    suffixes = {'G1':2, 'G2':2, 'FINAL':4, 'EVAL':16}[phase]
    for root in roots:
        folds = [root['life']] if phase == 'EVAL' else [life for life in LIVES if life != root['life']]
        for heldout in folds:
            modes = [('H2', 'H2', None, None)]
            for route in ROUTES:
                cell = index[heldout, route]
                if phase == 'EVAL':
                    modes.append((route, route, None, cell['selected_parents'][0]))
                else:
                    modes.extend((f'{route}_W{item["candidate_slot"]}', route, item['candidate_slot'], item['word']) for item in cell['slots'])
            for suffix in range(suffixes):
                for mode, route, candidate_slot, word in modes:
                    rows.append(dict(branch_id=f'{phase}:{root["root_id"]}:fold{heldout}:{suffix}:{mode}',
                        root_id=root['root_id'], phase=phase, life=root['life'], query='risk1',
                        replica=root['replica'], slot=root['slot'], heldout_life=heldout,
                        route=route, candidate_slot=candidate_slot, mode=mode, suffix=suffix,
                        seed=branch_seed(phase, root, suffix, heldout), program=deepcopy(word)))
    return rows


def compact_outcome(row):
    keys = ('branch_id', 'root_id', 'phase', 'life', 'query', 'replica', 'slot',
            'heldout_life', 'route', 'candidate_slot', 'mode', 'suffix', 'seed')
    data = {key:row[key] for key in keys}
    data.update({key:deepcopy(row['result'][key]) for key in ('score', 'steps', 'status', 'components', 'utility')})
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
                             item['seed'], MAX_STEPS, .1)
            row.update({key:value for key, value in item.items() if key != 'program'})
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
    importlib.import_module('scripts.analyze_controlled_predictive_consequence_generation_v168')
    files = {Path(__file__).resolve(), ROOT/'specs/CONSEQUENCE_GUIDED_GENERATION_V168.md',
             ROOT/'reports/v168_runtime_tmp/run_stage.py'}
    files.update((ROOT/'tests').glob('*consequence_generation*v168.py'))
    for module in list(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name:
            path = Path(name).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'): files.add(path)
    for name in ('ntuple_kernel_v120', 'contextual_ntuple_v134', 'frozen_leaf_planning_v135'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    for path in sorted(files):
        target = directory/'source'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    return len(files)


def run(directory=OUTPUT):
    started = perf_counter(); directory = directory.resolve(); directory.mkdir(parents=True, exist_ok=False)
    capsule = extract_source(); save(directory/'source_capsule.json', capsule)
    data = dict(schema='acfqp.consequence_generation.v168.run', status='frozen', settings=settings(),
        phases={}, phase_order=[], inherited_cost_refs=capsule['cost_refs'],
        frozen_source_files=snapshot_code(directory), new_parameter_updates=0)
    source_roster = [dict(phase=phase, life=life, query='risk1', replica=replica,
                         seed=source_seed(phase, life, replica))
        for phase in ('TRAIN_SOURCE', 'EVAL_SOURCE') for life in LIVES for replica in range(4)]
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
    generation_started = perf_counter()
    frequencies = [source_frequencies(source_rows, heldout) for heldout in LIVES]
    save(directory/'source_frequencies.json', frequencies)
    data['generation_seconds'] = perf_counter()-generation_started; del source_rows
    if not all(cell['complete'] for cell in frequencies): stop(); return
    selections = None
    for phase in ('G1', 'G2', 'FINAL'):
        cells = phase_cells(frequencies, selections, phase)
        save(directory/f'inputs_{phase.lower()}.json', dict(roots=roots, cells=cells, branch_roster=branch_roster(roots, cells, phase)))
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
    save(directory/'inputs_eval.json', dict(roots=roots, cells=selections, branch_roster=branch_roster(roots, selections, 'EVAL')))
    execute('EVAL', branch_lifecycle, roots, selections)
    outcomes = [row for life in data['phases']['EVAL']['lifecycles'] for row in read(directory/life['outcomes_ref'])]
    save(directory/'summary.json', summarize_eval(roots, outcomes))
    data.update(status='complete', seconds=perf_counter()-started); save(directory/'run.json', data)
    print(dict(status='complete', seconds=data['seconds']), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)
