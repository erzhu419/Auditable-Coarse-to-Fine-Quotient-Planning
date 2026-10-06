from copy import deepcopy
from fractions import Fraction as F

import pytest

from scripts import retained_life_end_tapes_v238 as tapes
from acfqp.science import source_predictive_evidence_v236 as predictive


def fixture():
    operators, alphabet = tapes.OPERATORS, tapes.ALPHABETS
    a_law = {op: {cat: F(cat == 'DELIVERY') for cat in alphabet[op]} for op in operators}
    b_law = deepcopy(a_law)
    b_law['SHORT_PASS'] = {'DELIVERY': F(0), 'LOST': F(1)}
    cases = [dict(id=f'case{i}', context='B' if 27 <= i < 54 else 'A',
        stage='B' if 27 <= i < 54 else ('A_RETURN' if i >= 54 else 'A')) for i in range(78)]
    laws = [b_law if case['context'] == 'B' else a_law for case in cases]
    identities = [0 if case['context'] == 'B' else 1 for case in cases]
    worlds = {0: (cases, laws, identities, dict(changed_operator='SHORT_PASS', b_to_a=[1, 2, 0]))}
    sources, evidence = [], dict(life=0, a=[], b=[])
    for context, amount, start in (('A', 384, 0), ('B', 128, 27)):
        for identity in range(3):
            anchor = {}
            for j, op in enumerate(operators):
                category = 'LOST' if context == 'B' and op == 'SHORT_PASS' else 'DELIVERY'
                increments = {cat: amount*int(cat == category) for cat in alphabet[op]}
                anchor[op] = increments
                sources.append(dict(life=0, context=context, index=start+identity,
                    slot=identity+(3 if context == 'B' else 0), operator=op,
                    seed=9000+(start+identity)*3+j, draw_start=0, draw_end=amount, increments=increments))
            evidence[context.lower()].append(anchor)
    operators_by_arm = {
        'ORACLE_GAP': ('SHORT_PASS', 'DETOUR_PASS', 'SHORT_PASS', 'RECOVERY_RETRY',
                       'RECOVERY_RETRY', 'DETOUR_PASS', 'DETOUR_PASS'),
        'ORACLE_BALANCED': ('RECOVERY_RETRY', 'SHORT_PASS', 'DETOUR_PASS', 'SHORT_PASS',
                            'SHORT_PASS', 'DETOUR_PASS', 'RECOVERY_RETRY')}
    indices = (3, 4, 30, 31, 54, 55, 77)
    states = {arm: dict(A=deepcopy(evidence['a']), B=deepcopy(evidence['b'])) for arm in operators_by_arm}
    history, rows = dict.fromkeys(operators_by_arm, 0), []
    for offset, index in enumerate(indices):
        for arm, op_schedule in operators_by_arm.items():
            op, case, identity = op_schedule[offset], cases[index], identities[index]
            state = states[arm]
            if index == 30:
                state['A_at_switch'] = deepcopy(state['A'])
            pool = state[case['context']][identity]
            before = deepcopy(pool)
            category = 'LOST' if case['context'] == 'B' and op == 'SHORT_PASS' else 'DELIVERY'
            increments = {cat: 16*int(cat == category) for cat in alphabet[op]}
            for cat, amount in increments.items():
                pool[op][cat] += amount
            effective = deepcopy(pool)
            if case['context'] == 'B':
                for other in operators:
                    if other != 'SHORT_PASS':
                        for cat in alphabet[other]:
                            effective[other][cat] += state['A_at_switch'][1][other][cat]
            member = {other: dict.fromkeys(alphabet[other], 0) for other in operators}
            member[op] = increments
            source_fee = 3456 if index < 30 else 4608
            rows.append(dict(life=0, index=index, arm=arm, case=case, identity=identity,
                seeds={other: 20000+index*3+j for j, other in enumerate(operators)},
                batches=[dict(operator=op, draw_start=0, draw_end=16, increments=increments)],
                spent=16, member=member, pooled_before=before, pooled_after=deepcopy(pool),
                source_paid_samples=source_fee, history_paid_samples=history[arm],
                current_paid_samples=16, new_paid_samples=16,
                total_reference_paid_samples=source_fee+history[arm]+16,
                terminal_plan=dict(envelopes={other: dict(counts=effective[other]) for other in operators},
                    effective_n={other: sum(effective[other].values()) for other in operators})))
            history[arm] += 16
    selected = [dict(life=0, index=index, arm=arm, kind='positive' if index >= 54 else 'failure',
        phase='A_RETURN' if index >= 54 else ('late_B' if index >= 30 else 'A'))
        for index, arm in ((4, 'ORACLE_GAP'), (30, 'ORACLE_GAP'), (54, 'ORACLE_GAP'),
                           (30, 'ORACLE_BALANCED'), (54, 'ORACLE_BALANCED'))]
    return sources, [evidence], rows, worlds, selected


