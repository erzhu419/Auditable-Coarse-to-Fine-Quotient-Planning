"""Runner checks use synthetic draws, never a paid task experiment."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from types import SimpleNamespace

from scripts import run_oracle_gap_lifecycle_v231 as runner


def install_synthetic(monkeypatch, stop_after):
    original = runner.core
    calls, draw_laws = [], []

    def make_plan(member, case, state, identity, index, work):
        amount = sum(sum(row.values()) for row in member.values())
        pool = runner.selected_pool(state, case, identity)
        calls.append((amount, sum(sum(row.values()) for row in pool.values())))
        ready = amount >= stop_after
        return dict(mix=[('WAIT', F(1))], predicted_utility=F(0), risk_upper=F(0),
            utility_lower=F(2 if ready else 0), goal_upper=F(4), goal_impossible=False,
            queries={q: dict(policy='WAIT') for q in ('reward', 'goal', 'risk')},
            query_certificates={q: dict(policy='WAIT', regret_upper=F(10), certified=ready)
                for q in ('reward', 'goal', 'risk')}, query_ready=ready,
            envelopes={op: dict(bounds={cat: [F(0), F(1)] for cat in runner.ALPHABETS[op]})
                for op in runner.OPERATORS},
            joint_constraints={'retained': amount}, query_certificate={'proof': amount},
            projection_supports={'proof': amount})

    def synthetic_draw(rng, law, op, increments, number, work, progress):
        draw_laws.append(law)
        cats = runner.ALPHABETS[op]
        for _ in range(number):
            increments[cats[rng.randrange(len(cats))]] += 1
            progress['draw_end'] += 1
            progress['n'] += 1

    monkeypatch.setattr(runner, 'core', SimpleNamespace(empty=original.empty,
        make_plan=make_plan, observe=original.observe, ready=original.ready,
        balanced=original.balanced))
    monkeypatch.setattr(runner, 'draw', synthetic_draw)
    state = original.prepare([original.empty() for _ in range(3)], 0, Counter())
    return state, calls, draw_laws


def case():
    return dict(context='A', stage='A', id='synthetic', operating='high', retry_cost='19/20')


def test_real_batch_updates_pool_once_before_next_plan(monkeypatch):
    state, calls, draw_laws = install_synthetic(monkeypatch, 32)
    law = object()
    row = runner.run_target(0, 3, case(), 0, state, runner.ARMS[0], law,
        Counter(), source_paid_samples=3456, history_paid_samples=37)
    assert calls == [(0, 0), (16, 16), (32, 32)]
    assert row['spent'] == row['current_paid_samples'] == row['new_paid_samples'] == 32
    assert row['total_reference_paid_samples'] == 3456+37+32
    assert sum(sum(v.values()) for v in row['pooled_before'].values()) == 0
    assert sum(sum(v.values()) for v in row['pooled_after'].values()) == 32
    assert draw_laws == [law, law]
    assert row['joint_completed']
    assert all('joint_constraints' not in batch['plan'] for batch in row['batches'])
    assert row['terminal_plan']['query_certificate'] == {'proof': 32}


def test_paired_operator_streams_charge_each_actual_read(monkeypatch):
    state, calls, draw_laws = install_synthetic(monkeypatch, 48)
    second = deepcopy(state)

    def reverse_order(member, plan, spent, work):
        op = runner.OPERATORS[2-spent//16]
        return dict(operator=op, reason='synthetic')

    monkeypatch.setattr(runner.acquisition, 'choose', reverse_order)
    rows = [runner.run_target(0, 3, case(), 0, active, arm, object(),
        Counter(), 3456, 0) for active, arm in zip((state, second), runner.ARMS)]
    assert rows[0]['seeds'] == rows[1]['seeds']
    assert rows[0]['member'] == rows[1]['member']
    assert [batch['operator'] for batch in rows[0]['batches']] == list(runner.OPERATORS)
    assert [batch['operator'] for batch in rows[1]['batches']] == list(reversed(runner.OPERATORS))
    assert sum(row['new_paid_samples'] for row in rows) == 96
    assert len(draw_laws) == 6
    assert calls == [(0, 0), (16, 16), (32, 32), (48, 48)]*2


def test_budget_exhaustion_has_no_extra_draw_or_forecast(monkeypatch):
    state, calls, draw_laws = install_synthetic(monkeypatch, 10000)
    row = runner.run_target(0, 3, case(), 0, state, runner.ARMS[0], object(),
        Counter(), 3456, 0)
    assert row['spent'] == runner.CAP == 384
    assert len(row['batches']) == len(draw_laws) == 24
    assert len(calls) == 25
    assert all(member == pooled for member, pooled in calls)
    assert all(sum(counts.values()) == 128 for counts in row['member'].values())
    assert not row['joint_completed']


def test_source_batches_preserve_required_seed_and_paid_sizes(monkeypatch):
    install_synthetic(monkeypatch, 32)
    records, laws = [], {0: object(), 27: object()}
    a, _ = runner.sources(0, (0,), 'A', laws, records, Counter())
    b, _ = runner.sources(0, (27,), 'B', laws, records, Counter())
    assert sum(sum(row.values()) for row in a[0].values()) == 1152
    assert sum(sum(row.values()) for row in b[0].values()) == 384
    assert len(records) == 72+24
    for row in records:
        j = runner.OPERATORS.index(row['operator'])
        assert row['seed'] == 262000+(row['life']*6+row['slot'])*3+j
        assert row['draw_end']-row['draw_start'] == 16
        assert sum(row['increments'].values()) == 16


def test_post_decision_scoring_preserves_record_and_detects_false_certificate(monkeypatch):
    state, _, _ = install_synthetic(monkeypatch, 16)
    row = runner.run_target(0, 3, case(), 0, state, runner.ARMS[0], object(),
        Counter(), 3456, 0)
    saved = runner.exact_json(row)
    before = deepcopy(saved)
    _, laws, _, _ = runner.task.world(0)
    assessed = runner.evaluate(saved, laws[3])
    assert saved == before
    assert assessed['terminal']['false_execution_certificate']
    assert assessed['terminal']['false_query_certificate']
    assert not assessed['terminal']['false_impossible_certificate']
