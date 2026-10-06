"""Independent fresh-tape and chronological audit of the V229 lifecycle.

The scoped producer and task module are not imported.  The public roster,
hidden kernels, retained integer observations and all model decisions are
reconstructed before any oracle result is evaluated.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from itertools import combinations
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import scoped_repair_v229_math as math

OUTPUT = ROOT/'reports/scoped_lifecycle_v229'
ARMS, OPERATORS, SUPPORT = math.ARMS, math.OPERATORS, math.SUPPORT
STAGES = ('A', 'B', 'A_RETURN')
TARGET_INDEXES = tuple(range(3, 27))+tuple(range(30, 78))
SOURCE_INDEXES = (0, 1, 2, 27, 28, 29)
WEATHER = {
    'normal': (F(9, 10), F(17, 20), F(1, 100), F(7, 50), F(1, 4)),
    'wet': (F(99, 100), F(7, 10), F(3, 25), F(9, 50), F(9, 10)),
    'blocked': (F(13, 20), F(4, 5), F(1, 100), F(19, 100), F(2, 5)),
}
SOURCE_FILES = (
    'scripts/__init__.py',
    'src/acfqp/__init__.py',
    'src/acfqp/science/__init__.py',
    'src/acfqp/artifacts.py',
    'src/acfqp/build_coverage.py',
    'src/acfqp/core.py',
    'src/acfqp/enumeration.py',
    'src/acfqp/domains/__init__.py',
    'src/acfqp/domains/g2048.py',
    'src/acfqp/domains/matching_buffer.py',
    'src/acfqp/domains/semantic.py',
    'src/acfqp/domains/standard_2048.py',
    'src/acfqp/science/latent_resource_2048_v1.py',
    'src/acfqp/science/query_calibration_v215.py',
    'src/acfqp/science/scoped_repair_v228.py',
    'src/acfqp/science/scoped_union_v228.py',
    'src/acfqp/science/scoped_queries_v228.py',
    'src/acfqp/science/scoped_route_task_v228.py',
    'src/acfqp/science/mixture_confidence_v225.py',
    'src/acfqp/science/assignment_union_v222.py',
    'src/acfqp/science/fixed_source_acquisition_v219.py',
    'src/acfqp/science/joint_acquisition_v218.py',
    'src/acfqp/science/source_stopping_v216.py',
    'src/acfqp/science/query_sufficient_v214.py',
    'src/acfqp/science/latent_mechanisms_v213.py',
    'src/acfqp/science/latent_route_task_v213.py',
    'src/acfqp/science/strategic_maintenance_v210.py',
    'src/acfqp/science/contracted_risk_reuse_v209.py',
    'src/acfqp/science/constrained_acquisition_v208.py',
    'src/acfqp/science/online_lifecycle_v206.py',
    'src/acfqp/science/conditioned_mechanisms_v205.py',
    'src/acfqp/science/mechanism_switch_task_v205.py',
    'src/acfqp/science/target_risk_acquisition_v204.py',
    'src/acfqp/science/robust_route_planning_v203.py',
    'src/acfqp/science/continual_route_kernels_v202.py',
    'src/acfqp/science/structured_route_task_v201.py',
    'src/acfqp/science/persistent_evidence_v221.py',
    'scripts/run_conditioned_mechanisms_v205.py',
    'scripts/run_persistent_evidence_v221.py',
    'scripts/analyze_conditioned_mechanisms_v205.py',
    'scripts/analyze_latent_mechanisms_v213.py',
    'scripts/analyze_joint_acquisition_v218.py',
    'scripts/analyze_fixed_source_acquisition_v219.py',
    'scripts/analyze_assignment_union_v222.py',
    'scripts/analyze_mixture_confidence_v225.py',
    'scripts/scoped_repair_v229_math.py',
    'scripts/scoped_lifecycle_v229_stats.py',
    'scripts/run_scoped_lifecycle_v229.py',
    'scripts/analyze_scoped_lifecycle_v229.py',
    'tests/test_scoped_lifecycle_v229.py',
    'tests/test_scoped_lifecycle_v229_replay.py',
    'specs/SCOPED_REPAIR_V228.md',
    'specs/SCOPED_REPAIR_V228_PROOF.md',
    'specs/SCOPED_LIFECYCLE_V229.md',
    'reports/v229_runtime_tmp/run_stage.py',
)


def law(label):
    short, delivery, lost, recovery, retry = WEATHER[label]
    return dict(SHORT_PASS=dict(DELIVERY=short, LOST=1-short),
                DETOUR_PASS=dict(DELIVERY=delivery, LOST=lost, RECOVERY=recovery),
                RECOVERY_RETRY=dict(DELIVERY=retry, LOST=1-retry))


def changed_law(base, operator):
    result = deepcopy(base)
    right = 'RECOVERY' if operator == 'DETOUR_PASS' else 'LOST'
    result[operator]['DELIVERY'], result[operator][right] = (
        base[operator][right], base[operator]['DELIVERY'])
    return result


def world(life):
    a_labels = list(WEATHER)
    random.Random(248100+life).shuffle(a_labels)
    b_labels = list(WEATHER)
    random.Random(248900+life).shuffle(b_labels)
    if b_labels == a_labels:
        b_labels = b_labels[1:]+b_labels[:1]
    permutation = [a_labels.index(label) for label in b_labels]
    changed = OPERATORS[life % 3]
    a_laws = [law(label) for label in a_labels]
    cases = [dict(id=f'v228_l{life:02d}_source_{i}', operating='high',
                  retry_cost='19/20', context='A', stage='SOURCE') for i in range(3)]
    laws, identities, ranges = deepcopy(a_laws), list(range(3)), {}
    for stage_number, stage in enumerate(STAGES):
        if stage == 'B':
            for i, old_index in enumerate(permutation):
                cases.append(dict(id=f'v228_l{life:02d}_b_source_{i}', operating='high',
                                  retry_cost='19/20', context='B', stage='B_SOURCE'))
                laws.append(changed_law(a_laws[old_index], changed))
                identities.append(i)
        types = list(range(3))*8
        costs = [(operating, retry) for operating in ('low', 'high')
                 for retry in ('17/20', '19/20')]*6
        random.Random(248200+100*stage_number+life).shuffle(types)
        random.Random(248600+100*stage_number+life).shuffle(costs)
        start = len(cases)
        for i, (identity, (operating, retry)) in enumerate(zip(types, costs)):
            cases.append(dict(id=f'v228_l{life:02d}_{stage.lower()}_{i:02d}',
                              operating=operating, retry_cost=retry,
                              context='B' if stage == 'B' else 'A', stage=stage))
            base = a_laws[permutation[identity] if stage == 'B' else identity]
            laws.append(changed_law(base, changed) if stage == 'B' else deepcopy(base))
            identities.append(identity)
        ranges[stage] = [start, len(cases)]
    metadata = dict(changed_operator=changed, source_labels=a_labels,
                    b_source_labels=b_labels, b_to_a=permutation, stage_ranges=ranges,
                    source_indexes=[0, 1, 2], b_source_indexes=[27, 28, 29],
                    changes_per_type=1, public_context=True)
    return cases, laws, identities, metadata


def read(name):
    return json.loads((OUTPUT/name).read_text())


def save(name, value):
    (OUTPUT/name).write_text(json.dumps(math.exact_json(value), indent=2)+'\n')


def covered(box, current_law):
    return all(lo <= current_law[operator][category] <= hi
               for operator, row in box.items()
               for category, (lo, hi) in row['bounds'].items())


def oracle_goal(pure):
    utility = lambda vector: vector[0]+4*vector[2]
    options = [utility(vector) for vector in pure.values() if vector[1] <= F(1, 20)]
    for left, right in combinations(pure.values(), 2):
        if min(left[1], right[1]) < F(1, 20) < max(left[1], right[1]):
            weight = (F(1, 20)-right[1])/(left[1]-right[1])
            options.append(weight*utility(left)+(1-weight)*utility(right))
    return max(options)


def true_candidate(case, identity, metadata, arm):
    if case['context'] == 'A':
        return 'A/'+str(identity)
    if arm == 'REBUILD_CS':
        return 'rebuild/'+str(identity)
    branch = metadata['changed_operator']+':'+''.join(map(str, metadata['b_to_a']))
    return branch+'/'+str(identity)


def mean(values):
    values = list(values)
    return sum(values)/len(values)


def metrics(rows):
    points = [point for row in rows for point in row['history']]
    return dict(targets=len(rows), target_samples=sum(row['spent'] for row in rows),
        execution_certified=sum(row['execution_certified'] for row in rows),
        goal_impossible_certified=sum(row['goal_impossible'] for row in rows),
        oracle_unreachable=sum(F(row['oracle_goal']) < 2 for row in rows),
        false_impossible_certificates=sum(row['goal_impossible'] and F(row['oracle_goal']) >= 2 for row in rows),
        goal_resolved=sum(row['execution_certified'] or row['goal_impossible'] for row in rows),
        query_certified=sum(row['query_certified'] for row in rows),
        resolved_queries=sum((row['execution_certified'] or row['goal_impossible']) and row['query_certified']
                             for row in rows),
        actual_utility=mean(float(F(row['terminal']['actual_utility'])) for row in rows),
        actual_query_regret=mean(float(F(query['regret'])) for row in rows for query in row['query_post'].values()),
        maximum_actual_risk=max(float(F(point['actual'][1])) for point in points),
        point_commits=sum(row['point_committed'] for row in rows),
        wrong_point_commits=sum(row['point_committed'] and not row['point_commit_correct'] for row in rows))


def summarize(results, source_costs, model_seconds, work, common_a):
    arms = {}
    for arm in ARMS:
        rows = [row for row in results if row['arm'] == arm]
        stage = {name: metrics([row for row in rows if row['stage'] == name]) for name in STAGES}
        late = metrics([row for row in rows if row['stage'] == 'B' and row['index'] >= 42])
        total = metrics(rows)
        source = sum(source_costs[arm])
        total.update(source_samples=source, total_samples=source+total['target_samples'],
                     model_processing_seconds=sum(model_seconds[arm]),
                     model_processing_seconds_per_life=model_seconds[arm], stages=stage, late_b=late)
        arms[arm] = total
    contrasts = {}
    for reference in ('REBUILD_CS', 'PARAM'):
        for key in (reference.lower()+'_minus_repair_samples', reference.lower()+'_minus_repair_b_samples',
                    'repair_minus_'+reference.lower()+'_late_b_utility',
                    'repair_minus_'+reference.lower()+'_late_b_regret',
                    'repair_minus_'+reference.lower()+'_late_b_resolved_queries'):
            contrasts[key] = []
    for life in range(12):
        rows = {arm: [row for row in results if row['life'] == life and row['arm'] == arm] for arm in ARMS}
        costs = {arm: source_costs[arm][life]+sum(row['spent'] for row in rows[arm]) for arm in ARMS}
        b_cost = {arm: sum(row['spent'] for row in rows[arm] if row['stage'] == 'B') for arm in ARMS}
        late = {arm: metrics([row for row in rows[arm] if row['stage'] == 'B' and row['index'] >= 42])
                for arm in ARMS}
        for reference in ('REBUILD_CS', 'PARAM'):
            values = dict(
                **{reference.lower()+'_minus_repair_samples': costs[reference]-costs['REPAIR_CS'],
                   reference.lower()+'_minus_repair_b_samples': b_cost[reference]-b_cost['REPAIR_CS']},
                **{'repair_minus_'+reference.lower()+'_late_b_utility':
                       late['REPAIR_CS']['actual_utility']-late[reference]['actual_utility'],
                   'repair_minus_'+reference.lower()+'_late_b_regret':
                       late['REPAIR_CS']['actual_query_regret']-late[reference]['actual_query_regret'],
                   'repair_minus_'+reference.lower()+'_late_b_resolved_queries':
                       late['REPAIR_CS']['resolved_queries']-late[reference]['resolved_queries']})
            for key, value in values.items():
                contrasts[key].append(value)
    rng = random.Random(251900)
    boot = {key: [] for key in contrasts}
    for _ in range(5000):
        indexes = [rng.randrange(12) for _ in range(12)]
        work['bootstrap_index_draws'] += 12
        for key, values in contrasts.items():
            boot[key].append(mean(values[index] for index in indexes))
            work['bootstrap_mean_terms'] += 12
    intervals = {key: dict(mean=mean(values), ci=[sorted(boot[key])[124], sorted(boot[key])[4874]])
                 for key, values in contrasts.items()}
    history = [point for row in results for point in row['history']]
    repair = arms['REPAIR_CS']
    ratio = sum(model_seconds['REPAIR_CS'])/sum(model_seconds['REBUILD_CS'])
    conditions = dict(
        RISK_SCOPE=all(F(point['actual'][1]) <= F(1, 20) and F(point['risk_upper']) <= F(1, 20)
                       and point['coverage'] and point['true_candidate'] and point['true_candidate_coverage']
                       and point['query_bounds_ok']
                       and point['goal_upper_ok'] for point in history)
            and all(row['true_branch_retained'] and row['true_masks_retained'] for row in results)
            and all(arm['wrong_point_commits'] == 0 and arm['false_impossible_certificates'] == 0
                    for arm in arms.values()),
        B_QUALITY=repair['late_b']['resolved_queries'] >= 108
            and repair['late_b']['actual_query_regret'] <= .05
            and all(repair['late_b']['resolved_queries'] >= arms[reference]['late_b']['resolved_queries']
                    and intervals['repair_minus_'+reference.lower()+'_late_b_utility']['ci'][0] >= -.05
                    for reference in ('REBUILD_CS', 'PARAM')),
        OLD_RETENTION=common_a and repair['stages']['A_RETURN']['resolved_queries'] >= 216
            and all(repair['stages'][stage]['actual_query_regret'] <= .05 for stage in ('A', 'A_RETURN')),
        REBUILD_REFERENCE=intervals['rebuild_cs_minus_repair_samples']['mean'] >= 64
            and intervals['rebuild_cs_minus_repair_samples']['ci'][0] > 0,
        PARAMETER_REFERENCE=intervals['param_minus_repair_samples']['mean'] >= 64
            and intervals['param_minus_repair_samples']['ci'][0] > 0,
        PROCESSING_COST=ratio <= 1.25)
    complete = len(results) == 2592 and all(
        arms[arm]['stages'][stage]['targets'] == 288 for arm in ARMS for stage in STAGES)
    return dict(complete=complete, arms=arms, contrasts=contrasts, bootstrap=intervals, conditions=conditions,
        common_A_paths=common_a, processing_ratio_repair_to_rebuild=ratio,
        bootstrap_design=dict(unit='whole_paired_lifecycle', lives=12, seed=251900,
                              repeats=5000, interval='95_percent_percentile'),
        confidence=dict(scope='per_arm_per_lifecycle', delta=.05, member_streams=504,
                        member_delta=.025, member_threshold=20160, A_pool_streams=21,
                        A_pool_delta=.0125, B_pool_streams=21, B_pool_delta=.0125, pool_threshold=1680),
        decision='SCOPED_REPAIR_LIFECYCLE_SUPPORTED' if complete and all(conditions.values())
                 else 'SCOPED_REPAIR_LIFECYCLE_NOT_SUPPORTED')


PLAN_FIELDS = ('mix', 'predicted', 'predicted_utility', 'risk_upper', 'utility_lower',
               'envelopes', 'risks', 'goals_lower', 'pure_vectors', 'candidates',
               'candidate_labels', 'mode', 'posterior', 'queries', 'query_certificates',
               'query_ready', 'goal_upper', 'goal_impossible')
FLAGS = ('execution_certified', 'goal_impossible', 'query_certified', 'fallback')


def compact_box(block):
    return {op: dict(bounds=deepcopy(row['bounds'])) for op, row in block.items()}


def compact_plan(plan):
    result = {key: deepcopy(plan[key]) for key in PLAN_FIELDS}
    result['envelopes'] = compact_box(result['envelopes'])
    return result


def compact_bank(bank, include_scope=False):
    result = dict(bounds=[compact_box(box) for box in bank['bounds']],
                  masks=deepcopy(bank['masks']), no_feasible=bank['no_feasible'])
    if include_scope:
        result['changed_op'] = bank['changed_op']
        if 'permutation' in bank:
            result['permutation'] = bank['permutation']
    return result


def compact_state(state):
    result = dict(a=compact_bank(state['a']),
                  b=None if state['b'] is None else {
                      name: compact_bank(bank, True) for name, bank in state['b'].items()},
                  b_points=deepcopy(state['b_points']))
    if 'a_at_switch' in state:
        result['a_at_switch'] = [compact_box(box) for box in state['a_at_switch']]
    return result


def restored_plan(saved):
    plan = deepcopy(saved)
    for key in ('predicted_utility', 'risk_upper', 'utility_lower', 'goal_upper'):
        plan[key] = F(plan[key])
    plan['mix'] = [(name, F(weight)) for name, weight in plan['mix']]
    plan['predicted'] = list(map(F, plan['predicted']))
    for key in ('risks', 'goals_lower'):
        plan[key] = {name: F(value) for name, value in plan[key].items()}
    plan['pure_vectors'] = {name: list(map(F, vector)) for name, vector in plan['pure_vectors'].items()}
    plan['posterior'] = {op: {cat: F(value) for cat, value in row.items()}
                         for op, row in plan['posterior'].items()}
    for row in plan['envelopes'].values():
        row['bounds'] = {cat: list(map(F, pair)) for cat, pair in row['bounds'].items()}
    for row in plan['query_certificates'].values():
        row['regret_upper'] = F(row['regret_upper'])
    return plan


def retained_rows(life):
    path = OUTPUT/f'records_life_{life:02d}.jsonl'
    return [json.loads(line) for line in path.read_text().splitlines()]


def arm_order(life):
    shift = life % len(ARMS)
    return ARMS[shift:]+ARMS[:shift]


def draw_batch(rng, current_law, operator, number, work):
    increments = dict.fromkeys(SUPPORT[operator], 0)
    for _ in range(number):
        value, cumulative = rng.random(), F(0)
        for key in ('controlled_samples', 'controlled_resets', 'environment_random_draws'):
            work[key] += 1
        for category in SUPPORT[operator]:
            cumulative += current_law[operator][category]
            work['sampling_threshold_accumulations'] += 1
            work['sampling_threshold_comparisons'] += 1
            if value < float(cumulative):
                increments[category] += 1
                break
    return increments


def reconstruct_sources(rows, worlds, work):
    lookup = {(row['life'], row['slot'], row['operator'], row['draw_start']): row for row in rows}
    flags = dict(complete=len(rows) == len(lookup) == 3456,
                 seeds=True, increments=True, budgets=True, context=True)
    libraries = []
    for life in range(12):
        scopes = {'a': [], 'b': []}
        for slot, index in enumerate(SOURCE_INDEXES):
            context = 'A' if slot < 3 else 'B'
            amount = 384 if context == 'A' else 128
            anchor = math.empty()
            for j, operator in enumerate(OPERATORS):
                seed = 249000+(life*6+slot)*3+j
                rng = random.Random(seed)
                for start in range(0, amount, 16):
                    row = lookup[life, slot, operator, start]
                    increments = draw_batch(rng, worlds[life][1][index], operator, 16, work)
                    flags['seeds'] &= row['seed'] == seed
                    flags['context'] &= row['context'] == context and row['index'] == index
                    flags['increments'] &= row['draw_end'] == start+16 and row['increments'] == increments
                    for category, count in increments.items():
                        anchor[operator][category] += count
                flags['budgets'] &= sum(anchor[operator].values()) == amount
            scopes[context.lower()].append(anchor)
        libraries.append(dict(life=life, **scopes))
    return libraries, flags


def same_a_rows(rows):
    common = True
    by_index = {(row['index'], row['arm']): row for row in rows}
    for index in tuple(range(3, 27))+tuple(range(54, 78)):
        reference = by_index[index, ARMS[0]]
        for arm in ARMS[1:]:
            row = by_index[index, arm]
            excluded = {'arm', 'library_before', 'library_after'}
            common &= {key: value for key, value in reference.items() if key not in excluded} == {
                key: value for key, value in row.items() if key not in excluded}
            common &= all(reference[key]['a'] == row[key]['a'] for key in ('library_before', 'library_after'))
    return common


def true_bank(state, case, metadata, arm):
    if case['context'] == 'A':
        return state['a']
    name = ('rebuild' if arm == 'REBUILD_CS' else
            metadata['changed_operator']+':'+''.join(map(str, metadata['b_to_a'])))
    return state['b'][name]


def score_point(plan, member, state, case, current_law, identity, metadata, arm, spent, work):
    result = math.score(plan, current_law, case, spent, work)
    key = true_candidate(case, identity, metadata, arm)
    queries = math.query_score(plan['queries'], current_law, case)
    result.update(true_candidate=key in plan['candidates'],
                  query_bounds_ok=all(F(0) <= queries[query]['regret'] <= certificate['regret_upper']
                                      for query, certificate in plan['query_certificates'].items()),
                  goal_upper_ok=oracle_goal(math.vectors(case, current_law)) <= plan['goal_upper'])
    bank = true_bank(state, case, metadata, arm)
    block = math.candidates(bank, member, work).get(identity)
    true_box = block is not None and covered(block, current_law)
    # A coverage miss is scientific evidence, not a replay mismatch. It enters
    # RISK_SCOPE separately from the coordinate union's coverage.
    result['true_candidate_coverage'] = true_box
    return result, true_box


def evaluate(libraries, worlds, work):
    results, candidate_boxes = [], Counter()
    for life in range(12):
        cases, laws, identities, metadata = worlds[life]
        states = {arm: math.prepare(libraries[life]['a'], arm, work) for arm in ARMS}
        a_indexes, b_indexes = [], []
        for row in retained_rows(life):
            index, arm, case = row['index'], row['arm'], row['case']
            if index == 30 and arm == arm_order(life)[0]:
                for current in states.values():
                    math.begin_b(current, libraries[life]['b'], work)
            state = states[arm]
            member, spent = math.empty(), 0
            initial = restored_plan(row['initial_plan'])
            scored, true_box = score_point(initial, member, state, case, laws[index], identities[index],
                                          metadata, arm, spent, work)
            history = [scored]
            candidate_boxes['points'] += 1
            candidate_boxes['covered'] += true_box
            for batch in row['batches']:
                for category, count in batch['increments'].items():
                    member[batch['operator']][category] += count
                spent += 16
                plan = restored_plan(batch['plan'])
                scored, true_box = score_point(plan, member, state, case, laws[index], identities[index],
                                              metadata, arm, spent, work)
                history.append(scored)
                candidate_boxes['points'] += 1
                candidate_boxes['covered'] += true_box
            terminal = restored_plan(row['terminal_plan'])
            event = math.advance(state, member, case, terminal, work)
            if arm == arm_order(life)[0]:
                (b_indexes if case['context'] == 'B' else a_indexes).append(index)
            bank = true_bank(state, case, metadata, arm)
            source_indexes = (0, 1, 2) if case['context'] == 'A' else (27, 28, 29)
            indexes = a_indexes if case['context'] == 'A' else b_indexes
            branch_retained = not bank['no_feasible'] and len(bank['bounds']) == 3 and all(
                covered(box, laws[source_index]) for box, source_index in zip(bank['bounds'], source_indexes))
            masks_retained = len(bank['masks']) == len(indexes) and all(
                identities[member_index] in mask for member_index, mask in zip(indexes, bank['masks']))
            commit = event.get('point_commit')
            results.append(dict(life=life, index=index, arm=arm, stage=case['stage'], spent=spent,
                **{key: row[key] for key in FLAGS}, history=history, terminal=history[-1],
                query_pre=math.query_score(initial['queries'], laws[index], case),
                query_post=math.query_score(terminal['queries'], laws[index], case),
                oracle_goal=oracle_goal(math.vectors(case, laws[index])),
                true_branch_retained=branch_retained, true_masks_retained=masks_retained,
                point_committed=commit is not None,
                point_commit_correct=commit is not None and commit['index'] == identities[index]))
    return results, candidate_boxes


def analyze():
    begun = perf_counter()
    checks, replay_work, scoring_work = [], Counter(), Counter()
    source_draws = Counter()
    target_draws = {arm: Counter() for arm in ARMS}
    planning = {arm: Counter() for arm in ARMS}

    def check(name, value):
        checks.append(dict(name=name, passed=bool(value)))

    try:
        check('complete_frozen_code_specification_and_audit_manifest',
              read('source_manifest.json') == [dict(path=name) for name in SOURCE_FILES])
        check('retained_code_and_protocol_snapshots_match_run_sources', all(
            (OUTPUT/'source_code'/name).read_bytes() == (ROOT/name).read_bytes() for name in SOURCE_FILES))
        worlds = [world(life) for life in range(12)]
        check('fixed_public_cases_without_hidden_types_or_changes', math.same(read('cases.json'), [
            dict(life=life, cases=worlds[life][0]) for life in range(12)]))
        libraries, flags = reconstruct_sources(read('source_records.json'), worlds, source_draws)
        for name, flag in flags.items():
            check('fresh_paid_A_B_sources_'+name, flag)
        check('source_evidence_reconstructed_from_actual_observations',
              math.same(read('source_evidence.json'), libraries))
        common_a = True
        for life in range(12):
            cases = worlds[life][0]
            rows = retained_rows(life)
            expected_order = [(life, index, arm) for index in TARGET_INDEXES for arm in arm_order(life)]
            check(f'life_{life}_complete_unique_chronological_targets',
                  [(row['life'], row['index'], row['arm']) for row in rows] == expected_order)
            common_a &= same_a_rows(rows)
            states = {arm: math.prepare(libraries[life]['a'], arm, planning[arm]) for arm in ARMS}
            flags = dict(plans=True, choices=True, counts=True, seeds=True,
                         state=True, certificates=True, fees=True, isolation=True,
                         all_ended_members=True)
            for row in rows:
                index, arm = row['index'], row['arm']
                if index == 30 and arm == arm_order(life)[0]:
                    for other in ARMS:
                        math.begin_b(states[other], libraries[life]['b'], planning[other])
                case, state = cases[index], states[arm]
                before = deepcopy(state)
                flags['state'] &= math.same(row['library_before'], compact_state(state))
                flags['plans'] &= row['case'] == case
                seeds = {operator: 250000+(life*78+index)*3+j for j, operator in enumerate(OPERATORS)}
                flags['seeds'] &= row['seeds'] == seeds
                rng = {operator: random.Random(seed) for operator, seed in seeds.items()}
                member, spent, consumed = math.empty(), 0, Counter()
                plan = math.make_plan(member, case, state, planning[arm])
                flags['plans'] &= math.same(row['initial_plan'], compact_plan(plan))
                for batch in row['batches']:
                    choice = math.choose(member, case, state, plan, spent, planning[arm])
                    flags['choices'] &= choice is not None and math.same(batch['choice'], choice)
                    operator = choice['operator']
                    increments = draw_batch(rng[operator], worlds[life][1][index], operator, 16, target_draws[arm])
                    flags['counts'] &= batch['operator'] == operator and batch['draw_start'] == consumed[operator]
                    flags['counts'] &= batch['increments'] == increments and sum(increments.values()) == 16
                    for category, count in increments.items():
                        member[operator][category] += count
                    consumed[operator] += 16
                    spent += 16
                    flags['counts'] &= batch['draw_end'] == consumed[operator] and batch['spent'] == spent
                    plan = math.make_plan(member, case, state, planning[arm])
                    flags['plans'] &= math.same(batch['plan'], compact_plan(plan))
                flags['choices'] &= math.choose(member, case, state, plan, spent, planning[arm]) is None
                split = math.finish(plan)
                flags['certificates'] &= all(row[key] == split[key] for key in FLAGS)
                flags['plans'] &= math.same(row['terminal_plan'], compact_plan(split['execution_plan']))
                flags['counts'] &= math.same(row['member'], member)
                flags['fees'] &= row['spent'] == spent and 0 <= spent <= 384
                # Planning and forecasts have not committed evidence.
                flags['state'] &= state == before
                event = math.advance(state, member, case, plan, planning[arm])
                flags['state'] &= math.same(row['advance'], event)
                flags['state'] &= math.same(row['library_after'], compact_state(state))
                untouched = 'a' if case['context'] == 'B' else 'b'
                flags['isolation'] &= state[untouched] == before[untouched]
                if case['context'] == 'B':
                    count = index-29
                    flags['all_ended_members'] &= all(len(bank['members']) == count for bank in state['b'].values())
                else:
                    count = index-2 if case['stage'] == 'A' else 24+index-53
                    flags['all_ended_members'] &= len(state['a']['members']) == count
                expected = dict(life=life, index=index, case=case, arm=arm, seeds=seeds,
                    initial_plan=row['initial_plan'], batches=row['batches'], spent=spent, member=member,
                    terminal_plan=compact_plan(plan), advance=event,
                    library_before=compact_state(before), library_after=compact_state(state),
                    **{key: split[key] for key in FLAGS})
                flags['state'] &= math.same(row, expected)
            for name, flag in flags.items():
                check(f'life_{life}_independent_{name}', flag)
            print(json.dumps(dict(phase='independent_decisions', life=life, records=len(rows))), flush=True)
        check('common_A_and_return_learner_paths', common_a == read('run.json')['common_A_path'])
        # All acquisition decisions and updates are reconstructed at this point.
        # The second pass uses only saved decisions to evaluate hidden truths.
        results, true_boxes = evaluate(libraries, worlds, scoring_work)
        check('delayed_actual_risk_query_goal_scope_and_commit_results', math.same(read('results.json'), results))
        run = read('run.json')
        check('rotated_method_order_with_separate_arm_lifecycle_caches',
              run['arm_orders'] == [list(arm_order(life)) for life in range(12)]
              and run['cache_policy'] == 'separate_arm_lifecycle')
        source_costs = {arm: [4608]*12 for arm in ARMS}
        stats = Counter()
        summary = summarize(results, source_costs, run['model_seconds'], stats, common_a)
        check('independent_paired_lifecycle_statistics_and_frozen_six_conditions',
              math.same(read('summary.json'), summary))
        check('full_paid_A_and_B_source_fee_in_every_arm', run['source_costs'] == source_costs)
        check('shared_physical_source_generation_55296_samples', run['source_generation_costs'] == dict(source_draws))
        for arm in ARMS:
            check(arm+'_actual_target_draws_resets_and_observation_processing', all(
                run['arm_costs'][arm].get(key, 0) == value for key, value in target_draws[arm].items()))
            check(arm+'_complete_paid_sample_totals',
                  summary['arms'][arm]['target_samples'] == target_draws[arm]['controlled_samples']
                  and summary['arms'][arm]['source_samples'] == 55296)
        check('fixed_whole_lifecycle_bootstrap_consumption', run['bootstrap_costs'] == dict(stats))
        check('all_learner_decisions_frozen_before_oracle_evaluation', run['phases'] == [
            'protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete'])
        measured = [run['source_generation_seconds']]+[run[key][arm]
                    for key in ('model_seconds', 'observation_seconds') for arm in ARMS]
        check('complete_nonnegative_model_source_and_target_timing_ledgers',
              all(len(values) == 12 and all(value >= 0 for value in values) for values in measured)
              and run['seconds'] >= sum(sum(values) for values in measured))
        complete = True
    except Exception as error:
        check('reconstruction', False)
        checks[-1]['error'] = f'{type(error).__name__}: {error}'
        complete, true_boxes = False, Counter()
    for work in planning.values():
        replay_work.update(work)
    output = dict(valid=complete and all(item['passed'] for item in checks), complete=complete,
                  checks=checks, costs=dict(replay_work), source_replay_costs=dict(source_draws),
                  target_replay_costs={arm: dict(work) for arm, work in target_draws.items()},
                  oracle_costs=dict(scoring_work), true_candidate_box_coverage=dict(true_boxes),
                  seconds=perf_counter()-begun)
    save('analysis.json', output)
    print(json.dumps(dict(valid=output['valid'], complete=complete, checks=len(checks))), flush=True)
    return output


if __name__ == '__main__':
    raise SystemExit(0 if analyze()['valid'] else 1)
