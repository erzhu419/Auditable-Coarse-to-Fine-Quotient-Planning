"""One oracle-assisted H4 query-family quotient and its own-policy ground replay.

The six models share the disjoint union of two retained FULL kernels.  Planning
uses joint Fraction R/F/S vectors; no concrete boards or oracle boundary values
are passed to a quotient planner.  Only compact models, membership, policies and
root/full-state summary metrics are persisted, not the oracle Q profiles.
"""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import json
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
INPUT_BASE = ROOT/'reports/controlled_predictive_composition_v69'
OUTPUT = ROOT/'reports/controlled_predictive_reference_feasibility_v199'
SCHEMA = 'acfqp.reference_feasibility.v199'
EPSILON = Fraction(1, 10**12)
WIDTHS = (Fraction(0), Fraction(1, 256), Fraction(1, 64), Fraction(1, 16), Fraction(1, 4), Fraction(1))
CASE_NAMES = ('v69_h4_00', 'v69_h4_01')
ZERO_COUNTS = ('new_environment_samples', 'new_physical_samples', 'new_model_fits',
    'new_parameter_solves', 'new_native_weight_updates', 'new_teacher_tapes')
SOURCE_FILES = ('scripts/run_controlled_predictive_reference_feasibility_v199.py',
    'scripts/analyze_controlled_predictive_reference_feasibility_v199.py',
    'tests/test_reference_feasibility_runner_v199.py',
    'tests/test_reference_feasibility_analysis_v199.py',
    'specs/REFERENCE_FEASIBILITY_V199.md', 'reports/v199_runtime_tmp/run_checks.py',
    'reports/v199_runtime_tmp/run_stage.py')


class ReferenceExecutionError(RuntimeError):
    """A failed pilot retains the work completed before its failure."""
    def __init__(self, operation, error, counts):
        super().__init__(str(error))
        self.record = dict(operation=operation, error=dict(type=type(error).__name__, message=str(error)),
            costs=dict(counts))


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False)+'\n')


def compact_bytes(payload):
    return (json.dumps(payload, separators=(',', ':'), allow_nan=False)+'\n').encode('utf-8')


def decode_kernel(payload, counts=None):
    counts = Counter() if counts is None else counts
    cells = {state: (layer, status) for state, layer, status in payload['cells']}
    rows, actions = {}, defaultdict(list)
    counts['kernel_payloads_decoded'] += 1
    counts['kernel_cells_decoded'] += len(cells)
    for state, action, outcomes in payload['rows']:
        rows[state, action] = [(Fraction(p, q), target, Fraction(r, s)) for p, q, target, r, s in outcomes]
        actions[state].append(action)
        counts['kernel_action_rows_decoded'] += 1
        counts['kernel_outcomes_decoded'] += len(outcomes)
    return dict(cells=cells, rows=rows, roots=list(payload['roots']),
        actions={state: tuple(sorted(names)) for state, names in actions.items()})


def disjoint_union(payloads, counts=None):
    """Case order follows the input dict; native IDs are remapped ascending."""
    counts = Counter() if counts is None else counts
    cells, rows, actions, roots, bindings = {}, {}, {}, [], []
    for name, payload in payloads.items():
        original = decode_kernel(payload, counts)
        offset = len(cells)
        remap = {state: offset+index for index, state in enumerate(sorted(original['cells']))}
        for state in sorted(original['cells']):
            cells[remap[state]] = original['cells'][state]
            counts['union_states_remapped'] += 1
        for state, action in sorted(original['rows']):
            outcomes = original['rows'][state, action]
            rows[remap[state], action] = [(p, remap[target], r) for p, target, r in outcomes]
            counts['union_action_rows_remapped'] += 1
            counts['union_outcomes_remapped'] += len(outcomes)
        actions.update({remap[state]: names for state, names in original['actions'].items()})
        for state in original['roots']:
            roots.append(remap[state])
            bindings.append(dict(case=name, original_root=state, union_root=remap[state]))
    return dict(cells=cells, rows=rows, actions=actions, roots=roots), bindings


