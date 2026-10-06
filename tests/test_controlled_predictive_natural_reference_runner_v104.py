"""V104 dispatch reuses old references and retains only newly executed suffixes."""
from concurrent.futures import Future
from copy import deepcopy
import gzip
import json
from pathlib import Path
import pytest
from scripts import run_controlled_predictive_natural_reference_v104 as m


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_natural_reference_runner_v104.checks.json'
    data = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    data['attempts'].append(dict(failed_tests=request.session.testsfailed-before,
        new_environment_transitions=0, new_model_prefix_transitions=0, new_model_fits=0,
        new_candidate_predictions=0, scope='Mock reference execution; real dispatch and artifact binding.'))
    path.write_text(json.dumps(data, indent=2) + '\n')


def retained(episode):
    return dict(id=f'life_9_reward_{episode}', life=9, query='reward', episode=episode,
        board=[0] * 16, step=3, source_seed=10390900 + episode,
        reference_origin='inherited' if episode < 2 else 'new',
        inherited_reference={'keep': episode} if episode < 2 else None,
        predictions={'fixed': episode}, natural={'fixed': episode})


def test_inherited_reference_cannot_reach_sampler(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'sample_root', lambda *a, **kw: pytest.fail('inherited root sampled'))
    with pytest.raises(ValueError, match='only roots without'):
        m.reference_job(retained(0), tmp_path, {})
    assert not (tmp_path / 'references').exists()


def test_new_suffix_uses_original_namespace_and_saves_both_blocks(tmp_path, monkeypatch):
    calls = []
    rule = object()
    monkeypatch.setattr(m.LearnedDynamics, 'from_payload', lambda _: rule)
    raw = [dict(option='H2', replica=i, game=dict(status='LOST')) for i in (0, 31)]
    log = dict(trajectories=2, censored_root=False, ground_work=dict(sampled_transitions=17))
    def sample(root, actual_rule, life, **kwargs):
        calls.append((deepcopy(root), life, kwargs))
        assert actual_rule is rule
        return [], raw, log
    monkeypatch.setattr(m, 'sample_root', sample)
    monkeypatch.setattr(m, 'audit_reference', lambda root, rows, actual_log, **kw:
        {'same_log': actual_log is log and rows is raw and kw == dict(replicas=32, life_base=103000)})
    item = retained(2)
    result = m.reference_job(item, tmp_path, {})
    assert calls[0][1:] == (103009, dict(replicas=32, max_steps=2000))
    assert set(calls[0][0]) == {'life', 'query', 'episode', 'board', 'step', 'source_seed'}
    folder = tmp_path / 'references' / item['id']
    with gzip.open(folder / 'games.jsonl.gz', 'rt') as handle:
        rows = [json.loads(line) for line in handle]
    assert [row['block'] for row in rows] == ['A', 'B']
    assert all(row['root_id'] == item['id'] for row in rows)
    assert json.loads((folder / 'reference.json').read_text()) == result
    assert result['log'] == log
    with pytest.raises(FileExistsError):
        m.reference_job(item, tmp_path, {})
    assert len(calls) == 1


def test_main_dispatches_only_missing_roots_and_preserves_source_settings(tmp_path, monkeypatch):
    source = tmp_path / 'source'; source.mkdir()
    settings = dict(methods=['H2_ONLY', 'frozen'], contrasts=[['frozen', 'H2_ONLY']],
        queries={'reward': {}}, lifecycles=[9], validation_roots_per_query=2)
    (source / 'run.json').write_text(json.dumps(dict(settings=settings)))
    (source / 'supplied_dynamics.json').write_text('{}')
    roots = [retained(i) for i in range(8)]
    frozen = deepcopy(roots)
    monkeypatch.setattr(m, 'SOURCE', source)
    monkeypatch.setattr(m, 'snapshot', lambda p: None)
    monkeypatch.setattr(m, 'load_cohort', lambda *args: (roots, dict(counts=dict(retained_prediction_events=8))))
    calls = []
    def reference(root, directory, payload):
        calls.append(root['episode'])
        return dict(root_id=root['id'], checks={'valid': True}, log=dict(censored_root=False,
            trajectories=160, ground_work=dict(sampled_transitions=17)))
    monkeypatch.setattr(m, 'reference_job', reference)
    class Pool:
        def __init__(self, max_workers):
            assert max_workers == 4
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def submit(self, function, *args):
            future = Future(); future.set_result(function(*args)); return future
    monkeypatch.setattr(m, 'ProcessPoolExecutor', Pool)
    output = tmp_path / 'output'
    m.run(output)
    result = json.loads((output / 'run.json').read_text())
    assert calls == list(range(2, 8)) and result['status'] == 'complete'
    assert roots == frozen and result['cohort']['roots'] == frozen
    assert len(result['references']) == 6
    assert result['settings']['methods'] == settings['methods']
    assert result['settings']['contrasts'] == settings['contrasts']
    assert result['settings']['validation_roots_per_query'] == 8
    assert result['settings']['reference_life_base'] == 103000
