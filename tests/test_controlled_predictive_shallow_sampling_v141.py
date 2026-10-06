"""Finite isolation of first-spawn sampling from V140 program continuation."""
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
from acfqp.science import controlled_predictive_shallow_sampling_v141 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import ACTIONS, NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'reports/v141_runtime_tmp/core_checks'
RETAINED = ROOT/'reports/controlled_predictive_factored_fragments_v139'
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
    path = ROOT/'reports/controlled_predictive_shallow_sampling_v141.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        planner_work=dict(sum((planner.counts for planner in SEARCHES+DEEP), Counter())),
        setup_counts=dict(sum((model.setup_counts for model in SEARCHES+DEEP+MODELS+SOURCES), EXTRA.copy())),
        model_work=dict(sum((model.counts for model in MODELS+SOURCES), Counter())),
        newly_sampled_environment_transitions=0,
        newly_sampled_model_transitions=sum(planner.counts['model_sampled_transitions'] for planner in SEARCHES+DEEP),
        scope='Finite static boards; V140 first-spawn instrumentation and frozen H1 arithmetic.'))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2)+'\n')


def factored():
    return json.loads((RETAINED/'train_0/FACTORED_64.json').read_text())


def leaf(target=TARGET, frozen=True, distribution=((1, Fraction(9, 10)), (2, Fraction(1, 10)))):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'), distribution, 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape)%11*.001
    source.weights.flags.writeable = False
    source.updates = 42; SOURCES.append(source)
    result = QueryTD(QueryParent(source, SOURCE, target, .5), 'PRIOR', BUILD)
    if frozen:
        result.freeze()
    MODELS.append(result)
    return result


def planner(model=None, programs=None):
    result = core.ShallowSamplingPlanner(leaf() if model is None else model,
        factored() if programs is None else programs, BUILD)
    SEARCHES.append(result)
    return result


def instrumented_deep(search, monkeypatch):
    """Only records V140's actual first spawn; its original algorithm stays intact."""
    original = Path(previous.__file__).with_suffix('.cpp')
    text = original.read_text()
    statement = 'spawn(current,probability_rank1,rng,counts);'
    assert text.count(statement) == 2
    record = statement+' captured.push_back(action); captured.push_back(replica); captured.insert(captured.end(),current,current+16);'
    text = '#include <vector>\nstatic std::vector<int32_t> captured;\n'+text.replace(statement, record, 1)
    text = '#include <cstdint>\n'+text
    text += '\nextern "C" int captured_size_v141() {return captured.size();}\n'
    text += 'extern "C" void captured_take_v141(int32_t* out) {std::copy(captured.begin(),captured.end(),out); captured.clear();}\n'
    cpp, output = BUILD/'first_spawn_probe.cpp', BUILD/'first_spawn_probe.so'
    cpp.write_text(text)
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
    library.program_choose_v140.argtypes = [ip, ip, ci, dp, ip, lp, ip, ip, ci, ip,
        cd, cd, cd, cd, cd, cd, ci, ci, ci, cu, ip, lp, dp, dp, ip, ip, up]
    library.program_choose_v140.restype = ci
    library.captured_size_v141.restype = ci
    library.captured_take_v141.argtypes = [ip]
    library.captured_take_v141.restype = None
    monkeypatch.setattr(previous, '_backend', lambda build_dir, counts: library)
    policy = json.loads((ROOT/'reports/controlled_predictive_program_planning_v140/train_0/LEARNED_64.json').read_text())
    deep = previous.ProgramPlanner(search.model, factored(), policy, build_dir=BUILD)
    DEEP.append(deep)
    return deep, library


def test_v140_actual_first_spawns_candidates_budgets_and_explicit_sampled_h1_match(monkeypatch):
    search = planner()
    deep, library = instrumented_deep(search, monkeypatch)
    for board in (SPARSE, NEAR_LOSS, GOAL):
        for seed in (141, 2**40+141):
            shallow = search.choose(board, simulation_seed=seed)
            baseline = deep.choose(board, simulation_seed=seed)
            size = library.captured_size_v141()
            captured = np.empty(size, dtype=np.int32)
            library.captured_take_v141(captured)
            outcomes = {(ACTIONS[row[0]], int(row[1])): row[2:].tolist() for row in captured.reshape(-1, 18)}
            assert shallow['action_values'].keys() == baseline['action_values'].keys()
            for action, row in shallow['action_values'].items():
                for key in ('afterstate', 'score', 'budget', 'rollouts'):
                    assert row[key] == baseline['action_values'][action][key]
                if not row['rollouts']:
                    continue
                explicit = []
                for replica in range(row['rollouts']):
                    spawned = search._first_spawn(row['afterstate'], action, replica, seed)
                    assert spawned == outcomes[action, replica]
                    # Python QueryTD independently maximizes all legal second actions.
                    explicit.append(search.model.choose(spawned)['value'])
                assert row['tail_value'] == pytest.approx(sum(explicit)/len(explicit), abs=1e-12)
                assert row['value'] == pytest.approx(row['score']/2048.+sum(explicit)/len(explicit), abs=1e-12)
            expected = max(shallow['action_values'], key=lambda action: shallow['action_values'][action]['value'])
            assert shallow['action'] == expected


