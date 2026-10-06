"""Recover ordered outcomes of V231's paid prefixes, without acquiring a suffix.

Replay is an environment-side operation.  Only observed categories and their
paid provenance leave this module; neither laws nor oracle labels are returned.
Per-operator queues preserve observation order.  Their reconstruction alone
does not justify treating adaptively interleaved queue products as iid pairs.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import gzip
import importlib
import json
from pathlib import Path
import random
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT/'reports/oracle_gap_lifecycle_v231'
SELECTION = ROOT/'reports/kernel_query_profile_v232/inputs.jsonl.gz'
OPERATORS = ('SHORT_PASS', 'DETOUR_PASS', 'RECOVERY_RETRY')
ALPHABETS = {'SHORT_PASS': ('DELIVERY', 'LOST'),
             'DETOUR_PASS': ('DELIVERY', 'LOST', 'RECOVERY'),
             'RECOVERY_RETRY': ('DELIVERY', 'LOST')}


def counts(queues):
    return {op: {cat: queues[op].count(cat) for cat in ALPHABETS[op]}
            for op in OPERATORS}


def empty_queues():
    return {op: [] for op in OPERATORS}


def replay_batch(record, law, generator, cursor):
    """Replay exactly a recorded interval and reject unrecoverable outcomes."""
    op = record['operator']
    if record['draw_start'] != cursor:
        raise ValueError('recorded operator prefix is not contiguous')
    number = record['draw_end']-cursor
    if number != sum(record['increments'].values()):
        raise ValueError('recorded batch length differs from paid counts')
    observed = []
    # Match the captured V205 draw function's Fraction accumulation/float test.
    for _ in range(number):
        value, cumulative = generator.random(), Fraction(0)
        for category in ALPHABETS[op]:
            cumulative += law[op][category]
            if value < float(cumulative):
                observed.append(category)
                break
    actual = {category: observed.count(category) for category in ALPHABETS[op]}
    if actual != record['increments']:
        raise ValueError('seed replay differs from retained paid batch outcomes')
    return observed


def frozen_worlds(input_dir):
    """Import the captured task closure under an isolated package name."""
    source = input_dir/'source_code'
    name = '_retained_v231_task'
    package = ModuleType(name)
    package.__path__ = [str(source/'src/acfqp')]
    sys.modules[name] = package
    science = ModuleType(name+'.science')
    science.__path__ = [str(source/'src/acfqp/science')]
    sys.modules[name+'.science'] = science
    task = importlib.import_module(name+'.science.scoped_route_task_v228')
    worlds = {life: task.world(life) for life in range(3)}
    paths = sorted(str(Path(module.__file__).resolve().relative_to(ROOT))
                   for key, module in tuple(sys.modules.items())
                   if key.startswith(name+'.') and getattr(module, '__file__', None))
    paths.append(str((source/'scripts/run_conditioned_mechanisms_v205.py').relative_to(ROOT)))
    return worlds, paths


def read_rows(input_dir):
    rows = []
    for path in sorted(input_dir.glob('records_life_*.jsonl.gz')):
        with gzip.open(path, 'rt') as handle:
            rows.extend(json.loads(line) for line in handle)
    return rows


def _segment(record, kind, availability_order, arm=None):
    result = {key: record[key] for key in
              ('life', 'context', 'index', 'operator', 'seed', 'draw_start', 'draw_end')}
    result.update(kind=kind, availability_order=availability_order)
    if arm is not None:
        result['arm'] = arm
    return result


def _joined(state, case, identity):
    current = state[case['context']][identity]
    queues, provenance = deepcopy(current['queues']), deepcopy(current['provenance'])
    if case['context'] == 'B':
        inherited = state['A_at_switch'][state['b_to_a'][identity]]
        for op in OPERATORS:
            if op != state['changed_operator']:
                queues[op] = inherited['queues'][op]+queues[op]
                provenance[op] = deepcopy(inherited['provenance'][op])+provenance[op]
    for op in OPERATORS:
        cursor = 0
        for segment in provenance[op]:
            segment['queue_start'] = cursor
            cursor += segment['draw_end']-segment['draw_start']
            segment['queue_end'] = cursor
        if cursor != len(queues[op]):
            raise ValueError('queue provenance differs from recovered prefix')
    return queues, provenance


def reconstruct_data(source_records, evidence, rows, worlds, selection):
    """Recover a frozen selection while verifying every physical paid batch."""
    selected = {(r['life'], r['index'], r['arm']): r for r in selection}
    recovered_sources, source_generators, source_cursors = {}, {}, Counter()
    source_samples = 0
    for record in source_records:
        key = record['life'], record['context'], record['index'], record['operator']
        if key not in source_generators:
            source_generators[key] = random.Random(record['seed'])
        events = replay_batch(record, worlds[record['life']][1][record['index']],
                              source_generators[key], source_cursors[key])
        source_cursors[key] += len(events)
        recovered_sources.setdefault(key[:2], []).append((record, events))
        source_samples += len(events)
    source_evidence = {r['life']: r for r in evidence}
    snapshots, target_samples, target_batches, availability_order = {}, 0, 0, 0

    def source_bank(life, context):
        nonlocal availability_order
        pools = [dict(queues=empty_queues(), provenance=empty_queues()) for _ in range(3)]
        for record, events in recovered_sources[life, context]:
            identity = record['slot'] if context == 'A' else record['slot']-3
            op, pool = record['operator'], pools[identity]
            pool['queues'][op].extend(events)
            pool['provenance'][op].append(_segment(record, 'source', availability_order))
            availability_order += 1
        if [counts(pool['queues']) for pool in pools] != source_evidence[life][context.lower()]:
            raise ValueError('recovered source evidence differs from paid anchors')
        return pools

    states, history, current_life, b_sources, last_index = {}, {}, None, None, {}
    for row in rows:
        life, index, arm = row['life'], row['index'], row['arm']
        case, identity = row['case'], row['identity']
        if life != current_life:
            if current_life is not None and life <= current_life:
                raise ValueError('retained life chronology is not increasing')
            a_sources = source_bank(life, 'A')
            states, history, last_index = {}, {}, {}
            current_life, b_sources = life, None
        if arm not in states:
            states[arm] = {'A': deepcopy(a_sources)}
            history[arm] = 0
        state = states[arm]
        if index <= last_index.get(arm, -1):
            raise ValueError('retained target chronology repeats or reorders a member')
        last_index[arm] = index
        if case != worlds[life][0][index] or identity != worlds[life][2][index]:
            raise ValueError('captured task differs from retained target identity')
        if case['context'] == 'B' and 'B' not in state:
            if b_sources is None:
                b_sources = source_bank(life, 'B')
            state['A_at_switch'] = deepcopy(state['A'])
            state['B'] = deepcopy(b_sources)
            state.update({k: deepcopy(worlds[life][3][k])
                          for k in ('b_to_a', 'changed_operator')})
        pool = state[case['context']][identity]
        if counts(pool['queues']) != row['pooled_before']:
            raise ValueError('retained pool prefix differs before target update')
        generators = {op: random.Random(row['seeds'][op]) for op in OPERATORS}
        member, cursors = empty_queues(), Counter()
        for batch in row['batches']:
            op = batch['operator']
            events = replay_batch(batch, worlds[life][1][index], generators[op], cursors[op])
            cursors[op] += len(events)
            member[op].extend(events)
            pool['queues'][op].extend(events)
            record = dict(batch, life=life, context=case['context'], index=index,
                          seed=row['seeds'][op])
            pool['provenance'][op].append(_segment(record, 'target', availability_order, arm))
            availability_order += 1
            target_samples += len(events)
            target_batches += 1
        amount = sum(map(len, member.values()))
        if amount != row['spent'] or counts(member) != row['member']:
            raise ValueError('recovered member differs from retained paid observations')
        if counts(pool['queues']) != row['pooled_after']:
            raise ValueError('retained pool prefix differs after target update')
        source_paid = 3456 if index < 30 else 4608
        fees = dict(source_paid_samples=source_paid, history_paid_samples=history[arm],
                    current_paid_samples=amount,
                    total_reference_paid_samples=source_paid+history[arm]+amount)
        if any(row[key] != value for key, value in fees.items()) or row['new_paid_samples'] != amount:
            raise ValueError('retained target fee differs from actual paid chronology')
        history[arm] += amount
        key = life, index, arm
        if key in selected:
            queues, provenance = _joined(state, case, identity)
            expected = row['terminal_plan']['envelopes']
            if any(counts(queues)[op] != expected[op]['counts'] or
                   len(queues[op]) != row['terminal_plan']['effective_n'][op]
                   for op in OPERATORS):
                raise ValueError('recovered effective pool differs from terminal plan')
            descriptor = selected[key]
            fees['evidence_samples'] = sum(map(len, queues.values()))
            snapshots[key] = dict(life=life, index=index, arm=arm,
                kind=descriptor['kind'], phase=descriptor['phase'],
                case=deepcopy(case), identity=identity, operators=queues,
                provenance=provenance, fees=fees,
                changed_operator=worlds[life][3]['changed_operator'],
                member=member, new_observations=0, new_paid_samples=0)
    if set(snapshots) != set(selected):
        raise ValueError('frozen selection contains a missing paid target snapshot')
    return dict(snapshots=[snapshots[r['life'], r['index'], r['arm']] for r in selection],
        summary=dict(target_rows=len(rows), selected_snapshots=len(snapshots),
            source_batches=len(source_records), target_batches=target_batches,
            replayed_physical_source_samples=source_samples,
            replayed_target_samples=target_samples,
            new_observations=0, new_paid_samples=0,
            all_paid_batches_exact=True,
            queue_product_validity='requires a predictable-pairing statistical argument',
            row_fee_scope='cumulative reference fees are not additive'))


def reconstruct(input_dir=INPUT, selection_path=SELECTION):
    input_dir, selection_path = Path(input_dir), Path(selection_path)
    worlds, source_paths = frozen_worlds(input_dir)
    cases = json.loads((input_dir/'cases.json').read_text())
    if any(row['cases'] != worlds[row['life']][0] for row in cases):
        raise ValueError('frozen task cases differ from retained public roster')
    with gzip.open(selection_path, 'rt') as handle:
        selection = [json.loads(line) for line in handle]
    recovered = reconstruct_data(json.loads((input_dir/'source_records.json').read_text()),
        json.loads((input_dir/'source_evidence.json').read_text()),
        read_rows(input_dir), worlds, selection)
    recovered['source_code_paths'] = source_paths
    recovered['input_paths'] = [str(path.relative_to(ROOT)) for path in
        (input_dir/'source_records.json', input_dir/'source_evidence.json', input_dir/'cases.json',
         selection_path, *sorted(input_dir.glob('records_life_*.jsonl.gz')))]
    return recovered
