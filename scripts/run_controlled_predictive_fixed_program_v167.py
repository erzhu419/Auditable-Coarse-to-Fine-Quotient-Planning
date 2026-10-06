"""Confirm the frozen S0/B program with new paired continuations only."""
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
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'src'))
from scripts import run_controlled_predictive_supported_program_v164 as prior
from acfqp.science.controlled_predictive_feedback_program_v162 import run_branch
from acfqp.science.controlled_predictive_fixed_program_v167 import (
    build_program, build_roster, extract_candidate, summarize)
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics

SOURCE = ROOT / 'reports/controlled_predictive_supported_program_v164'
NOMINATION = ROOT / 'reports/controlled_predictive_program_ranking_v166'
OUTPUT = ROOT / 'reports/controlled_predictive_fixed_program_v167'
MAX_STEPS, SUFFIXES, WORKERS = 2000, 16, 4
read, save, append = prior.read, prior.save, prior.append


def settings():
    return dict(lifecycles=[0, 1, 2, 3], queries=['risk1'], evaluation_roots=32,
        roots_per_history=8, suffixes=SUFFIXES, modes=['H2', 'S0_B'],
        physical_games=0, physical_branches=1024, maximum_environment_transitions=2048000,
        max_steps=MAX_STEPS, p_four=.1, workers=WORKERS, new_parameter_updates=0,
        seed_formula='16700000000+50000000+life*1000000+replica*1000+slot*100+suffix',
        source_roots='all V164 risk1 EVAL roots; no new source games',
        program='original S0 first DOWN/probe RIGHT, forced original B suffix DOWN/RIGHT/DOWN; FEEDBACK BB, existing D4 transport, at most four prefix steps, same-step fallback',
        bank='unchanged both-query teacher bank; risk8 setup/load retained, zero risk8 decisions',
        primary='S0_B-H2 terminal risk1 utility, new continuations only',
        weighting='16 suffixes/root, eight roots/history, four histories equally',
        uncertainty='paired normal CI95 conditional on these frozen EVAL roots and four histories',
        frozen_policy='no stopping, extra suffixes, selection, candidate/probe/word changes or U006')


def extract_source():
    source_run, source_analysis, capsule = (read(SOURCE / name) for name in ('run.json', 'analysis.json', 'source_capsule.json'))
    nomination_run, nomination_analysis = (read(NOMINATION / name) for name in ('run.json', 'analysis.json'))
    if not (source_run['status'] == 'complete' and source_analysis['complete']
            and source_analysis['primary_complete'] and nomination_run['status'] == 'complete'
            and nomination_analysis['valid']):
        raise ValueError('Audited V164 and V166 completion required')
    refs = deepcopy(capsule['cost_refs']) + [dict(path=str(SOURCE / 'analysis.json'), fields=['costs'])]
    refs += [dict(path=str(ROOT / f'reports/v164_runtime_tmp/{name}_checks.json'), fields=['attempts'])
             for name in ('core', 'runner', 'analyzer')]
    for version, stem in ((165, 'program_headroom'), (166, 'program_ranking')):
        refs.append(dict(path=str(ROOT / f'reports/controlled_predictive_{stem}_v{version}/result.json'), fields=['costs']))
        refs += [dict(path=str(ROOT / f'reports/v{version}_runtime_tmp/{name}_checks.json'), fields=['attempts'])
                 for name in ('core', 'analyzer', 'stage')]
    return dict(schema='acfqp.fixed_program.v167.source', snapshots=deepcopy(capsule['snapshots']),
        source_run_ref=str(SOURCE / 'run.json'), source_analysis_ref=str(SOURCE / 'analysis.json'),
        nomination_run_ref=str(NOMINATION / 'run.json'), nomination_analysis_ref=str(NOMINATION / 'analysis.json'),
        nomination_roster_ref=str(NOMINATION / 'retained_roster.json'),
        cost_refs=refs, inherited_v164_environment_samples=source_analysis['costs']['new_environment_samples'],
        this_stage_test_refs=[str(ROOT / f'reports/v167_runtime_tmp/{name}_checks.json')
                              for name in ('core', 'runner', 'analyzer')])


