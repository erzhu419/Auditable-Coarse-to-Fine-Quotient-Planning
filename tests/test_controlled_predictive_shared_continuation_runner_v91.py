"""The runner accumulates history once and keeps early selectors frozen."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('continuation_runner_v91',
    ROOT / 'scripts/run_controlled_predictive_shared_continuation_v91.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_checkpoint_accumulation_frozen_models_and_inherited_cost(monkeypatch, tmp_path):
    fitted, evaluated, validated = [], [], []

    class Selector:
        def __init__(self, checkpoint):
            self.checkpoint = checkpoint

        @classmethod
        def fit(cls, rows, checkpoint):
            fitted.append((checkpoint, [row['episode'] for row in rows]))
            return cls(checkpoint), {'counts': {'tree_fits': 0}}

        def to_payload(self):
            return {'checkpoint': self.checkpoint}

        @classmethod
        def from_payload(cls, value):
            return cls(value['checkpoint'])

    def load(folder):
        checkpoint = int(folder.name.split('_')[-1])
        root = dict(episode=checkpoint - 1, censored=False,
            mc_rows=[{'episode': checkpoint - 1}])
        return [root], [{'episode': checkpoint - 1}], {'counts': {}}

    def decompose(roots, tails, checkpoint):
        assert [root['episode'] for root in roots] == [row['episode'] for row in tails]
        assert max(row['episode'] for row in tails) < checkpoint
        models = {name: Selector(checkpoint) for name in ('full', 'fold_0', 'fold_1')}
        return Selector(checkpoint), models, [], {'counts': {'tree_fits': 0}}

    def evaluate(life, checkpoint, folder, deployed, rule):
        evaluated.append((checkpoint, {name: model.checkpoint if model else None
                                      for name, model in deployed.items()}))
        return {'methods': {}}, [], []

    def validate(roots, missing, folder, rule, deployed, tail):
        validated.append(tail.checkpoint)
        return {'roots': []}

    monkeypatch.setattr(MODULE, 'load_batch', load)
    monkeypatch.setattr(MODULE, 'JointSelector', Selector)
    monkeypatch.setattr(MODULE, 'fit_decomposed', decompose)
    monkeypatch.setattr(MODULE, 'evaluate_checkpoint', evaluate)
    monkeypatch.setattr(MODULE, 'validate_roots', validate)
    monkeypatch.setattr(MODULE, 'LearnedDynamics', SimpleNamespace(from_payload=lambda payload: None))
    prior = {'checkpoints': [dict(episodes=cp,
        source=dict(work={'sampled_transitions': cp}, games=12),
        branches=dict(work={'sampled_transitions': cp * 10}, trajectories=480)) for cp in (6, 12)]}
    result = MODULE.lifecycle_run(0, tmp_path, {}, prior)
    assert fitted == [(6, [5]), (12, [5, 11])]
    assert evaluated == [(6, {'H2_ONLY': None, 'MC': 6, 'DECOMPOSED': 6}),
        (12, {'H2_ONLY': None, 'MC': 12, 'DECOMPOSED': 12,
              'MC_FROZEN_6': 6, 'DECOMPOSED_FROZEN_6': 6})]
    assert validated == [12]
    assert result['inherited'] == dict(source_work={'sampled_transitions': 18},
        branch_work={'sampled_transitions': 180}, source_games=24, branch_trajectories=960)


def test_new_natural_seed_uses_checkpoint_without_changing_execution_stream(monkeypatch):
    observed = []

    class Controller:
        def __init__(self, selector, query, rule, rng, mode):
            self.work = {}
            self.events = []
            self.fragment_actions = 0
            self.selected_option = self.initiation_step = None
            self.rng = rng

    def episode(seed, act, max_steps):
        controller = act.__closure__[0].cell_contents
        observed.append((seed, controller.rng.random()))
        return dict(return_score=0, status='CUTOFF', steps_count=0, final_board=[1] * 16,
            seconds=0, work={}, steps=[])

    monkeypatch.setattr(MODULE, 'FragmentController', Controller)
    monkeypatch.setattr(MODULE.experience, 'run_episode', episode)
    for checkpoint, method in ((6, 'MC'), (12, 'MC'), (12, 'DECOMPOSED')):
        MODULE.evaluate_game(method, SimpleNamespace(checkpoint=checkpoint), None, 2,
            checkpoint, 3, 'reward')
    assert observed[0][0] == 9250203
    assert observed[1][0] == 9310203
    assert observed[1] == observed[2]
    assert observed[0][1] != observed[1][1]
