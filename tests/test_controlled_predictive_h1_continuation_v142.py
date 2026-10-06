"""Finite all-action continuation semantics, paired streams and rollout accounting."""
from collections import Counter
from copy import deepcopy
import ctypes
from fractions import Fraction
import json
import os
from pathlib import Path
import subprocess

import numpy as np
import pytest

from acfqp.science import controlled_predictive_program_planning_v140 as previous
from acfqp.science import controlled_predictive_h1_continuation_v142 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import ACTIONS, NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'reports/v142_runtime_tmp/core_checks'
SOURCE = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
TARGET = dict(reward_weight=1., failure_penalty=1., goal_bonus=1.)
SPARSE = [1, 1]+[0]*14
NEAR_LOSS = [1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 0]
LOST = [1, 2, 1, 2, 2, 1, 2, 1]*2
GOAL = [3, 3]+[0]*14
SEARCHES, MODELS, SOURCES, DEEP = [], [], [], []
EXTRA = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    BUILD.mkdir(parents=True, exist_ok=True)
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_h1_continuation_v142.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        planner_work=dict(sum((planner.counts for planner in SEARCHES+DEEP), Counter())),
        setup_counts=dict(sum((model.setup_counts for model in SEARCHES+DEEP+MODELS+SOURCES), Counter())),
        model_work=dict(sum((model.counts for model in MODELS+SOURCES), Counter())),
        finite_oracle_work=dict(EXTRA), newly_sampled_environment_transitions=0,
        newly_sampled_model_transitions=sum(planner.counts['model_sampled_transitions'] for planner in SEARCHES+DEEP)+EXTRA['oracle_model_sampled_transitions'],
        scope='Static boards; V140 paired first spawns, independent Python H1 continuation and shared seeded uniform streams.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def factored():
    return json.loads((ROOT/'reports/controlled_predictive_factored_fragments_v139/train_0/FACTORED_64.json').read_text())


def leaf(target=TARGET, constant=None, frozen=True,
         distribution=((1, Fraction(9, 10)), (2, Fraction(1, 10)))):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'), distribution, 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape)%11*.001 if constant is None else constant/32
    source.weights.flags.writeable = False
    source.updates = 42; SOURCES.append(source)
    model = QueryTD(QueryParent(source, SOURCE, target, .5), 'PRIOR', BUILD)
    if frozen:
        model.freeze()
    MODELS.append(model)
    return model


def planner(model=None, programs=None):
    search = core.H1ContinuationPlanner(leaf() if model is None else model,
        factored() if programs is None else programs, BUILD)
    SEARCHES.append(search)
    return search


def instrumented(search, monkeypatch):
    """Record actual native choices/spawns; independently expose seeded uniforms."""
    original = Path(previous.__file__).with_suffix('.cpp')
    old = original.read_text()
    first = 'spawn(current,probability_rank1,rng,counts);'
    record = first+' deep_capture.push_back(action); deep_capture.push_back(replica); deep_capture.insert(deep_capture.end(),current,current+16);'
    old = '#include <cstdint>\n#include <vector>\nstatic std::vector<int32_t> deep_capture;\n'+old.replace(first, record, 1)
    old_path = BUILD/'v140_first_spawn.cpp'; old_path.write_text(old)
    text = Path(core.__file__).with_suffix('.cpp').read_text()
    text = text.replace('#include "controlled_predictive_program_planning_v140.cpp"', '#include "'+str(old_path)+'"\nstatic std::vector<int32_t> events;\nvoid capture(int kind,int root,int rep,int depth,int chosen,const int32_t* b) {events.insert(events.end(),{kind,root,rep,depth,chosen}); events.insert(events.end(),b,b+16);}')
    assert text.count(first) == 2
    text = text.replace(first, first+' capture(0,action,replica,-1,-1,current);', 1)
    last = text.rfind(first)
    text = text[:last]+text[last:].replace(first, first+' capture(2,action,replica,depth,chosen,current);', 1)
    selection = 'next,gained,chosen_value,counts);'
    assert text.count(selection) == 1
    text = text.replace(selection, selection+' capture(1,action,replica,depth,chosen,next);')
    text += '''
extern "C" int event_size_v142(int deep) { return deep ? deep_capture.size() : events.size(); }
extern "C" void event_take_v142(int deep,int32_t* out) {auto& v=deep ? deep_capture : events; std::copy(v.begin(),v.end(),out); v.clear();}
extern "C" void oracle_uniforms_v142(uint64_t seed,int action,int replica,double* out) {
    std::seed_seq sequence{static_cast<uint32_t>(seed),static_cast<uint32_t>(seed>>32),static_cast<uint32_t>(action),static_cast<uint32_t>(replica)};
    std::mt19937_64 engine(sequence);
    for (int i=0;i<8;++i) out[i]=(engine()>>11)*0x1.0p-53;
}
'''
    cpp, output = BUILD/'trace_probe.cpp', BUILD/'trace_probe.so'; cpp.write_text(text)
    subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off', str(cpp),
        str(original.with_name('controlled_predictive_ntuple_kernel_v120.cpp')), '-o', str(output)],
        check=True, capture_output=True, text=True, env=dict(os.environ, TMPDIR=str(BUILD)))
    EXTRA.update(finite_probe_cpp_compilations=1, finite_probe_cpp_translation_units_compiled=2)
    library = ctypes.CDLL(str(output))
    ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
    lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
    dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
    up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
    ci, cd, cu = ctypes.c_int, ctypes.c_double, ctypes.c_uint64
    library.continuation_choose_v142.argtypes = search.library.continuation_choose_v142.argtypes
    library.continuation_choose_v142.restype = ci
    library.program_choose_v140.argtypes = [ip, ip, ci, dp, ip, lp, ip, ip, ci, ip,
        cd, cd, cd, cd, cd, cd, ci, ci, ci, cu, ip, lp, dp, dp, ip, ip, up]
    library.program_choose_v140.restype = ci
    library.event_size_v142.argtypes = [ci]; library.event_size_v142.restype = ci
    library.event_take_v142.argtypes = [ci, ip]; library.event_take_v142.restype = None
    library.oracle_uniforms_v142.argtypes = [cu, ci, ci, dp]; library.oracle_uniforms_v142.restype = None
    search.library = library
    monkeypatch.setattr(previous, '_backend', lambda build_dir, counts: library)
    policy = json.loads((ROOT/'reports/controlled_predictive_program_planning_v140/train_0/LEARNED_64.json').read_text())
    deep = previous.ProgramPlanner(search.model, factored(), policy, build_dir=BUILD); DEEP.append(deep)
    return library, deep


