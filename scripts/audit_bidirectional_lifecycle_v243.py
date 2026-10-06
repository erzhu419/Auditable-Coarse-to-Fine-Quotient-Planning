"""Independent native-prefix, transfer and lifecycle audit of V243.

The V243 producer is not imported. New paid streams and states are reconstructed;
the established independent likelihood and projection arithmetic checks each
new retained proof once. Scientific failures remain distinct from invalid data.
"""
from collections import Counter
from copy import deepcopy
from decimal import localcontext
from fractions import Fraction as F
from itertools import chain, repeat
from pathlib import Path
import gzip
import json
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_oracle_gap_lifecycle_v231 as paid
from scripts import audit_joint_query_qualification_v235 as global_audit
from scripts import audit_convex_query_null_v240 as convex_audit

OUTPUT = ROOT/'reports/bidirectional_lifecycle_v243'
OPERATORS, ALPHABETS = paid.OPERATORS, paid.ALPHABETS
ARMS, LIVES, TARGETS = ('ONE_WAY', 'TWO_WAY', 'REBUILD'), (0, 1, 2), paid.TARGETS
BATCH, CAP, SOURCE_BASE, TARGET_BASE = 16, 384, 280000, 281000
LIFE_CAPS, TARGET_CAPS = (14144, 17072, 17168), (9536, 12464, 12560)
REGRET, THRESHOLD = F(1, 20), 960
COMPUTATION_CACHE_SCOPE = dict(query_certificates='per_life_arm', scalar_intervals='per_life_arm',
    execution_normalizer='per_life_arm_maxsize4096',
    query_and_convex_normalizer='shared_within_arm_per_life_maxsize256')
evidence, arithmetic, math, joint = global_audit.evidence, global_audit.arithmetic, paid.math, paid.joint
empty, plus, samples, fractions = paid.empty, paid.plus, paid.samples, paid.fractions


def freeze(value):
    if isinstance(value, dict):
        return tuple((key, freeze(item)) for key, item in sorted(value.items()))
    if isinstance(value, list):
        return tuple(map(freeze, value))
    return value


def source_replay(rows, check):
    sources, cursor = {}, 0
    for life in LIVES:
        _, laws, _, _ = paid.world(life)
        sources[life] = {}
        for context, indexes, size in (('A', (0, 1, 2), 384), ('B', (27, 28, 29), 128)):
            anchors = []
            for local, index in enumerate(indexes):
                slot = local if context == 'A' else local+3
                anchor = empty()
                for j, operator in enumerate(OPERATORS):
                    seed = SOURCE_BASE+(life*6+slot)*3+j
                    generator = random.Random(seed)
                    for offset in range(0, size, BATCH):
                        increments = paid.draw(generator, laws[index], operator)
                        expected = dict(life=life, context=context, index=index, slot=slot,
                            operator=operator, seed=seed, draw_start=offset, draw_end=offset+BATCH, increments=increments)
                        check('fresh_source_random_batch_and_offset', cursor < len(rows) and rows[cursor] == expected)
                        cursor += 1
                        for category, count in increments.items():
                            anchor[operator][category] += count
                anchors.append(anchor)
            sources[life][context.lower()] = anchors
    check('all_source_batches_once', cursor == len(rows) == 864)
    return sources


def evidence_counts(state, case, identity, arm, metadata):
    context = case['context'].lower()
    counts = deepcopy(state[context][identity])
    if context == 'b' and arm in ('ONE_WAY', 'TWO_WAY'):
        inherited = state['a_switch'][metadata['b_to_a'][identity]]
        for operator in OPERATORS:
            if operator != metadata['changed_operator']:
                for category, count in inherited[operator].items():
                    counts[operator][category] += count
    if case.get('stage') == 'A_RETURN' and arm == 'TWO_WAY':
        b_identity = metadata['b_to_a'].index(identity)
        native = state['b'][b_identity]
        for operator in OPERATORS:
            if operator != metadata['changed_operator']:
                for category, count in native[operator].items():
                    counts[operator][category] += count
    return counts


def execution_constraints(life, index, case, identity, sources, state, member, arm, metadata):
    context = case['context'].lower()
    result = {}
    for operator in OPERATORS:
        event = f'l{life}/{case["context"]}/pool{identity}/{operator}'
        rows = [dict(counts=sources[context][identity][operator], threshold=720, event=event),
                dict(counts=state[context][identity][operator], threshold=720, event=event),
                dict(counts=member[operator], threshold=8640, event=f'l{life}/member{index}/{operator}')]
        if context == 'b' and arm in ('ONE_WAY', 'TWO_WAY') and operator != metadata['changed_operator']:
            a_index = metadata['b_to_a'][identity]
            a_event = f'l{life}/A/pool{a_index}/{operator}'
            rows.extend([dict(counts=sources['a'][a_index][operator], threshold=720, event=a_event),
                         dict(counts=state['a_switch'][a_index][operator], threshold=720, event=a_event)])
        if case.get('stage') == 'A_RETURN' and arm == 'TWO_WAY' and operator != metadata['changed_operator']:
            b_identity = metadata['b_to_a'].index(identity)
            b_event = f'l{life}/B/pool{b_identity}/{operator}'
            rows.extend([dict(counts=sources['b'][b_identity][operator], threshold=720, event=b_event),
                         dict(counts=state['b'][b_identity][operator], threshold=720, event=b_event)])
        result[operator] = rows
    return result


