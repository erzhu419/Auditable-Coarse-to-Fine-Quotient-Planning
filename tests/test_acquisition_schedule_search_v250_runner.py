"""Verify the new schedule, full-reservation ledger, search selection and barrier."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import gzip
from io import StringIO
import json
import pytest

from scripts import run_acquisition_schedule_search_v250 as runner
from scripts import run_shared_probe_timing_v249 as predecessor


def test_fixed_eight_plans_and_budget_pressure():
    assert runner.PLAN_IDS == ('SD128_B0', 'SD128_B384', 'SD512_B0', 'SD512_B384',
        'SD1024_B0', 'SD1024_B384', 'ALL512_B0', 'ALL512_B384')
    assert [plan['quota_samples'] for plan in runner.PLANS] == [768, 1920, 3072, 4224, 6144, 7296, 4608, 5760]
    assert runner.PLANS[6]['a_row_samples'] == dict.fromkeys(runner.OPERATORS, 512)
    assert runner.TOTAL_BUDGETS[0]-runner.SOURCE_COST-runner.PLANS[5]['quota_samples'] == 2240
    assert len(runner.LIVES)*len(runner.PLANS)*len(runner.TARGETS) == 1728


def public_bundle():
    cases = [dict(context='B' if 27 <= index < 54 else 'A',
        stage='A' if index < 27 else 'B' if index < 54 else 'A_RETURN') for index in range(78)]
    return dict(a=[runner.core.empty() for _ in range(3)], b=[runner.core.empty() for _ in range(3)],
        cases=cases, laws=[f'law{index}' for index in range(78)], identities=[index % 3 for index in range(78)],
        metadata=dict(changed_operator='DETOUR_PASS', b_to_a=[0, 1, 2]))


def controlled_draw(log):
    def draw(generator, law, operator, increments, amount, work, progress):
        sample = tuple(generator.random() for _ in range(amount))
        log.append((law, operator, progress['draw_end'], sample))
        increments[next(iter(increments))] += amount
        progress['draw_end'] += amount
        work['controlled_samples'] += amount
    return draw


def test_contextual_probes_pair_prefixes_and_only_change_the_native_pool(monkeypatch):
    bundle, draws = public_bundle(), []
    monkeypatch.setattr(runner, 'draw', controlled_draw(draws))
    base = dict(a=dict(sources=deepcopy(bundle['a']), pools=deepcopy(bundle['a'])),
        b=dict(sources=deepcopy(bundle['b']), pools=deepcopy(bundle['b'])), a_at_switch=dict(marker='frozen'))
    a_state, longer_state, b_state = deepcopy(base), deepcopy(base), deepcopy(base)
    a_log, longer_log, b_log = StringIO(), StringIO(), StringIO()
    a = runner.context_probes(0, runner.PLANS[0], 'A', a_state, bundle, 0, 0,
        Counter(), a_log, {}, {})
    longer = runner.context_probes(0, runner.PLANS[2], 'A', longer_state, bundle, 0, 0,
        Counter(), longer_log, {}, {})
    b = runner.context_probes(0, runner.PLANS[1], 'B', b_state, bundle, 100, 768,
        Counter(), b_log, {}, {})
    aa, ll, bb = ([json.loads(line) for line in stream.getvalue().splitlines()]
                  for stream in (a_log, longer_log, b_log))
    extended = {(row['identity'], row['operator'], row['draw_start']): row for row in ll}
    assert all(row['increments'] == extended[row['identity'], row['operator'], row['draw_start']]['increments']
               and row['seed'] == extended[row['identity'], row['operator'], row['draw_start']]['seed'] for row in aa)
    assert (a['paid_samples'], longer['paid_samples'], b['paid_samples']) == (768, 3072, 1920)
    assert all(row['source_paid_samples'] == 3456 and row['trigger_index'] == 3 for row in aa)
    assert all(row['source_paid_samples'] == 4608 and row['trigger_index'] == 30
        and row['source_index'] == 27+row['identity'] and row['operator'] == 'DETOUR_PASS' for row in bb)
    assert aa[0]['seed'] == 294000 and bb[0]['seed'] == 294000+3*3+1
    assert {row[0] for row in draws[-72:]} == {'law27', 'law28', 'law29'}
    for state in (a_state, longer_state, b_state):
        assert state['a']['sources'] == base['a']['sources'] and state['b']['sources'] == base['b']['sources']
        assert state['a_at_switch'] == base['a_at_switch']
    assert a_state['b'] == base['b'] and b_state['a'] == base['a']
    assert sum(a_state['a']['pools'][0]['RECOVERY_RETRY'].values()) == 0
    assert sum(b_state['b']['pools'][2]['DETOUR_PASS'].values()) == 384


def test_target_stops_reserve_future_b_and_do_not_double_charge_paid_a(monkeypatch):
    case = dict(context='A', stage='A', operating='low', retry_cost='17/20')
    draws = []
    monkeypatch.setattr(runner, 'draw', controlled_draw(draws))
    monkeypatch.setattr(runner.acquisition, 'choose', lambda *args: dict(operator='SHORT_PASS', reason='synthetic'))
    monkeypatch.setattr(runner, 'retain_plan', lambda plan, *args: deepcopy(plan))
    monkeypatch.setattr(runner.core, 'ready', lambda plan: plan['query_ready'])

    def plan(member, case, state, *args):
        ready = sum(sum(counts.values()) for counts in member.values()) >= state['stop_after']
        return dict(case=case, query_ready=ready, utility_lower=F(2 if ready else 0),
            goal_impossible=False, mix=[('WAIT', F(1))])

    monkeypatch.setattr(runner.core, 'make_plan', plan)
    answers = []
    for spec, history, paid, stop in ((runner.PLANS[1], 7584, 768, 16),
        (runner.PLANS[1], 7584, 768, 400), (runner.PLANS[7], 0, 4608, 400)):
        state = dict(a=dict(pools=[runner.core.empty()]), stop_after=stop)
        answers.append(runner.run_target(0, 3, case, 0, state, spec, 'law3', Counter(),
            3456, history, paid, {}, StringIO(), {}))
    ready, budget, cap = answers
    assert ready['spent'] == 16 and ready['joint_completed']
    assert budget['spent'] == 32 and budget['budget_exhausted'] and budget['fallback']
    assert cap['spent'] == 384 and cap['member_cap_exhausted']
    for row in answers:
        assert row['future_B_source_reserved'] == 1152 and row['pending_probe_reserved'] == 1152
        assert 14144-row['total_reference_paid_samples']-row['future_B_source_reserved']-row['pending_probe_reserved'] == row['life_budget_remaining_after']
    assert ready['seeds'] == budget['seeds'] == cap['seeds']
    assert ready['seeds']['SHORT_PASS'] == 289000+3*3 and draws[0][3] == draws[1][3]


def test_worker_admits_a_before_target3_and_b_only_after_begin_b(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, 'OUTPUT', tmp_path)
    monkeypatch.setattr(runner, 'activate_cold_caches', lambda: {})
    monkeypatch.setattr(runner, 'draw', controlled_draw([]))
    bundle, starts, snapshots = public_bundle(), [], []

    def prepare(anchors, life, arm, work):
        assert arm == 'ONE_WAY'
        return dict(arm=arm, a=dict(sources=deepcopy(anchors), pools=deepcopy(anchors)), b=None, a_at_switch=None)

    def begin_b(state, anchors, *args):
        snapshots.append(deepcopy(state['a']))
        state['a_at_switch'] = deepcopy(state['a'])
        state['b'] = dict(sources=deepcopy(anchors), pools=deepcopy(anchors))

    def target(life, index, case, identity, state, spec, law, work, source_paid, ordinary_paid,
               probe_paid, query_cache, profiles, profile_ids):
        starts.append((index, source_paid, ordinary_paid, probe_paid, id(query_cache)))
        if index < 30:
            assert state['b'] is None and probe_paid == 768
        else:
            assert probe_paid == 1920 and sum(state['b']['pools'][2]['DETOUR_PASS'].values()) == 384
        return dict(spent=0, model_seconds=0., acquisition_seconds=0., observation_seconds=0.,
            output_seconds=0., query_certified=False, joint_completed=False)

    monkeypatch.setattr(runner.core, 'prepare', prepare)
    monkeypatch.setattr(runner.core, 'begin_b', begin_b)
    monkeypatch.setattr(runner, 'run_target', target)
    artifact = runner.run_life_plan(0, runner.PLANS[1], bundle)
    assert starts[0][:4] == (3, 3456, 0, 768)
    assert next(row for row in starts if row[0] == 30)[:4] == (30, 4608, 0, 1920)
    assert sum(snapshots[0]['pools'][0]['SHORT_PASS'].values()) == 128
    assert artifact['final_state']['a_at_switch'] == snapshots[0]
    assert artifact['probe_ledger']['by_context'] == dict(A=768, B=1152)
    assert artifact['probe_ledger']['pending_reserved_samples'] == 0
    assert sum(sum(counts.values()) for counts in bundle['a'][0].values()) == 0


def test_reused_process_resets_all_caches_for_its_next_plan(monkeypatch):
    for module, attr in ((predecessor.scalar_cs, '_INTERVAL_CACHE'),
        (predecessor.execution_joint, 'mixture_normalizer'), (predecessor.query_joint, 'mixture_normalizer'),
        (predecessor.convex, 'mixture_normalizer')):
        monkeypatch.setattr(module, attr, getattr(module, attr))
    first = runner.activate_cold_caches()
    predecessor.scalar_cs._INTERVAL_CACHE['previous_plan'] = object()
    second = runner.activate_cold_caches()
    assert predecessor.scalar_cs._INTERVAL_CACHE == {}
    assert first['query'] is not second['query'] and first['execution'] is not second['execution']
    assert second['query'].cache_info().currsize == second['execution'].cache_info().currsize == 0
    assert predecessor.query_joint.mixture_normalizer is predecessor.convex.mixture_normalizer is second['query']


def cohort():
    records = []
    for life in runner.LIVES:
        for candidate in runner.PLAN_IDS:
            for index in runner.TARGETS:
                records.append(dict(life=life, arm=candidate, candidate=candidate, index=index,
                    stage='A' if index < 30 else 'B' if index < 54 else 'A_RETURN',
                    spent=16, query_certified=True, joint_completed=True, execution_certified=True,
                    goal_impossible=False, fallback=False, budget_exhausted=False, model_seconds=0.,
                    history=[dict(false_query_certificates=0, false_execution_certificate=False,
                        false_impossible_certificate=False, violation=False, goal_upper_ok=True, coverage=True)],
                    executed=dict(actual_utility=F(3), violation=False)))
    timings = {scope: {candidate: dict.fromkeys(runner.LIVES, .1) for candidate in runner.PLAN_IDS}
               for scope in runner.TIMING_SCOPES}
    return records, timings


def test_two_winners_are_independent_and_keep_all_eight_search_costs():
    records, timings = cohort()
    cheap = [row for row in records if row['arm'] == 'SD128_B0']
    for row in cheap[:85]:
        row['joint_completed'] = False
    summary = runner.summarize(records, timings)
    assert summary['selected'] == 'SD128_B384' and summary['budget_quality_witness'] == 'SD128_B0'
    assert summary['candidates'][0]['budget_quality_feasible'] and not summary['candidates'][0]['qualification_witness']
    assert summary['physical_source_samples'] == 0 and summary['inherited_source_samples_charged_per_candidate'] == 13824
    assert summary['physical_probe_samples'] == 3*sum(plan['quota_samples'] for plan in runner.PLANS)
    assert summary['new_environment_observations'] == 1728*16+summary['physical_probe_samples']
    assert summary['total_search_model_seconds'] == pytest.approx(8*3*4*.1)
    assert summary['post_selection_coverage_guarantee'] is None and not summary['selected_guarantee_claimed']


def test_expensive_quality_witness_is_not_labeled_budget_unreachable():
    records, timings = cohort()
    for row in records:
        if row['arm'] != 'SD128_B0':
            row['query_certified'] = False
    for life in runner.LIVES:
        selected = [row for row in records if row['arm'] == 'SD128_B0' and row['life'] == life]
        remaining = runner.TOTAL_BUDGETS[life]-runner.SOURCE_COST-runner.PLANS[0]['quota_samples']
        for row in selected:
            row['spent'] = min(runner.CAP, remaining)
            remaining -= row['spent']
    summary = runner.summarize(records, timings)
    assert summary['selected'] is None and summary['budget_quality_witness'] == 'SD128_B0'
    assert summary['candidates'][0]['total_samples'] == sum(runner.TOTAL_BUDGETS)
    assert summary['candidates'][0]['budget_quality_feasible']
    assert not summary['candidates'][0]['qualification_conditions']['whole_charged_cost']


def test_declared_tie_order_and_safety_error_exclusion():
    choices = [dict(candidate='a', order=0, total_samples=100, joint_completed=133, eligible=True),
        dict(candidate='b', order=1, total_samples=100, joint_completed=134, eligible=True),
        dict(candidate='c', order=2, total_samples=100, joint_completed=134, eligible=True),
        dict(candidate='d', order=3, total_samples=90, joint_completed=216, eligible=False)]
    assert runner.winner(choices, 'eligible') == 'b'
    assert runner.winner([dict(row, eligible=False) for row in choices], 'eligible') is None
    records, timings = cohort()
    records[0]['history'][0]['goal_upper_ok'] = False
    summary = runner.summarize(records, timings)
    assert not summary['candidates'][0]['budget_quality_feasible'] and not summary['candidates'][0]['qualification_witness']


def test_parent_reuses_sources_and_freezes_all_1728_before_any_score(monkeypatch, tmp_path):
    output, source, events = tmp_path/'output', tmp_path/'source', []
    source.mkdir()
    bundle = public_bundle()
    runner.save(source/'source_evidence.json', [dict(life=life, a=bundle['a'], b=bundle['b']) for life in runner.LIVES])
    runner.save(source/'cases.json', [dict(life=life, cases=bundle['cases']) for life in runner.LIVES])
    runner.save(source/'interfaces.json', [dict(life=life, identities=bundle['identities'], metadata=bundle['metadata']) for life in runner.LIVES])
    monkeypatch.setattr(runner, 'OUTPUT', output)
    monkeypatch.setattr(runner, 'SOURCE_DIRECTORY', source)
    monkeypatch.setattr(runner, 'prerequisites', lambda: dict(admitted=True))
    monkeypatch.setattr(runner, 'capture', lambda: events.append('capture'))
    monkeypatch.setattr(runner.task, 'world', lambda life: (None, [None]*78, None, None))
    monkeypatch.setattr(runner, 'draw', lambda *args: pytest.fail('Parent must not redraw settled sources'))

    class Future:
        def __init__(self, life, spec):
            self.life, self.spec = life, spec

        def result(self):
            assert events.count('submit') == 24
            events.append('finish')
            candidate = self.spec['candidate']
            with gzip.open(output/f'records_life_{self.life:02d}_{candidate}.jsonl.gz', 'wt') as stream:
                for index in runner.TARGETS:
                    stream.write(json.dumps(dict(life=self.life, index=index, arm=candidate, candidate=candidate, identity=0))+'\n')
            return dict(life=self.life, arm=candidate, candidate=candidate, final_state={}, probe_ledger={},
                timings=dict.fromkeys(runner.TIMING_SCOPES, 0.), output_seconds=0., life_plan_wall_seconds=0.,
                normalizer_cache_statistics={}, work={}, profiles=0)

    class Executor:
        def __init__(self, max_workers):
            assert max_workers == 8

        def __enter__(self):
            return self

        def __exit__(self, *args):
            events.append('workers_exited')

        def submit(self, operation, life, spec, supplied):
            assert operation is runner.run_life_plan and events[0] == 'capture'
            assert (output/'source_reference.json').exists() and (output/'interfaces.json').exists()
            assert supplied['a'] == bundle['a'] and supplied['b'] == bundle['b']
            assert json.loads((output/'run.json').read_text())['phases'] == ['protocol_frozen']
            events.append('submit')
            return Future(life, spec)

    def evaluate(row, law):
        assert events.count('finish') == 24 and 'workers_exited' in events
        assert json.loads((output/'run.json').read_text())['phases'] == ['protocol_frozen', 'all_decisions_frozen']
        events.append('score')
        return row

    monkeypatch.setattr(runner, 'ProcessPoolExecutor', Executor)
    monkeypatch.setattr(runner, 'evaluate', evaluate)
    monkeypatch.setattr(runner, 'summarize', lambda rows, timings: dict(records=len(rows)))
    summary = runner.run()
    assert summary['records'] == events.count('score') == 1728
    assert json.loads((output/'run.json').read_text())['complete']
