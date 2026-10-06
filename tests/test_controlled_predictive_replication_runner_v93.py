"""Fresh training streams and incremental equal-budget deployment wiring."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('replication_runner_v93',
    ROOT / 'scripts/run_controlled_predictive_replication_v93.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_fresh_sources_incremental_budget_and_both_frozen_selectors(monkeypatch, tmp_path):
    acquired, learned, funded, evaluated = [], [], [], []

    class Selector:
        def __init__(self, checkpoint):
            self.checkpoint = checkpoint

        def to_payload(self):
            return {'checkpoint': self.checkpoint}

        @classmethod
        def from_payload(cls, value):
            return cls(value['checkpoint'])

        @classmethod
        def fit(cls, rows, checkpoint):
            assert [row['episode'] for row in rows[::4]] == ([5] if checkpoint == 6 else [5, 11])
            return cls(checkpoint), {'counts': {'tree_fits': 0}}

    def acquire(life, previous, checkpoint, rule, folder):
        acquired.append((life, previous, checkpoint))
        return [], {'work': {'sampled_transitions': checkpoint}}, {'work': {'sampled_transitions': 10 * checkpoint}}

    def load(folder):
        episode = int(folder.name.split('_')[-1]) - 1
        root = dict(episode=episode, query='reward', board=[episode] * 16, censored=False,
            prefixes={}, mc_rows=[dict(episode=episode, query='reward', board=[episode] * 16,
                option=option, target=[0, 0, 0]) for option in MODULE.OPTIONS[1:]])
        return [root], [{'episode': episode}], {}

    def prefixes(roots, rule, life, folder):
        assert len(roots) == 1
        return {MODULE.root_key(root): root['episode'] for root in roots}, {
            'ground_work': {'sampled_transitions': 100 * (roots[0]['episode'] + 1)}}

    def learn(roots, unary, paired, pools, checkpoint):
        learned.append((checkpoint, [root['episode'] for root in roots], sorted(pools.values())))
        assert unary == paired == [{'episode': root['episode']} for root in roots]
        selectors = {name: Selector(checkpoint) for name in ('MC', 'PAIR_ONLY', 'CORRECTED', 'V91_DECOMPOSED')}
        return selectors, {'full': Selector(checkpoint)}, {'full': Selector(checkpoint)}, {}, {}

    def extra(roots, rule, life, checkpoint, budget, emit):
        funded.append((checkpoint, budget, [root['episode'] for root in roots]))
        return [], {'ground_work': {'sampled_transitions': budget}}

    def evaluate(life, checkpoint, folder, deployed, rule):
        evaluated.append({name: model.checkpoint if model else None for name, model in deployed.items()})
        return {'methods': {}}

    for name, value in (('acquire_batch', acquire), ('load_unary', load), ('load_paired', load),
            ('acquire_prefix_batch', prefixes), ('learn', learn), ('acquire_extra', extra),
            ('evaluate_checkpoint', evaluate), ('JointSelector', Selector)):
        monkeypatch.setattr(MODULE, name, value)
    monkeypatch.setattr(MODULE, 'LearnedDynamics', SimpleNamespace(from_payload=lambda value: None))
    result = MODULE.lifecycle_run(3, tmp_path, {})
    assert acquired == [(9303, 0, 6), (9303, 6, 12)]
    assert learned == [(6, [5], [5]), (12, [5, 11], [5, 11])]
    assert funded == [(6, 600, [5]), (12, 1200, [11])]
    assert evaluated[-1] == dict(H2_ONLY=None, MC=12, PAIR_ONLY=12, CORRECTED=12,
        V91_DECOMPOSED=12, MC_EXTRA=12, CORRECTED_FROZEN_6=6, MC_EXTRA_FROZEN_6=6)
    costs = result['checkpoints'][-1]['method_acquisition']
    assert costs['CORRECTED']['total_training_transitions'] == costs['MC_EXTRA']['total_training_transitions'] == 1998
    assert costs['MC']['total_training_transitions'] == costs['V91_DECOMPOSED']['total_training_transitions'] == 198
    assert costs['CORRECTED_FROZEN_6']['total_training_transitions'] == costs['MC_EXTRA_FROZEN_6']['total_training_transitions'] == 666
    assert costs['H2_ONLY']['total_training_transitions'] == 0


def test_natural_and_prefix_seeds_are_fresh_but_paired_across_methods(monkeypatch):
    observed = []

    class Controller:
        def __init__(self, selector, query, rule, rng, mode):
            self.work, self.events = {}, []
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
    for checkpoint, method in ((6, 'CORRECTED'), (12, 'CORRECTED'), (12, 'MC_EXTRA')):
        MODULE.evaluate_game(method, SimpleNamespace(checkpoint=checkpoint), None, 3,
                             checkpoint, 0, 'reward')
    assert observed[0][0] == 9450300
    assert observed[1][0] == 9510300
    assert observed[1] == observed[2] and observed[0][1] != observed[1][1]
    assert MODULE.prefix_seed(dict(query='risk_goal', episode=11), 3) == 193031011000
