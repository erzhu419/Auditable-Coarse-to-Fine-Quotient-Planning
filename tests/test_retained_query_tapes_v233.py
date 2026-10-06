from copy import deepcopy
from fractions import Fraction as F
import random

import pytest

from scripts import retained_query_tapes_v233 as tapes


def fixture():
    ops, alphabet = tapes.OPERATORS, tapes.ALPHABETS
    a_law = {op: {cat: F(cat == 'DELIVERY') for cat in alphabet[op]} for op in ops}
    b_law = deepcopy(a_law)
    b_law['SHORT_PASS'] = {'DELIVERY': F(0), 'LOST': F(1)}
    cases = [dict(id=f'case{i}', context='B' if 27 <= i < 54 else 'A',
                  stage='B' if 27 <= i < 54 else ('A_RETURN' if i >= 54 else 'A'))
             for i in range(78)]
    laws = [b_law if c['context'] == 'B' else a_law for c in cases]
    identities = [1]*78
    identities[30] = 0
    worlds = {0: (cases, laws, identities,
                  dict(changed_operator='SHORT_PASS', b_to_a=[1, 2, 0]))}
    sources, evidence = [], dict(life=0, a=[], b=[])
    for context, amount, start in (('A', 384, 0), ('B', 128, 27)):
        for identity in range(3):
            anchor = {}
            for j, op in enumerate(ops):
                category = 'LOST' if context == 'B' and op == 'SHORT_PASS' else 'DELIVERY'
                increments = {cat: amount*int(cat == category) for cat in alphabet[op]}
                anchor[op] = increments
                sources.append(dict(life=0, context=context, index=start+identity,
                    slot=identity+(3 if context == 'B' else 0), operator=op,
                    seed=9000+(start+identity)*3+j, draw_start=0, draw_end=amount,
                    increments=increments))
            evidence[context.lower()].append(anchor)
    a, b = deepcopy(evidence['a']), deepcopy(evidence['b'])
    a_switch, rows, history = None, [], 0
    for index, op in ((3, 'SHORT_PASS'), (4, 'DETOUR_PASS'),
                      (30, 'SHORT_PASS'), (54, 'RECOVERY_RETRY')):
        if index == 30:
            a_switch = deepcopy(a)
        identity, case = identities[index], cases[index]
        pool = (a if case['context'] == 'A' else b)[identity]
        before = deepcopy(pool)
        category = 'LOST' if index == 30 else 'DELIVERY'
        increments = {cat: 16*int(cat == category) for cat in alphabet[op]}
        for cat, amount in increments.items():
            pool[op][cat] += amount
        effective = deepcopy(pool)
        if case['context'] == 'B':
            for other in ops:
                if other != 'SHORT_PASS':
                    for cat in alphabet[other]:
                        effective[other][cat] += a_switch[1][other][cat]
        member = {other: dict.fromkeys(alphabet[other], 0) for other in ops}
        member[op] = increments
        source_fee = 3456 if index < 30 else 4608
        rows.append(dict(life=0, index=index, arm='ORACLE_GAP', case=case,
            identity=identity, seeds={other: 20000+index*3+j for j, other in enumerate(ops)},
            batches=[dict(operator=op, draw_start=0, draw_end=16, increments=increments)],
            spent=16, member=member, pooled_before=before, pooled_after=deepcopy(pool),
            source_paid_samples=source_fee, history_paid_samples=history,
            current_paid_samples=16, new_paid_samples=16,
            total_reference_paid_samples=source_fee+history+16,
            terminal_plan=dict(envelopes={other: dict(counts=effective[other]) for other in ops},
                effective_n={other: sum(effective[other].values()) for other in ops})))
        history += 16
    selected = [dict(life=0, index=i, arm='ORACLE_GAP',
                     kind='failure' if i < 54 else 'positive',
                     phase='late_B' if i == 30 else 'A_RETURN') for i in (4, 30, 54)]
    return sources, [evidence], rows, worlds, selected


def test_paid_replay_matches_counts_and_stops_at_recorded_end():
    law = {'SHORT_PASS': {'DELIVERY': F(3, 5), 'LOST': F(2, 5)}}
    expected_generator = random.Random(99)
    expected = ['DELIVERY' if expected_generator.random() < .6 else 'LOST' for _ in range(16)]
    record = dict(operator='SHORT_PASS', draw_start=0, draw_end=16,
                  increments={cat: expected.count(cat) for cat in tapes.ALPHABETS['SHORT_PASS']})
    generator = random.Random(99)
    assert tapes.replay_batch(record, law, generator, 0) == expected
    assert generator.getstate() == expected_generator.getstate()


def test_no_source_or_current_member_double_count_and_a_return_excludes_b():
    result = tapes.reconstruct_data(*fixture())
    a, b, returned = result['snapshots']
    assert {op: len(q) for op, q in a['operators'].items()} == {
        'SHORT_PASS': 400, 'DETOUR_PASS': 400, 'RECOVERY_RETRY': 384}
    assert len(b['operators']['SHORT_PASS']) == 144
    assert set(b['operators']['SHORT_PASS']) == {'LOST'}
    assert len(b['operators']['DETOUR_PASS']) == 528
    assert len(b['operators']['RECOVERY_RETRY']) == 512
    assert {op: len(q) for op, q in returned['operators'].items()} == {
        'SHORT_PASS': 400, 'DETOUR_PASS': 400, 'RECOVERY_RETRY': 400}
    assert set(returned['operators']['SHORT_PASS']) == {'DELIVERY'}


def test_paid_chronology_provenance_and_nonadditive_fees():
    result = tapes.reconstruct_data(*fixture())
    summary = result['summary']
    assert summary['replayed_physical_source_samples'] == 4608
    assert summary['replayed_target_samples'] == 64
    assert summary['new_observations'] == summary['new_paid_samples'] == 0
    b = result['snapshots'][1]
    segments = b['provenance']['DETOUR_PASS']
    assert [s['context'] for s in segments] == ['A', 'A', 'B']
    assert [s['kind'] for s in segments] == ['source', 'target', 'source']
    assert [s['queue_start'] for s in segments] == [0, 384, 400]
    assert [s['queue_end'] for s in segments] == [384, 400, 528]
    assert [s['availability_order'] for s in segments] == sorted(s['availability_order'] for s in segments)
    assert b['fees']['total_reference_paid_samples'] == 4608+32+16
    assert b['fees']['evidence_samples'] == 144+528+512


def test_replay_count_mismatch_is_an_error_not_sorted_or_synthesized():
    sources, evidence, rows, worlds, selection = fixture()
    rows[0]['batches'][0]['increments'] = {'DELIVERY': 15, 'LOST': 1}
    with pytest.raises(ValueError, match='seed replay differs'):
        tapes.reconstruct_data(sources, evidence, rows, worlds, selection)


def test_existing_pool_duplicate_and_fee_mismatch_are_detected():
    sources, evidence, rows, worlds, selection = fixture()
    rows[1]['pooled_before']['SHORT_PASS']['DELIVERY'] += 16
    with pytest.raises(ValueError, match='prefix differs before'):
        tapes.reconstruct_data(sources, evidence, rows, worlds, selection)
    sources, evidence, rows, worlds, selection = fixture()
    rows[1]['history_paid_samples'] += 16
    with pytest.raises(ValueError, match='fee differs'):
        tapes.reconstruct_data(sources, evidence, rows, worlds, selection)
