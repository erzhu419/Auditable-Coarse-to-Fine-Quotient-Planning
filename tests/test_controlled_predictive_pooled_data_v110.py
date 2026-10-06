"""Source-history exclusion and true acquisition-batch membership are binding."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_pooled_data_v110 as module

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_pooled_data_v110.checks.json'
    log = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    log['attempts'].append(dict(failures=request.session.testsfailed - before,
        fixture_work=dict(WORK), new_environment_transitions=0, new_synthetic_transitions=0,
        neural_model_fits=0, neural_candidate_predictions=0, new_feature_vectors=0,
        actual_source_files_read=0,
        scope='synthetic records and mocked original loader; no production bank reads'))
    path.write_text(json.dumps(log, indent=2) + '\n')


def rows():
    # First batch ends after episode 5 reward; the second adds episode 5 risk.
    return [dict(query=query, episode=episode, features=[[index]])
        for index, (episode, query) in enumerate(
            [(0, 'reward'), (4, 'risk_goal'), (5, 'reward'), (5, 'risk_goal'), (6, 'reward')])]


@pytest.fixture
def mocked_bank(monkeypatch):
    originals = {life: rows() for life in (11, 12, 13, 14)}
    calls = []
    def loader(source, life, allocation):
        assert source == 'fixture-source' and allocation == {'life': life}
        calls.append(life)
        WORK['mock_source_loader_calls'] += 1
        WORK['mock_records_returned'] += len(originals[life])
        return originals[life], {'ignored_parameters': [life]}, dict(life=life,
            half_cutoff=6, full_cutoff=7, stage_rosters=[{'records': 3}, {'records': 2}],
            counts=dict(record_files_read=2, records_read=5, half_payload_files_read=2,
                files_read=4, normalization_recomputations=1, conflict_mass_recomputations=1,
                new_environment_transitions=0, new_synthetic_transitions=0,
                neural_model_fits=0, neural_candidate_predictions=0, new_feature_vectors=0,
                model_prefix_trajectories=0), checks={'original_roster_bound': True}, seconds=0.)
    monkeypatch.setattr(module, 'load_training', loader)
    bank, log = module.load_bank('fixture-source', [{'life': life} for life in (14, 12, 11, 13)])
    return bank, log, originals, calls


def test_half_membership_uses_actual_batch_not_episode_cutoff(mocked_bank):
    bank, log, originals, _ = mocked_bank
    assert [record['is_half'] for record in bank[11]] == [True, True, True, False, False]
    assert bank[11][3]['episode'] < log['histories'][0]['half_cutoff']
    assert all('is_half' not in record and 'source_life' not in record for record in originals[11])
    bank[11][0]['features'][0][0] = -99
    assert originals[11][0]['features'] == [[0]]


def test_source_identity_preserves_matching_query_episodes_in_different_histories(mocked_bank):
    bank, _, _, _ = mocked_bank
    records, log = module.pool_fold(bank, 13)
    assert log['source_lives'] == [11, 12, 14] and len(records) == 15
    assert log['half']['training_roster'] == [
        [11, 'reward', 0], [11, 'reward', 5], [12, 'reward', 0],
        [12, 'reward', 5], [14, 'reward', 0], [14, 'reward', 5]]
    assert log['full']['training_roster'][:4] == [
        [11, 'reward', 0], [11, 'reward', 5], [11, 'risk_goal', 5], [11, 'reward', 6]]
    assert log['half']['heldout_roster'] == log['full']['heldout_roster'] == [
        [11, 'risk_goal', 4], [12, 'risk_goal', 4], [14, 'risk_goal', 4]]
    assert log['half']['records'] == 9 and log['full']['training_roots'] == 12


def test_target_history_contents_do_not_change_fold_data_or_rosters(mocked_bank):
    bank, _, _, _ = mocked_bank
    records, log = module.pool_fold(bank, 12)
    changed = deepcopy(bank)
    changed[12] = [{'target_only_content': 'must never be read'}]
    new_records, new_log = module.pool_fold(changed, 12)
    assert records == new_records
    assert {key: value for key, value in log.items() if key != 'seconds'} == {
        key: value for key, value in new_log.items() if key != 'seconds'}


def test_bank_is_read_once_and_reused_by_every_fold(mocked_bank):
    bank, log, _, calls = mocked_bank
    for target in bank:
        _, fold_log = module.pool_fold(bank, target)
        assert all(fold_log['checks'].values())
    assert calls == [11, 12, 13, 14]
    assert log['counts']['record_files_read'] == log['counts']['half_payload_files_read'] == 8
    assert log['counts']['records_read'] == 20 and log['counts']['half_records'] == 12
    assert log['counts']['histories_loaded'] == 4 and all(log['checks'].values())
    assert log['rosters']['11']['half']['training_roster'] == [[11, 'reward', 0], [11, 'reward', 5]]
    assert log['rosters']['11']['full']['training_roster'][2] == [11, 'risk_goal', 5]


def test_duplicate_source_query_episode_identity_is_rejected(mocked_bank):
    bank, _, _, _ = mocked_bank
    bank[11].append(deepcopy(bank[11][0]))
    with pytest.raises(ValueError, match='identities must be unique'):
        module.pool_fold(bank, 12)
