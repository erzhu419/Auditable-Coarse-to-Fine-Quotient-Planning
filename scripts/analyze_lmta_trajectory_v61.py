"""Independently replay paired trajectories and compare with retained exact means."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from random import Random
from statistics import NormalDist, mean, variance
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
METHODS = ['LOOKAHEAD_1_ANALYTIC', 'LOOKAHEAD_2_ANALYTIC']
IDS = [580000+100*panel+i for panel in range(4) for i in range(16)]
LIMITS = dict(max_planner_action_values=2000000, max_decisions=100000, max_wall_seconds=60.)
PROTOCOL = dict(budget=2, horizon=3, replicates=128, methods=METHODS, graph_ids=IDS,
    seed_base=61000000, seed_graph_stride=1000, limits=LIMITS, calibration_family_size=12, calibration_alpha=.05)
SOURCE_DIRS = dict(policies='reports/lmta_analytic_scale_v58', replay='reports/lmta_analytic_short_v59',
    changed='reports/lmta_changed_policy_v60')
ENV = ('environment_calls', 'rng_draws', 'eligible_edge_attempts', 'successful_edge_attempts', 'seeded_nodes', 'activated_targets')
Z95, ZSIM = NormalDist().inv_cdf(.975), NormalDist().inv_cdf(1-.05/24)


def key(row):
    return row['graph_id'], row['method'], tuple(row['statuses']), row['remaining_budget'], row['remaining_days']


def close(a, b):
    return isinstance(a, (int, float)) and math.isfinite(a) and math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10)


def replay(row, graph, certificates):
    """No planner imports: decisions use certificates; edge draws use an independent implementation."""
    errors, work, env, verified = Counter(), Counter(), Counter(), Counter()
    nodes, edges = graph['nodes'], sorted(map(tuple, graph['edges']))
    indegree = Counter(target for _, target in edges)
    seed = 61000000+row['graph_id']*1000+row['replicate']
    if row['seed'] != seed:
        errors['trajectory_seed'] += 1
    rng, statuses, budget, total = Random(seed), [0]*nodes, 2, 0
    decisions = row['decisions']
    complete = row['status'] == 'complete'
    if (not 1 <= len(decisions) <= 3 or (complete and len(decisions) != 3)
            or row['status'] not in ('complete', 'resource_limit')
            or (complete and row['stop_reason'] is not None)):
        errors['trajectory_status_and_length'] += 1
    for day, decision in enumerate(decisions):
        expected_key = (row['graph_id'], row['method'], tuple(statuses), budget, 3-day)
        if (tuple(decision['statuses']), decision['remaining_budget'], decision['remaining_days']) != expected_key[2:]:
            errors['decision_state_chain'] += 1
        certificate = certificates.get(expected_key)
        if certificate is None:
            errors['missing_policy_certificate'] += 1
        elif any(decision.get(name) != certificate.get(name) for name in
                 ('selected', 'planned_value', 'root_action_values', 'decision_work')):
            errors['policy_or_work_certificate'] += 1
        verified['certificate_queries'] += 1
        work.update(decision['decision_work'])
        if any(not isinstance(v, int) or v < 0 for v in decision['decision_work'].values()):
            errors['nonnegative_integer_decision_work'] += 1
        if any(not close(decision[name], decision[name]) or decision[name] < 0 for name in ('decision_seconds', 'environment_seconds')):
            errors['decision_time'] += 1
        interrupted = not complete and day == len(decisions)-1
        if interrupted:
            if (decision['next_statuses'] is not None or decision['reward'] is not None
                    or decision['environment_work'] != dict.fromkeys(ENV, 0) or decision['environment_seconds'] != 0):
                errors['partial_decision_environment'] += 1
            continue
        selected = decision['selected']
        legal_count = min(statuses.count(0), budget, (budget+2-day)//(3-day))
        if len(selected) != legal_count or len(set(selected)) != len(selected) or any(statuses[node] != 0 for node in selected):
            errors['legal_action_allocation'] += 1
        seeded = list(statuses)
        for node in selected:
            seeded[node] = 1
        successful, eligible, successes = set(), 0, 0
        for source, target in edges:
            uniform = rng.random()
            if seeded[source] == 1 and seeded[target] == 0:
                eligible += 1
                if uniform < 1/indegree[target]:
                    successes += 1
                    successful.add(target)
        expected_env = dict(environment_calls=1, rng_draws=len(edges), eligible_edge_attempts=eligible,
            successful_edge_attempts=successes, seeded_nodes=len(selected), activated_targets=len(successful))
        next_statuses = [2 if status == 1 else status for status in seeded]
        for target in successful:
            next_statuses[target] = 1
        reward = len(selected)+len(successful)
        if decision['next_statuses'] != next_statuses or decision['reward'] != reward or decision['environment_work'] != expected_env:
            errors['independent_transition_replay'] += 1
        verified['verification_random_draws'] += len(edges)
        verified['verification_environment_steps'] += 1
        env.update(expected_env)
        statuses, budget, total = next_statuses, budget-len(selected), total+reward
    if row['return'] != (total if complete else None):
        errors['trajectory_return'] += 1
    return dict(errors=dict(errors), decision_work=dict(work), environment_work=dict(env), verification=dict(verified))


def estimate(groups, exact):
    """Fixed-graph stratified Monte Carlo uncertainty, never between-graph variance."""
    center = mean(mean(values) for values in groups)
    se = math.sqrt(sum(variance(values)/len(values) for values in groups)/len(groups)**2)
    interval = lambda z: [center-z*se, center+z*se]
    return dict(mean=center, exact_mean=exact, error=center-exact, standard_error=se,
        nominal_95_interval=interval(Z95), simultaneous_interval=interval(ZSIM),
        simultaneous_contains_exact=center-ZSIM*se-1e-10 <= exact <= center+ZSIM*se+1e-10)


def compare_work(actual, expected):
    # Counter addition omits zero totals, including all one-day outcome counts.
    return {name: dict(actual=actual.get(name, 0), exact_expected=128*expected[name],
        actual_over_expected=actual.get(name, 0)/(128*expected[name]) if expected[name] else None)
        for name in ('action_value_evaluations', 'transition_outcomes', 'target_probability_evaluations')}


def summarize(manifest, cases, rows, graphs, certificates, exact_analysis):
    started, errors, checks = perf_counter(), Counter(), Counter()
    graph_index = {graph['graph_id']: graph for graph in graphs}
    if (manifest.get('schema') != 'acfqp.lmta_trajectory.v61' or manifest.get('status') != 'complete'
            or manifest.get('protocol') != PROTOCOL or manifest.get('source_directories') != SOURCE_DIRS
            or manifest.get('graphs') != graphs or sorted(graph_index) != IDS
            or manifest.get('cold_decisions') is not True or manifest.get('runtime', {}).get('gc_enabled') is not True):
        errors['manifest_protocol'] += 1
    if exact_analysis.get('integrity', {}).get('passed') is not True or exact_analysis.get('complete_unified_policy_evidence') is not True:
        errors['exact_source_integrity'] += 1
    expected_order = [(g, m) for index, g in enumerate(IDS) for m in (METHODS if index%2 == 0 else METHODS[::-1])]
    if [(c['graph_id'], c['method']) for c in cases] != expected_order:
        errors['case_roster_and_order'] += 1
    grouped, values = defaultdict(list), {}
    for row in rows:
        grouped[row['graph_id'], row['method']].append(row)
    total_work, total_env = Counter(), Counter()
    for case in cases:
        identity = case['graph_id'], case['method']
        block, graph = grouped[identity], graph_index[case['graph_id']]
        work, env, decision_count = Counter(), Counter(), 0
        completed = [row for row in block if row['status'] == 'complete']
        if (case['nodes'] != graph['nodes'] or case['budget'] != 2 or case['horizon'] != 3
                or case['requested_replicates'] != 128 or [r['replicate'] for r in block] != list(range(len(block)))
                or case['trajectory_records'] != len(block) or case['completed_replicates'] != len(completed)
                or not close(case['total_return'], sum(r['return'] for r in completed))):
            errors['block_binding_and_counts'] += 1
        for row in block:
            checked = replay(row, graph, certificates)
            errors.update(checked['errors']); checks.update(checked['verification'])
            for index, decision in enumerate(row['decisions']):
                work.update(decision['decision_work']); decision_count += 1
                charged_limit = (work['action_value_evaluations'] >= LIMITS['max_planner_action_values']
                    or decision_count >= LIMITS['max_decisions'])
                if charged_limit and not (row is block[-1] and row['status']=='resource_limit' and index==len(row['decisions'])-1):
                    errors['continued_after_charged_limit'] += 1
            env.update(checked['environment_work'])
        full = case['status'] == 'complete'
        if ((full and (len(completed) != 128 or case['stop_reason'] is not None))
                or (not full and (case['status'] != 'resource_limit' or len(block)-len(completed) != 1
                    or not block or block[-1]['status'] != 'resource_limit' or block[-1]['stop_reason'] != case['stop_reason']))):
            errors['block_status'] += 1
        if dict(work) != case['decision_work'] or Counter(env) != Counter(case['environment_work']) or decision_count != case['decision_records']:
            errors['block_work_accounting'] += 1
        limits = PROTOCOL['limits']
        expected_stop = ('max_planner_action_values' if work['action_value_evaluations'] >= limits['max_planner_action_values']
            else 'max_decisions' if decision_count >= limits['max_decisions']
            else 'max_wall_seconds' if case['last_limit_check_seconds'] >= limits['max_wall_seconds'] else None)
        if case['stop_reason'] != expected_stop:
            errors['resource_limit_priority'] += 1
        for kind in ('decision', 'environment'):
            if not close(case[kind+'_seconds'], sum(d[kind+'_seconds'] for r in block for d in r['decisions'])):
                errors['block_time_sums'] += 1
        time_names = ('decision_seconds', 'environment_seconds', 'wall_seconds', 'prepare_gc_seconds', 'cleanup_seconds',
            'decision_total_seconds', 'block_seconds', 'serialization_seconds', 'last_limit_check_seconds')
        if (any(not close(case.get(n), case.get(n)) or case[n] < 0 for n in time_names)
                or not close(case['decision_total_seconds'], case['decision_seconds']+case['cleanup_seconds'])
                or not close(case['block_seconds'], case['wall_seconds']+case['cleanup_seconds'])
                or case['wall_seconds']+1e-10 < case['decision_seconds']+case['environment_seconds']):
            errors['block_time_accounting'] += 1
        total_work.update(work); total_env.update(env)
        values[identity] = {row['replicate']: row['return'] for row in completed}
    if set(grouped) != {(c['graph_id'], c['method']) for c in cases}:
        errors['unbound_trajectories'] += 1
    counts = dict(completed_blocks=len(cases), successful_blocks=sum(c['status']=='complete' for c in cases),
        resource_limited_blocks=sum(c['status']=='resource_limit' for c in cases), trajectory_records=len(rows),
        completed_trajectories=sum(len(v) for v in values.values()), decision_records=sum(len(r['decisions']) for r in rows))
    if any(manifest.get(k) != v for k, v in counts.items()):
        errors['manifest_counts'] += 1
    zero_names = ('new_graphs', 'new_full_policy_evaluations', 'new_RL_updates', 'new_MCTS_calls')
    if any(manifest.get(name) != 0 for name in zero_names):
        errors['new_work_scope'] += 1
    runner_times = ('source_read_seconds', 'graph_reconstruction_seconds', 'data_output_seconds', 'whole_runner_seconds')
    if any(not close(manifest.get(n), manifest.get(n)) or manifest[n] < 0 for n in runner_times):
        errors['runner_times'] += 1
    complete = not errors and counts['successful_blocks'] == 128 and counts['completed_trajectories'] == 16384
    panels = []
    if complete:
        for exact in exact_analysis['unified_three_depth_strata']:
            ids = [point['graph_id'] for point in exact['per_graph']]
            estimates = {method: estimate([list(values[g,method].values()) for g in ids], exact['values'][method]['mean']) for method in METHODS}
            paired = estimate([[values[g,METHODS[1]][rep]-values[g,METHODS[0]][rep] for rep in range(128)] for g in ids],
                exact['contrasts']['two_minus_one']['mean'])
            work = {method: dict(sum((Counter(c['decision_work']) for c in cases if c['graph_id'] in ids and c['method']==method), Counter())) for method in METHODS}
            comparisons = {method: compare_work(work[method], exact['expected_work_sums'][method]) for method in METHODS}
            panels.append(dict(nodes=exact['nodes'], stratum=exact['stratum'], graph_count=len(ids), replicates_per_graph=128,
                methods=estimates, paired_two_minus_one=paired, work=comparisons))
    calibration = all(e['simultaneous_contains_exact'] for panel in panels for e in [*panel['methods'].values(), panel['paired_two_minus_one']]) if complete else None
    return dict(schema='acfqp.lmta_trajectory_analysis.v61', protocol=PROTOCOL,
        integrity=dict(passed=not errors, errors=dict(errors)), complete_trajectory_evidence=complete,
        calibration_consistent=calibration, panels=panels,
        calibration=dict(family_size=12, alpha=.05, simultaneous_z=ZSIM, nominal_z=Z95,
            scope='Approximate normal Monte Carlo diagnostic on 64 fixed graphs; not a scientific gate or graph-generalization interval.'),
        accounting=dict(**counts, decision_work=dict(total_work), environment_work=dict(total_env), verification=dict(checks),
            missing_complete_trajectories=16384-counts['completed_trajectories'], new_full_policy_evaluations=0,
            new_analysis_planner_calls=0, new_graphs=0, new_RL_updates=0, new_MCTS_calls=0,
            runner={n:manifest[n] for n in runner_times},
            block_times={n:sum(c[n] for c in cases) for n in ('decision_seconds','environment_seconds','wall_seconds','prepare_gc_seconds','cleanup_seconds','block_seconds','serialization_seconds')},
            analysis_seconds_before_serialization=perf_counter()-started),
        exact_source='V60 unified evidence: changed 580109 one-day policy freshly evaluated; other short policies preserve V59 certificates.',
        scope='Simulator random draws and independent verification draws are separate. Planner outcome enumeration is not environment sampling. Timings are descriptive.')


def read_jsonl(path):
    with path.open() as stream:
        return [json.loads(line) for line in stream]


def analyze_files(output):
    started = perf_counter()
    manifest = json.loads((output/'manifest.json').read_text())
    cases, rows = read_jsonl(output/'cases.jsonl'), read_jsonl(output/'trajectories.jsonl')
    wanted = {key(dict(d, graph_id=r['graph_id'], method=r['method'])) for r in rows for d in r['decisions']}
    certificates = {}
    for source in ('replay', 'changed'):
        with (ROOT/SOURCE_DIRS[source]/'states.jsonl').open() as stream:
            for line in stream:
                record = json.loads(line)
                if source == 'replay' and (record['graph_id'],record['method']) == (580109,METHODS[0]):
                    continue
                identity = key(record)
                if identity in wanted:
                    certificates[identity] = {n:record[n] for n in ('selected','planned_value','root_action_values','decision_work')}
    graphs = json.loads((ROOT/SOURCE_DIRS['policies']/'manifest.json').read_text())['graphs']
    exact = json.loads((ROOT/SOURCE_DIRS['changed']/'analysis.json').read_text())
    analysis = summarize(manifest, cases, rows, graphs, certificates, exact)
    analysis['accounting'].update(retained_certificate_keys=len(certificates), requested_certificate_keys=len(wanted),
        analysis_wall_seconds_including_reads=perf_counter()-started)
    (output/'analysis.json').write_text(json.dumps(analysis, indent=2)+'\n')
    print(json.dumps(dict(integrity=analysis['integrity'], complete=analysis['complete_trajectory_evidence'], calibration=analysis['calibration_consistent'])))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT/'reports/lmta_trajectory_v61')
    args = parser.parse_args()
    with (args.output/'analysis_repair_attempt.json').open('x') as attempt:
        started, error = perf_counter(), None
        try:
            analyze_files(args.output)
        except Exception as caught:
            error = f'{type(caught).__name__}: {caught}'
            raise
        finally:
            attempt.write(json.dumps(dict(wall_seconds=perf_counter()-started,
                exit_code=int(error is not None), error=error), indent=2)+'\n')


if __name__ == '__main__':
    main()
