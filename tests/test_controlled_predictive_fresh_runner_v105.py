"""Fresh acquisition binding, complete natural cohort and frozen reference dispatch."""
from concurrent.futures import Future
from copy import deepcopy
import gzip
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from scripts import run_controlled_predictive_fresh_ranking_v105 as m


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_fresh_runner_v105.checks.json'
    data = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    data['attempts'].append(dict(failed_tests=request.session.testsfailed-before,
        new_environment_transitions=0, new_model_transitions=0, new_neural_model_fits=0,
        new_candidate_predictions=0, scope='Mock acquisition/fits/games; actual cumulative binding, cohort and dispatch logic.'))
    path.write_text(json.dumps(data, indent=2) + '\n')


def test_fresh_incremental_data_fits_both_widths_and_deploys_original_ages(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'BUDGETS', (20, 40))
    monkeypatch.setattr(m.LearnedDynamics, 'from_payload', lambda _: None)
    calls, fits = [], []
    def acquire(life, replicas, rule, budget, cursor, folder):
        calls.append((life, replicas, budget, cursor))
        return [], cursor + 2, dict(used_transitions=budget, episode_cutoff=cursor + 2, start_cursor=cursor)
    def load(acq, folder, rule, life):
        return [dict(query=q, episode=acq['start_cursor']) for q in m.QUERIES], {}
    def fit(records, cutoff, hidden):
        fits.append((len(records), cutoff, hidden))
        row = dict(checkpoint=cutoff, family='UNIFORM_SHRINK', hidden=hidden, n=len(records))
        return SimpleNamespace(to_payload=lambda: row), dict(counts=dict(neural_model_fits=1),
            models={'UNIFORM_SHRINK': dict(final_loss=.1)})
    monkeypatch.setattr(m, 'acquire_batch', acquire)
    monkeypatch.setattr(m, 'load_batch', load)
    monkeypatch.setattr(m, 'fit_model', fit)
    allocation = m.construct_history(11, tmp_path, {})
    assert calls == [(11, 4, 20, 0), (11, 4, 20, 2)]
    assert fits == [(2, 2, 4), (2, 2, 16), (4, 4, 4), (4, 4, 16)]
    assert allocation['new_neural_model_fits'] == 4
    assert allocation['new_training_environment_transitions'] == 40
    assert allocation['inherited_training_environment_transitions'] == 0
    monkeypatch.setattr(m.CandidateModel, 'from_payload', lambda row: SimpleNamespace(**row, to_payload=lambda: row))
    def evaluate(life, budget, folder, deployed, rule):
        for name in m.METHODS[2:]:
            assert deployed[name].n == (2 if name.endswith('_FROZEN_HALF') else 4)
            assert deployed[name].hidden == (4 if '_H4_' in name else 16)
        return {}, [], []
    monkeypatch.setattr(m, 'evaluate_checkpoint', evaluate)
    result, roots = m.evaluate_history(11, tmp_path, {}, allocation)
    assert result['evaluation']['model_metadata'] == allocation['model_metadata'] and roots == []
    assert result['evaluation']['validation'] == dict(roots=[], missing_roots=[], new_selector_calls=0, new_model_transitions=0, seconds=0.)


def test_all_natural_query_roots_retain_actual_events(tmp_path, monkeypatch):
    def game(method, selector, rule, life, checkpoint, replica, query, max_steps):
        event = dict(option='H2', predictions={option: dict(value=0.) for option in m.OPTIONS})
        row = dict(seed=10591100+replica, score=0, selected_option='H2', initiation_step=0,
            committed_length_matches=True, controller_events=1, planning_counts={'model_uniform_draws':4}, steps=1,
            candidate_evaluation={'wiring': {'valid':True}})
        raw = dict(method=method, episode={'steps':[dict(board=[2]*16, action=0, next_board=[4]*16)]},
            controller_events=[] if method == 'H2_ONLY' else [event], model_prefixes=[])
        return row, raw
    monkeypatch.setattr(m, 'evaluate_game', game)
    evaluation, roots, missing = m.evaluate_checkpoint(11, 512000, tmp_path, dict.fromkeys(m.METHODS), None)
    assert not missing and len(roots) == 16
    assert {(r['query'], r['episode']) for r in roots} == {(q,i) for q in m.QUERIES for i in range(8)}
    assert all(set(r['predictions']) == set(m.METHODS[1:]) for r in roots)
    assert all(evaluation['wiring'].values())