def coefficients(query):
    return tuple(Fraction(str(query[name])) for name in ('reward_weight', 'failure_penalty', 'goal_bonus'))


def query_value(vector, query):
    reward, failure, success = coefficients(query)
    return reward*vector[0]-failure*vector[1]+success*vector[2]


def terminal_vector(status):
    return (Fraction(0), Fraction(status == 'LOST'), Fraction(status == 'WON'))


def _row_vector(outcomes, values, counts, prefix):
    total = [Fraction(0), Fraction(0), Fraction(0)]
    counts[prefix+'_dp_action_rows'] += 1
    for probability, target, reward in outcomes:
        child = values[target]
        total[0] += probability*(reward+child[0])
        total[1] += probability*child[1]
        total[2] += probability*child[2]
        counts[prefix+'_dp_outcome_terms'] += 1
        counts[prefix+'_dp_reward_additions'] += 1
        counts[prefix+'_dp_component_products'] += 3
        counts[prefix+'_dp_component_additions'] += 3
    return tuple(total)


def solve(kernel, query, counts=None, prefix='oracle'):
    """Bottom-up exact joint-vector planning on this kernel's own successors."""
    counts = Counter() if counts is None else counts
    reward, failure, success = coefficients(query)
    values, qvectors, policy = {}, {}, {}
    counts[prefix+'_dp_calls'] += 1
    for state in sorted(kernel['cells'], key=lambda s: (kernel['cells'][s][0], s)):
        _, status = kernel['cells'][state]
        counts[prefix+'_dp_states'] += 1
        if status != 'ACTIVE':
            values[state] = terminal_vector(status)
            counts[prefix+'_dp_terminal_states'] += 1
            continue
        counts[prefix+'_dp_active_states'] += 1
        winner, best = None, None
        for action in kernel['actions'][state]:
            vector = _row_vector(kernel['rows'][state, action], values, counts, prefix)
            qvectors[state, action] = vector
            utility = reward*vector[0]-failure*vector[1]+success*vector[2]
            counts[prefix+'_dp_utility_evaluations'] += 1
            if winner is None:
                winner, best = action, utility
            else:
                counts[prefix+'_dp_choice_comparisons'] += 1
                if utility > best+EPSILON:
                    winner, best = action, utility
        policy[state] = winner
        values[state] = qvectors[state, winner]
    return dict(values=values, qvectors=qvectors, policy=policy)


def replay_policy(kernel, policy, counts=None):
    """Evaluate the supplied ground policy everywhere, without oracle values."""
    counts = Counter() if counts is None else counts
    values = {}
    counts['replay_dp_calls'] += 1
    for state in sorted(kernel['cells'], key=lambda s: (kernel['cells'][s][0], s)):
        _, status = kernel['cells'][state]
        counts['replay_dp_states'] += 1
        if status != 'ACTIVE':
            values[state] = terminal_vector(status)
            counts['replay_dp_terminal_states'] += 1
        else:
            counts['replay_dp_active_states'] += 1
            values[state] = _row_vector(kernel['rows'][state, policy[state]], values, counts, 'replay')
    return values


