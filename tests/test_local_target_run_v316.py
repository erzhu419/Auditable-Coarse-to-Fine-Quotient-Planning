"""One real fresh chain catches reuse of V314 seeds, data or head versions."""
import gzip
import json

from acfqp.science import local_target_run_v316 as run
from acfqp.science.native_value_stream_v286 import NativeValueStream
from acfqp.science.natural_model_revision_v281 import load_leaf


def test_new_cohort_collects_fresh_facts_and_builds_its_own_bank_versions(monkeypatch):
    root = run.Path(run.__file__).resolve().parents[3]
    out = root / 'reports/local_targets_v316/runtime/tests/driver_life20'
    out.mkdir(parents=True, exist_ok=True)
    source_summary = json.loads((root / 'reports/fresh_source_v312/source_summary.json').read_text())
    source = source_summary['source_provenance']['parents'][0]
    life_id = 20
    monkeypatch.setattr(run, 'INITIAL_RAW', 8192)
    monkeypatch.setattr(run, 'ROUND_RAW', 8192)
    evaluation_seeds, physical_rows = [], []

    def static_evaluation(leaf, life, task, belief, runtime, engine, version=None):
        assert not leaf.weights.flags.writeable
        if version is not None:
            assert not leaf.risk_weights.flags.writeable
            assert version['updates'] == leaf.updates
        seeds = [run.evaluation_seed(life, task, episode) for episode in range(32)]
        expected = [316900000000 + life * 1000000 + (100000 if task == 'B' else 0) + episode
                    for episode in range(32)]
        assert seeds == expected
        evaluation_seeds.extend(seeds)
        return dict(game_summaries=[dict(seed=seed, score=0, steps=0, status='LOST', utility=-4.)
                                   for seed in seeds], estimated_p_four=belief['estimated_p_four'],
                    head_version=version, counts=dict(environment={}, planning={}), cpu_seconds=0., seconds=0.)

    monkeypatch.setattr(run, '_evaluate', static_evaluation)
    template, _ = load_leaf(source, out)
    engine = NativeValueStream(template, 316899999999, out)
    try:
        with gzip.open(out / 'trace.jsonl.gz', 'wt') as stream:
            def emit(row):
                stream.write(json.dumps(row, separators=(',', ':')) + '\n')
                if row['kind'] in ('WARMUP', 'CONFIRMATION', 'TRAIN'):
                    physical_rows.append(dict(kind=row['kind'], phase=row['phase'],
                        seed=row.get('summary', {}).get('seed'),
                        stream_seed=row['start']['stream_seed'] if row['kind'] == 'TRAIN' else None))
            life = run._run_lifecycle(template, source, life_id, out, out, engine, emit)
    finally:
        engine.close()

    assert life['initial_context_precondition_met']
    assert {row['context_id'] for row in life['initial'].values()} == {0, 1}
    assert len(evaluation_seeds) == 384
    assert physical_rows
    seen_seeds = set(evaluation_seeds)
    for task_index, task in enumerate(run.TASKS):
        initial = life['initial'][task]
        warmup = initial['acquisition']['warmup']['game_summaries']
        assert [game['seed'] for game in warmup] == [
            316100000000 + task_index * 100000 + life_id * 1000000 + episode
            for episode in range(len(warmup))]
        seen_seeds.update(game['seed'] for game in warmup)
        training = initial['acquisition']['training']
        initial_seed = 316200000000 + task_index * 100000 + life_id * 10000000
        assert training['before_stream']['stream_seed'] == initial_seed
        assert training['before_stream']['raw_tiles'] == 0 and training['raw_tiles'] == 8192
        assert {row['stream_seed'] for row in physical_rows if row['kind'] == 'TRAIN' and row['phase'] == task + '0'} == {initial_seed}
        seen_seeds.add(initial_seed)
        first = initial['head_versions']['FIRST_LOCAL']
        assert first['base_file'] is None and first['lifecycle'] == life_id
        assert first['source_checkpoint'] == source['checkpoint']
        for round_index in (1, 2):
            batch = life['rounds'][str(round_index)][task]
            collector = batch['collectors']['FIXED_FIRST']
            expected_seed = 316500000000 + life_id * 10000000 + task_index * 1000000 + round_index * 100000
            assert collector['acquisition']['training']['before_stream']['stream_seed'] == expected_seed
            assert collector['acquisition']['training']['before_stream']['raw_tiles'] == 0
            assert collector['actor_version'] == first
            assert {row['stream_seed'] for row in physical_rows if row['kind'] == 'TRAIN' and row['phase'] == f'{task}_R{round_index}'} == {expected_seed}
            seen_seeds.add(expected_seed)
            for arm in run.UPDATING_ARMS:
                receipt = batch['arms'][arm]['head_version']
                previous = first if round_index == 1 else life['rounds']['1'][task]['arms'][arm]['head_version']
                assert receipt['base_file'] == previous['file']
                assert receipt['lifecycle'] == life_id and receipt['context_id'] == initial['context_id']
                assert run.Path(receipt['file']).resolve().is_relative_to(out.resolve())
                if arm == 'TD_LOCAL':
                    fit = batch['arms'][arm]['fit']
                    assert fit['bootstrap_version'] == previous
                    assert run.Path(fit['target_artifact']['file']).resolve().is_relative_to(out.resolve())
        assert run.Path(first['file']).resolve().is_relative_to(out.resolve())
    # All supported V314 warmup, initial, collection and evaluation seeds are below
    # 315e9, while every actual new stream/game receipt in this fixture is above it.
    assert min(seen_seeds) > 315000000000
