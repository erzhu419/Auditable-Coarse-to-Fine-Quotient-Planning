"""Repeat fixed V81 heldout choices with first-only and continuing interventions."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_policy_advantage_v81 import Policy, QUERIES
from acfqp.science.controlled_predictive_policy_roots_v82 import prepare_roots
from acfqp.science.controlled_predictive_policy_effects_v82 import ARMS, sample_triplet
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics

SOURCE = ROOT / 'reports/controlled_predictive_policy_iteration_v81'
REPLICAS = 16


def save(path, payload):
    path.write_text(json.dumps(payload, allow_nan=False, separators=(',', ':'))+'\n')


def snapshot(directory):
    files = ['scripts/run_controlled_predictive_policy_effects_v82.py',
             'scripts/analyze_controlled_predictive_policy_effects_v82.py',
             'specs/PAIRED_POLICY_EFFECTS_V82.md']
    files += [f'src/acfqp/science/controlled_predictive_{name}_v{version}.py' for name, version in (
        ('policy_roots', 82), ('policy_effects', 82), ('policy_advantage', 81),
        ('decision_experience', 78), ('lifelong', 77), ('lifelong_planner', 77),
        ('lifelong_experience', 77), ('relational_dynamics', 69), ('effect_contract', 74),
        ('grouped_contract', 73), ('local_contract', 72))]
    files += ['src/acfqp/domains/standard_2048.py', 'src/acfqp/domains/g2048.py']
    for relative in files:
        target = directory / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)


def histories(raw):
    return {item['method']: [(step['board'], step['action'], step['next_board'], step['score'], step['status'])
                            for step in item['game']['steps']] for item in raw}


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    payload = json.loads((SOURCE / 'supplied_dynamics.json').read_text())
    save(directory / 'supplied_dynamics.json', payload)
    rule = LearnedDynamics.from_payload(payload)
    source_run = json.loads((SOURCE / 'run.json').read_text())
    report = dict(schema='acfqp.fixed_policy_effects.v82', status='preparing',
        platform=platform.platform(), executable=sys.executable, python=sys.version,
        inherited_source=str(SOURCE), settings=dict(lifecycles=[0, 1, 2], queries=QUERIES,
            replicas=REPLICAS, methods=list(ARMS), max_steps=2000,
            roots_per_query_per_lifecycle=4, trajectory_ceiling=1152, transition_ceiling=2304000),
        lifecycles=[])
    policies = {}
    # Freeze every root and model before drawing the first new environment sample.
    for lifecycle in report['settings']['lifecycles']:
        folder = directory / f'life_{lifecycle}'
        folder.mkdir()
        roots, preparation = prepare_roots(SOURCE, lifecycle, rule)
        assert len(roots) == 8
        assert Counter(root['query'] for root in roots) == {query: 4 for query in QUERIES}
        p1_payload = json.loads((SOURCE / f'life_{lifecycle}/iteration_1/current_policy.json').read_text())
        p1 = Policy.from_payload(p1_payload)
        assert p1.iteration == 1 and p1.parent.iteration == 0
        policies[lifecycle] = (Policy.from_payload(p1.parent.to_payload()), p1)
        save(folder / 'P0.json', p1.parent.to_payload())
        save(folder / 'P1.json', p1_payload)
        save(folder / 'fixed_roots.json', roots)
        old = next(life for life in source_run['lifecycles'] if life['id'] == lifecycle)['rounds'][0]
        inherited = dict(behavior_work=old['behavior']['work'], branch_work=old['branches']['work'],
            construction_costs={key: value for key, value in old['methods']['CURRENT']['costs'].items()
                                if key not in ('evaluation_seconds', 'total_seconds')},
            fitting_counts=old['update']['counts'])
        report['lifecycles'].append(dict(id=lifecycle, preparation=preparation,
            inherited_policy_construction=inherited, roots=[dict(root=root, games=[]) for root in roots]))
    report['status'] = 'running'
    save(directory / 'run.json', report)
    for life in report['lifecycles']:
        lifecycle = life['id']
        p0, p1 = policies[lifecycle]
        folder = directory / f'life_{lifecycle}'
        for record in life['roots']:
            root = record['root']
            tick = perf_counter()
            ground, planning, outcomes = Counter(), Counter(), Counter()
            paired_first, identical_no_override = True, True
            no_override = root['selected_action'] == root['reference_action']
            path = folder / f"{root['query']}_root_{root['root_index']}.jsonl.gz"
            with gzip.open(path, 'wt') as output:
                for replica in range(REPLICAS):
                    games, raw, log = sample_triplet(root, p0, p1, rule, lifecycle, replica)
                    traces = histories(raw)
                    paired_first &= traces['FIRST_ONLY'][0] == traces['FULL_UPDATE'][0]
                    if no_override:
                        identical_no_override &= traces['PARENT'] == traces['FIRST_ONLY']
                    assert paired_first and identical_no_override
                    for method, game in games.items():
                        record['games'].append(dict(method=method, **game))
                        ground.update(game['environment_counts'])
                        planning.update(game['planning_counts'])
                        outcomes[game['status']] += 1
                    output.write(json.dumps(dict(replica=replica, root=root, trajectories=raw),
                                            allow_nan=False, separators=(',', ':'))+'\n')
            record.update(work=dict(ground=dict(ground), planning=dict(planning)), outcomes=dict(outcomes),
                seconds=perf_counter()-tick,
                wiring=dict(same_first_transition_first_full=paired_first,
                    no_override_parent_first_identical=identical_no_override if no_override else None))
            report['actual_wall_seconds'] = perf_counter()-started
            save(directory / 'run.json', report)
            print(json.dumps(dict(phase='root', lifecycle=lifecycle, query=root['query'],
                root_index=root['root_index'], override=not no_override, trajectories=len(record['games']),
                sampled_transitions=ground['sampled_transitions'], outcomes=dict(outcomes))), flush=True)
    report.update(status='complete', actual_wall_seconds=perf_counter()-started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