def partition_key(kernel, profiles, state, width, counts=None):
    counts = Counter() if counts is None else counts
    layer, status = kernel['cells'][state]
    legal = kernel['actions'].get(state, ())
    coordinates = []
    counts['profile_partition_states'] += 1
    if status == 'ACTIVE':
        for name in sorted(profiles):
            for action in legal:
                for component in profiles[name]['qvectors'][state, action]:
                    counts['profile_coordinate_reads'] += 1
                    if width:
                        coordinates.append(component//width)
                        counts['profile_floor_divisions'] += 1
                    else:
                        coordinates.append(component)
    return layer, status, legal, tuple(coordinates)


def model_payload(kernel):
    return dict(schema=SCHEMA+'.model',
        cells=[[state, *kernel['cells'][state]] for state in sorted(kernel['cells'])],
        rows=[[state, action, [[p.numerator, p.denominator, target, r.numerator, r.denominator]
            for p, target, r in kernel['rows'][state, action]]] for state, action in sorted(kernel['rows'])],
        roots=list(kernel['roots']))


def compile_reference(kernel, profiles, width, counts=None):
    """Partition by complete profiles, then compile uniform-member closed rows.

    Member laws and expected rewards are read once per cell/action.  Their sums
    produce the quotient row; the retained temporary laws also supply TV/spread.
    """
    counts = Counter() if counts is None else counts
    keys = {state: partition_key(kernel, profiles, state, width, counts) for state in sorted(kernel['cells'])}
    key_ids = {key: index for index, key in enumerate(sorted(set(keys.values())))}
    mapping = {state: key_ids[key] for state, key in keys.items()}
    members = defaultdict(list)
    for state, cell in mapping.items():
        members[cell].append(state)
    cells, rows, actions = {}, {}, {}
    max_reward_spread, max_tv = Fraction(0), Fraction(0)
    for cell in sorted(members):
        states = members[cell]
        exemplar = states[0]
        cells[cell] = kernel['cells'][exemplar]
        counts['compiled_cells'] += 1
        legal = kernel['actions'].get(exemplar, ())
        if legal:
            actions[cell] = legal
        for action in legal:
            laws, rewards = [], []
            total_law, total_reward = defaultdict(Fraction), Fraction(0)
            for state in states:
                law, expected_reward = defaultdict(Fraction), Fraction(0)
                counts['compiled_member_action_rows'] += 1
                for p, target, immediate in kernel['rows'][state, action]:
                    expected_reward += p*immediate
                    next_cell = mapping[target]
                    law[next_cell] += p
                    total_law[next_cell] += p
                    counts['compiled_member_outcome_terms'] += 1
                    counts['compiled_expected_reward_products'] += 1
                    counts['compiled_expected_reward_additions'] += 1
                    counts['compiled_successor_additions'] += 2
                laws.append(law)
                rewards.append(expected_reward)
                total_reward += expected_reward
                counts['compiled_reward_member_additions'] += 1
            mean_reward = total_reward/len(states)
            counts['compiled_reward_mean_divisions'] += 1
            mean_law = {target: mass/len(states) for target, mass in sorted(total_law.items())}
            counts['compiled_successor_mean_divisions'] += len(mean_law)
            rows[cell, action] = [(p, target, mean_reward) for target, p in mean_law.items()]
            counts['compiled_action_rows'] += 1
            counts['compiled_outcomes'] += len(mean_law)
            max_reward_spread = max(max_reward_spread, max(rewards)-min(rewards))
            for law in laws:
                targets = sorted(set(law)|set(mean_law))
                tv = sum((abs(law.get(target, Fraction(0))-mean_law.get(target, Fraction(0)))
                    for target in targets), Fraction(0))/2
                counts['compiled_member_tv_coordinates'] += len(targets)
                counts['compiled_tv_evaluations'] += 1
                max_tv = max(max_tv, tv)
    abstract = dict(cells=cells, rows=rows, actions=actions, roots=[mapping[root] for root in kernel['roots']])
    payload = model_payload(abstract)
    mapping_records = [[state, cell] for state, cell in sorted(mapping.items())]
    member_records = [[cell, members[cell]] for cell in sorted(members)]
    metrics = dict(cells=len(cells), active_cells=sum(status == 'ACTIVE' for _, status in cells.values()),
        action_rows=len(rows), outcomes=sum(len(row) for row in rows.values()),
        serialized_bytes=len(compact_bytes(payload)), mapping_bytes=len(compact_bytes(mapping_records)),
        membership_bytes=len(compact_bytes(member_records)), max_reward_spread=float(max_reward_spread),
        max_successor_tv=float(max_tv))
    record = dict(width=[width.numerator, width.denominator], model=payload, mapping=mapping_records,
        members=member_records, metrics=metrics)
    return record, abstract, mapping


def evaluate_width(kernel, queries, profiles, bindings, record, abstract, mapping, counts):
    active = [state for state in sorted(kernel['cells']) if kernel['cells'][state][1] == 'ACTIVE']
    results, decisions = [], []
    value_preserved = True
    for name in sorted(queries):
        query, oracle = queries[name], profiles[name]
        planned = solve(abstract, query, counts, 'abstract')
        lifted = {state: planned['policy'][mapping[state]] for state in active}
        counts['policy_lifts'] += len(active)
        actual = replay_policy(kernel, lifted, counts)
        max_regret, max_errors = Fraction(0), [Fraction(0), Fraction(0), Fraction(0)]
        for state in active:
            regret = query_value(oracle['values'][state], query)-query_value(actual[state], query)
            counts['evaluation_active_regret_states'] += 1
            max_regret = max(max_regret, regret)
            value_preserved = value_preserved and abs(regret) <= Fraction(1, 10**10)
            for k in range(3):
                error = abs(planned['values'][mapping[state]][k]-actual[state][k])
                max_errors[k] = max(max_errors[k], error)
                value_preserved = value_preserved and error <= Fraction(1, 10**10)
                counts['evaluation_component_error_coordinates'] += 1
        roots = []
        for binding in bindings:
            state, cell = binding['union_root'], mapping[binding['union_root']]
            oracle_utility = query_value(oracle['values'][state], query)
            actual_utility = query_value(actual[state], query)
            roots.append(dict(case=binding['case'], union_root=state, abstract_root=cell,
                action=lifted.get(state), oracle_action=oracle['policy'].get(state),
                predicted_rfs=[float(value) for value in planned['values'][cell]],
                actual_rfs=[float(value) for value in actual[state]],
                oracle_rfs=[float(value) for value in oracle['values'][state]],
                oracle_utility=float(oracle_utility), actual_utility=float(actual_utility),
                regret=float(oracle_utility-actual_utility)))
            counts['evaluation_root_records'] += 1
        results.append(dict(query=name, root_records=roots, max_active_regret=float(max_regret),
            max_active_prediction_error=[float(value) for value in max_errors]))
        decisions.append(dict(query=name, policy=[[cell, action] for cell, action in sorted(planned['policy'].items())],
            root_records=roots))
    maximum_regret = max(row['max_active_regret'] for row in results)
    maximum_errors = [max(row['max_active_prediction_error'][k] for row in results) for k in range(3)]
    ground_active = len(active)
    qualifies = (2*record['metrics']['active_cells'] <= ground_active and
        2*record['metrics']['action_rows'] <= len(kernel['rows']) and maximum_regret <= .01 and max(maximum_errors) <= .01)
    curve = dict(width=record['width'], model=record['metrics'], queries=results,
        max_active_regret=maximum_regret, max_active_prediction_error=maximum_errors, qualifies=qualifies)
    return curve, dict(width=record['width'], queries=decisions), value_preserved


def evaluate_case(kernel, queries, bindings, counts=None, on_profiles=None, on_width=None):
    """One all-query oracle profile, six shared compilations and own-policy replays."""
    counts = Counter() if counts is None else counts
    profiles = {name: solve(kernel, queries[name], counts, 'oracle') for name in sorted(queries)}
    if on_profiles is not None:
        on_profiles()
    models, choices, curve = [], [], []
    positive_control_valid = False
    for width in WIDTHS:
        record, abstract, mapping = compile_reference(kernel, profiles, width, counts)
        result, decision, value_preserved = evaluate_width(kernel, queries, profiles, bindings,
            record, abstract, mapping, counts)
        if width == 0:
            positive_control_valid = value_preserved
        models.append(record)
        choices.append(decision)
        curve.append(result)
        if on_width is not None:
            on_width(models, choices, curve)
    qualifying = [row['width'] for row in curve if row['qualifies']]
    summary = dict(schema=SCHEMA+'.summary', complete=True,
        ground=dict(cells=len(kernel['cells']), active_cells=sum(status == 'ACTIVE' for _, status in kernel['cells'].values()),
            action_rows=len(kernel['rows']), outcomes=sum(len(row) for row in kernel['rows'].values())),
        curve=curve, positive_control_valid=positive_control_valid,
        routing=dict(qualifying_widths=qualifying,
            next_step='learn_reference_distinctions' if qualifying else 'reassess_reference_family'))
    return dict(compiled=dict(models=models, root_bindings=bindings), choices=dict(width_records=choices), summary=summary)


def retain_inputs(output, counts, input_base=None):
    """Read exactly the five declared files; retain originals before decoding."""
    input_base = INPUT_BASE if input_base is None else Path(input_base)
    specs = [(input_base/'manifest.json', 'v69_manifest.json')]
    for name in CASE_NAMES:
        specs.extend(((input_base/name/'FULL.model.json', name+'_FULL.model.json'),
            (input_base/name/'portable_inputs.json', name+'_portable_inputs.json')))
    decoded, records = [], []
    for original, saved_name in specs:
        raw = original.read_bytes()
        counts['input_files_read'] += 1
        counts['input_bytes_read'] += len(raw)
        destination = output/'inputs'/saved_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        counts['input_files_retained'] += 1
        counts['input_bytes_retained'] += len(raw)
        records.append(dict(original=str(original), saved='inputs/'+saved_name, bytes=len(raw)))
        save(output/'input_manifest.json', dict(schema=SCHEMA+'.inputs', records=records))
        decoded.append(json.loads(raw))
    if decoded[0]['status'] != 'complete':
        raise ValueError('retained V69 manifest is not complete')
    queries = decoded[2]['queries']
    if len(queries) != 14 or queries != decoded[4]['queries']:
        raise ValueError('two fixed portable query families must agree and contain fourteen queries')
    return {CASE_NAMES[0]: decoded[1], CASE_NAMES[1]: decoded[3]}, queries


def freeze_source(output):
    records = []
    for relative in SOURCE_FILES:
        raw = (ROOT/relative).read_bytes()
        saved = output/'source_code'/relative
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_bytes(raw)
        records.append(dict(original=str(ROOT/relative), saved='source_code/'+relative, bytes=len(raw)))
    save(output/'source_manifest.json', dict(schema=SCHEMA+'.source', records=records))


def run(output=OUTPUT):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    counts = Counter({key: 0 for key in ZERO_COUNTS})
    begun = perf_counter()
    record = dict(schema=SCHEMA+'.run', status='running', complete=False, phases=[], costs={})
    operation = 'source_freeze'
    def phase(name):
        record['phases'].append(dict(phase=name, input_reads=counts['input_files_read'], seconds=perf_counter()-begun))
        record['costs'] = dict(counts)
        save(output/'run.json', record)
        print(json.dumps(dict(event=name, input_reads=counts['input_files_read'])), flush=True)
    try:
        freeze_source(output)
        phase('protocol_frozen')
        operation = 'inputs'
        payloads, queries = retain_inputs(output, counts)
        phase('inputs_retained')
        operation = 'union'
        kernel, bindings = disjoint_union(payloads, counts)
        def retain_width(models, choices, curve):
            save(output/'compiled.json', dict(models=models, root_bindings=bindings))
            save(output/'choices.json', dict(width_records=choices))
            record['costs'] = dict(counts)
            save(output/'run.json', record)
        operation = 'reference_curve'
        result = evaluate_case(kernel, queries, bindings, counts,
            on_profiles=lambda: phase('profiles_frozen'), on_width=retain_width)
        save(output/'summary.json', result['summary'])
        phase('curve_complete')
        record.update(status='complete', complete=True, seconds=perf_counter()-begun)
        phase('complete')
        return record
    except Exception as error:
        failure = ReferenceExecutionError(operation, error, counts)
        record.update(status='failed', complete=False, seconds=perf_counter()-begun,
            failure=failure.record['error'], costs=dict(counts))
        save(output/'failed_execution.json', failure.record)
        save(output/'run.json', record)
        raise failure from error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
