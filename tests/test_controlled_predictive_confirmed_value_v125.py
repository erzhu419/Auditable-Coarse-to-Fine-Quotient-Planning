"""Synthetic routing/TD timing checks; no newly sampled environment data."""
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_confirmed_value_v125 import ConfirmedValueBank
from acfqp.science.controlled_predictive_ntuple_td_v120 import ALPHA, NtupleValue
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'reports/controlled_predictive_confirmed_value_v125_build'
INITIAL = [2] * 26 + [1] * 230
OLD_BLOCK = [2] * 6 + [1] * 58
BOARD = (1, 1, 0, 0) + (0,) * 12
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
BANKS, MODELS, EVALUATIONS = [], [], []


def aggregate_work(objects):
    result = sum((item.counts for item in objects), Counter())
    for key in ('max_pending_transitions', 'router_max_uncommitted_observations'):
        if key in result:
            result[key] = max(item.counts[key] for item in objects)
    return dict(result)


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    failures_before = request.session.testsfailed
    yield
    path = ROOT / 'reports/controlled_predictive_confirmed_value_v125.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    models = {id(model): model for model in MODELS
        + [model for bank in BANKS + EVALUATIONS for model in bank.banks.values()]}
    native = sum((model.counts for model in models.values()), Counter())
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed - failures_before,
        native_model_work=dict(native),
        setup_work=dict(sum((model.setup_counts for model in models.values()), Counter())),
        bank_work=aggregate_work(BANKS),
        evaluation_work=aggregate_work(EVALUATIONS),
        source_rank_initialization_work=dict(sum((Counter(bank.initial_router_payload['counts'])
            for bank in BANKS), Counter())),
        setup_seconds=sum(model.setup_seconds for model in models.values()),
        newly_sampled_environment_transitions=0, optimizer_steps=native['td_updates'],
        scope='Synthetic boards and ranks; native-model and bank counters overlap, do not sum.'))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def source():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    result = NtupleValue(rule, BUILD)
    result.weights[:] = (np.arange(result.weights.size).reshape(result.weights.shape) % 7) * .000125
    MODELS.append(result)
    return result


def bank(method='BANK'):
    result = ConfirmedValueBank(source(), INITIAL, BUILD, method=method)
    BANKS.append(result)
    return result


def feed(model, ranks, *, targets=True):
    events, commits = [], []
    for rank in ranks:
        origin = model.context_id
        event = model.observe(rank)
        if event is not None:
            events.append(event)
        commit = model.finish_transition(BOARD, origin, 1. if targets else None,
                                         model.context_id if targets else None)
        if commit is not None:
            commits.append(commit)
    return events, commits


def test_full_block_delay_keeps_targets_and_replays_updates_in_order():
    model = bank()
    reference = source()
    before = model.banks[0].weights.copy()
    for index, rank in enumerate(OLD_BLOCK):
        origin = model.context_id
        model.observe(rank)
        choice = model.choose(BOARD, QUERY)
        target = choice['value'] + index / 100.
        commit = model.finish_transition(choice['afterstate'], origin, target, choice['context_id'])
        # Stored target, rather than any commit-time recomputation.
        reference.update(choice['afterstate'], target, ALPHA)
        if index < 63:
            assert commit is None and model.updates == 0
            np.testing.assert_array_equal(model.banks[0].weights, before)
    assert commit['applied'] == 64 and commit['censored'] == 0
    assert model.updates == 64 and model.pending_transitions == []
    np.testing.assert_array_equal(model.banks[0].weights, reference.weights)


def test_confirmed_change_clones_before_td_and_keeps_source_exact():
    model = bank()
    before = model.banks[0].weights.copy()
    events, commits = feed(model, [2] * 64)
    assert events[-1]['kind'] == 'quarantined' and not commits
    assert len(model.pending_transitions) == 64 and model.updates == 0
    np.testing.assert_array_equal(model.banks[0].weights, before)
    events, commits = feed(model, [2] * 64)
    assert events[-1]['kind'] == 'created'
    assert commits == [dict(obs_index=384, committed_n=128,
        context_id=1, bank_id=1, applied=0, censored=128, untargeted=0)]
    assert model.origins[1]['updates_at_creation'] == 0
    assert not np.shares_memory(model.banks[0].weights, model.banks[1].weights)
    for value in model.banks.values():
        np.testing.assert_array_equal(value.weights, before)
    assert model.counts['bank_copied_bytes'] == before.nbytes
    assert model.counts['max_pending_transitions'] == 128


def test_reactivated_source_is_preserved_through_new_context_learning():
    model = bank()
    source_weights = model.banks[0].weights.copy()
    feed(model, [2] * 128)
    feed(model, [2] * 64)
    learned_weights = model.banks[1].weights.copy()
    assert model.updates == 64
    assert not np.array_equal(learned_weights, source_weights)
    np.testing.assert_array_equal(model.banks[0].weights, source_weights)
    events, commits = feed(model, OLD_BLOCK * 2)
    assert events[-1]['kind'] == 'reactivated'
    assert model.context_id == model.active_bank_id == 0
    assert commits[-1]['censored'] == 128 and commits[-1]['applied'] == 0
    np.testing.assert_array_equal(model.banks[0].weights, source_weights)
    np.testing.assert_array_equal(model.banks[1].weights, learned_weights)