def transfer_view(case, identity, state, arm, metadata):
    if case.get('stage') != 'A_RETURN' or arm != 'TWO_WAY':
        return None
    b_identity = metadata['b_to_a'].index(identity)
    operators = [operator for operator in OPERATORS if operator != metadata['changed_operator']]
    counts = {operator: deepcopy(state['b'][b_identity][operator]) for operator in operators}
    return dict(a_identity=identity, mapped_b_identity=b_identity, operators=operators,
        transferred_counts=counts, total_samples=sum(sum(row.values()) for row in counts.values()))


def transfer_ledger(life, index, sources, state, metadata):
    rows = []
    for a_identity in range(3):
        b_identity = metadata['b_to_a'].index(a_identity)
        for operator in OPERATORS:
            if operator == metadata['changed_operator']:
                continue
            source = sources['b'][b_identity][operator]
            native = state['b'][b_identity][operator]
            target = {category: native[category]-source[category] for category in ALPHABETS[operator]}
            rows.append(dict(a_identity=a_identity, b_identity=b_identity, operator=operator,
                event=f'l{life}/B/pool{b_identity}/{operator}', source_counts=deepcopy(source),
                pool_counts=deepcopy(native), target_counts=target, source_samples=sum(source.values()),
                target_samples=sum(target.values()), total_samples=sum(native.values())))
    return dict(stage='A_RETURN', first_target_index=index, rows=rows,
        total_source_samples=sum(row['source_samples'] for row in rows),
        total_target_samples=sum(row['target_samples'] for row in rows),
        total_samples=sum(row['total_samples'] for row in rows))


def relevant_cost(case, family):
    if family == 'D_REC_R':
        return F(case['retry_cost'])
    short, detour = (F(1, 10), F(1, 20)) if case['operating'] == 'low' else (F(3, 25), F(7, 100))
    return detour-short


def audit_convex_profile(case, certificate, check):
    cert = fractions(certificate)
    family, counts, result = cert['family'], cert['projected_counts'], cert['result']
    check('fixed_convex_direction_region_and_relevant_cost', cert['query'] == 'risk'
        and cert['chosen'] == 'DETOUR_RETURN'
        and (cert['other'], family) in (('SHORT', 'S_D_FULL'), ('DETOUR_RETRY', 'D_REC_R'))
        and cert['threshold'] == THRESHOLD and cert['regret_threshold'] == REGRET
        and cert['relevant_cost'] == relevant_cost(case, family)
        and result['family'] == family and result['projected_counts'] == counts)
    optimizer = result['optimizer']
    start = ([F(9, 10), F(1, 10), F(1, 20), F(1, 10), F(17, 20)] if family == 'S_D_FULL'
             else [F(1, 2), F(9, 10)])
    check('single_frozen_convex_suggestion', optimizer['method'] == 'SLSQP' and optimizer['start'] == start
        and optimizer['options'] == dict(maxiter=500, ftol=1e-12)
        and optimizer['bounds'] == [1e-9, 1-1e-9]
        and optimizer['objective_scaling'] == 'negative_log_likelihood_divided_by_projected_count_total')
    point, tangent = result['proposed_point'], result['global_tangent']
    if tangent is None:
        check('no_tangent_never_certifies', not cert['certified'] and cert['status'] == 'unknown')
        return False
    multiplier = tangent['multiplier']
    expected = convex_audit.tangent_components(case, family, counts, point, multiplier)
    check('exact_full_domain_concave_tangent', tangent['point'] == point and multiplier >= 0
        and all(tangent[field] == expected[field] for field in
            ('h_point', 'gradient_likelihood', 'gradient_h', 'residual_gradient', 'residual_support'))
        and tangent['log_likelihood_upper'] >= expected['log_likelihood_upper']
        and tangent['global_upper'] == tangent['log_likelihood_upper']+multiplier*tangent['h_point']+tangent['residual_support']
        and tangent['global_upper'] >= expected['global_upper'])
    fixed_multiplier = (max(F(0), (expected['gradient_likelihood']['S']['LOST']
        -expected['gradient_likelihood']['S']['DELIVERY'])/8) if family == 'S_D_FULL'
        else max(F(0), -expected['gradient_likelihood']['R']))
    minimum = sum((arithmetic.logarithm(evidence.predictive_weight(tuple(row.values())))[0]
                   for row in counts.values()), F(0))
    check('outward_joint_numerator_and_frozen_tangent_multiplier', multiplier == fixed_multiplier
        and tangent['log_mixture_lower'] <= minimum
        and tangent['log_threshold_upper'] >= arithmetic.logarithm(THRESHOLD)[1]
        and tangent['log_e_lower'] == tangent['log_mixture_lower']-tangent['global_upper'])
    certified = tangent['log_e_lower'] > tangent['log_threshold_upper']
    check('strict_global_tangent_exclusion', tangent['certified'] == certified and cert['certified'] == certified
        and cert['status'] == ('certified' if certified else 'unknown'))
    return certified


