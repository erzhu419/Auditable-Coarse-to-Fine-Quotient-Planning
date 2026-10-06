"""Exercise query-only allocation, release accounting and the scoring barrier."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import gzip
from io import StringIO
import json
import pytest

from scripts import run_query_shared_acquisition_v251 as runner


def public_bundle():
    cases = [dict(context='B' if 27 <= index < 54 else 'A',
        stage='A' if index < 27 else 'B' if index < 54 else 'A_RETURN',
        operating='high', retry_cost='19/20') for index in range(78)]
    return dict(a=[runner.core.empty() for _ in range(3)], b=[runner.core.empty() for _ in range(3)],
        cases=cases, laws=[f'law{index}' for index in range(78)], identities=[index % 3 for index in range(78)],
        metadata=dict(changed_operator='DETOUR_PASS', b_to_a=[0, 1, 2]))


def base_state(bundle):
    return dict(arm='ONE_WAY', a=dict(sources=deepcopy(bundle['a']), pools=deepcopy(bundle['a'])),
        b=dict(sources=deepcopy(bundle['b']), pools=deepcopy(bundle['b'])), a_at_switch=None)


def controlled_draw(log):
    def draw(generator, law, operator, increments, amount, work, progress):
        random_values = tuple(generator.random() for _ in range(amount))
        log.append((law, operator, progress['draw_end'], random_values))
        increments[next(iter(increments))] += amount
        progress['draw_end'] += amount
        work['controlled_samples'] += amount
    return draw


def ledger():
    return dict(cap_samples=4224, paid_samples=0, pending_samples=4224, released_samples=0)


def test_fixed_cohort_and_cost_interfaces():
    assert runner.ARMS == ('UNIFORM_SHARED', 'QUERY_FIXED', 'QUERY_SHARED')
    assert len(runner.LIVES)*len(runner.ARMS)*len(runner.TARGETS) == 648
    assert (runner.SOURCE_BASE, runner.TARGET_BASE, runner.PROBE_BASE) == (295000, 296000, 297000)
    assert (runner.A_SHARED_CAP, runner.B_SHARED_FIXED, runner.SHARED_CAP) == (3072, 1152, 4224)
    assert runner.PUBLIC_COSTS == (('low', '17/20'), ('low', '19/20'), ('high', '17/20'), ('high', '19/20'))


def test_preview_reads_source_once_and_only_uses_query_math(monkeypatch):
    bundle = public_bundle()
    for op in runner.OPERATORS:
        bundle['a'][0][op][next(iter(bundle['a'][0][op]))] = 384
    state = base_state(bundle)
    state['a']['pools'][0]['SHORT_PASS']['DELIVERY'] += 16
    before = deepcopy(state)
    profiles, profile_ids, work, seen = StringIO(), {}, Counter(), []

    def forbidden(*args, **kwargs):
        raise AssertionError('auxiliary preview created execution/member planning')

    monkeypatch.setattr(runner.core, 'make_plan', forbidden)
    monkeypatch.setattr(runner.mechanics.robust, 'solve', forbidden)

    def certificates(counts, case, point, cache, work):
        assert counts == state['a']['pools'][0]
        assert sum(counts['SHORT_PASS'].values()) == 400
        assert point['reward']['policy'] == 'WAIT'
        assert case['operating'] == 'low' and case['retry_cost'] == '17/20'
        seen.append(deepcopy(counts))
        certificate = dict(query='goal', chosen=point['goal']['policy'], other='WAIT',
            family='S', projected_counts={'S': {'DELIVERY': 400, 'OTHER': 0}}, certified=True)
        return dict(queries=dict(reward=dict(policy='WAIT', certified=True),
            goal=dict(policy=point['goal']['policy'], certified=True, comparisons=[certificate]),
            risk=dict(policy=point['risk']['policy'], certified=False)), all_ready=False)

    monkeypatch.setattr(runner.online, 'certificates', certificates)
    cpu_clock, wall_clock = iter((10., 13.)), iter((20., 25.))
    monkeypatch.setattr(runner, 'process_time', lambda: next(cpu_clock))
    monkeypatch.setattr(runner, 'perf_counter', lambda: next(wall_clock))
    result = runner.query_preview(0, 'QUERY_SHARED', 0, 0, 0, 0, state, bundle,
        {}, work, profiles, profile_ids)
    saved = result['record']
    assert state == before and len(seen) == 1
    assert saved['posterior'] == runner.mechanics.posterior(saved['evidence_counts'])
    assert saved['pure_vectors'] == runner.mechanics.vectors(saved['case'], saved['posterior'])
    assert set(saved) == {'life', 'arm', 'preview_id', 'identity', 'cost_index', 'after_probe_batch',
        'case', 'evidence_counts', 'posterior', 'pure_vectors', 'queries', 'query_evidence', 'query_ready'}
    assert saved['query_evidence']['queries']['goal']['comparisons'] == [dict(profile_id=0, other='WAIT', certified=True)]
    assert json.loads(profiles.getvalue())['certificate']['family'] == 'S'
    assert work['aux_query_previews'] == 1
    assert result['model_seconds'] == 3. and result['output_seconds'] == 5.


def test_active_set_balances_only_observed_unready_types():
    s, d = runner.OPERATORS[:2]
    rows = [{s: 0, d: 0}, {s: 16, d: 16}, {s: 32, d: 0}]
    choice = runner.shared_choice('QUERY_SHARED', [True, False, False], rows)
    assert (choice['identity'], choice['operator']) == (1, s)
    assert choice['unresolved_types'] == [1, 2]
    rows[1][s] += 16
    choice = runner.shared_choice('QUERY_FIXED', [True, False, False], rows)
    assert (choice['identity'], choice['operator']) == (2, d)
    choice = runner.shared_choice('QUERY_FIXED', [True]*3, rows)
    assert (choice['identity'], choice['operator'], choice['reason']) == (0, s, 'all_ready_balanced_all_rows')
    assert runner.shared_choice('QUERY_FIXED', [False, True, True], rows)['reason'] == 'unresolved_type_balanced_row'


def phase_fixture(monkeypatch, ready_rule):
    monkeypatch.setattr(runner, 'draw', controlled_draw([]))

    def preview(life, arm, identity, cost_index, preview_id, after, state, bundle, *args):
        ready = ready_rule(identity, cost_index, state['a']['pools'][identity])
        return dict(record=dict(life=life, arm=arm, identity=identity, cost_index=cost_index,
            preview_id=preview_id, after_probe_batch=after, query_ready=ready),
            model_seconds=.1, output_seconds=.01)

    monkeypatch.setattr(runner, 'query_preview', preview)

    def phase(arm):
        bundle = public_bundle()
        state, paid = base_state(bundle), ledger()
        previews, probes = StringIO(), StringIO()
        result = runner.shared_a(0, arm, state, bundle, Counter(), {}, StringIO(), {},
            previews, probes, paid, {}, {})
        return result, paid, [json.loads(line) for line in previews.getvalue().splitlines()], state

    return phase


def test_actual_stop_and_fixed_continuation_share_prefix_and_rejudge_ready(monkeypatch):
    def readiness(identity, cost, rows):
        s, d = (sum(rows[op].values()) for op in runner.OPERATORS[:2])
        if identity == 1:
            return d >= 16 if cost == 3 else s >= 16
        if identity == 0:
            return s != 16
        return True

    phase = phase_fixture(monkeypatch, readiness)
    shared, released, previews, _ = phase('QUERY_SHARED')
    fixed, full, _, _ = phase('QUERY_FIXED')
    sf, ff = shared['phase'], fixed['phase']
    assert sf['batches'] == ff['batches'][:2]
    assert sf['a_paid_samples'] == sf['first_all_ready_paid'] == ff['first_all_ready_paid'] == 32
    assert sf['stop_reason'] == 'all_ready' and sf['released_delta'] == 3040
    assert released == dict(cap_samples=4224, paid_samples=32, pending_samples=1152, released_samples=3040)
    assert shared['previews'] == len(previews) == 20
    assert sf['latest_preview_ids'][1] == [16, 17, 18, 19]
    assert ff['batches'][2]['choice']['reason'] == 'all_ready_balanced_all_rows'
    assert ff['batches'][3]['choice']['reason'] == 'unresolved_type_balanced_row'
    assert ff['batches'][3]['choice']['identity'] == 0
    assert ff['stop_reason'] == 'cap' and ff['a_paid_samples'] == 3072
    assert full == dict(cap_samples=4224, paid_samples=3072, pending_samples=1152, released_samples=0)
    assert sum(shared['timings'].values()) >= 20*.1


def test_shared_ready_at_exact_cap_has_ready_priority_and_uniform_no_preview(monkeypatch):
    phase = phase_fixture(monkeypatch, lambda identity, cost, rows:
        sum(sum(row.values()) for row in rows.values()) >= 1024)
    shared, paid, _, _ = phase('QUERY_SHARED')
    assert shared['phase']['a_paid_samples'] == 3072
    assert shared['phase']['stop_reason'] == 'all_ready' and shared['phase']['released_delta'] == 0
    assert paid['pending_samples'] == 1152
    uniform, _, previews, state = phase('UNIFORM_SHARED')
    assert previews == [] and uniform['phase']['initial_previews'] == []
    assert uniform['phase']['stop_reason'] == 'cap'
    assert all(sum(state['a']['pools'][identity][op].values()) == 512
        for identity in range(3) for op in runner.OPERATORS[:2])


def test_probe_streams_keep_persistent_paired_offsets_and_native_only_updates(monkeypatch):
    bundle, draws = public_bundle(), []
    monkeypatch.setattr(runner, 'draw', controlled_draw(draws))
    states = [base_state(bundle), base_state(bundle)]
    rows = []
    for arm, state in zip(('QUERY_SHARED', 'QUERY_FIXED'), states):
        paid, generators, offsets = ledger(), {}, {}
        for sequence, (context, identity, op) in enumerate((('A', 1, 'SHORT_PASS'),
            ('A', 1, 'DETOUR_PASS'), ('A', 1, 'SHORT_PASS'), ('B', 2, 'DETOUR_PASS')), 1):
            result = runner.observe_probe(1, arm, context, identity, op, state, bundle,
                100, paid, Counter(), StringIO(), generators, offsets, sequence)
            rows.append(result['row'])
    for left, right in zip(rows[:4], rows[4:]):
        assert {k: v for k, v in left.items() if k != 'arm'} == {k: v for k, v in right.items() if k != 'arm'}
    assert [row['draw_start'] for row in rows[:4]] == [0, 0, 16, 0]
    assert rows[0]['seed'] == 297000+(6+1)*3
    assert rows[3]['seed'] == 297000+(6+3+2)*3+1
    assert rows[0]['source_paid_samples'] == 3456 and rows[3]['source_paid_samples'] == 4608
    assert rows[3]['source_index'] == 29 and draws[3][0] == 'law29'
    assert draws[:4] == draws[4:]
    for state in states:
        assert state['a']['sources'] == bundle['a'] and state['b']['sources'] == bundle['b']
        assert state['a_at_switch'] is None
        assert sum(state['a']['pools'][1]['RECOVERY_RETRY'].values()) == 0
        assert sum(state['b']['pools'][2]['DETOUR_PASS'].values()) == 16


def test_released_a_capacity_is_available_b_stays_reserved_and_stops_are_unchanged(monkeypatch):
    case = dict(context='A', stage='A', operating='low', retry_cost='17/20')
    draws = []
    monkeypatch.setattr(runner, 'draw', controlled_draw(draws))
    monkeypatch.setattr(runner.acquisition, 'choose', lambda *args: dict(operator='SHORT_PASS', reason='old'))
    monkeypatch.setattr(runner, 'retain_plan', lambda plan, *args: deepcopy(plan))
    monkeypatch.setattr(runner.core, 'ready', lambda plan: plan['query_ready'])

    def plan(member, case, state, *args):
        ready = sum(sum(row.values()) for row in member.values()) >= state['stop_after']
        return dict(case=case, query_ready=ready, utility_lower=F(2 if ready else 0),
            goal_impossible=False, mix=[('WAIT', F(1))])

    monkeypatch.setattr(runner.core, 'make_plan', plan)
    answers = []
    for history, actual, pending, released, stop in ((8320, 32, 1152, 3040, 16),
        (8320, 32, 1152, 3040, 400), (0, 3072, 1152, 0, 400)):
        state = dict(a=dict(pools=[runner.core.empty()]), stop_after=stop)
        answers.append(runner.run_target(0, 3, case, 0, state, 'QUERY_SHARED', 'law3', Counter(),
            3456, history, actual, pending, released, {}, StringIO(), {}))
    ready, budget, cap = answers
    assert ready['spent'] == 16 and ready['joint_completed']
    assert budget['spent'] == 32 and budget['budget_exhausted'] and budget['fallback']
    assert cap['spent'] == 384 and cap['member_cap_exhausted']
    assert ready['life_budget_remaining_before'] == 32
    assert ready['seeds']['SHORT_PASS'] == 296000+3*3
    assert draws[0][3] == draws[1][3]
    for row in answers:
        assert row['actual_probe_paid_before']+row['pending_probe_reserved']+row['released_probe_samples'] == 4224
        assert 14144-row['total_reference_paid_samples']-row['future_B_source_reserved']-row['pending_probe_reserved'] == row['life_budget_remaining_after']


def test_worker_copies_a_after_shared_phase_and_admits_b_before_fixed_probes(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, 'OUTPUT', tmp_path)
    monkeypatch.setattr(runner, 'activate_cold_caches', lambda: {})
    monkeypatch.setattr(runner, 'draw', controlled_draw([]))
    bundle, starts = public_bundle(), []
    def prepare(anchors, life, arm, work):
        assert arm == 'ONE_WAY'
        return dict(arm=arm, a=dict(sources=deepcopy(anchors), pools=deepcopy(anchors)), b=None, a_at_switch=None)
    def begin_b(state, anchors, *args):
        assert sum(state['a']['pools'][0]['SHORT_PASS'].values()) == 512
        state['a_at_switch'] = deepcopy(state['a'])
        state['b'] = dict(sources=deepcopy(anchors), pools=deepcopy(anchors))
    def target(life, index, case, identity, state, arm, law, work, source_paid, ordinary,
               actual, pending, released, query_cache, profiles, ids):
        starts.append((index, source_paid, ordinary, actual, pending, released))
        if index < 30:
            assert state['b'] is None and pending == 1152
        else:
            assert pending == 0 and sum(state['b']['pools'][2]['DETOUR_PASS'].values()) == 384
        return dict(spent=0, model_seconds=0., acquisition_seconds=0., observation_seconds=0.,
            output_seconds=0., query_certified=False, joint_completed=False)
    monkeypatch.setattr(runner.core, 'prepare', prepare)
    monkeypatch.setattr(runner.core, 'begin_b', begin_b)
    monkeypatch.setattr(runner, 'run_target', target)
    artifact = runner.run_life_arm(0, 'UNIFORM_SHARED', bundle)
    assert starts[0] == (3, 3456, 0, 3072, 1152, 0)
    assert next(item for item in starts if item[0] == 30) == (30, 4608, 0, 4224, 0, 0)
    assert artifact['probe_ledger']['by_context'] == dict(A=3072, B=1152)
    assert artifact['previews'] == 0 and artifact['probe_ledger']['probe_batches'] == 264
    assert sum(artifact['final_state']['a_at_switch']['pools'][0]['SHORT_PASS'].values()) == 512
    assert bundle['a'] == [runner.core.empty() for _ in range(3)]


def cohort():
    rows, previews, ledgers = [], [], []
    for life in runner.LIVES:
        for arm in runner.ARMS:
            shared = 160 if arm == 'QUERY_SHARED' else 3072
            ledgers.append(dict(life=life, arm=arm, cap_samples=4224, paid_samples=shared+1152,
                pending_reserved_samples=0, released_samples=3072-shared,
                by_context=dict(A=shared, B=1152), probe_batches=(shared+1152)//16))
            if arm != 'UNIFORM_SHARED':
                previews.append(dict(life=life, arm=arm, false_aux_query_certificates=0))
            for index in runner.TARGETS:
                rows.append(dict(life=life, arm=arm, index=index, identity=index % 3,
                    stage='A' if index < 30 else 'B' if index < 54 else 'A_RETURN', spent=16,
                    query_certified=True, joint_completed=True, execution_certified=True,
                    goal_impossible=False, fallback=False, budget_exhausted=False, model_seconds=0.,
                    history=[dict(false_query_certificates=0, false_execution_certificate=False,
                        false_impossible_certificate=False, violation=False, goal_upper_ok=True, coverage=True)],
                    executed=dict(actual_utility=F(3), violation=False)))
    timings = {scope: {arm: dict.fromkeys(runner.LIVES, .1 if scope != 'acquisition' else .09)
        for arm in runner.ARMS} for scope in runner.TIMING_SCOPES}
    return rows, previews, timings, ledgers


def test_auxiliary_scores_have_query_only_errors_and_safety_includes_them(monkeypatch):
    pure = dict(WAIT=[F(0), F(0), F(0)], SHORT=[F(-1, 10), F(0), F(1)],
        DETOUR_RETURN=[F(-1, 20), F(0), F(1, 2)], DETOUR_RETRY=[F(-1), F(0), F(1, 2)])
    monkeypatch.setattr(runner.query_score.__globals__['core'], 'vectors', lambda case, law: pure)
    row = dict(life=0, arm='QUERY_SHARED', preview_id=0, identity=1, cost_index=0, after_probe_batch=0,
        case={}, queries={query: dict(policy='WAIT') for query in ('reward', 'goal', 'risk')},
        query_evidence=dict(queries={query: dict(certified=query != 'risk') for query in ('reward', 'goal', 'risk')}))
    result = runner.score_preview(row, 'truth_after_freeze')
    assert result['false_aux_query_certificates'] == 1
    assert result['queries']['goal']['regret'] == F(39, 10)
    assert 'executed' not in result and 'member' not in result and 'execution_certified' not in result
    rows, previews, timings, ledgers = cohort()
    summary = runner.summarize(rows, previews, timings, ledgers)
    assert len(summary['conditions']) == 11 and summary['stage_condition_met']
    assert summary['methods']['QUERY_SHARED']['model_seconds'] == pytest.approx(3*6*.1)
    assert summary['methods']['QUERY_SHARED']['acquisition_seconds'] == pytest.approx(3*.09)
    assert summary['physical_source_samples'] == summary['source_samples_charged_per_arm'] == 13824
    assert summary['physical_probe_samples'] == sum(item['paid_samples'] for item in ledgers)
    assert summary['new_environment_observations'] == 13824+648*16+summary['physical_probe_samples']
    previews[0]['false_aux_query_certificates'] = 1
    summary = runner.summarize(rows, previews, timings, ledgers)
    assert not summary['conditions']['valid_certificates_and_execution']
    assert summary['methods']['QUERY_FIXED']['aux_false_query_certificates'] == 1


def test_parent_freezes_all_jobs_and_previews_before_both_truth_scores(monkeypatch, tmp_path):
    events, finished, captures, source_calls = [], [], [], []
    monkeypatch.setattr(runner, 'OUTPUT', tmp_path/'output')
    monkeypatch.setattr(runner, 'prerequisites', lambda: dict(v250_complete=True, v250_independent_valid=True))
    monkeypatch.setattr(runner, 'capture', lambda: captures.append('captured'))
    bundle = public_bundle()
    monkeypatch.setattr(runner.task, 'world', lambda life: (bundle['cases'], bundle['laws'], bundle['identities'], bundle['metadata']))
    def source(life, context, laws, records, work):
        assert captures and not events
        source_calls.append((life, context))
        return deepcopy(bundle['a'] if context == 'A' else bundle['b']), .1
    monkeypatch.setattr(runner, 'sources', source)
    _, _, times, all_ledgers = cohort()
    class Future:
        def __init__(self, life, arm):
            self.life, self.arm = life, arm
        def result(self):
            assert len(events) == 9
            finished.append((self.life, self.arm))
            with gzip.open(runner.worker_filename('records', self.life, self.arm), 'wt') as stream:
                for index in runner.TARGETS:
                    runner.write_row(stream, dict(life=self.life, arm=self.arm, index=index, identity=index % 3))
            with gzip.open(runner.worker_filename('previews', self.life, self.arm), 'wt') as stream:
                if self.arm != 'UNIFORM_SHARED':
                    runner.write_row(stream, dict(life=self.life, arm=self.arm, identity=1, preview_id=0))
            return dict(life=self.life, arm=self.arm, final_state={}, work={}, profiles=0,
                previews=0 if self.arm == 'UNIFORM_SHARED' else 1, output_seconds=0.,
                normalizer_cache_statistics={}, life_arm_wall_seconds=.2,
                timings={scope: times[scope][self.arm][self.life] for scope in runner.TIMING_SCOPES},
                probe_ledger=next(item for item in all_ledgers if item['life'] == self.life and item['arm'] == self.arm),
                a_phase_summary=dict(a_paid_samples=0, released_delta=0, stop_reason='cap',
                    final_ready_by_type=[], first_all_ready_paid=None))
    class Executor:
        def __init__(self, max_workers):
            assert max_workers == 9
        def __enter__(self):
            return self
        def submit(self, function, life, arm, bundle):
            assert function is runner.run_life_arm and len(source_calls) == 6
            events.append((life, arm))
            return Future(life, arm)
        def __exit__(self, *args):
            assert len(finished) == 9
            events.append('executor_exited')
    monkeypatch.setattr(runner, 'ProcessPoolExecutor', Executor)
    scores, auxscores = [], []
    def frozen():
        assert len(finished) == 9 and events[-1] == 'executor_exited'
        protocol = json.loads((runner.OUTPUT/'run.json').read_text())
        assert protocol['phases'][-1] == 'all_decisions_and_previews_frozen'
        assert sum(len(gzip.open(runner.worker_filename('records', life, arm), 'rt').readlines())
            for life in runner.LIVES for arm in runner.ARMS) == 648
        assert sum(len(gzip.open(runner.worker_filename('previews', life, arm), 'rt').readlines())
            for life in runner.LIVES for arm in runner.ARMS) == 6
    def evaluate(row, law):
        frozen()
        assert law == f'law{row["index"]}'
        scores.append((row['life'], row['arm'], row['index']))
        return row
    def aux(row, law):
        frozen()
        assert law == 'law1'
        auxscores.append((row['life'], row['arm']))
        return row
    monkeypatch.setattr(runner, 'evaluate', evaluate)
    monkeypatch.setattr(runner, 'score_preview', aux)
    monkeypatch.setattr(runner, 'summarize', lambda records, previews, timings, ledgers:
        dict(records=len(records), aux_preview_records=len(previews), complete=True))
    result = runner.run()
    assert len(scores) == result['records'] == 648
    assert len(auxscores) == result['aux_preview_records'] == 6
    assert source_calls == [(life, context) for life in runner.LIVES for context in ('A', 'B')]
    assert json.loads((runner.OUTPUT/'run.json').read_text())['complete']
