"""Real FIRST/kernel wiring with eight groups; synthetic eval is serialization-only."""
import json
from pathlib import Path

import numpy as np

from acfqp.science import query_supervision_run_v319 as runner
from acfqp.science.query_facts_v319 import iter_query_lifecycles
from acfqp.science.natural_model_revision_v281 import load_leaf

ROOT = Path(__file__).resolve().parents[1]


def test_real_first_four_stages_group_files_and_private_lineage(monkeypatch):
    # A wrong preboard, head wiring, RNG pairing, quota or JSON shape blocks formal acquisition.
    out = ROOT/'reports/query_supervision_v319/test_logs/driver_fixture'
    runtime = out/'runtime'; runtime.mkdir(parents=True, exist_ok=True)
    prior = json.loads((ROOT/'reports/greedy_targets_v317/summary.json').read_text())
    source = prior['source_provenance']['parents'][0]
    reader = iter_query_lifecycles(prior, 0)
    life, datasets, extraction = next(reader); reader.close()
    template, setup = load_leaf(source, runtime)
    evaluations = []

    def evaluate(leaf, identity, task, belief, runtime, engine, version=None):
        assert identity == 0 and not leaf.weights.flags.writeable if version is None else not leaf.reward_weights.flags.writeable
        evaluations.append((task, version))
        return dict(game_summaries=[dict(seed=runner.evaluation_seed(identity,task,i),
            status='LOST', utility=0.) for i in range(32)], estimated_p_four=belief['estimated_p_four'],
            counts={'environment':{}}, cpu_seconds=0., head_version=version)

    monkeypatch.setattr(runner, 'GROUPS', 8)
    monkeypatch.setattr(runner, '_evaluate', evaluate)
    result = runner._run_life(template, source, life, datasets, extraction, runtime, out, None)
    restored = json.loads((out/'lifecycle_receipts/life_0.json').read_text())
    assert restored == result and len(evaluations) == 12
    for task in runner.TASKS:
        original = life['initial'][task]['head_versions']['FIRST_LOCAL']
        assert result['initial'][task]['head_version'] == original
        previous = {a:original for a in runner.UPDATING_ARMS}
        for number in ('1','2'):
            stage = result['rounds'][number][task]
            assert stage['teacher_unchanged'] and stage['teacher_version'] == original
            assert stage['inactive_head_versions_before'] == stage['inactive_head_versions_after']
            ranks = []
            for arm in runner.UPDATING_ARMS:
                item = stage['arms'][arm]
                assert item['head_version']['base_file'] == previous[arm]['file']
                assert item['updates_after']-item['updates_before'] == 8
                assert item['fit']['learning_counts']['rootgroup_updates'] == 8
                assert item['supervision']['counts']['supervision_start_spawns'] == 32
                assert item['supervision']['teacher_updates'] == original['updates']
                artifact = item['supervision']['group_artifact']
                with np.load(artifact['file'], allow_pickle=False) as saved:
                    assert saved['roots'].shape == (8,16) and saved['targetreward'].shape == (8,4)
                    assert np.array_equal(saved['mean_reward'],saved['targetreward'].mean(axis=1))
                    assert np.array_equal(saved['mean_win'],saved['targetwin'].mean(axis=1))
                    ranks.append(saved['spawn_ranks'].copy())
                previous[arm] = item['head_version']
            assert np.array_equal(*ranks)
    accounting = runner.accounting(prior, [result], [dict(cpu_seconds=1.,compiler_cpu_seconds=0.)], 0., 1.)
    assert accounting['new_training_raw_tiles'] == 256
    assert accounting['new_evaluation_games'] == 384
    assert accounting['group_files'] == accounting['new_head_files'] == 8
    assert accounting['census_files'] == 4
    for arm in runner.UPDATING_ARMS:
        assert accounting['per_arm'][arm]['new_training_raw_tiles'] == 128
        assert accounting['per_arm'][arm]['rootgroups'] == 32
    json.dumps(accounting, allow_nan=False)
