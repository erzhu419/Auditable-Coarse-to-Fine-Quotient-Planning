"""Extend the whole retained V78 acceptance cohort without replaying prefixes."""
from collections import Counter
import argparse
import gzip
import json
from pathlib import Path
import platform
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_lifelong_v77 import Knowledge
from acfqp.science import controlled_predictive_lifelong_planner_v77 as planner
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_terminal_continuation_v79 import extend_episode

SOURCE = ROOT / 'reports/controlled_predictive_decision_v78'
CHECKPOINTS = (39, 75)
QUERIES = dict(reward=dict(reward_weight=1., failure_penalty=0., goal_bonus=0.),
               risk_goal=dict(reward_weight=1., failure_penalty=4., goal_bonus=4.))


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def scalar(score, status, query):
    return (query['reward_weight'] * score / 2048
            - query['failure_penalty'] * (status == 'LOST')
            + query['goal_bonus'] * (status == 'WON'))


def continue_trajectory(raw, model, rule, max_total_steps=2000):
    """Bind the old query/model and restore its planner stream exactly."""
    started = perf_counter()
    prefix = raw['game']
    query = QUERIES[raw['query']]
    work, decisions = Counter(), []
    before = dict(model.counts)
    model_restore = 0
    rng = random.Random(prefix['seed'] + 1000000000000)
    if prefix['status'] == 'CUTOFF' and prefix['steps_count'] < max_total_steps:
        model_restore = 4 * prefix['steps_count']
        for _ in range(model_restore):
            rng.random()

    def act(board, absolute_step):
        decision = planner.choose(board, query, model, rule, rng, work=work)
        decisions.append(dict(step=absolute_step, action=decision['action'],
                              metrics=decision['metrics'], value=decision['value']))
        return decision['action']

    result = extend_episode(prefix, act, max_total_steps=max_total_steps)
    short = dict(score=prefix['return_score'], steps=prefix['steps_count'], status=prefix['status'], work=prefix['work'],
        utility=scalar(prefix['return_score'], prefix['status'], query))
    full = dict(score=result['total_score'], steps=result['total_steps'], status=result['status'],
        utility=scalar(result['total_score'], result['status'], query))
    extension = dict(resumed=result['resumed'], new_steps=result['suffix']['steps_count'],
        work=result['suffix']['work'], planning_counts=dict(work),
        prediction_counts={k: v-before.get(k, 0) for k,v in model.counts.items()
                           if v != before.get(k, 0)},
        restoration_random_draws=result['restoration_random_draws'],
        model_restoration_random_draws=model_restore, seconds=perf_counter()-started)
    row = {key: raw[key] for key in ('stratum', 'root', 'query', 'replica', 'model')}
    row.update(seed=prefix['seed'], short=short, full=full, extension=extension)
    return row, dict(suffix=result['suffix'], decisions=decisions)


def run_stage(lifecycle, checkpoint, folder, rule):
    started = perf_counter()
    source_folder = SOURCE / f'life_{lifecycle}'
    cp_source = source_folder / f'checkpoint_{checkpoint}'
    prefix_path = cp_source / 'acceptance_episodes.jsonl.gz'
    incumbent_path = source_folder / ('initial_knowledge.json' if checkpoint == 39
                                       else 'checkpoint_39/DECISION.json')
    model_paths = dict(incumbent=incumbent_path, candidate=cp_source / 'candidate.json')
    models = {}
    for name, path in model_paths.items():
        payload = json.loads(path.read_text())
        models[name] = Knowledge.from_payload(payload)
        save(folder / f'{name}.json', payload)
    learning = json.loads((cp_source / 'learning.json').read_text())
    expected = learning['acceptance_rollouts']['trajectories']
    stage = dict(episodes=checkpoint, expected_trajectories=expected, trajectories=[],
        prefix_file=str(prefix_path.relative_to(ROOT)),
        model_sources={name: str(path.relative_to(ROOT)) for name,path in model_paths.items()})
    work, planning_work, outcomes = Counter(), Counter(), Counter()
    with gzip.open(prefix_path, 'rt', encoding='utf-8') as inputs, \
         gzip.open(folder / 'suffixes.jsonl.gz', 'wt', encoding='utf-8') as output:
        for index, line in enumerate(inputs):
            raw = json.loads(line)
            row, suffix = continue_trajectory(raw, models[raw['model']], rule)
            row['prefix_line'] = index + 1
            stage['trajectories'].append(row)
            suffix.update(prefix_line=index+1, prefix_file=stage['prefix_file'],
                          stratum=row['stratum'], root=row['root'], query=row['query'],
                          replica=row['replica'], model=row['model'])
            output.write(json.dumps(suffix, allow_nan=False, separators=(',', ':')) + '\n')
            work.update(row['extension']['work'])
            planning_work.update(row['extension']['planning_counts'])
            outcomes[row['full']['status']] += 1
            if (index+1) % 32 == 0:
                output.flush()
                print(json.dumps(dict(phase='suffixes', lifecycle=lifecycle, episodes=checkpoint,
                    completed=index+1, expected=expected, new_transitions=work['sampled_transitions'],
                    outcomes=dict(outcomes))), flush=True)
    stage.update(work=dict(work), planning_counts=dict(planning_work), outcomes=dict(outcomes),
                 seconds=perf_counter()-started)
    save(folder / 'checkpoint.json', stage)
    print(json.dumps(dict(phase='stage_complete', lifecycle=lifecycle, episodes=checkpoint,
        trajectories=len(stage['trajectories']), new_transitions=work['sampled_transitions'],
        outcomes=dict(outcomes))), flush=True)
    return stage


def snapshot(directory):
    new_paths = ['scripts/run_controlled_predictive_terminal_v79.py',
                 'scripts/analyze_controlled_predictive_terminal_v79.py',
                 'specs/PAIRED_TERMINAL_CONTINUATIONS_V79.md',
                 'src/acfqp/science/controlled_predictive_terminal_continuation_v79.py']
    for relative in new_paths:
        target = directory / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    # Inherited code was compared directly with this snapshot before the run.
    for old in (SOURCE / 'source/src').rglob('*.py'):
        target = directory / 'source/src' / old.relative_to(SOURCE / 'source/src')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(old, target)


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    rule_payload = json.loads((SOURCE / 'supplied_dynamics.json').read_text())
    save(directory / 'supplied_dynamics.json', rule_payload)
    rule = LearnedDynamics.from_payload(rule_payload)
    report = dict(schema='acfqp.terminal_continuations.v79', status='running',
        inherited_source=str(SOURCE), platform=platform.platform(), python=sys.version,
        executable=sys.executable, settings=dict(lifecycles=[0, 1, 2],
            checkpoints=list(CHECKPOINTS), queries=QUERIES, expected_trajectories=712,
            max_total_steps=2000, new_transition_ceiling=1367760), lifecycles=[])
    save(directory / 'run.json', report)
    for lifecycle in (0, 1, 2):
        life = dict(id=lifecycle, stages=[])
        report['lifecycles'].append(life)
        for checkpoint in CHECKPOINTS:
            folder = directory / f'life_{lifecycle}/checkpoint_{checkpoint}'
            folder.mkdir(parents=True)
            life['stages'].append(run_stage(lifecycle, checkpoint, folder, rule))
            report['actual_wall_seconds'] = perf_counter()-started
            save(directory / 'run.json', report)
    report.update(status='complete', actual_wall_seconds=perf_counter()-started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