def audit_profile(profile, check):
    certificate, case = profile['certificate'], profile['case']
    if certificate.get('engine') == 'convex_tangent':
        return audit_convex_profile(case, certificate, check)
    raw = global_audit.embedded_counts(certificate['projected_counts'])
    queues = {operator: chain.from_iterable(repeat(category, count) for category, count in row.items())
              for operator, row in raw.items()}
    return global_audit.audit_certificate(queues, case, certificate['query'], certificate['chosen'],
                                          certificate['other'], certificate, check)


def audit_reference(profile, reference, counts, case, query, chosen, other, certified, check):
    cert = profile['certificate']
    family = evidence.relevant_family(query, chosen, other)
    uniform = {operator: dict.fromkeys(categories, F(1, len(categories))) for operator, categories in ALPHABETS.items()}
    projected, _ = evidence.named_projection(family, counts, uniform)
    convex = query == 'risk' and chosen == 'DETOUR_RETURN' and other in ('SHORT', 'DETOUR_RETRY')
    cost_matches = (F(cert['relevant_cost']) == relevant_cost(case, family) if convex else
                   profile['case'] == {field: case[field] for field in ('operating', 'retry_cost')})
    check('profile_reference_actual_paid_projection_direction_and_cost',
        (cert['query'], cert['chosen'], cert['other'], cert['family']) == (query, chosen, other, family)
        and cert['projected_counts'] == projected and cost_matches
        and (cert.get('engine') == 'convex_tangent') == convex
        and reference['other'] == other and reference['certified'] == cert['certified'] == certified)
    return certified


def ready(plan):
    return (F(plan['utility_lower']) >= 2 or plan['goal_impossible']) and plan['query_ready']


def terminal_stop(spent, available, plan):
    return ready(plan) or spent+BATCH > min(CAP, available)


def binary_encloses(constraints, bounds):
    lower, upper = joint.binary_interval(constraints)
    with localcontext() as ctx:
        ctx.prec = 100
        return all(joint.decimal(bounds[category][0]) <= reference[0]
            and joint.decimal(bounds[category][1]) >= reference[1]
            for category, reference in (('DELIVERY', (lower, upper)), ('LOST', (1-upper, 1-lower))))


def audit_projection(constraints, saved, check):
    """Keep the independent 100-digit brackets; allow no binary tolerance."""
    plan, raw = fractions(saved), {}
    for operator in OPERATORS:
        raw[operator] = dict(bounds={})
        if operator != 'DETOUR_PASS':
            check('terminal_binary_projection_without_tolerance',
                binary_encloses(constraints[operator], plan['envelopes'][operator]['bounds']))
            raw[operator]['bounds'] = deepcopy(plan['envelopes'][operator]['bounds'])
        else:
            for category, support in plan['projection_supports'][operator].items():
                positive = {other: F(other == category) for other in ALPHABETS[operator]}
                negative = {other: -value for other, value in positive.items()}
                check('terminal_marginal_upper_dual', joint.audit_support(constraints[operator], positive, support['upper']))
                check('terminal_marginal_lower_dual', joint.audit_support(constraints[operator], negative, support['lower']))
                raw[operator]['bounds'][category] = [max(F(0), -support['lower']['upper']),
                                                     min(F(1), support['upper']['upper'])]
    expected = math.project_simplex(raw)
    check('terminal_projected_detour_box', plan['envelopes']['DETOUR_PASS']['bounds']
        == expected['DETOUR_PASS']['bounds'])


