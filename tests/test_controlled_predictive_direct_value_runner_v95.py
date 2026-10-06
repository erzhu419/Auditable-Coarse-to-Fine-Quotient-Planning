"""Fixed knowledge, independent simulation seeds and unrecomputed validation decisions."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('direct_runner_v95', ROOT / 'scripts/run_controlled_predictive_direct_value_v95.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_loads_current_and_frozen_knowledge_without_fitting(monkeypatch, tmp_path):
    class Model:
        @classmethod
        def from_payload(cls, payload):
            return SimpleNamespace(**payload)

    source, stage = tmp_path / 'source', tmp_path / 'stage'
    stage.mkdir()
    prior = []
    for checkpoint in (6, 12):
        directory = source / 'life_3' / f'checkpoint_{checkpoint}'
        directory.mkdir(parents=True)
        for family in M.VALUE_METHODS:
            for kind in ('full', 'selector'):
                M.save(directory / f'{family.lower()}_{kind}.json', dict(checkpoint=checkpoint,
                    excluded_fold=None, training_method=family))
        prior.append(dict(episodes=checkpoint, updates={'value': {'counts': {'tree_fits': 774}},
            'heads': {'counts': {'tree_fits': 4}}}, inherited_acquisition={
            'source': {'sampled_transitions': 10}, 'branches': {'sampled_transitions': 100}},
            method_acquisition={family: {'total_training_transitions': checkpoint * 10} for family in M.VALUE_METHODS}))
    M.save(source / 'life_3/run.json', {'checkpoints': prior})
    monkeypatch.setattr(M, 'SOURCE', source)
    monkeypatch.setattr(M, 'BellmanValue', Model)
    monkeypatch.setattr(M, 'JointSelector', Model)
    deployed, log = M.load_deployed(3, stage)
    assert set(deployed) == set(M.METHODS[12])
    for name, model in deployed.items():
        if model is not None:
            assert model.checkpoint == (6 if name.endswith('_FROZEN_6') else 12)
    assert log['historical_v94_tree_fits'] == 1556
    assert log['inherited_training'] == {'source': {'sampled_transitions': 20}, 'branches': {'sampled_transitions': 200}}
    assert len(list(stage.glob('*_model.json'))) == 8


def test_actor_and_candidate_streams_are_separate_and_model_age_independent(monkeypatch):
    natural, simulated = [], []

    class Direct:
        def __init__(self, value, rule, seed, replicas):
            self.checkpoint = value.checkpoint
            self.last_log, self.last_prefixes = None, []
            simulated.append((seed, replicas, self.checkpoint))

    class Controller:
        def __init__(self, selector, query, rule, rng, mode):
            self.work, self.events = {}, []
            self.fragment_actions = 0
            self.selected_option = self.initiation_step = None
            self.rng = rng

    def episode(seed, act, max_steps):
        controller = act.__closure__[0].cell_contents
        natural.append((seed, controller.rng.random()))
        return dict(return_score=0, status='CUTOFF', steps_count=0, final_board=[1] * 16,
                    seconds=0, work={}, steps=[])

    monkeypatch.setattr(M, 'DirectSelector', Direct)
    monkeypatch.setattr(M, 'FragmentController', Controller)
    monkeypatch.setattr(M.experience, 'run_episode', episode)
    for method, age in (('MC_TAIL', 12), ('FQE_DIRECT', 12), ('FQE_DIRECT_FROZEN_6', 6)):
        game, raw = M.evaluate_game(method, SimpleNamespace(checkpoint=age), None, 3, 12, 0, 'reward')
        assert game['candidate_evaluation'] is None and raw['model_prefixes'] == []
    assert natural[0] == natural[1] == natural[2]
    assert natural[0][0] == 9710300
    assert simulated == [(195030000000, 32, 12), (195030000000, 32, 6)]


def test_validation_preserves_original_deployed_predictions_and_full_cutoff_cost(monkeypatch, tmp_path):
    root = dict(board=[1] * 16, query='reward', episode=0, life=3, step=5,
                source_seed=9710300, predictions={'FQE_DIRECT': {'option': 'SPACE_4', 'value': .25}})
    expected = deepcopy(root['predictions'])
    calls = []

    def sample(record, rule, life, replicas):
        calls.append((life, replicas))
        root['predictions']['FQE_DIRECT']['value'] = .25
        return [], [{'game': {'status': 'CUTOFF'}}], dict(censored_root=True,
            ground_work={'sampled_transitions': 2000}, pair_deltas={})

    def forbid(*args, **kwargs):
        raise AssertionError('validation must reuse the deployed prediction')

    monkeypatch.setattr(M, 'sample_root', sample)
    monkeypatch.setattr(M, 'DirectSelector', forbid)
    result = M.validate_roots([root], [], tmp_path, None)
    record = result['roots'][0]
    assert calls == [(95003, 16)]
    assert record['predictions'] == expected
    assert not record['reference_complete'] and record['paired_reference'] == {}
    assert record['terminal_log']['ground_work']['sampled_transitions'] == 2000
    assert result['new_selector_calls'] == result['new_model_transitions'] == 0
