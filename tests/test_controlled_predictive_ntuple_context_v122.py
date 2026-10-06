"""Synthetic checks for causal routing, bank persistence, and eval isolation."""
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_ntuple_context_v122 import ContextValueBank
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import (
    LearnedDynamics, RewriteProgram)

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'reports/controlled_predictive_ntuple_context_v122_build'
SOURCES, BANKS, RESTORED, EVALUATIONS = [], [], [], []
INITIAL = [2]*26 + [1]*230
OLD_BLOCK = [2]*6 + [1]*58
BOARD = (1, 1, 0, 0) + (0,)*12
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT / 'reports/controlled_predictive_ntuple_context_v122.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    work, setup = Counter(), Counter()
    models = {id(model): model for model in SOURCES + RESTORED
        + [model for bank in BANKS + EVALUATIONS for model in bank.banks.values()]}
    for model in models.values():
        work.update(model.counts)
        setup.update(model.setup_counts)
    payload['attempts'].append(dict(tests=5, failures=request.session.testsfailed-before,
        native_model_work=dict(work), setup_work=dict(setup),
        bank_work=dict(sum((bank.counts for bank in BANKS), Counter())),
        evaluation_work=dict(sum((bank.counts for bank in EVALUATIONS), Counter())),
        source_rank_initialization_work=dict(sum((Counter(bank.initial_router_payload['counts'])
            for bank in BANKS), Counter())),
        setup_seconds=sum(model.setup_seconds for model in models.values()),
        newly_sampled_environment_transitions=0,
        optimizer_steps=work['td_updates'],
        scope='Synthetic ranks and boards only; no environment samples. Native-model and bank work overlap; do not sum.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def bank():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    SOURCES.append(source)
    source.weights[:] = (np.arange(source.weights.size).reshape(source.weights.shape) % 7)*.000125
    result = ContextValueBank(source, INITIAL, BUILD)
    BANKS.append(result)
    return result


def feed(model, ranks):
    events = []
    for rank in ranks:
        event = model.observe(rank)
        if event is not None:
            events.append(event)
    return events


def test_source_context_is_exact_warmup_without_new_rank_work():
    model = bank()
    payload = model.to_payload()
    assert payload['router']['observations_seen'] == 256
    assert payload['router']['pending'] == dict(n=0, fours=0)
    assert payload['router']['modules'] == [dict(id=0, alpha=27, beta=231, visits=1)]
    assert model.counts == Counter()
    assert model.setup_counts == Counter()
    assert payload['banks'][0]['kind'] == 'source'
    with pytest.raises(ValueError, match='exactly 256'):
        ContextValueBank(model.banks[0], INITIAL[:-1], BUILD)


def test_routing_waits_for_full_block_then_clones_and_preserves_inactive_weights():
    model = bank()
    old_weights = model.banks[0].weights.copy()
    old_choice = model.choose(BOARD, QUERY)
    assert old_choice['bank_id'] == 0
    assert not feed(model, [2]*63)
    assert model.active_bank_id == 0 and len(model.banks) == 1
    event = model.observe(2)
    assert event['kind'] == 'created' and model.active_bank_id == 1
    assert event['obs_index'] == 320
    np.testing.assert_array_equal(model.banks[1].weights, old_weights)
    assert not np.shares_memory(model.banks[0].weights, model.banks[1].weights)
    assert model.counts['bank_copied_bytes'] == old_weights.nbytes
    assert model.setup_counts['allocated_weight_parameters'] == old_weights.size
    new_choice = model.choose(BOARD, QUERY)
    assert new_choice['bank_id'] == 1
    assert new_choice['action_values'] == old_choice['action_values']
    assert model.update_pending(new_choice['afterstate'], 1, new_choice['value'] + 1.)
    changed_weights = model.banks[1].weights.copy()
    assert not np.array_equal(changed_weights, old_weights)
    np.testing.assert_array_equal(model.banks[0].weights, old_weights)
    events = feed(model, OLD_BLOCK)
    assert events[-1]['kind'] == 'reactivated' and model.active_bank_id == 0
    np.testing.assert_array_equal(model.banks[0].weights, old_weights)
    np.testing.assert_array_equal(model.banks[1].weights, changed_weights)
    assert model.choose(BOARD, QUERY)['action_values'] == old_choice['action_values']
    assert model.counts['router_module_creations'] == 1
    assert model.counts['router_module_reactivations'] == 1


def test_pending_targets_never_cross_route_switch_including_loss_target():
    model = bank()
    choice = model.choose(BOARD, QUERY)
    before = model.banks[0].weights.copy()
    feed(model, [2]*64)
    assert not model.update_pending(choice['afterstate'], choice['bank_id'], 10.)
    assert not model.update_pending(choice['afterstate'], choice['bank_id'], -4.)
    assert model.updates == 0
    assert model.counts['cross_context_update_skips'] == 2
    np.testing.assert_array_equal(model.banks[0].weights, before)
    np.testing.assert_array_equal(model.banks[1].weights, before)
    assert model.update_pending(choice['afterstate'], 1, 3.)
    assert model.updates == 1 and model.counts['td_updates'] == 1
    np.testing.assert_array_equal(model.banks[0].weights, before)


def test_evaluation_routing_is_local_and_all_shared_weights_are_readonly():
    model = bank()
    trained_choice = model.choose(BOARD, QUERY)
    assert model.update_pending(trained_choice['afterstate'], 0, 2.)
    before, payload = model.banks[0].weights.copy(), model.to_payload()
    evaluation = model.evaluation_copy()
    EVALUATIONS.append(evaluation)
    assert np.shares_memory(evaluation.banks[0].weights, model.banks[0].weights)
    assert evaluation.banks[0].counts == Counter()
    assert evaluation.choose(BOARD, QUERY)['bank_id'] == 0
    feed(evaluation, [2]*64)
    assert evaluation.active_bank_id == 1 and len(evaluation.banks) == 2
    assert evaluation.choose(BOARD, QUERY)['bank_id'] == 1
    assert np.shares_memory(evaluation.banks[1].weights, model.banks[0].weights)
    assert evaluation.counts['bank_weight_copies'] == 0
    assert evaluation.counts['evaluation_weight_views'] == 2
    with pytest.raises(ValueError, match='read-only'):
        evaluation.banks[1].weights[0, 0] = 1.
    with pytest.raises(RuntimeError, match='cannot update'):
        evaluation.update_pending(BOARD, 1, 2.)
    assert model.to_payload() == payload
    np.testing.assert_array_equal(model.banks[0].weights, before)
    assert model.banks[0].weights.flags.writeable
    assert model.evaluation_copy().active_bank_id == 0


def test_saved_banks_and_router_restore_exact_values_and_parent_update_origin():
    model = bank()
    choice = model.choose(BOARD, QUERY)
    model.update_pending(choice['afterstate'], 0, 2.)
    feed(model, [2]*64)
    assert model.origins[1]['updates_at_creation'] == 1
    assert model.origins[1]['parent_bank_id'] == 0
    assert model.banks[1].updates == 1 and model.updates == 1
    model.update_pending(choice['afterstate'], 1, 3.)
    manifest = model.save(BUILD / 'roundtrip')
    json.dumps(manifest)
    assert manifest['updates'] == 2
    assert len(manifest['model_files']) == 2
    assert model.counts['checkpoint_saves'] == 2
    router = SpawnMemory.from_payload(manifest['router'])
    assert router.to_payload() == model.router.to_payload()
    for row in manifest['model_files']:
        restored = NtupleValue.load(row['path'], model.rule, BUILD)
        restored.counts = Counter(checkpoint_loads=1,
            checkpoint_loaded_parameters=row['nonzero_weights'])
        RESTORED.append(restored)
        original = model.banks[row['bank_id']]
        np.testing.assert_array_equal(restored.weights, original.weights)
        assert restored.updates == original.updates
        assert restored.choose(BOARD, QUERY)['action_values'] == original.choose(BOARD, QUERY)['action_values']