def branch_lifecycle(source, phase, roots, program, directory):
    started = perf_counter(); life = source['life']
    folder = directory / 'eval' / f'life_{life}'; folder.mkdir(parents=True)
    bank, parents, leaves, records = prior.teachers(source, folder)
    rule = LearnedDynamics.from_payload(source['rule']); before = rule.to_payload()
    rootmap = {root['root_id']: root for root in roots if root['life'] == life}
    trace = folder / 'branches.jsonl.gz'
    environment, policy, setup, statuses = Counter(), Counter(), Counter(), Counter()
    outcomes = []
    with gzip.open(trace, 'wt') as output:
        for item in build_roster(roots):
            root = rootmap.get(item['root_id'])
            if root is None:
                continue
            selected, arm = (None, 'H2') if item['mode'] == 'H2' else (program, 'FEEDBACK')
            row = run_branch(root['board'], bank, rule, 'risk1', selected, arm, item['seed'], MAX_STEPS, .1)
            row.update(item)
            row.update(phase=phase, heldout_life=life, life=life,
                       query='risk1', replica=root['replica'], slot=root['slot'])
            append(output, row); outcomes.append(prior.compact_outcome(row)); result = row['result']
            environment.update(result['environment_counts']); policy.update(result['policy_counts'])
            setup.update(result['program_setup_counts']); statuses[result['status']] += 1
            if item['suffix'] == SUFFIXES - 1 and item['mode'] == 'S0_B':
                print(dict(event='root_completed', life=life, root_id=root['root_id'], physical_branches=len(outcomes)), flush=True)
    prior.finish_teachers(bank, parents, leaves, records); save(folder / 'outcomes.json', outcomes)
    record = dict(phase=phase, life=life, branch_trace=str(trace.relative_to(directory)),
        outcomes_ref=str((folder / 'outcomes.json').relative_to(directory)),
        teacher_bank=records, rule_before=before, rule_after=rule.to_payload(),
        physical_branches=len(outcomes), environment_counts=dict(environment),
        policy_counts=dict(policy), program_setup_counts=dict(setup),
        statuses=dict(statuses), seconds=perf_counter() - started)
    save(folder / 'lifecycle.json', record)
    return record


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_fixed_program_v167')
    files = {Path(__file__).resolve(), ROOT / 'specs/FIXED_PROGRAM_CONFIRMATION_V167.md',
             ROOT / 'reports/v167_runtime_tmp/run_stage.py'}
    files.update((ROOT / 'tests').glob('*fixed_program*v167.py'))
    for module in list(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name:
            path = Path(name).resolve()
            if path.is_relative_to(ROOT / 'src') or path.is_relative_to(ROOT / 'scripts'):
                files.add(path)
    for name in ('ntuple_kernel_v120', 'contextual_ntuple_v134', 'frozen_leaf_planning_v135'):
        files.add(ROOT / f'src/acfqp/science/controlled_predictive_{name}.cpp')
    for path in sorted(files):
        target = directory / 'source' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    return len(files)


def run(directory=OUTPUT):
    started = perf_counter(); directory = directory.resolve(); directory.mkdir(parents=True, exist_ok=False)
    capsule = extract_source(); save(directory / 'source_capsule.json', capsule)
    roots = [root for root in read(SOURCE / 'eval_roots.json') if root['query'] == 'risk1']
    candidate = extract_candidate(read(SOURCE / 'generated_candidates.json'), read(NOMINATION / 'retained_roster.json'))
    program = build_program(candidate); roster = build_roster(roots)
    save(directory / 'eval_roots.json', roots); save(directory / 'frozen_candidate.json', candidate)
    save(directory / 'frozen_program.json', program)
    save(directory / 'evaluation_inputs.json', dict(roots=roots, program=program, branch_roster=roster))
    data = dict(schema='acfqp.fixed_program.v167.run', status='frozen', settings=settings(),
        phases={}, phase_order=[], inherited_cost_refs=capsule['cost_refs'], frozen_source_files=snapshot_code(directory))
    save(directory / 'frozen_inputs.json', deepcopy(data)); save(directory / 'run.json', data)
    data.update(status='eval', phase_order=['INPUTS_FROZEN']); save(directory / 'run.json', data)
    data['phases']['EVAL'] = prior.parallel_phase(branch_lifecycle, capsule['snapshots'], 'EVAL', roots, program, directory)
    data['phase_order'].append('EVAL')
    outcomes = [row for life in data['phases']['EVAL']['lifecycles'] for row in read(directory / life['outcomes_ref'])]
    save(directory / 'summary.json', summarize(roots, outcomes))
    data.update(status='complete', seconds=perf_counter() - started, new_parameter_updates=0)
    save(directory / 'run.json', data)
    print(dict(status='complete', seconds=data['seconds'], physical_branches=len(outcomes)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)