def test_false_alarm_commits_both_blocks_to_unchanged_context():
    model = bank()
    feed(model, [2] * 64)
    events, commits = feed(model, OLD_BLOCK)
    assert events[-1]['kind'] == 'updated' and not events[-1]['confirmed']
    assert model.context_id == 0 and len(model.banks) == 1
    assert commits[-1]['applied'] == 128 and commits[-1]['censored'] == 0
    assert model.router.counts['rejections'] == 1


def test_shared_control_matches_delay_and_censoring_without_creating_alias_banks():
    models = [bank(method) for method in ('BANK', 'DELAY')]
    histories = [feed(model, [2] * 192 + OLD_BLOCK * 2) for model in models]
    assert histories[0][0] == histories[1][0]
    assert [{key: value for key, value in row.items() if key != 'bank_id'}
        for row in histories[0][1]] == [
        {key: value for key, value in row.items() if key != 'bank_id'}
        for row in histories[1][1]]
    assert len(models[0].banks) == 2 and len(models[1].banks) == 1
    assert models[0].counts['cross_context_target_skips'] == 256
    assert models[1].counts['cross_context_target_skips'] == 256
    assert models[0].updates == models[1].updates == 64
    assert models[1].counts['bank_weight_copies'] == 0


def test_terminal_and_cutoff_records_conserve_observations_and_pending_work():
    model = bank()
    feed(model, OLD_BLOCK[:61], targets=False)
    # A terminal loss has a fixed target and no next-action context.
    model.observe(1)
    assert model.finish_transition(BOARD, 0, -4.) is None
    # Goal and cutoff transitions still consume observations but no TD target.
    model.observe(1)
    assert model.finish_transition(None, 0, None) is None
    payload = model.to_payload()
    assert len(payload['pending_transitions']) == 63
    assert payload['router']['pending']['n'] == 63
    # No game/phase boundary method exists; the next observation completes it.
    model.observe(1)
    commit = model.finish_transition(BOARD, 0, None)
    assert commit['applied'] == 1 and commit['untargeted'] == 63
    assert model.updates == 1
    assert model.counts['queued_targets'] == 1
    assert model.counts['committed_transitions'] == 64


def test_evaluation_copies_router_pending_but_cannot_train_or_modify_parent():
    for method in ('BANK', 'DELAY'):
        model = bank(method)
        feed(model, [2] * 64)
        before = model.to_payload()
        weights = model.banks[0].weights.copy()
        evaluation = model.evaluation_copy()
        EVALUATIONS.append(evaluation)
        assert evaluation.pending_transitions == []
        assert evaluation.router.to_payload() == model.router.to_payload()
        for rank in [2] * 64:
            evaluation.observe(rank)
        assert evaluation.context_id == 1
        assert evaluation.active_bank_id == (1 if method == 'BANK' else 0)
        assert len(evaluation.banks) == (2 if method == 'BANK' else 1)
        for value in evaluation.banks.values():
            assert np.shares_memory(value.weights, model.banks[0].weights)
            assert not value.weights.flags.writeable
        with pytest.raises(RuntimeError, match='cannot update'):
            evaluation.finish_transition(BOARD, 1, 1.)
        assert model.to_payload() == before
        np.testing.assert_array_equal(model.banks[0].weights, weights)


def test_checkpoint_preserves_unfinished_targets_and_source_model_values():
    model = bank()
    feed(model, OLD_BLOCK[:17])
    payload = model.to_payload()
    manifest = model.save(BUILD / 'roundtrip')
    assert manifest['pending_transitions'] == payload['pending_transitions']
    assert manifest['router'] == payload['router']
    assert manifest['schema'] == 'acfqp.confirmed_value.v125'
    assert len(manifest['model_files']) == 1
    for row in manifest['model_files']:
        restored = NtupleValue.load(row['path'], model.rule, BUILD)
        restored.counts = Counter(checkpoint_loads=1,
            checkpoint_loaded_parameters=row['nonzero_weights'])
        MODELS.append(restored)
        np.testing.assert_array_equal(restored.weights, model.banks[row['bank_id']].weights)
        assert restored.updates == 0
    json.dumps(manifest)


def test_missing_or_duplicate_transition_completion_is_detected():
    model = bank()
    with pytest.raises(RuntimeError, match='observe must precede'):
        model.finish_transition(BOARD, 0, 1.)
    model.observe(1)
    with pytest.raises(RuntimeError, match='finish_transition must follow'):
        model.observe(1)
    model.finish_transition(BOARD, 0, 1., 0)
    with pytest.raises(RuntimeError, match='through finish_transition'):
        model.update_pending(BOARD, 0, 1.)