def test_reference_retains_frozen_event_and_correct_namespace(tmp_path, monkeypatch):
    item = dict(life=11, query='reward', episode=7, board=[2]*16, step=3, source_seed=10591107,
        predictions={'fixed':{'option':'SPACE_1'}})
    frozen = deepcopy(item)
    raw = [dict(option='H2', replica=i, game={'status':'LOST'}) for i in (0,31)]
    log = dict(censored_root=False, pair_deltas={}, ground_work={'sampled_transitions':17})
    monkeypatch.setattr(m.LearnedDynamics, 'from_payload', lambda _: None)
    def sample(root, rule, life, replicas):
        assert 'predictions' not in root and root['episode'] == 7 and life == 105011 and replicas == 32
        return [], raw, log
    monkeypatch.setattr(m, 'sample_root', sample)
    monkeypatch.setattr(m, 'audit_reference', lambda root, rows, actual, **kw:
        {'verified': actual is log and rows is raw and kw == dict(replicas=32, life_base=105000)})
    result = m.reference_job(item, tmp_path, {})
    assert item == frozen and result['predictions'] == item['predictions'] and result['reference_complete']
    folder = tmp_path / 'life_11/evaluation/references/reward_7'
    with gzip.open(folder / 'games.jsonl.gz', 'rt') as handle:
        assert [json.loads(line)['block'] for line in handle] == ['A','B']
    with pytest.raises(FileExistsError):
        m.reference_job(item, tmp_path, {})


def test_references_start_only_after_all_natural_decisions_are_saved(tmp_path, monkeypatch):
    source = tmp_path / 'source'; source.mkdir()
    (source / 'supplied_dynamics.json').write_text('{}')
    monkeypatch.setattr(m, 'SOURCE', source)
    monkeypatch.setattr(m, 'snapshot', lambda _: None)
    monkeypatch.setattr(m, 'construct_history', lambda *args: {})
    natural, references = [], []
    def evaluate(life, directory, payload, allocation):
        (directory / f'life_{life}').mkdir()
        natural.append(life)
        roots = [dict(life=life, query=q, episode=i) for q in m.QUERIES for i in range(8)]
        return dict(id=life, evaluation={'validation':{'roots':[], 'missing_roots':[], 'seconds':0.}}), roots
    def reference(root, directory, payload):
        assert set(natural) == set(m.LIFECYCLES)
        assert len(json.loads((directory / 'validation_cohort.json').read_text())['roots']) == 64
        references.append(root)
        return dict(root=root, reference_complete=True, seconds=2., terminal_log={'ground_work':{'sampled_transitions':17}})
    monkeypatch.setattr(m, 'evaluate_history', evaluate)
    monkeypatch.setattr(m, 'reference_job', reference)
    class Pool:
        def __init__(self, max_workers):
            assert max_workers == 4
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def submit(self, fn, *args):
            future = Future(); future.set_result(fn(*args)); return future
    monkeypatch.setattr(m, 'ProcessPoolExecutor', Pool)
    output = tmp_path / 'output'
    m.run(output)
    report = json.loads((output / 'run.json').read_text())
    assert report['status'] == 'complete' and len(references) == 64
    assert all(len(life['evaluation']['validation']['roots']) == 16 and life['evaluation']['validation']['seconds'] == 32. for life in report['lifecycles'])
