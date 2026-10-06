"""Test paid timing, evidence isolation, stopping and the scoring barrier."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import gzip
from io import StringIO
import json
import zlib

import pytest

from scripts import run_shared_probe_timing_v249 as runner

S, D, R = runner.OPERATORS


def anchors(number):
    return [{op: {category: number if category == 'DELIVERY' else 0
                  for category in runner.ALPHABETS[op]} for op in runner.OPERATORS}
            for _ in range(3)]


def bundle():
    cases, identities = [], []
    for index in range(78):
        stage = 'A' if index < 27 else 'B' if index < 54 else 'A_RETURN'
        cases.append(dict(id=str(index), context='B' if stage == 'B' else 'A',
                          stage=stage, operating='low', retry_cost='17/20'))
        identities.append(index % 3)
    return dict(cases=cases, laws=[object() for _ in cases], identities=identities,
        metadata=dict(changed_operator=S, b_to_a=(1, 2, 0)), a=anchors(384), b=anchors(128))


def native_state():
    data = bundle()
    state = runner.core.prepare(data['a'], 0, 'ONE_WAY', Counter())
    runner.core.begin_b(state, data['b'], S, data['metadata']['b_to_a'], Counter())
    return state


def controlled_draw(generator, law, operator, increments, number, work, progress):
    for _ in range(number):
        category = 'DELIVERY' if generator.random() < .5 else 'LOST'
        increments[category] += 1
    progress['draw_end'] += number
    work['controlled_samples'] += number
    work['controlled_resets'] += number


def install_planner(monkeypatch, ready):
    def plan(member, case, state, identity, index, cache, work):
        done = ready(index, sum(sum(row.values()) for row in member.values()))
        return dict(case=case, mix=[('WAIT', F(1))], utility_lower=F(2 if done else 0),
            goal_impossible=False, query_ready=done,
            evidence_counts=runner.core.point_counts(case, state, identity),
            query_evidence=dict(queries={'reward': dict(policy='WAIT', certified=True)},
                                all_ready=done, threshold=960))

    monkeypatch.setattr(runner.core, 'make_plan', plan)
    monkeypatch.setattr(runner, 'draw', controlled_draw)
    monkeypatch.setattr(runner.acquisition, 'choose', lambda *args: dict(operator=S, reason='synthetic'))


def target(monkeypatch, arm, history, probe_paid, stop_after):
    install_planner(monkeypatch, lambda index, count: count >= stop_after)
    return runner.run_target(0, 54, bundle()['cases'][54], 0, native_state(), arm,
        object(), Counter(), 4608, history, probe_paid, {}, StringIO(), {})


def test_probe_reservation_is_not_double_charged_when_pending_becomes_paid(monkeypatch):
    assert runner.PROBE_AMOUNT == 128 and runner.PROBE_QUOTA == 768
    assert runner.SOURCE_BASE == 288000 and runner.TARGET_BASE == 289000 and runner.PROBE_BASE == 290000
    assert [runner.probe_quota(arm) for arm in runner.ARMS] == [768, 768, 0]
    pending = target(monkeypatch, 'DEFERRED_SHARED', 8752, 0, 32)
    paid = target(monkeypatch, 'BEFORE_SHARED', 8752, 768, 32)
    control = target(monkeypatch, 'REBUILD', 8752, 0, 32)
    assert pending['life_budget_remaining_before'] == paid['life_budget_remaining_before'] == 16
    assert pending['spent'] == paid['spent'] == 16 and pending['fallback'] and paid['fallback']
    assert pending['pending_probe_reserved'] == 768 and paid['pending_probe_reserved'] == 0
    assert pending['total_reference_paid_samples']+pending['pending_probe_reserved'] == 14144
    assert paid['total_reference_paid_samples'] == 14144
    assert control['life_budget_remaining_before'] == 784 and control['spent'] == 32
    assert control['joint_completed'] and control['probe_quota_samples'] == 0


def test_probe_native_pool_update_never_rewrites_sources_switch_b_or_member(monkeypatch):
    install_planner(monkeypatch, lambda index, count: count >= 16)
    state, data, work = native_state(), bundle(), Counter()
    preserved = deepcopy((state['a']['sources'], state['a_at_switch'], state['b']))
    member = runner.core.empty()
    before = deepcopy(state['a']['pools'][0])
    result = runner.shared_probes(0, 'BEFORE_SHARED', 0, 54, 'before_target', state,
        data['cases'], data['laws'], 0, 0, work, StringIO(), {}, {})
    assert result['paid_samples'] == 256 and result['batches'] == 16
    assert (state['a']['sources'], state['a_at_switch'], state['b']) == preserved
    assert member == runner.core.empty()
    assert sum(state['a']['pools'][0][S].values()) == sum(before[S].values())+128
    assert sum(state['a']['pools'][0][D].values()) == sum(before[D].values())+128
    assert state['a']['pools'][0][R] == before[R]
    row = runner.run_target(0, 54, data['cases'][54], 0, state, 'BEFORE_SHARED',
        object(), work, 4608, 0, 256, {}, StringIO(), {})
    assert sum(row['member'][S].values()) == row['spent'] == 16
    assert sum(row['initial_plan']['evidence_counts'][S].values()) == 512
    assert sum(row['terminal_plan']['evidence_counts'][S].values()) == 528
    assert sum(row['pooled_after'][S].values()) == 528
    assert (state['a']['sources'], state['a_at_switch'], state['b']) == preserved


def test_paired_probe_streams_are_identical_and_cannot_be_read_twice(monkeypatch):
    monkeypatch.setattr(runner, 'draw', controlled_draw)
    outputs = []
    for arm, timing in (('BEFORE_SHARED', 'before_target'), ('DEFERRED_SHARED', 'after_target')):
        state, data, stream = native_state(), bundle(), StringIO()
        generators, offsets = {}, {}
        first = runner.shared_probes(1, arm, 2, 56, timing, state, data['cases'], data['laws'],
            80, 0, Counter(), stream, generators, offsets)
        second = runner.shared_probes(1, arm, 2, 57, timing, state, data['cases'], data['laws'],
            96, first['paid_samples'], Counter(), stream, generators, offsets)
        rows = [json.loads(line) for line in stream.getvalue().splitlines()]
        assert second['batches'] == 0 and second['paid_samples'] == 256
        assert [row['draw_start'] for row in rows] == list(range(0, 128, 16))*2
        assert [row['pending_probe_reserved_after'] for row in rows][-1] == 512
        outputs.append([(row['seed'], row['draw_start'], row['draw_end'], row['increments']) for row in rows])
    assert outputs[0] == outputs[1]


@pytest.mark.parametrize('stop_after,spent,completed', [(0, 0, True), (16, 16, True), (400, 384, False)])
def test_original_ready_and_member_cap_stop_are_preserved(monkeypatch, stop_after, spent, completed):
    row = target(monkeypatch, 'BEFORE_SHARED', 0, 768, stop_after)
    assert row['spent'] == spent and row['joint_completed'] == completed
    assert row['member_cap_exhausted'] == (spent == 384)
    assert row['fallback'] == (not completed)
    assert sum(sum(counts.values()) for counts in row['member'].values()) == spent


@pytest.mark.parametrize('arm', ['BEFORE_SHARED', 'DEFERRED_SHARED', 'REBUILD'])
def test_worker_freezes_terminals_then_probes_and_admits_b_only_at_switch(monkeypatch, tmp_path, arm):
    monkeypatch.setattr(runner, 'OUTPUT', tmp_path)
    install_planner(monkeypatch, lambda index, count: index != 56)
    prepare, begin_b = runner.core.prepare, runner.core.begin_b
    admitted = []

    def initial(anchors, life, actual_arm, work):
        state = prepare(anchors, life, actual_arm, work)
        assert state['b'] is None
        admitted.append(('A', actual_arm))
        return state

    def switching(state, anchors, changed_operator, mapping, work):
        assert state['b'] is None and state['a_at_switch'] is None
        admitted.append(('B', 30))
        return begin_b(state, anchors, changed_operator, mapping, work)

    monkeypatch.setattr(runner.core, 'prepare', initial)
    monkeypatch.setattr(runner.core, 'begin_b', switching)
    probes = runner.shared_probes

    def after_or_before(*args, **kwargs):
        trigger, timing = args[3], args[4]
        # The worker has flushed complete rows but has not closed the gzip footer.
        compressed = runner.worker_filename('records', 0, arm).read_bytes()
        text = zlib.decompressobj(31).decompress(compressed).decode()
        saved = [json.loads(line) for line in text.splitlines()]
        if timing == 'before_target':
            assert trigger == 54 and all(row['index'] < 54 for row in saved)
        else:
            assert saved[-1]['index'] == trigger
            assert saved[-1]['terminal_plan'] and saved[-1]['executed_mix']
        return probes(*args, **kwargs)

    monkeypatch.setattr(runner, 'shared_probes', after_or_before)
    artifact = runner.run_life_arm(0, arm, bundle())
    with gzip.open(runner.worker_filename('records', 0, arm), 'rt') as stream:
        rows = [json.loads(line) for line in stream]
    probe_rows = [json.loads(line) for line in runner.worker_filename('probes', 0, arm).read_text().splitlines()]
    assert len(rows) == 72 and admitted == [('A', runner.CORE_ARMS[arm]), ('B', 30)]
    assert artifact['probe_ledger']['paid_samples'] == runner.probe_quota(arm)
    assert artifact['probe_ledger']['pending_reserved_samples'] == 0
    if arm == 'REBUILD':
        assert not probe_rows and artifact['probe_ledger']['probe_batches'] == 0
    else:
        expected = [(54, identity) for identity in range(3)] if arm == 'BEFORE_SHARED' else [(54, 0), (55, 1), (56, 2)]
        assert [(row['trigger_index'], row['identity']) for row in probe_rows[::16]] == expected
        assert artifact['probe_ledger']['probe_batches'] == 48
        assert artifact['probe_ledger']['completed_probe_identities'] == [0, 1, 2]
        zero = next(row for row in rows if row['index'] == 54)
        fallback = next(row for row in rows if row['index'] == 56)
        assert zero['spent'] == 0 and zero['joint_completed']
        assert fallback['spent'] == 384 and fallback['fallback']
        expected_zero_n = 512 if arm == 'BEFORE_SHARED' else 384
        assert sum(zero['pooled_after'][S].values()) == expected_zero_n
        assert sum(zero['terminal_plan']['evidence_counts'][S].values()) == expected_zero_n
        if arm == 'DEFERRED_SHARED':
            first_probe = next(row for row in probe_rows if row['trigger_index'] == 54)
            assert sum(first_probe['pool_before'].values()) == 384
            assert sum(first_probe['pool_after'].values()) == 400
            assert sum(fallback['terminal_plan']['evidence_counts'][S].values()) == 768


def test_cache_activation_keeps_each_worker_cold_and_separate():
    first = runner.activate_cold_caches()
    first['query']((10, 10))
    runner.scalar_cs._INTERVAL_CACHE['previous_worker'] = object()
    second = runner.activate_cold_caches()
    assert second['query'] is not first['query'] and second['execution'] is not first['execution']
    assert first['query'].cache_info().currsize == 1 and second['query'].cache_info().currsize == 0
    assert runner.scalar_cs._INTERVAL_CACHE == {}
    assert runner.query_joint.mixture_normalizer is second['query']
    assert runner.convex.mixture_normalizer is second['query']


def test_parent_joins_all_nine_workers_and_freezes_all_648_before_scoring(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, 'OUTPUT', tmp_path/'cohort')
    monkeypatch.setattr(runner, 'prerequisites', lambda: {'admitted': True})
    events, source_calls = [], []
    monkeypatch.setattr(runner, 'capture', lambda: events.append('capture'))
    data = bundle()
    monkeypatch.setattr(runner.task, 'world', lambda life: (data['cases'], data['laws'], data['identities'], data['metadata']))

    def sources(life, context, laws, records, work):
        source_calls.append((life, context))
        return anchors(384 if context == 'A' else 128), 0.

    monkeypatch.setattr(runner, 'sources', sources)

    class Future:
        def __init__(self, life, arm):
            self.life, self.arm = life, arm

        def result(self):
            assert events.count('submit') == 9
            events.append('finish')
            with gzip.open(runner.worker_filename('records', self.life, self.arm), 'wt') as stream:
                for index in runner.TARGETS:
                    stream.write(json.dumps(dict(life=self.life, arm=self.arm, index=index,
                        identity=data['identities'][index], case=data['cases'][index]))+'\n')
            return dict(life=self.life, arm=self.arm, final_state={'return_merge': None},
                timings=dict.fromkeys(runner.TIMING_SCOPES, 0.), work={}, profiles=0,
                probe_ledger={}, normalizer_cache_statistics={}, life_arm_wall_seconds=0., output_seconds=0.)

    class Executor:
        def __init__(self, max_workers):
            assert max_workers == 9

        def __enter__(self):
            return self

        def __exit__(self, *args):
            events.append('workers_exited')

        def submit(self, operation, life, arm, shared):
            assert operation is runner.run_life_arm and shared['a'] and shared['b']
            assert json.loads((runner.OUTPUT/'run.json').read_text())['phases'] == ['protocol_frozen']
            events.append('submit')
            return Future(life, arm)

    monkeypatch.setattr(runner, 'ProcessPoolExecutor', Executor)

    def evaluate(row, law):
        assert events.count('finish') == 9 and 'workers_exited' in events
        assert json.loads((runner.OUTPUT/'run.json').read_text())['phases'] == ['protocol_frozen', 'all_decisions_frozen']
        events.append('score')
        return row

    monkeypatch.setattr(runner, 'evaluate', evaluate)
    monkeypatch.setattr(runner, 'summarize', lambda records, timings: dict(complete=True, records=len(records)))
    summary = runner.run()
    assert summary['records'] == events.count('score') == 648
    assert source_calls == [(life, context) for life in runner.LIVES for context in ('A', 'B')]
    assert events[0] == 'capture' and events.index('workers_exited') < events.index('score')


def test_frozen_conditions_charge_all_probe_costs_and_require_real_rebuild_saving():
    records = []
    for life in runner.LIVES:
        for arm in runner.ARMS:
            for index in runner.TARGETS:
                records.append(dict(life=life, arm=arm, index=index, identity=index % 3,
                    stage='A' if index < 30 else 'B' if index < 54 else 'A_RETURN',
                    spent=16 if arm == 'REBUILD' else 0, model_seconds=0.,
                    execution_certified=True, goal_impossible=False, query_certified=True,
                    joint_completed=True, fallback=False, budget_exhausted=False,
                    history=[dict(false_query_certificates=0, false_execution_certificate=False,
                        false_impossible_certificate=False, violation=False, goal_upper_ok=True, coverage=True)],
                    executed=dict(actual_utility=F(3), violation=False)))
    timings = {scope: {arm: dict.fromkeys(runner.LIVES, 0.) for arm in runner.ARMS}
               for scope in runner.TIMING_SCOPES}
    result = runner.summarize(records, timings)
    assert result['stage_condition_met'] and len(result['conditions']) == 11
    assert result['methods']['BEFORE_SHARED']['probe_samples'] == 2304
    assert result['methods']['BEFORE_SHARED']['total_samples'] == 16128
    assert result['methods']['BEFORE_SHARED']['first_return']['targets'] == 9
    assert result['methods']['BEFORE_SHARED']['later_return']['targets'] == 63
    tied = deepcopy(records)
    for row in tied:
        if row['arm'] == 'REBUILD' and row['stage'] == 'A_RETURN':
            row['spent'] = 0
    assert not runner.summarize(tied, timings)['conditions']['actual_acquisition_saving_vs_rebuild']
    next(row for row in records if row['arm'] == 'BEFORE_SHARED')['spent'] = 16
    assert not runner.summarize(records, timings)['conditions']['actual_acquisition_nondegrading_vs_deferred_shared']