def audit_plan(plan, case, counts, constraints, profiles, profile_decisions, projection_cache, used_profiles, check):
    point = fractions(plan)
    posterior = paid.posterior(counts)
    selected = paid.point_queries(case, posterior)
    check('point_counts_paid_once_and_public_case', point['case'] == fractions(case)
        and point['evidence_counts'] == counts and point['posterior'] == posterior
        and point['effective_n'] == {operator: sum(row.values()) for operator, row in counts.items()}
        and all(point['queries'][query]['policy'] == policy for query, policy in selected.items()))
    check('actual_execution_constraints_and_envelope_counts', point['joint_constraints'] == constraints
        and all(point['envelopes'][operator]['counts'] == counts[operator]
            and point['envelopes'][operator]['n'] == sum(counts[operator].values()) for operator in OPERATORS))
    projection_key = freeze({operator: [{field: region[field] for field in ('counts', 'threshold')}
        for region in rows] for operator, rows in constraints.items()})
    projection = dict(supports=point['projection_supports'],
        bounds={operator: point['envelopes'][operator]['bounds'] for operator in OPERATORS})
    if projection_cache.get(projection_key) != projection:
        audit_projection(constraints, plan, check)
        projection_cache[projection_key] = projection
    pure = joint.vectors(case, posterior)
    risks = math.prior.settled.risk_bounds(point['envelopes'])
    goals = math.prior.settled.goal_bounds(point['envelopes'], case)
    check('point_vectors_and_robust_execution_coordinates', point['pure_vectors'] == pure
        and point['risks'] == risks and point['goals_lower'] == goals)
    check('execution_probability_mixture_and_bounds', all(weight >= 0 for _, weight in point['mix'])
        and sum(weight for _, weight in point['mix']) == 1
        and point['risk_upper'] == sum(weight*risks[policy] for policy, weight in point['mix']) <= REGRET
        and point['utility_lower'] == sum(weight*goals[policy] for policy, weight in point['mix']))
    check('optimistic_goal_and_impossible_decision', point['goal_upper'] == math.goal_upper(case, point['envelopes'])
        and point['goal_impossible'] == (point['goal_upper'] < 2))
    query_evidence = point['query_evidence']
    ready = {'reward': True}
    blockers = {query: [] for query in joint.WEIGHTS}
    check('analytic_reward_query_is_wait', query_evidence['queries']['reward']
        == dict(policy='WAIT', certified=True, kind='known_nonnegative_cost'))
    for query in ('goal', 'risk'):
        decision = query_evidence['queries'][query]
        chosen = selected[query]
        alternatives = [policy for policy in joint.POLICIES if policy != chosen]
        check('complete_original_query_alternative_roster', decision['policy'] == chosen
            and [reference['other'] for reference in decision['comparisons']] == alternatives)
        decisions = []
        for reference, other in zip(decision['comparisons'], alternatives):
            profile_id = reference['profile_id']
            used_profiles.add(profile_id)
            profile, certified = profiles[profile_id], profile_decisions[profile_id]
            audit_reference(profile, reference, counts, case, query, chosen, other, certified, check)
            decisions.append(certified)
            if not certified:
                blockers[query].append(other)
        ready[query] = all(decisions)
        check('three_alternatives_and', len(decisions) == 3 and decision['certified'] == ready[query])
    check('all_queries_and_and_marker_bounds', query_evidence['all_ready'] == point['query_ready'] == all(ready.values())
        and query_evidence['threshold'] == THRESHOLD
        and all(point['query_certificates'][query]['policy'] == selected[query]
            and point['query_certificates'][query]['certified'] == ready[query]
            and point['query_certificates'][query]['regret_upper'] == (F(0) if query == 'reward' else REGRET if ready[query] else F(20))
            for query in ready))
    marker = {query: {policy: F(policy in blockers[query]) for policy in joint.POLICIES} for query in joint.WEIGHTS}
    check('actual_unresolved_acquisition_blockers', point['query_gap_bounds'] == marker
        and point['query_blockers'] == blockers
        and point['query_gap_bounds_kind'] == 'uncertified_comparison_marker_not_regret_bound')
    return ready


def score_plan(saved, case, law, spent, executed_mix=None):
    plan = fractions(saved)
    pure = joint.vectors(case, law)
    mix = plan['mix'] if executed_mix is None else fractions(executed_mix)
    vector = [sum(weight*pure[policy][coordinate] for policy, weight in mix) for coordinate in range(3)]
    return dict(spent=spent, actual=vector, actual_utility=vector[0]+4*vector[2],
        risk_upper=plan['risk_upper'], utility_lower=plan['utility_lower'],
        violation=vector[1] > REGRET, coverage=math.covered(plan['envelopes'], law))


def score_history(row, law):
    case, history = row['case'], []
    pure = joint.vectors(case, law)
    optimum = paid.oracle_goal(pure)
    plans = [(row['initial_plan'], 0)]+[(batch['plan'], batch['spent']) for batch in row['batches']]
    for saved, spent in plans:
        plan, queries = fractions(saved), {}
        point = score_plan(saved, case, law, spent)
        for query, weights in joint.WEIGHTS.items():
            policy = plan['queries'][query]['policy']
            value = joint.utility(pure[policy], weights)
            queries[query] = dict(policy=policy, actual=pure[policy], utility=value,
                regret=max(joint.utility(vector, weights) for vector in pure.values())-value)
        point.update(queries=queries,
            false_query_certificates=sum(plan['query_certificates'][query]['certified'] and queries[query]['regret'] > REGRET
                for query in queries),
            false_execution_certificate=plan['utility_lower'] >= 2 and (point['actual_utility'] < 2 or point['violation']),
            false_impossible_certificate=plan['goal_impossible'] and optimum >= 2,
            goal_upper_ok=optimum <= plan['goal_upper'])
        history.append(point)
    result = {field: row[field] for field in ('life', 'index', 'arm', 'spent', 'execution_certified',
        'goal_impossible', 'query_certified', 'joint_completed', 'fallback', 'budget_exhausted', 'model_seconds')}
    executed = score_plan(row['terminal_plan'], case, law, row['spent'], row['executed_mix'])
    if row['fallback']:
        executed['risk_upper'] = executed['utility_lower'] = F(0)
    result.update(stage=case['stage'], history=history, terminal=history[-1], executed=executed)
    return result


