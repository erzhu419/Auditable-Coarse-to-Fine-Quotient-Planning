"""Independent synthetic checks; no retained SOURCE or TARGET is opened."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction

from scripts import analyze_controlled_predictive_deep_transfer_v200 as audit


F = Fraction


def synthetic_source():
    states = [dict(board=[rank]+[0]*15, status='ACTIVE', legal=['DOWN']) for rank in (1, 1, 1, 1, 2, 2, 2, 2)]
    states += [dict(board=[6]+[0]*15, status='WON', legal=[]), dict(board=[1, 2]*8, status='LOST', legal=[])]
    return dict(states=states, controlled=list(range(8)), rows=[[sid, 'DOWN', [[1, 1, 8 if sid < 4 else 9, 0, 1]]]
        for sid in range(8)], root_ids=[0], mask_augmentations=0)


def test_features_learned_predicates_new_boards_and_unknown_masks():
    for split, count in (('SOURCE', 32), ('TARGET', 24)):
        cases = audit.fixed_roster()[split]
        assert len(cases) == count
        for index, case in enumerate(cases):
            first, second = audit.PAIRS[index % 12]
            assert first//4 != second//4 and first%4 != second%4
            assert [cell for cell, rank in enumerate(case['board']) if rank == 5] == sorted((first, second))
            assert all(0 <= rank <= 4 for cell, rank in enumerate(case['board']) if cell not in (first, second))
    features = audit.board_features((2, 2, 0, 0)+(1, 3, 0, 0)+(1, 4, 0, 0)+(5, 4, 0, 0))
    assert len(features) == 42
    assert features[16:19] == (1, 0, 0)
    assert features[28:32] == (0, 0, 0, 0)
    assert features[32:36] == (1, 0, 0, 0)
    assert features[-2:] == (8, 5)
    source = synthetic_source()
    learned = audit.rebuild_model(source)
    coarse = audit.rebuild_model(source, False)
    assert len(learned['trees']['1']) == 1
    tree = learned['trees']['1'][0]['tree']
    assert tree['feature'] == 0 and tree['threshold'] == 1
    first = audit.encode(learned, (1,)+(3,)*15, 'ACTIVE', ['DOWN'], 4)
    second = audit.encode(learned, (2,)+(3,)*15, 'ACTIVE', ['DOWN'], 4)
    assert first != second
    assert audit.encode(coarse, (1,)+(3,)*15, 'ACTIVE', ['DOWN'], 4) == audit.encode(coarse, (2,)+(3,)*15, 'ACTIVE', ['DOWN'], 4)
    assert audit.encode(learned, (1,)+(3,)*15, 'ACTIVE', ['LEFT'], 4) is None
    assert audit.encode(learned, (1,)+(3,)*15, 'ACTIVE', ['LEFT'], 0) == 2
    assert all(len(record['members']) == 4 for branch in (tree['left'], tree['right']) for record in [branch])


def test_uniform_rational_rows_joint_policy_and_own_native_replay():
    coarse = audit.rebuild_model(synthetic_source(), False)
    first = coarse['trees']['1'][0]['tree']['cell']
    assert coarse['rows'][0] == [first, 'DOWN', [[1, 2, 0, 0, 1], [1, 2, 1, 0, 1]]]
    model = dict(cells=[[0, 0, 'WON'], [1, 0, 'LOST'], [2, 0, 'CUTOFF'], [3, 1, 'ACTIVE']],
        rows=[[3, 'DOWN', [[1, 1, 1, 2, 1]]], [3, 'LEFT', [[1, 1, 0, 1, 1]]]],
        trees={'1': [dict(mask=['DOWN', 'LEFT'], tree=dict(cell=3, members=[0]))]})
    plan = audit.plan_model(model, audit.QUERIES['risk'])
    assert plan['policy'][3] == 'LEFT' and plan['values'][3] == (F(1), F(0), F(1))
    root, won, lost = (1,)*16, (6,)*16, (2,)*16
    native = audit.Native()
    native.boards.update({root: ('ACTIVE', ('DOWN', 'LEFT')), won: ('WON', ()), lost: ('LOST', ())})
    native.rows[root, 'DOWN'] = ((F(1), lost, F(2)),)
    native.rows[root, 'LEFT'] = ((F(1), won, F(1)),)
    wrong = dict(values=plan['values'], policy={3: 'DOWN'})
    replay = audit.own_policy_replay(native, root, 1, 'risk', 'LEARNED', model, wrong)
    assert replay['vector'] == (F(2), F(1), F(0))
    assert replay['vector'] != plan['values'][3]
    assert native.work['native_swipe_calls'] == 0
    assert native.work['policy_replay_action_rows'] == 1
    unsupported = deepcopy(model)
    unsupported['trees']['1'][0]['mask'] = ['LEFT']
    fallback = audit.own_policy_replay(native, root, 1, 'goal', 'COARSE', unsupported, plan)
    assert fallback['action'] == 'DOWN'
    assert fallback['fallback_probability'] == fallback['fallback_visits'] == 1


def audit_fixture_source(board):
    native = audit.Native()
    states, index, rows = [], {}, []
    def intern(current):
        current = tuple(current)
        if current not in index:
            status, legal = native.classify(current)
            index[current] = len(states)
            states.append(dict(board=list(current), status=status, legal=list(legal)))
        return index[current]
    root = intern(board)
    for action in states[root]['legal']:
        outcomes = []
        for p, child, reward in native.outcomes(tuple(board), action):
            outcomes.append([p.numerator, p.denominator, intern(child), reward.numerator, reward.denominator])
        rows.append([root, action, outcomes])
    return dict(states=states, rows=rows, controlled=[root], root_ids=[root], mask_augmentations=0)


def test_source_native_authenticity_does_not_allow_target_contamination():
    board = [5]*16
    source = audit_fixture_source(board)
    cases = [dict(board=board)]
    assert audit.source_framing(source, cases)
    assert all(row['passed'] for row in audit.source_truth(source))
    clean_model = audit.rebuild_model(source, False)
    injected = audit_fixture_source([1, 1]+[5]*14)
    polluted = deepcopy(source)
    offset = len(polluted['states'])
    polluted['states'].extend(injected['states'])
    polluted['controlled'].append(offset)
    polluted['rows'].extend([[sid+offset, action, [[p, q, child+offset, r, s] for p, q, child, r, s in outcomes]]
        for sid, action, outcomes in injected['rows']])
    assert all(row['passed'] for row in audit.source_truth(polluted))
    assert not audit.source_framing(polluted, cases)
    assert audit.rebuild_model(polluted, False)['rows'] != clean_model['rows']
    tampered = deepcopy(source)
    tampered['rows'][0][2][0][3] += 1
    assert not all(row['passed'] for row in audit.source_truth(tampered))


def test_four_conditions_require_unique_full_risk_goal_preferences_and_depth():
    def oracle(name):
        vectors = {'DOWN': (F(5, 4), F(1), F(0)), 'LEFT': (F(1), F(0), F(1))} if name == 'reward' else {
            'DOWN': (F(9, 10), F(0), F(9, 20)), 'LEFT': (F(1), F(1, 2), F(1, 2))}
        selected = 'LEFT' if name == 'goal' else 'DOWN'
        result = audit.packed(vectors[selected], audit.QUERIES[name], selected)
        result['action_vector_fractions'] = {action: [str(x) for x in vector] for action, vector in vectors.items()}
        return result
    records = []
    for index in range(24):
        rows = []
        for horizon in (3, 4):
            for name, query in audit.QUERIES.items():
                reference = oracle(name)
                vector = tuple(Fraction(x) for x in reference['component_fractions'])
                arms = {}
                for mode in ('COARSE', 'LEARNED', 'LEARNED_D1', 'NATIVE_H2'):
                    actual = (vector[0]-F(1, 50), vector[1], vector[2]) if mode in ('COARSE', 'LEARNED_D1') else vector
                    arms[mode] = dict(actual=audit.packed(actual, query), predicted=audit.packed(actual, query), regret=0., expected_fallback_visits=0.)
                rows.append(dict(horizon=horizon, query=name, oracle=reference, arms=arms))
        records.append(dict(root_id=f'synthetic_{index}', evaluations=rows))
    model = dict(cells=[[3+h, h, 'ACTIVE'] for h in range(1, 5)], rows=[[3+h, 'DOWN', []] for h in range(1, 5)])
    models = {'LEARNED': model}
    benchmark = {'3': dict(D4_states=100, D4_rows=100), '4': dict(D4_states=100, D4_rows=100),
        'terminal_support_counts': dict(WON=1, LOST=1, ACTIVE=1)}
    summary = audit.decision_summary(records, models, benchmark)
    assert all(summary['conditions'].values()) and summary['advance']
    tied = deepcopy(records)
    for record in tied:
        for row in record['evaluations']:
            if row['query'] == 'reward':
                row['oracle']['action_vector_fractions']['LEFT'][0] = '5/4'
    assert not audit.decision_summary(tied, models, benchmark)['conditions']['TASK']
    fallback = deepcopy(records)
    fallback[0]['evaluations'][0]['arms']['LEARNED']['expected_fallback_visits'] = .001
    rejected = audit.decision_summary(fallback, models, benchmark)
    assert not rejected['conditions']['QUALITY'] and not rejected['advance']