def take(library, deep=False):
    size = library.event_size_v142(int(deep))
    result = np.empty(size, dtype=np.int32); library.event_take_v142(int(deep), result)
    return result.reshape(-1, 18 if deep else 21).tolist()


def explicit_trajectory(search, after, action, replica, allowance, uniforms):
    current, events, cursor, used, total = list(after), [], 0, 0, 0.
    def spawn(kind, depth, chosen):
        nonlocal cursor
        empty = [i for i, value in enumerate(current) if value == 0]
        cell = empty[int(uniforms[cursor]*len(empty))]
        current[cell] = 1 if uniforms[cursor+1] < search.spawn_probabilities[0] else 2
        cursor += 2; EXTRA['oracle_model_sampled_transitions'] += 1
        events.append([kind, action, replica, depth, chosen, *current])
    spawn(0, -1, -1)
    terminal = False
    for depth in range(3):
        if allowance-used < 8:
            break
        choice = search.model.choose(current)
        used += 0 if choice['status'] == 'WON' else 4
        chosen = -2 if choice['status'] == 'WON' else -1 if choice['status'] == 'LOST' else ACTIONS.index(choice['action'])
        events.append([1, action, replica, depth, chosen, *choice['afterstate']])
        if chosen < 0:
            total += choice['value']; terminal = True; break
        total += choice['score']/2048.
        current = list(choice['afterstate'])
        if max(current) >= search.radix:
            total += search.goal; terminal = True; break
        spawn(2, depth, chosen)
    if not terminal:
        choice = search.model.choose(current)
        total += choice['value']; used += 0 if choice['status'] == 'WON' else 4
    return total, used, events


def test_actual_full_trajectories_match_python_h1_and_v140_initial_samples(monkeypatch):
    search = planner(); library, deep = instrumented(search, monkeypatch)
    for board in (SPARSE, NEAR_LOSS, GOAL):
        for seed in (142, 2**40+142):
            choice = search.choose(board, simulation_seed=seed)
            baseline = deep.choose(board, simulation_seed=seed)
            observed, old = take(library), take(library, True)
            assert [[row[1], row[2], *row[5:]] for row in observed if row[0] == 0] == old
            expected_events = []
            for action, row in choice['action_values'].items():
                assert {key: row[key] for key in ('afterstate','score','budget','rollouts')} == {
                    key: baseline['action_values'][action][key] for key in ('afterstate','score','budget','rollouts')}
                if not row['rollouts']:
                    continue
                total, used = 0., 0
                for replica in range(row['rollouts']):
                    uniforms = np.empty(8)
                    library.oracle_uniforms_v142(seed, ACTIONS.index(action), replica, uniforms)
                    EXTRA['oracle_rng_initializations'] += 1; EXTRA['oracle_uniform_draws'] += 8
                    allowance = row['budget']//row['rollouts']+int(replica < row['budget']%row['rollouts'])
                    result, cost, events = explicit_trajectory(search, row['afterstate'], ACTIONS.index(action), replica, allowance, uniforms)
                    assert cost <= allowance
                    expected_events.extend(events); total += result; used += cost
                assert row['tail_value'] == pytest.approx(total/row['rollouts'], abs=1e-12)
                assert row['value'] == pytest.approx(row['score']/2048.+total/row['rollouts'], abs=1e-12)
                assert row['used'] == used
            assert observed == expected_events
            assert choice['action'] == max(choice['action_values'], key=lambda action: choice['action_values'][action]['value'])


