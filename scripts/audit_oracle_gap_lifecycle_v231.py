"""Independent paid-tape, true-pool, acquisition and certificate audit of V231.

No V231 producer or task module is imported.  Previously independent route
arithmetic and likelihood-witness checks supply the mathematical primitives.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import gzip
import json
from math import sqrt
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import scoped_repair_v229_math as math
from scripts import audit_joint_gap_v230 as joint
from scripts.analyze_scoped_lifecycle_v229 import world, oracle_goal

OUTPUT = ROOT/'reports/oracle_gap_lifecycle_v231'
OPERATORS, ALPHABETS = math.OPERATORS, math.SUPPORT
ARMS = ('ORACLE_BALANCED', 'ORACLE_GAP')
LIVES = (0, 1, 2)
TARGETS = tuple(range(3, 27))+tuple(range(30, 78))
BATCH, CAP, THRESHOLD = 16, 384, F(1, 20)


def empty():
    return {op: dict.fromkeys(ALPHABETS[op], 0) for op in OPERATORS}


def plus(first, second):
    return {op: {cat: first[op][cat]+second[op][cat]
                 for cat in ALPHABETS[op]} for op in OPERATORS}


def samples(counts):
    return sum(sum(row.values()) for row in counts.values())


def fractions(value):
    if isinstance(value, dict):
        return {key: fractions(item) for key, item in value.items()}
    if isinstance(value, list):
        return [fractions(item) for item in value]
    if isinstance(value, str):
        try:
            return F(value)
        except ValueError:
            return value
    return value


def same(saved, expected):
    return fractions(saved) == expected


def ready(plan):
    return (F(plan['utility_lower']) >= 2 or plan['goal_impossible']) and plan['query_ready']


def draw(generator, law, operator, count=16):
    result = dict.fromkeys(ALPHABETS[operator], 0)
    for _ in range(count):
        value, cumulative = generator.random(), F(0)
        for cat in ALPHABETS[operator]:
            cumulative += law[operator][cat]
            if value < float(cumulative):
                result[cat] += 1
                break
    return result


def posterior(counts):
    return {op: {cat: F(2*counts[op][cat]+1,
                         2*sum(counts[op].values())+len(ALPHABETS[op]))
                 for cat in ALPHABETS[op]} for op in OPERATORS}


def point_queries(case, probabilities):
    vectors = joint.vectors(case, probabilities)
    return {query: min(joint.POLICIES,
                      key=lambda policy: (-joint.utility(vectors[policy], weights), policy))
            for query, weights in joint.WEIGHTS.items()}


def balanced(member):
    return min(OPERATORS, key=lambda op: (sum(member[op].values()), OPERATORS.index(op)))


def gap_choice(member, saved):
    """Reconstruct span/contraction scores without the acquisition producer."""
    plan = fractions(saved)
    values, query_span, execution_span = {}, dict.fromkeys(OPERATORS, F(0)), {}
    for op in OPERATORS:
        values[op] = []
        for vertex in math.row_vertices(plan['envelopes'][op]['bounds']):
            kernel = dict(plan['posterior'])
            kernel[op] = vertex
            values[op].append(joint.vectors(plan['case'], kernel))
    for query, certificate in plan['query_certificates'].items():
        if certificate['certified']:
            continue
        selected, weights = certificate['policy'], joint.WEIGHTS[query]
        alternatives = [policy for policy in joint.POLICIES if policy != selected
                        and plan['query_gap_bounds'][query][policy] > THRESHOLD]
        for op in OPERATORS:
            for alternative in alternatives:
                gaps = [joint.utility(v[alternative], weights)-joint.utility(v[selected], weights)
                        for v in values[op]]
                query_span[op] += max(gaps)-min(gaps)
    weight = (F(0) if plan['goal_impossible'] else
              min(F(1), max(F(0), 2-plan['utility_lower'])/2))
    for op in OPERATORS:
        spans = []
        for policy in joint.POLICIES:
            if policy == 'WAIT':
                continue
            goals = [joint.utility(v[policy], joint.WEIGHTS['goal']) for v in values[op]]
            risks = [v[policy][1] for v in values[op]]
            spans.append(max(goals)-min(goals)+4*(max(risks)-min(risks)))
        execution_span[op] = weight*max(spans)
    contraction = {op: 1-sqrt(plan['effective_n'][op]/(plan['effective_n'][op]+16))
                   for op in OPERATORS}
    scores = {op: float(query_span[op]+execution_span[op])*contraction[op] for op in OPERATORS}
    selected = min(OPERATORS, key=lambda op: (
        -scores[op], sum(member[op].values()), OPERATORS.index(op)))
    return dict(operator=selected, scores=scores, query_influence=query_span,
                execution_influence=execution_span, contraction=contraction)


def constraints_for(life, index, case, identity, sources, pooled, member, a_switch, metadata):
    context = case['context'].lower()
    result = {}
    for op in OPERATORS:
        event = f'l{life}/{case["context"]}/pool{identity}/{op}'
        rows = [dict(counts=sources[context][identity][op], threshold=720, event=event),
                dict(counts=pooled[op], threshold=720, event=event),
                dict(counts=member[op], threshold=8640,
                     event=f'l{life}/member{index}/{op}')]
        if context == 'b' and op != metadata['changed_operator']:
            a_index = metadata['b_to_a'][identity]
            a_event = f'l{life}/A/pool{a_index}/{op}'
            rows.extend([dict(counts=sources['a'][a_index][op], threshold=720, event=a_event),
                         dict(counts=a_switch[a_index][op], threshold=720, event=a_event)])
        result[op] = rows
    return result


def actual(plan, case, law):
    plan = fractions(plan)
    vectors = joint.vectors(case, law)
    vector = [sum(weight*vectors[policy][j] for policy, weight in plan['mix']) for j in range(3)]
    return dict(vector=vector, utility=vector[0]+4*vector[2],
                regrets=joint.actual_regrets(case, law, plan['queries']),
                optimal_safe_goal=oracle_goal(vectors))


def records_for(life):
    with gzip.open(OUTPUT/f'records_life_{life:02d}.jsonl.gz', 'rt') as stream:
        yield from (json.loads(line) for line in stream)


def audit_projection(constraints, saved, check):
    """Verify retained marginal duals and their outward final simplex box."""
    plan = fractions(saved)
    raw = {}
    for op in OPERATORS:
        raw[op] = dict(bounds={})
        if op != 'DETOUR_PASS':
            lower, upper = joint.binary_interval(constraints[op])
            for cat in ALPHABETS[op]:
                pair = (lower, upper) if cat == 'DELIVERY' else (1-upper, 1-lower)
                saved_pair = plan['envelopes'][op]['bounds'][cat]
                check('terminal_binary_projection',
                      joint.decimal(saved_pair[0]) <= pair[0]+joint.NUMERICAL_TOLERANCE
                      and joint.decimal(saved_pair[1])+joint.NUMERICAL_TOLERANCE >= pair[1])
                raw[op]['bounds'][cat] = list(saved_pair)
        else:
            for cat, row in plan['projection_supports'][op].items():
                positive = {c: F(c == cat) for c in ALPHABETS[op]}
                negative = {c: -value for c, value in positive.items()}
                check('terminal_marginal_upper_dual', joint.audit_support(constraints[op], positive, row['upper']))
                check('terminal_marginal_lower_dual', joint.audit_support(constraints[op], negative, row['lower']))
                raw[op]['bounds'][cat] = [max(F(0), -row['lower']['upper']),
                                          min(F(1), row['upper']['upper'])]
    expected = math.project_simplex(raw)
    check('terminal_projected_detour_box', plan['envelopes']['DETOUR_PASS']['bounds']
          == expected['DETOUR_PASS']['bounds'])


def audit_point(saved, case, law, expected_counts, constraints, check):
    plan = fractions(saved)
    probabilities = posterior(expected_counts)
    chosen = point_queries(case, probabilities)
    check('point_posterior_from_actual_counts', plan['posterior'] == probabilities)
    check('actual_effective_row_counts', plan['effective_n'] == {
        op: sum(expected_counts[op].values()) for op in OPERATORS})
    check('point_policy_not_oracle_action', all(plan['queries'][q]['policy'] == chosen[q]
          for q in joint.WEIGHTS))
    check('unchanged_public_case', plan['case'] == fractions(case))
    check('true_coordinate_coverage', math.covered(plan['envelopes'], law))
    check('observed_counts_in_envelopes', all(plan['envelopes'][op]['counts'] == expected_counts[op]
          and plan['envelopes'][op]['n'] == sum(expected_counts[op].values()) for op in OPERATORS))
    pure = joint.vectors(case, probabilities)
    check('actual_point_vectors', plan['pure_vectors'] == pure)
    risks = math.prior.settled.risk_bounds(plan['envelopes'])
    goals = math.prior.settled.goal_bounds(plan['envelopes'], case)
    check('robust_risk_coordinates', plan['risks'] == risks)
    check('robust_goal_coordinates', plan['goals_lower'] == goals)
    check('mixture_is_probability', all(weight >= 0 for _, weight in plan['mix'])
          and sum(weight for _, weight in plan['mix']) == 1)
    check('mixture_risk_bound', plan['risk_upper'] == sum(weight*risks[policy]
          for policy, weight in plan['mix']))
    check('mixture_goal_bound', plan['utility_lower'] == sum(weight*goals[policy]
          for policy, weight in plan['mix']))
    point = actual(plan, case, law)
    check('true_safe_execution', point['vector'][1] <= plan['risk_upper'] <= THRESHOLD)
    check('true_goal_lower_bound', point['utility'] >= plan['utility_lower'])
    check('true_optimistic_goal_bound', point['optimal_safe_goal'] <= plan['goal_upper'])
    check('impossible_threshold', plan['goal_impossible'] == (plan['goal_upper'] < 2))
    for query, certificate in plan['query_certificates'].items():
        check('true_query_regret_bound', F(0) <= point['regrets'][query] <= certificate['regret_upper'])
        check('query_certificate_threshold', certificate['certified'] ==
              (certificate['regret_upper'] <= THRESHOLD))
        check('query_policy_consistency', certificate['policy'] == chosen[query])
    check('all_query_stop_condition', plan['query_ready'] == all(
        certificate['certified'] for certificate in plan['query_certificates'].values()))
    for op, rows in constraints.items():
        for region in rows:
            check('true_joint_CS_coverage', joint.contains(region, law[op]))
    return point


def audit_terminal(saved, constraints, check):
    plan = fractions(saved)
    check('terminal_constraints_from_paid_pools', plan['joint_constraints'] == constraints)
    audited = joint.audit_certificates(plan['case'], constraints, plan['query_certificate'])
    check('terminal_independent_gap_certificate', audited['valid'])
    check('terminal_selected_query_certificates', plan['query_certificates'] == plan['query_certificate']['queries'])
    check('terminal_query_ready', plan['query_ready'] == plan['query_certificate']['all_ready'])
    gaps = {q: dict.fromkeys(joint.POLICIES, F(0)) for q in joint.WEIGHTS}
    for row in plan['query_certificate']['support_records']:
        gaps[row['query']][row['other']] = max(gaps[row['query']][row['other']], row['support']['upper'])
    check('terminal_blocker_supports', plan['query_gap_bounds'] == gaps)
    audit_projection(constraints, plan, check)


def source_replay(saved, check):
    evidence, cursor = {}, 0
    for life in LIVES:
        _, laws, _, _ = world(life)
        evidence[life] = {}
        for context, indexes, size in (('A', (0, 1, 2), 384), ('B', (27, 28, 29), 128)):
            anchors = []
            for local, index in enumerate(indexes):
                slot = local if context == 'A' else local+3
                anchor = empty()
                for j, op in enumerate(OPERATORS):
                    seed = 262000+(life*6+slot)*3+j
                    generator = random.Random(seed)
                    for offset in range(0, size, BATCH):
                        increments = draw(generator, laws[index], op)
                        expected = dict(life=life, context=context, index=index, slot=slot,
                                        operator=op, seed=seed, draw_start=offset,
                                        draw_end=offset+BATCH, increments=increments)
                        check('source_actual_fresh_batch', cursor < len(saved) and saved[cursor] == expected)
                        cursor += 1
                        for cat, count in increments.items():
                            anchor[op][cat] += count
                anchors.append(anchor)
            evidence[life][context.lower()] = anchors
    check('source_records_complete', cursor == len(saved))
    return evidence


def run():
    begun, checks, expected = perf_counter(), Counter(), Counter()

    def check(name, condition):
        expected[name] += 1
        checks[name] += bool(condition)

    read = lambda name: json.loads((OUTPUT/name).read_text())
    source_evidence = source_replay(read('source_records.json'), check)
    saved_evidence = {row['life']: dict(a=row['a'], b=row['b']) for row in read('source_evidence.json')}
    check('source_evidence_from_paid_batches', source_evidence == saved_evidence)
    check('per_arm_per_life_event_budget', F(216, 8640)+F(9, 720)+F(9, 720) == F(1, 20))
    check('member_stream_allocation', len(TARGETS)*len(OPERATORS) == 216)
    run_info, summary = read('run.json'), read('summary.json')
    check('decisions_frozen_before_oracle_scoring', run_info['phases'] == [
        'protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete'])
    check('diagnostic_protocol', run_info['qualification_only'] and not run_info['fresh_scientific_gate']
          and not run_info['scientific_gate_changed'] and run_info['lives'] == list(LIVES)
          and run_info['arms'] == list(ARMS) and run_info['targets_per_life'] == 72
          and run_info['cap'] == CAP and run_info['batch'] == BATCH
          and run_info['source_seed_base'] == 262000 and run_info['target_seed_base'] == 263000)
    final_saved = {row['life']: row['states'] for row in read('final_states.json')}
    assessed, summaries, seen = {}, [], set()
    arm_totals = dict.fromkeys(ARMS, 0)
    for life in LIVES:
        cases, laws, identities, metadata = world(life)
        sources = source_evidence[life]
        states = {arm: dict(a=deepcopy(sources['a']), b=None, a_switch=None) for arm in ARMS}
        histories = dict.fromkeys(ARMS, 0)
        with gzip.open(OUTPUT/f'results_life_{life:02d}.jsonl.gz', 'rt') as stream:
            assessed.update({(life, result['index'], result['arm']): result
                             for line in stream if (result := json.loads(line))})
        rows = iter(records_for(life))
        for position, index in enumerate(TARGETS):
            if index == 30:
                for state in states.values():
                    state['a_switch'] = deepcopy(state['a'])
                    state['b'] = deepcopy(sources['b'])
            offset = (life+position) % 2
            for arm in ARMS[offset:]+ARMS[:offset]:
                row = next(rows)
                key = (life, index, arm)
                seen.add(key)
                check('frozen_chronological_arm_order', (row['life'], row['index'], row['arm']) == key)
                case, law, identity, state = cases[index], laws[index], identities[index], states[arm]
                check('public_case_and_oracle_identity', row['case'] == case and row['identity'] == identity)
                context = case['context'].lower()
                pool = state[context][identity]
                check('true_pool_before_target', row['pooled_before'] == pool)
                if context == 'b':
                    check('A_frozen_through_B', state['a'] == state['a_switch'])
                seeds = {op: 263000+(life*78+index)*3+j for j, op in enumerate(OPERATORS)}
                check('fresh_paired_target_streams', row['seeds'] == seeds)
                generators = {op: random.Random(seed) for op, seed in seeds.items()}
                member, offsets, spent = empty(), dict.fromkeys(OPERATORS, 0), 0

                def point(saved):
                    counts = deepcopy(pool)
                    if context == 'b':
                        inherited = state['a_switch'][metadata['b_to_a'][identity]]
                        for op in OPERATORS:
                            if op != metadata['changed_operator']:
                                for cat in ALPHABETS[op]:
                                    counts[op][cat] += inherited[op][cat]
                    constraints = constraints_for(life, index, case, identity, sources,
                                                  pool, member, state['a_switch'], metadata)
                    return audit_point(saved, case, law, counts, constraints, check), constraints

                current = row['initial_plan']
                evaluated, _ = point(current)
                truth_history = [evaluated]
                for batch in row['batches']:
                    check('stop_not_ignored', spent < CAP and not ready(current))
                    if arm == ARMS[0]:
                        choice = dict(operator=balanced(member), reason='balanced_current_target')
                        check('balanced_acquisition_choice', batch['choice'] == choice)
                    else:
                        choice = gap_choice(member, current)
                        check('gap_acquisition_operator', batch['choice']['operator'] == choice['operator']
                              and batch['choice']['reason'] == 'known_type_action_gap')
                        for field in ('scores', 'query_influence', 'execution_influence', 'contraction'):
                            check('gap_acquisition_'+field, same(batch['choice'][field], choice[field]))
                        check('gap_acquisition_actual_effective_n', batch['choice']['effective_n'] == current['effective_n'])
                    op = choice['operator']
                    increments = draw(generators[op], law, op)
                    check('fresh_actual_target_batch', batch['operator'] == op and batch['increments'] == increments)
                    check('own_stream_offsets', batch['draw_start'] == offsets[op]
                          and batch['draw_end'] == offsets[op]+BATCH)
                    offsets[op] += BATCH
                    for cat, count in increments.items():
                        member[op][cat] += count
                        pool[op][cat] += count
                    spent += BATCH
                    current = batch['plan']
                    evaluated, _ = point(current)
                    truth_history.append(evaluated)
                    check('actual_target_paid_prefix', batch['spent'] == spent)
                terminal = row['terminal_plan']
                heavy = ('joint_constraints', 'query_certificate', 'projection_supports')
                check('terminal_matches_last_actual_plan', {key: value for key, value in terminal.items()
                      if key not in heavy} == current)
                _, constraints = point(terminal)
                audit_terminal(terminal, constraints, check)
                check('correct_terminal_stop', spent == CAP or ready(terminal))
                check('target_actual_counts', row['member'] == member and row['spent'] == spent == samples(member))
                check('target_budget', 0 <= spent <= CAP and spent % BATCH == 0)
                check('pool_only_actual_batches', row['pooled_after'] == pool)
                source_fee = 3456 if index < 30 else 4608
                check('source_and_history_fees', row['source_paid_samples'] == source_fee
                      and row['history_paid_samples'] == histories[arm]
                      and row['current_paid_samples'] == row['new_paid_samples'] == spent
                      and row['total_reference_paid_samples'] == source_fee+histories[arm]+spent)
                check('correct_completion_flags', row['execution_certified'] == (F(terminal['utility_lower']) >= 2)
                      and row['goal_impossible'] == terminal['goal_impossible']
                      and row['query_certified'] == terminal['query_ready']
                      and row['joint_completed'] == ready(terminal) and not row['fallback'])
                check('finite_model_timing', row['model_seconds'] >= 0 and row['observation_seconds'] >= 0)
                scored = assessed[key]
                check('all_actual_points_scored', len(scored['history']) == len(truth_history))
                for saved_point, truth in zip(scored['history'], truth_history):
                    check('post_decision_actual_vectors', same(saved_point['actual'], truth['vector'])
                          and F(saved_point['actual_utility']) == truth['utility'])
                    check('post_decision_query_regrets', all(F(saved_point['queries'][q]['regret']) == truth['regrets'][q]
                          for q in joint.WEIGHTS))
                check('post_decision_goal_oracle', F(scored['oracle_goal']) == truth_history[-1]['optimal_safe_goal'])
                histories[arm] += spent
                arm_totals[arm] += spent
                summaries.append(dict(life=life, index=index, arm=arm, spent=spent,
                                      query_certified=row['query_certified'], joint_completed=row['joint_completed']))
                print(f'audit life={life} target={index} arm={arm} spent={spent}', flush=True)
        check('life_records_complete', next(rows, None) is None)
        for arm in ARMS:
            saved = final_saved[life][arm]
            check('final_A_sources_immutable', saved['a']['sources'] == sources['a'])
            check('final_A_actual_pool', saved['a']['pools'] == states[arm]['a'])
            check('final_B_sources_immutable', saved['b']['sources'] == sources['b'])
            check('final_B_actual_pool', saved['b']['pools'] == states[arm]['b'])
            check('A_switch_snapshot_preserved', saved['a_at_switch']['sources'] == sources['a']
                  and saved['a_at_switch']['pools'] == states[arm]['a_switch'])
            check('oracle_B_interface', saved['changed_operator'] == metadata['changed_operator']
                  and saved['b_to_a'] == metadata['b_to_a'])
    check('all_target_records_present', seen == {(life, index, arm) for life in LIVES for index in TARGETS for arm in ARMS})
    check('physical_paid_observations', summary['new_environment_observations'] == 13824+sum(arm_totals.values())
          and summary['physical_source_samples'] == summary['source_samples_charged_per_arm'] == 13824)
    for arm in ARMS:
        aggregate = summary['methods'][arm]
        arm_rows = [row for row in summaries if row['arm'] == arm]
        check('aggregate_paid_arm_samples', aggregate['source_samples'] == 13824
              and aggregate['target_samples'] == arm_totals[arm]
              and aggregate['total_samples'] == 13824+arm_totals[arm])
        check('aggregate_completions', aggregate['targets'] == len(arm_rows)
              and aggregate['query_certified'] == sum(row['query_certified'] for row in arm_rows)
              and aggregate['joint_completed'] == sum(row['joint_completed'] for row in arm_rows))
        for name in ('controlled_samples', 'controlled_resets', 'environment_random_draws'):
            check('actual_environment_work', summary['work'][arm][name] == arm_totals[arm])
    for name in ('controlled_samples', 'controlled_resets', 'environment_random_draws'):
        check('physical_source_work', summary['source_work'][name] == 13824)
    result = dict(valid=all(checks[name] == count for name, count in expected.items()), complete=True,
                  records=len(summaries), checks=dict(checks), expected=dict(expected),
                  failures={name: count-checks[name] for name, count in expected.items() if count != checks[name]},
                  physical_observations=13824+sum(arm_totals.values()), seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('checks', 'expected')}), flush=True)
    return result


if __name__ == '__main__':
    run()


