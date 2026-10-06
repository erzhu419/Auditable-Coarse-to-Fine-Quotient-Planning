"""Finite V151 feature, commitment and environment checks; no native planner."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import random

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.controlled_predictive_policy_modules_v151 import (
    FEATURE_DEFINITION, QUERIES, SCHEMA, ModuleGate, RootConsequences,
    run_module_branch, utility)

TEMP = Path(__file__).resolve().parents[1]/'reports/v151_runtime_tmp'
ROWS, MODELS = [], []
ORACLE, STUB_WORK = Counter(), Counter()
SPARSE = [1, 1]+[0]*14
LOSS_ROOT = [1, 1, 3, 4, 5, 6, 7, 8, 9, 10, 9, 10, 8, 7, 6, 5]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True); before = request.session.testsfailed
    yield
    environment = sum((Counter(r['result']['environment_counts']) for r in ROWS), Counter())
    model_work = sum((m.counts for m in MODELS), Counter())
    path = TEMP/'core_checks.json'; payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(i.module.__name__ == __name__ for i in request.session.items),
        failures=request.session.testsfailed-before, environment_counts=dict(environment),
        finite_real_training_updates=model_work['update_calls'], model_counts=dict(model_work),
        newly_sampled_environment_transitions=environment['sampled_transitions'], newly_sampled_model_transitions=0,
        native_planner_calls=0, deterministic_oracle_work=dict(ORACLE), stub_work=dict(STUB_WORK),
        scope='Fixed-board suffixes, synthetic three-component updates, scripted policies; no production games.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def model():
    result = RootConsequences(); MODELS.append(result); return result


def reference_features(board):
    classes = [int(r in (0, 3))+int(c in (0, 3)) for r in range(4) for c in range(4)]
    features = Counter({-1: 1})
    for i, rank in enumerate(board): features[classes[i]*11+rank] += 1
    for r in range(4):
        for c in range(4):
            i = 4*r+c
            for j in ([i+1] if c < 3 else [])+([i+4] if r < 3 else []):
                left, right = classes[i]*11+board[i], classes[j]*11+board[j]
                features[33+min(left, right)*33+max(left, right)] += 1
    ORACLE['feature_boards'] += 1
    return features


def test_root_features_include_bias_and_shared_multiplicities():
    board = [i % 11 for i in range(16)]; learner = model()
    actual, expected = learner._features(board), reference_features(board)
    assert actual == expected and actual[-1] == 1 and sum(actual.values()) == 41
    assert learner.counts == Counter(feature_board_reads=16, feature_rank_reads=64,
        feature_occurrences=41, unary_feature_occurrences=16, pair_feature_occurrences=24, bias_feature_occurrences=1)
    assert learner.setup_counts == Counter(topology_integer_cells=64, bias_integer_cells=1)
    assert FEATURE_DEFINITION['input'] == 'root_board'


def test_normalized_lms_fits_total_components_without_immediate_or_pair_subtraction():
    learner = model(); target = [2., -.25, .75]; features = reference_features(SPARSE)
    result = learner.update(SPARSE, target, alpha=.1)
    denominator = sum(n*n for n in features.values())
    assert result['denominator'] == denominator and result['prediction'] == [0., 0., 0.]
    for address, n in features.items():
        assert learner.weights[address] == pytest.approx([.1*n*y/denominator for y in target])
    assert learner.predict(SPARSE) == pytest.approx([.1*y for y in target])
    assert learner.counts['update_calls'] == learner.counts['root_updates'] == learner.updates == 1
    assert learner.counts['root_predictions'] == 2
    assert 'pair_predictions' not in learner.counts and 'pair_updates' not in learner.counts
    # An identical root remains an informative training example, with no same-action shortcut.
    learner.update(SPARSE, target, alpha=1.)
    assert learner.predict(SPARSE) == pytest.approx(target)
    assert learner.updates == 2


def test_checkpoint_freeze_and_warm_load_preserve_weights_but_reset_runtime_counts():
    learner = model(); learner.update(SPARSE, [1., 0., 1.]); learner.freeze()
    frozen = learner.state(); payload = learner.to_payload()
    assert payload['schema'] == SCHEMA and payload['feature_definition'] == FEATURE_DEFINITION
    assert payload['components'] == ['score_over_2048_difference', 'failure_difference', 'success_difference']
    restored = RootConsequences.from_payload(deepcopy(payload)); MODELS.append(restored)
    assert restored.state() == frozen and restored.counts == Counter()
    n = len(learner.weights)
    assert restored.setup_counts['loaded_weight_addresses'] == n
    assert payload['storage']['weight_parameters'] == 3*n
    with pytest.raises(RuntimeError, match='frozen'): restored.update(SPARSE, [0., 0., 0.])
    assert restored.state() == frozen and restored.counts == Counter()
    restored.frozen = False; restored.update(SPARSE, [0., 0., 0.])
    assert restored.updates == frozen['updates']+1 and learner.state() == frozen


class ScriptedPlanner:
    def __init__(self, actions):
        self.actions, self.calls = list(actions), []
        self.counts = Counter(choose_calls=7, value_predictions=11)
    def choose(self, board, query):
        self.calls.append((tuple(board), deepcopy(query)))
        self.counts.update(choose_calls=1, value_predictions=4)
        STUB_WORK.update(choose_calls=1, value_predictions=4)
        return dict(action=self.actions[len(self.calls)-1], action_values={'kept': 3.}, counts=dict(choose_calls=1))


class ScriptedModel:
    def __init__(self, values):
        self.values, self.calls = list(values), []; self.frozen = True; self.counts = Counter()
    def predict(self, board):
        self.calls.append(tuple(board)); self.counts['root_predictions'] += 1; STUB_WORK['root_predictions'] += 1
        return self.values[len(self.calls)-1]


def test_gate_commits_full_duration_and_binds_each_policy_to_its_own_query():
    bank = dict(risk1=ScriptedPlanner(['LEFT']*9), risk8=ScriptedPlanner(['RIGHT']*2))
    predictor = ScriptedModel([[0., 0., 1.], [0., 1., 0.], [0., 0., 0.], [0., 0., 1.]])
    gate = ModuleGate(bank, 'risk8', 8, predictor)
    outputs = [gate.choose(SPARSE, step) for step in range(11)]
    decisions = [r['module_decision'] for r in outputs]
    assert [d['policy_key'] for d in decisions] == ['risk1']*8+['risk8']*2+['risk1']
    assert [d['boundary'] for d in decisions] == [True]+[False]*7+[True]*3
    assert [d['remaining_after'] for d in decisions[:8]] == list(range(7, -1, -1))
    assert [d['estimated_advantage'] for d in decisions if d['boundary']] == [8., -8., 0., 8.]
    assert all(d['predicted_components'] is None for d in decisions[1:8])
    assert predictor.calls == [tuple(SPARSE)]*4
    assert gate.counts['learner_root_predictions'] == 4 and gate.counts['committed_module_decisions'] == 7
    assert gate.counts['module_accepts'] == 2 and gate.counts['baseline_boundary_decisions'] == 2
    assert gate.counts['policy_risk1_choose_calls'] == 9 and gate.counts['policy_risk8_choose_calls'] == 2
    assert gate.policy_counts_by_query == dict(risk1=Counter(choose_calls=9, value_predictions=36), risk8=Counter(choose_calls=2, value_predictions=8))
    assert all(q == QUERIES[key] for key, planner in bank.items() for _, q in planner.calls)
    assert all(r['action_values'] == {'kept': 3.} for r in outputs)
    assert gate.latest_decision == decisions[-1]


def test_strict_zero_gate_preserves_h2_and_alt_mode_commits_without_a_predictor():
    bank = dict(risk1=ScriptedPlanner(['LEFT']*4), risk8=ScriptedPlanner(['RIGHT']*4))
    gate = ModuleGate(bank, 'risk1', 1, ScriptedModel([[0., 0., 0.]]*2))
    assert [gate.choose(SPARSE, i)['action'] for i in range(2)] == ['LEFT']*2
    alt = ModuleGate(bank, 'risk1', 8, mode='ALT')
    assert [alt.choose(SPARSE, i)['action'] for i in range(2)] == ['RIGHT']*2
    assert alt.remaining == 6 and alt.counts['module_accepts'] == 1
    baseline = ModuleGate(bank, 'risk1', 0, mode='H2')
    assert baseline.choose(SPARSE, 0)['action'] == 'LEFT' and baseline.remaining == 0
    with pytest.raises(ValueError, match='frozen'): ModuleGate(bank, 'risk1', 8)


def branch(*args, **kwargs):
    result = run_module_branch(*args, **kwargs); ROWS.append(result); return result


def replay(row):
    board, rng = tuple(row['root_board']), random.Random(row['seed'])
    boards = [board]
    for action, cell, rank, score in zip(row['actions'], row['spawned_cells'], row['spawned_ranks'], row['scores'], strict=True):
        after, actual_score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
        ORACLE['explicit_ground_swipe_calls'] += 1
        assert changed and actual_score == score
        empty = [i for i, x in enumerate(after) if not x]
        assert cell == empty[int(rng.random()*len(empty))] and rank == (1 if rng.random() < .9 else 2)
        ORACLE['replayed_uniform_draws'] += 2
        board = list(after); board[cell] = rank; board = tuple(board); boards.append(board)
    assert row['final_board'] == list(board) and row['first_exit'] == list(boards[1])
    result = row['result']; steps = result['steps']; work = result['environment_counts']
    assert steps == len(row['actions']) and result['score'] == sum(row['scores'])
    assert work['sampled_transitions'] == work['ground_explicit_swipe_calls'] == steps
    assert work['environment_random_draws'] == 2*steps and work['ground_state_status_calls'] == steps+1
    assert work.get('initial_spawns', 0) == 0 and result['learning_counts'] == {}
    assert result['module_decisions'] == min(row['duration'], steps)
    assert result['continuation_decisions'] == max(0, steps-row['duration'])
    return boards


def test_same_first_action_does_not_erase_later_module_divergence():
    baseline_bank = dict(risk1=ScriptedPlanner(['LEFT', 'DOWN']), risk8=ScriptedPlanner([]))
    module_bank = dict(risk1=ScriptedPlanner([]), risk8=ScriptedPlanner(['LEFT', 'RIGHT']))
    baseline = branch(SPARSE, baseline_bank, 'risk1', 0, 123, max_steps=2)
    module = branch(SPARSE, module_bank, 'risk1', 8, 123, max_steps=2)
    replay(baseline); replay(module)
    assert baseline['first_action'] == module['first_action'] == 'LEFT'
    assert baseline['first_exit'] == module['first_exit'] and baseline['actions'][1] != module['actions'][1]
    assert baseline['policy_keys'] == ['risk1']*2 and module['policy_keys'] == ['risk8']*2
    assert all(q == QUERIES['risk8'] for _, q in module_bank['risk8'].calls)
    assert module['result']['policy_counts_by_query'] == dict(risk1={}, risk8=dict(choose_calls=2, value_predictions=8))
    assert module['result']['utility'] is None and module['result']['status'] == 'CUTOFF'


def test_one_step_module_resumes_target_on_the_current_board():
    bank = dict(risk1=ScriptedPlanner(['DOWN']), risk8=ScriptedPlanner(['LEFT']))
    row = branch(SPARSE, bank, 'risk1', 1, 123, max_steps=2); boards = replay(row)
    assert row['actions'] == ['LEFT', 'DOWN'] and row['policy_keys'] == ['risk8', 'risk1']
    assert bank['risk8'].calls == [(boards[0], QUERIES['risk8'])]
    assert bank['risk1'].calls == [(boards[1], QUERIES['risk1'])]
    assert row['result']['policy_counts'] == dict(choose_calls=2, value_predictions=8)
    assert row['result']['module_decisions'] == row['result']['continuation_decisions'] == 1


@pytest.mark.parametrize('query,expected_utility', [('risk1', 2.), ('risk8', 9.)])
def test_module_goal_still_spawns_stops_and_uses_target_terminal_utility(query, expected_utility):
    other = 'risk8' if query == 'risk1' else 'risk1'
    bank = {query: ScriptedPlanner([]), other: ScriptedPlanner(['LEFT'])}
    row = branch([10, 10]+[0]*14, bank, query, 8, 4); replay(row)
    assert row['result']['status'] == 'WON' and row['result']['steps'] == 1
    assert row['result']['components'] == [1., 0., 1.] and row['result']['utility'] == expected_utility
    assert row['first_exit'].count(0) == row['first_afterstate'].count(0)-1
    assert row['result']['continuation_decisions'] == 0 and bank[query].calls == []
    assert bank[other].calls[0][1] == QUERIES[other]


def test_loss_and_cutoff_remain_distinct_and_terminal_loss_is_charged_once():
    bank = dict(risk1=ScriptedPlanner(['LEFT']), risk8=ScriptedPlanner([]))
    loss = branch(LOSS_ROOT, bank, 'risk8', 8, 4); replay(loss)
    assert loss['result']['status'] == 'LOST' and loss['result']['components'] == [4/2048., 1., 0.]
    assert loss['result']['utility'] == 4/2048.-8.
    cutoff = branch(SPARSE, dict(risk1=ScriptedPlanner(['LEFT']), risk8=ScriptedPlanner([])), 'risk1', 0, 71, max_steps=1)
    replay(cutoff)
    assert cutoff['result']['status'] == 'CUTOFF' and cutoff['result']['utility'] is None
    assert cutoff['result']['components'] == [4/2048., 0., 0.]
    assert utility([1., .25, .5], 'risk8') == 3.