@pytest.mark.parametrize('board', [SPARSE, NEAR_LOSS, GOAL, LOST])
def test_only_first_spawn_and_full_h1_are_charged_with_same_root_budget(board):
    choice = planner().choose(board, simulation_seed=141)
    counts, rows = choice['counts'], list(choice['action_values'].values())
    trajectories = sum(row['rollouts'] for row in rows)
    assert counts['root_swipe_calls'] == counts['program_swipe_calls'] == 4
    assert counts.get('bootstrap_swipe_calls', 0) == 4*trajectories
    assert counts['model_swipe_budget'] == 4+sum(row['budget'] for row in rows)
    assert counts['model_swipes_used'] == counts['learned_swipe_calls'] == 4+4*trajectories
    assert counts.get('model_sampled_transitions', 0) == counts.get('rollouts_started', 0) == trajectories
    assert counts.get('simulation_uniform_draws', 0) == 2*trajectories
    assert counts.get('simulation_rng_initializations', 0) == counts.get('leaf_choose_calls', 0) == trajectories
    for key in ('rollout_actions', 'tree_calls', 'tree_predicate_checks', 'budget_early_bootstraps'):
        assert counts.get(key, 0) == 0
    for row in rows:
        expected_cap = 0 if max(row['afterstate']) >= 4 else 8*row['afterstate'].count(0)
        assert row['budget'] == expected_cap and row['used'] == 4*row['rollouts'] <= row['budget']
        assert row['rollouts'] == (max(1, expected_cap//16) if expected_cap else 0)
    if board == LOST:
        assert choice['status'] == 'LOST' and choice['value'] == -TARGET['failure_penalty']


@pytest.mark.parametrize('target', [SOURCE, TARGET])
def test_h1_preserves_query_conversion_second_action_max_and_terminal_values(target):
    model = leaf(target=target)
    search = planner(model)
    for board in (SPARSE, NEAR_LOSS, LOST, GOAL, [4]+[0]*15):
        expected = model.choose(board)
        before = model.counts.copy()
        assert search._h1(board) == expected['value']
        assert model.counts == before
        if expected['action_values']:
            assert expected['value'] == max(row['value'] for row in expected['action_values'].values())


def test_seed_repeatability_no_leaf_updates_no_program_or_tree_learning():
    model, programs = leaf(), factored()
    original = deepcopy(programs)
    search = planner(model, programs)
    weights, updates, counts = model.weights.copy(), model.updates, model.counts.copy()
    first = search.choose(SPARSE, simulation_seed=1)
    assert search.choose(SPARSE, simulation_seed=1, previous_action='UP') == first
    assert search.choose(SPARSE, simulation_seed=2)['action_values'] != first['action_values']
    np.testing.assert_array_equal(model.weights, weights)
    assert model.updates == updates and model.counts == counts
    assert programs == original and not search.programs.flags.writeable
    assert not hasattr(search, 'trees') and not search.weights.flags.writeable
    assert search.setup_counts.get('copied_tree_bytes', 0) == 0


def test_goal_bypass_missing_local_programs_and_fixed_leaf_requirements():
    search = planner()
    won = search.choose([4]+[0]*15)
    assert won['status'] == 'WON' and won['value'] == TARGET['goal_bonus']
    assert won['counts'].get('learned_swipe_calls', 0) == won['counts'].get('model_sampled_transitions', 0) == 0
    programs = factored(); programs['programs'] = []
    missing = planner(programs=programs)
    with pytest.raises(ValueError, match='coverage is incomplete'):
        missing.choose(SPARSE)
    assert missing.counts['line_misses'] == 1
    assert missing.counts['bootstrap_swipe_calls'] == missing.counts['model_sampled_transitions'] == 0
    with pytest.raises(ValueError, match='already be frozen'):
        planner(leaf(frozen=False))
    with pytest.raises(ValueError, match='target query is fixed'):
        search.choose(SPARSE, SOURCE)
    estimated = planner(leaf(distribution=((1, Fraction(8075, 9026)), (2, Fraction(951, 9026)))))
    assert estimated.spawn_probabilities == (8075/9026, 951/9026)