def aggregate(rows):
    points = [point for row in rows for point in row['history']]
    return dict(targets=len(rows), target_samples=sum(row['spent'] for row in rows),
        query_certified=sum(row['query_certified'] for row in rows),
        joint_completed=sum(row['joint_completed'] for row in rows),
        execution_certified=sum(row['execution_certified'] for row in rows),
        goal_impossible=sum(row['goal_impossible'] for row in rows),
        fallbacks=sum(row['fallback'] for row in rows),
        budget_exhausted_targets=sum(row['budget_exhausted'] for row in rows),
        model_seconds=sum(row['model_seconds'] for row in rows),
        false_query_certificates=sum(point['false_query_certificates'] for point in points),
        false_execution_certificates=sum(point['false_execution_certificate'] for point in points),
        false_impossible_certificates=sum(point['false_impossible_certificate'] for point in points),
        risk_violations=sum(point['violation'] for point in points),
        executed_risk_violations=sum(row['executed']['violation'] for row in rows),
        false_goal_uppers=sum(not point['goal_upper_ok'] for point in points),
        uncovered_boxes=sum(not point['coverage'] for point in points),
        mean_executed_utility=sum(float(row['executed']['actual_utility']) for row in rows)/len(rows))


def summaries(rows, timings):
    methods, lives = {}, []
    for arm in ARMS:
        selected = [row for row in rows if row['arm'] == arm]
        methods[arm] = dict(aggregate(selected), source_samples=13824,
            total_samples=13824+sum(row['spent'] for row in selected),
            late_b=aggregate([row for row in selected if 42 <= row['index'] < 54]),
            a_return=aggregate([row for row in selected if row['stage'] == 'A_RETURN']))
        methods[arm]['model_seconds'] = sum(timings[scope][arm][str(life)]
            for scope in ('planning', 'initialization', 'begin_b') for life in LIVES)
        methods[arm]['planning_seconds'] = sum(timings['planning'][arm].values())
        methods[arm]['initialization_seconds'] = sum(timings['initialization'][arm].values())
        methods[arm]['begin_b_seconds'] = sum(timings['begin_b'][arm].values())
        for life in LIVES:
            subset = [row for row in selected if row['life'] == life]
            lives.append(dict(life=life, arm=arm, source_samples=4608,
                total_samples=4608+sum(row['spent'] for row in subset), model_seconds=sum(timings[scope][arm][str(life)]
                    for scope in ('planning', 'initialization', 'begin_b')),
                stages={stage: aggregate([row for row in subset if row['stage'] == stage]) for stage in ('A', 'B', 'A_RETURN')}))
    two = methods['TWO_WAY']
    conditions = dict(late_b_quality=two['late_b']['query_certified'] >= 27,
        a_return_quality=two['a_return']['query_certified'] >= 54)
    for control in ('ONE_WAY', 'REBUILD'):
        name, other = control.lower(), methods[control]
        conditions.update({
            f'matched_{name}_late_b_quality': two['late_b']['query_certified'] >= other['late_b']['query_certified'],
            f'matched_{name}_a_return_quality': two['a_return']['query_certified'] >= other['a_return']['query_certified'],
            f'matched_{name}_joint_quality': two['joint_completed'] >= other['joint_completed'],
            f'actual_acquisition_saving_vs_{name}': two['total_samples'] < other['total_samples']})
    conditions['valid_certificates_and_execution'] = all(method[field] == 0 for method in methods.values()
            for field in ('false_query_certificates', 'false_execution_certificates',
                          'false_impossible_certificates', 'risk_violations', 'executed_risk_violations'))
    paired = []
    for life in LIVES:
        selected = {row['arm']: row for row in lives if row['life'] == life}
        one, two, rebuild = selected['ONE_WAY'], selected['TWO_WAY'], selected['REBUILD']
        paired.append(dict(life=life,
            one_way_minus_two_way_samples=one['total_samples']-two['total_samples'],
            rebuild_minus_two_way_samples=rebuild['total_samples']-two['total_samples'],
            return_one_way_minus_two_way_samples=one['stages']['A_RETURN']['target_samples']-two['stages']['A_RETURN']['target_samples'],
            return_two_way_minus_one_way_query_certified=two['stages']['A_RETURN']['query_certified']-one['stages']['A_RETURN']['query_certified'],
            return_two_way_minus_one_way_joint_completed=two['stages']['A_RETURN']['joint_completed']-one['stages']['A_RETURN']['joint_completed']))
    return methods, lives, conditions, paired