def test_life_end_a_resumes_all_a_targets_without_other_arm_or_b_data():
    result = tapes.reconstruct_data(*fixture())
    early, _, returned, _, balanced = result['snapshots']
    assert early['index'] == 4 and returned['index'] == 54
    assert early['operators'] == returned['operators']
    assert {op: len(values) for op, values in early['operators'].items()} == {
        'SHORT_PASS': 400, 'DETOUR_PASS': 432, 'RECOVERY_RETRY': 400}
    assert {op: len(values) for op, values in balanced['operators'].items()} == {
        'SHORT_PASS': 416, 'DETOUR_PASS': 400, 'RECOVERY_RETRY': 416}
    assert all(segment['context'] == 'A' for segments in early['provenance'].values() for segment in segments)
    assert all(segment['arm'] == 'ORACLE_GAP' for segments in early['provenance'].values()
               for segment in segments if segment['kind'] == 'target')
    assert early['endpoint_index'] == returned['endpoint_index'] == 77
    assert early['certificate_index'] == returned['certificate_index'] == 77
    assert early['evidence_end_index'] == returned['evidence_end_index'] == 77
    assert early['latest_pool_index'] == returned['latest_pool_index'] == 77


def test_b_inheritance_ends_before_return_and_changed_operator_uses_only_b():
    _, gap, _, balanced, _ = tapes.reconstruct_data(*fixture())['snapshots']
    for endpoint in (gap, balanced):
        assert endpoint['endpoint_index'] == 77 and endpoint['evidence_scope_end_index'] == 53
        assert endpoint['certificate_index'] == 77 and endpoint['evidence_end_index'] == 31
        assert endpoint['latest_pool_index'] == 31
        assert {op: len(values) for op, values in endpoint['operators'].items()} == {
            'SHORT_PASS': 144, 'DETOUR_PASS': 528, 'RECOVERY_RETRY': 528}
        for op, segments in endpoint['provenance'].items():
            assert all(segment['index'] <= 53 for segment in segments)
            assert all(segment['context'] == 'B' for segment in segments) if op == 'SHORT_PASS' else True
            assert [segment['availability_order'] for segment in segments] == sorted(
                segment['availability_order'] for segment in segments)
            assert segments[0]['queue_start'] == 0 and segments[-1]['queue_end'] == len(endpoint['operators'][op])
    assert len(gap['member']['SHORT_PASS']) == 16
    assert len(balanced['member']['DETOUR_PASS']) == 16


def test_existing_source_training_rule_covers_endpoint_rows_exactly_once():
    for endpoint in tapes.reconstruct_data(*fixture())['snapshots']:
        split = predictive.split_tape(endpoint)
        for op in tapes.OPERATORS:
            assert len(split['training'][op])+len(split['validation'][op]) == len(endpoint['operators'][op])
            expected = 128 if endpoint['case']['context'] == 'B' and op == 'SHORT_PASS' else 384
            assert len(split['training'][op]) == expected
            assert len(split['training_segments'][op]) == 1
            if endpoint['case']['context'] == 'B' and op != 'SHORT_PASS':
                assert any(segment['kind'] == 'source' and segment['context'] == 'B'
                           for segment in split['validation_segments'][op])


def test_full_life_fees_and_physical_replay_are_not_multiplied_by_query_count():
    result = tapes.reconstruct_data(*fixture())
    summary = result['summary']
    assert summary['replayed_physical_source_samples'] == 4608
    assert summary['replayed_target_samples'] == 2*7*16
    assert summary['target_rows'] == 14 and summary['selected_snapshots'] == 5
    assert summary['new_observations'] == summary['new_paid_samples'] == 0
    assert len(summary['life_arm_paid_totals']) == 2
    assert all(row['total_paid_samples'] == 4608+7*16 for row in summary['life_arm_paid_totals'])
    for endpoint in result['snapshots']:
        assert endpoint['fees']['source_paid_samples'] == 4608
        assert endpoint['fees']['history_paid_samples'] == endpoint['fees']['target_paid_samples'] == 7*16
        assert endpoint['fees']['current_paid_samples'] == 0
        assert endpoint['fees']['total_reference_paid_samples'] == 4608+7*16
    early = result['snapshots'][0]['early_fees']
    assert early['source_paid_samples'] == 3456
    assert early['history_paid_samples'] == early['current_paid_samples'] == 16
    assert early['total_reference_paid_samples'] == 3456+32
    assert early['evidence_samples'] == 400+400+384


def test_incomplete_endpoint_and_replay_mismatch_are_rejected():
    sources, evidence, rows, worlds, selected = fixture()
    with pytest.raises(ValueError, match='end at index 77'):
        tapes.reconstruct_data(sources, evidence, rows[:-1], worlds, selected)
    rows[0]['batches'][0]['increments'] = {'DELIVERY': 15, 'LOST': 1}
    with pytest.raises(ValueError, match='seed replay differs'):
        tapes.reconstruct_data(sources, evidence, rows, worlds, selected)