@pytest.mark.parametrize('target', [SOURCE, TARGET])
def test_h1_action_max_query_conversion_ties_and_terminal_semantics(target):
    model = leaf(target=target, constant=2.)
    search = planner(model)
    for board in (SPARSE, NEAR_LOSS, GOAL, LOST, [4]+[0]*15):
        expected = model.choose(board)
        before = model.counts.copy()
        assert search._h1_action(board) == {key: expected[key] for key in ('action','afterstate','score','value','status')}
        assert search._h1(board) == expected['value']
        assert model.counts == before
    if target == TARGET:
        # Source strongly prefers the goal; converted target prefers active successors.
        assert model.model.choose(GOAL, SOURCE)['action'] != search._h1_action(GOAL)['action']


@pytest.mark.parametrize('board', [SPARSE, NEAR_LOSS, GOAL, LOST])
def test_all_swipes_predictions_spawns_and_budget_are_charged(board):
    choice = planner().choose(board, simulation_seed=142)
    c = Counter(choice['counts']); rows = choice['action_values'].values()
    assert c['program_swipe_calls'] == c['root_swipe_calls'] == 4
    assert c['model_swipes_used'] == c['learned_swipe_calls'] == 4+c['continuation_swipe_calls']+c['bootstrap_swipe_calls']
    assert c['continuation_swipe_calls'] == 4*c['continuation_choose_calls']
    assert c['bootstrap_swipe_calls'] == 4*c['leaf_choose_calls']
    assert c['line_table_lookups'] == 4*(c['continuation_swipe_calls']+c['bootstrap_swipe_calls'])
    assert c['table_lookups'] == 32*c['value_predictions']
    assert c['continuation_value_predictions'] <= c['value_predictions']
    assert c['model_sampled_transitions'] == c['rollouts_started']+c['rollout_actions']-c['rollout_terminal_goal_states']
    assert c['simulation_uniform_draws'] == 2*c['model_sampled_transitions']
    assert c['continuation_choose_calls'] == c['rollout_actions']+c['rollout_terminal_loss_states']
    assert c['continuation_terminal_loss_states'] == c['rollout_terminal_loss_states']
    assert c['model_swipe_budget'] == 4+sum(row['budget'] for row in rows)
    assert c['model_swipes_used'] == 4+sum(row['used'] for row in rows)
    for row in rows:
        cap = 0 if max(row['afterstate']) >= 4 else 8*row['afterstate'].count(0)
        assert row['budget'] == cap and row['used'] <= cap
        assert row['rollouts'] == (max(1, cap//16) if cap else 0)
    assert c['tree_calls'] == c['tree_predicate_checks'] == c['direct_choose_calls'] == 0
    if board == NEAR_LOSS:
        assert any(row['budget'] == 8 for row in rows)
        assert c['budget_early_bootstraps'] > 0
    if board == SPARSE:
        assert c['rollout_actions'] == 3*c['rollouts_started']


def test_seed_repeatability_readonly_and_supported_frozen_requirements():
    model, programs = leaf(), factored(); original = deepcopy(programs)
    search = planner(model, programs)
    weights, updates, counts = model.weights.copy(), model.updates, model.counts.copy()
    first = search.choose(SPARSE, simulation_seed=1)
    assert search.choose(SPARSE, simulation_seed=1, previous_action='UP') == first
    assert search.choose(SPARSE, simulation_seed=2)['action_values'] != first['action_values']
    np.testing.assert_array_equal(model.weights, weights)
    assert model.updates == updates and model.counts == counts and programs == original
    assert not search.programs.flags.writeable and not search.weights.flags.writeable and not hasattr(search, 'trees')
    assert search.setup_counts.get('copied_tree_bytes', 0) == 0
    won = search.choose([4]+[0]*15)
    assert won['status'] == 'WON' and won['counts'].get('learned_swipe_calls', 0) == 0
    programs['programs'] = []
    missing = planner(programs=programs)
    with pytest.raises(ValueError, match='coverage is incomplete'):
        missing.choose(SPARSE)
    assert missing.counts['bootstrap_swipe_calls'] == missing.counts['continuation_swipe_calls'] == missing.counts['model_sampled_transitions'] == 0
    with pytest.raises(ValueError, match='already be frozen'):
        planner(leaf(frozen=False))
    with pytest.raises(ValueError, match='target query is fixed'):
        search.choose(SPARSE, SOURCE)
    estimated = planner(leaf(distribution=((1, Fraction(8075, 9026)), (2, Fraction(951, 9026)))))
    assert estimated.spawn_probabilities == (8075/9026, 951/9026)