def run():
    begun, checks, failures, location = perf_counter(), Counter(), [], {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    read = lambda name: evidence.load(OUTPUT/name)
    prerequisite = evidence.load(ROOT/'reports/convex_query_qualification_v241/analysis.json')
    numerical_repair = evidence.load(ROOT/'reports/v242_runtime_tmp/binary_interval_repair_verification.json')
    metadata, summary = read('run.json'), read('summary.json')
    check('prerequisite_and_frozen_fresh_protocol', prerequisite['valid'] and prerequisite['stage_condition_met']
        and numerical_repair['valid'] and numerical_repair['comparison_tolerance'] == 0
        and metadata['prerequisites'] == dict(v241_qualification_valid=True, v241_stage_condition_met=True,
            v242_interval_repair_valid=True, v242_cohort_valid_required=False)
        and metadata['complete'] and metadata['lives'] == list(LIVES) and metadata['arms'] == list(ARMS)
        and metadata['targets_per_life'] == 72 and metadata['cap'] == CAP and metadata['batch'] == BATCH
        and metadata['source_seed_base'] == SOURCE_BASE and metadata['target_seed_base'] == TARGET_BASE
        and metadata['per_life_total_budgets'] == list(LIFE_CAPS) and metadata['source_samples_per_life'] == 4608
        and metadata['query_stream_count'] == 48 and metadata['query_threshold'] == THRESHOLD
        and metadata['query_delta_per_life_arm'] == metadata['execution_delta_per_life_arm'] == '1/20'
        and metadata['combined_delta_upper'] == '1/10' and not metadata['scientific_gate_changed']
        and metadata['qualification_only'] and metadata['phases'] == [
            'protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete'])
    check('separate_query_and_execution_event_budgets', F(48, THRESHOLD) == REGRET
        and F(216, 8640)+F(9, 720)+F(9, 720) == REGRET and 2*REGRET == F(1, 10))
    check('per_arm_computation_cache_scope', metadata['computation_cache_scope']
        == summary['computation_cache_scope'] == COMPUTATION_CACHE_SCOPE)
    sources = source_replay(read('source_records.json'), check)
    check('paid_source_banks', read('source_evidence.json') == [dict(life=life, **sources[life]) for life in LIVES])
    cases_saved = {row['life']: row['cases'] for row in read('cases.json')}
    interfaces = {row['life']: row for row in read('interfaces.json')}
    final_states = {row['life']: row['states'] for row in read('final_states.json')}
    scored, seen, orders, proof_count, plans_count, leaf_count = [], set(), [], 0, 0, 0
    transfer_ledgers, observations = [], {arm: Counter() for arm in ARMS}
    work_counts = {arm: Counter() for arm in ARMS}
    convex_keys = {arm: set() for arm in ARMS}
    projection_count = 0
    for life in LIVES:
        cases, laws, identities, interface = paid.world(life)
        check('predeclared_public_world_and_interfaces', cases_saved[life] == cases
            and interfaces[life] == dict(life=life, identities=identities, metadata=interface))
        profiles = evidence.read_rows(OUTPUT/f'profiles_life_{life:02d}.jsonl.gz')
        check('complete_profile_numbering', [profile['profile_id'] for profile in profiles] == list(range(len(profiles))))
        profile_decisions = {}
        for profile in profiles:
            location = dict(life=life, profile_id=profile['profile_id'])
            profile_decisions[profile['profile_id']] = audit_profile(profile, check)
            leaf_count += len(profile['certificate'].get('leaves', ()))
        proof_count += len(profiles)
        states = {arm: dict(a=deepcopy(sources[life]['a']), b=None, a_switch=None) for arm in ARMS}
        histories, projection_cache, used_profiles = dict.fromkeys(ARMS, 0), {}, set()
        paired_pre_return = {}
        ledgers = dict.fromkeys(ARMS)
        results = evidence.read_rows(OUTPUT/f'results_life_{life:02d}.jsonl.gz')
        rows = iter(evidence.read_rows(OUTPUT/f'records_life_{life:02d}.jsonl.gz'))
        results_cursor = 0
        for position, index in enumerate(TARGETS):
            if index == 30:
                for state in states.values():
                    state['a_switch'] = deepcopy(state['a'])
                    state['b'] = deepcopy(sources[life]['b'])
            if index == 54:
                ledgers['TWO_WAY'] = transfer_ledger(life, index, sources[life], states['TWO_WAY'], interface)
            offset = (life+position) % 3
            order = ARMS[offset:]+ARMS[:offset]
            orders.append(dict(life=life, index=index, order=list(order)))
            for arm in order:
                row = next(rows)
                location = dict(life=life, index=index, arm=arm)
                seen.add((life, index, arm))
                check('all_targets_in_frozen_arm_order', (row['life'], row['index'], row['arm']) == (life, index, arm))
                case, identity, state = cases[index], identities[index], states[arm]
                context, source_fee = case['context'].lower(), 3456 if index < 30 else 4608
                pool = state[context][identity]
                check('actual_case_identity_and_own_pool_before', row['case'] == case and row['identity'] == identity
                    and row['pooled_before'] == pool and (context != 'b' or state['a'] == state['a_switch']))
                check('timing_nonnegative_and_measured_target_scopes',
                    all(row[field] >= 0 for field in ('model_seconds', 'observation_seconds', 'output_seconds')))
                observations[arm][life] += row['observation_seconds']
                seeds = {operator: TARGET_BASE+(life*78+index)*3+j for j, operator in enumerate(OPERATORS)}
                check('same_latent_target_seed_without_cross_arm_cursor', row['seeds'] == seeds)
                generators = {operator: random.Random(seed) for operator, seed in seeds.items()}
                member, spent, available = empty(), 0, TARGET_CAPS[life]-histories[arm]

                def plan_check(saved):
                    nonlocal plans_count, projection_count
                    counts = evidence_counts(state, case, identity, arm, interface)
                    constraints = execution_constraints(life, index, case, identity, sources[life], state,
                                                        member, arm, interface)
                    before = checks['terminal_projected_detour_box']
                    audit_plan(saved, case, counts, constraints, profiles, profile_decisions,
                               projection_cache, used_profiles, check)
                    check('return_native_unchanged_prefix_view_and_no_double_inheritance',
                        saved['return_transfer'] == transfer_view(case, identity, state, arm, interface))
                    projection_count += checks['terminal_projected_detour_box']-before
                    plans_count += 1
                    work_counts[arm]['online_query_comparison_calls'] += 6
                    for query in ('goal', 'risk'):
                        for reference in saved['query_evidence']['queries'][query]['comparisons']:
                            cert = profiles[reference['profile_id']]['certificate']
                            if cert.get('engine') == 'convex_tangent':
                                work_counts[arm]['online_convex_certificate_calls'] += 1
                                convex_keys[arm].add((life, cert['family'], query, cert['chosen'], cert['other'],
                                    F(cert['relevant_cost']), freeze(cert['projected_counts'])))

                current = row['initial_plan']
                plan_check(current)
                for batch in row['batches']:
                    check('acquisition_respects_joint_stop_and_both_budget_caps', spent+BATCH <= min(CAP, available)
                          and not ready(current))
                    choice = paid.gap_choice(member, current)
                    retained = batch['choice']
                    check('actual_gap_acquisition_operator_and_reason', retained['operator'] == choice['operator']
                          and retained['reason'] == 'known_type_action_gap')
                    for field in ('scores', 'query_influence', 'execution_influence', 'contraction'):
                        check('actual_gap_acquisition_'+field, fractions(retained[field]) == choice[field])
                    deficits = {query: max(F(0), F(cert['regret_upper'])-REGRET)
                                for query, cert in current['query_certificates'].items()}
                    deficits['execution'] = F(0) if current['goal_impossible'] else max(F(0), 2-F(current['utility_lower']))
                    check('actual_gap_effective_counts_and_deficits', retained['effective_n'] == current['effective_n']
                          and fractions(retained['initial_deficits']) == deficits)
                    operator = choice['operator']
                    draw_start = sum(member[operator].values())
                    increments = paid.draw(generators[operator], laws[index], operator)
                    check('own_paid_random_prefix_and_category_increments', batch['operator'] == operator
                        and batch['draw_start'] == draw_start and batch['draw_end'] == draw_start+BATCH
                        and batch['increments'] == increments)
                    for category, count in increments.items():
                        member[operator][category] += count
                        pool[operator][category] += count
                    spent += BATCH
                    check('actual_batch_paid_prefix', batch['spent'] == spent)
                    current = batch['plan']
                    plan_check(current)
                terminal = row['terminal_plan']
                check('terminal_is_last_observed_plan_and_valid_stop', terminal == current
                      and terminal_stop(spent, available, terminal))
                completed = ready(terminal)
                expected_mix = fractions(terminal['mix']) if completed else [['WAIT', F(1)]]
                check('terminal_flags_safe_fallback_and_own_actual_pool', row['member'] == member
                    and row['spent'] == row['current_paid_samples'] == row['new_paid_samples'] == spent == samples(member)
                    and row['pooled_after'] == pool and row['execution_certified'] == (F(terminal['utility_lower']) >= 2)
                    and row['goal_impossible'] == terminal['goal_impossible'] and row['query_certified'] == terminal['query_ready']
                    and row['joint_completed'] == completed and row['fallback'] == (not completed)
                    and fractions(row['executed_mix']) == expected_mix)
                check('source_history_fees_and_reserved_life_budget', row['source_paid_samples'] == source_fee
                    and row['history_paid_samples'] == histories[arm]
                    and row['total_reference_paid_samples'] == source_fee+histories[arm]+spent
                    and row['life_budget_remaining_before'] == available and row['life_budget_remaining_after'] == available-spent
                    and row['budget_exhausted'] == (available-spent < BATCH) and row['member_cap_exhausted'] == (spent == CAP)
                    and 0 <= spent <= min(CAP, available) and spent % BATCH == 0)
                if index < 54 and arm in ('ONE_WAY', 'TWO_WAY'):
                    paired = {field: value for field, value in row.items()
                              if field not in ('arm', 'model_seconds', 'observation_seconds', 'output_seconds')}
                    if index in paired_pre_return:
                        check('one_two_exact_acquisition_plans_stops_and_actions_before_return', paired == paired_pre_return[index])
                    else:
                        paired_pre_return[index] = paired
                independent_score = score_history(row, laws[index])
                check('frozen_decisions_all_points_and_actual_execution_truth', fractions(results[results_cursor]) == independent_score)
                scored.append(independent_score)
                results_cursor += 1
                histories[arm] += spent
                print(f'audit life={life} target={index} arm={arm} paid={spent}', flush=True)
        check('all_life_targets_and_results_retained', next(rows, None) is None and results_cursor == len(results) == 216)
        check('all_profiles_used_and_reported_once', used_profiles == set(range(len(profiles)))
              and summary['profiles'][str(life)] == len(profiles))
        for arm in ARMS:
            saved, state = final_states[life][arm], states[arm]
            check('final_banks_sources_switch_and_single_arm_retention', saved['life'] == life and saved['arm'] == arm
                and saved['a'] == dict(sources=sources[life]['a'], pools=state['a'])
                and saved['b'] == dict(sources=sources[life]['b'], pools=state['b'])
                and saved['a_at_switch'] == dict(sources=sources[life]['a'], pools=state['a_switch'])
                and saved['changed_operator'] == interface['changed_operator'] and saved['b_to_a'] == interface['b_to_a'])
            check('transfer_ledger_frozen_once_and_native_banks_never_rewritten', saved['return_merge'] == ledgers[arm])
            transfer_ledgers.append(dict(life=life, arm=arm, ledger=ledgers[arm]))
            check('actual_life_total_cap', 4608+histories[arm] <= LIFE_CAPS[life])
    methods, life_summaries, conditions, paired = summaries(scored, summary['timings'])
    check('complete_648_target_cohort_and_truth_freeze_order', len(seen) == len(scored) == 648
          and metadata['arm_orders'] == orders)
    check('actual_cost_quality_false_certificate_and_fixed_conditions_summary', summary['complete']
        and summary['records'] == 648 and summary['methods'] == methods and summary['life_summaries'] == life_summaries
        and summary['paired'] == paired and summary['conditions'] == conditions
        and summary['stage_condition_met'] == all(conditions.values()) and summary['qualification_only']
        and not summary['scientific_gate_changed'] and summary['physical_source_samples'] == 13824
        and summary['source_samples_charged_per_arm'] == 13824
        and summary['return_transfers'] == transfer_ledgers
        and summary['new_environment_observations'] == 13824+sum(row['spent'] for row in scored))
    for arm in ARMS:
        total = methods[arm]['target_samples']
        for field in ('controlled_samples', 'controlled_resets', 'environment_random_draws'):
            check('actual_target_environment_work', summary['work'][arm][field] == total)
        work_counts[arm]['online_convex_proposal_calls'] = len(convex_keys[arm])
        work_counts[arm]['online_convex_certificate_cache_hits'] = (
            work_counts[arm]['online_convex_certificate_calls']-len(convex_keys[arm]))
        for field, count in work_counts[arm].items():
            check('per_arm_online_certificate_work_and_no_cross_arm_compute_cache', summary['work'][arm].get(field, 0) == count)
        for life in LIVES:
            selected = [row for row in scored if row['life'] == life and row['arm'] == arm]
            check('per_arm_actual_planning_and_observation_seconds', summary['timings']['planning'][arm][str(life)]
                  == sum(row['model_seconds'] for row in selected)
                  and summary['timings']['observation'][arm][str(life)] == observations[arm][life])
            check('per_arm_bank_initialization_and_switch_seconds',
                summary['timings']['initialization'][arm][str(life)] >= 0
                and summary['timings']['begin_b'][arm][str(life)] >= 0)
            for name, capacity in (('execution', 4096), ('query', 256)):
                stats = summary['normalizer_cache_statistics'][arm][str(life)][name]
                check('per_arm_exact_normalizer_cache_statistics', stats['maxsize'] == capacity
                    and 0 <= stats['currsize'] <= min(stats['misses'], capacity)
                    and stats['hits'] >= 0)
    for field in ('controlled_samples', 'controlled_resets', 'environment_random_draws'):
        check('actual_source_environment_work', summary['source_work'][field] == 13824)
    executed_violations = {arm: sum(row['executed']['violation'] for row in scored if row['arm'] == arm) for arm in ARMS}
    planned_violations = {arm: methods[arm]['risk_violations'] for arm in ARMS}
    result = dict(valid=not failures, complete=True, records=648, plans=plans_count,
        independently_checked_profiles=proof_count, independently_checked_global_leaves=leaf_count,
        independently_checked_execution_projections=projection_count,
        methods=methods, conditions=conditions, stage_condition_met=all(conditions.values()),
        risk_violation_scope='all_retained_plans', planned_risk_violations=planned_violations,
        executed_risk_violations=executed_violations, physical_source_samples=13824,
        transferred_native_b_samples=sum(row['ledger']['total_samples'] for row in transfer_ledgers if row['ledger']),
        binary_projection_comparison_tolerance=0,
        physical_observations=13824+sum(row['spent'] for row in scored),
        checks=dict(checks), failures=failures, seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({field: value for field, value in result.items() if field not in ('checks', 'failures')}), flush=True)
    return result


if __name__ == '__main__':
    run()
