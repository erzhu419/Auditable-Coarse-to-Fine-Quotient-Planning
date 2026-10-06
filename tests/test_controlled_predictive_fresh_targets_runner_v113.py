"""Freeze predictions before fresh reference dispatch and retain incomplete evidence."""
from concurrent.futures import Future
from copy import deepcopy
import json
from pathlib import Path
import pytest
from scripts import run_controlled_predictive_fresh_targets_v113 as m


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_fresh_targets_runner_v113.checks.json'
    result = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    result['attempts'].append(dict(failed_tests=request.session.testsfailed - before,
        newly_sampled_environment_transitions=0, new_model_prefix_transitions=0,
        neural_model_fits=0, optimizer_steps=0, neural_candidate_predictions=0,
        scope='Synchronous mock jobs; fixed prediction persistence and reference binding only.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


class InlinePool:
    def __init__(self, max_workers):
        assert max_workers == 4
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def submit(self, function, *args):
        future = Future()
        try:
            future.set_result(function(*args))
        except Exception as error:
            future.set_exception(error)
        return future


def install(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    source.mkdir()
    old = dict(status='complete', settings={'lifecycles': list(m.SOURCE_BUNDLES)}, models=[{'retained': 'model'}],
        inherited_folds=[{'retained': 'fold'}], selections=[{'retained': 'choice'}],
        inherited_work={'V111': {'fits': 8}}, selection_acquisition_accounting={'retained': 'learning_cost'})
    analysis = dict(primary_complete=True, actual_executed_work={'fits': 24}, inherited_cohort_extraction_work={'retained': 'extraction'})
    (source / 'run.json').write_text(json.dumps(old))
    (source / 'analysis.json').write_text(json.dumps(analysis))
    dynamics = tmp_path / 'dynamics.json'
    dynamics.write_text('{}')
    monkeypatch.setattr(m, 'SOURCE', source)
    monkeypatch.setattr(m, 'DYNAMICS_SOURCE', dynamics)
    monkeypatch.setattr(m, 'snapshot', lambda *args: None)
    monkeypatch.setattr(m, 'ProcessPoolExecutor', InlinePool)
    calls = dict(histories=[], scores=0, references=[])
    options = dict(censored=False, missing=False)
    def build(life, directory, payload):
        calls['histories'].append(life)
        roots = [dict(root_id=f'{life}_{q}_{e}', life=life, query=q, episode=e)
            for q in m.QUERIES for e in range(8)]
        missing = []
        if options['missing'] and life == 15:
            missing.append(roots.pop())
        return dict(life=life, roots=roots, missing_roots=missing, checks={'complete': True},
            source_log={'ground_work': {'sampled_transitions': 16}})
    def score(source_run, roots):
        calls['scores'] += 1
        assert source_run == old and all('reference_log' not in root for root in roots)
        if len(roots) != 64:
            raise ValueError('all 64 new target roots required')
        models = [dict(bundle_id=bundle, method=method) for bundle in m.SOURCE_BUNDLES for method in m.METHODS[1:5]]
        decisions = [dict(bundle_id=bundle, root_id=root['root_id'], method=method, event={'fixed': True})
            for bundle in m.SOURCE_BUNDLES for root in roots for method in m.METHODS[1:]]
        return models, decisions, dict(checks={'complete': True}, counts={'model_root_scores': 1024})
    def reference(root, directory, payload):
        saved = json.loads((directory / 'pre_reference_cohort.json').read_text())
        assert len(saved['roots']) == 64 and len(saved['decisions']) == 1536
        assert saved['frozen_selections'] == old['selections']
        assert all('reference_log' not in row for row in saved['roots'])
        calls['references'].append(root['root_id'])
        censored = options['censored'] and root['root_id'] == '15_reward_0'
        return dict(root_id=root['root_id'], life=root['life'], query=root['query'], episode=root['episode'],
            reference_log=dict(censored_root=censored, trajectories=160, ground_work={'sampled_transitions': 160}),
            reference_audit={'bound': True}, reference_complete=not censored, seconds=.1)
    monkeypatch.setattr(m, 'build_target_history', build)
    monkeypatch.setattr(m, 'score_frozen_models', score)
    monkeypatch.setattr(m, 'reference_job', reference)
    return old, calls, options


@pytest.mark.parametrize('censored', (False, True))
def test_all_choices_are_saved_before_any_reference_and_no_censor_retry(tmp_path, monkeypatch, censored):
    old, calls, options = install(tmp_path, monkeypatch)
    options['censored'] = censored
    out = tmp_path / 'out'
    m.run(out)
    result = json.loads((out / 'run.json').read_text())
    saved = json.loads((out / 'pre_reference_cohort.json').read_text())
    assert result['status'] == 'complete' and all(result['runner_checks'].values())
    assert calls['histories'] == list(m.TARGETS) and calls['scores'] == 1
    assert len(calls['references']) == len(set(calls['references'])) == result['cohort']['completed_references'] == 64
    assert result['frozen_selections'] == old['selections']
    assert saved['decisions'] == result['decisions'] and saved['models'] == result['models']
    assert sum(not root['reference_complete'] for root in result['cohort']['roots']) == int(censored)
    assert result['inherited_work'] == {'V111': {'fits': 8}, 'V112': {'fits': 24}}


def test_missing_trigger_is_not_replaced_and_blocks_reference_sampling(tmp_path, monkeypatch):
    _, calls, options = install(tmp_path, monkeypatch)
    options['missing'] = True
    out = tmp_path / 'out'
    with pytest.raises(ValueError, match='all 64 new target roots'):
        m.run(out)
    result = json.loads((out / 'run.json').read_text())
    assert len(result['cohort']['roots']) == 63 and len(result['cohort']['missing_roots']) == 1
    assert calls['histories'] == list(m.TARGETS) and calls['references'] == []


def test_duplicate_or_misbound_reference_cannot_replace_a_frozen_root():
    root = dict(root_id='15_reward_0', life=15, query='reward', episode=0)
    cohort = dict(roots=[root], completed_references=0)
    record = dict(root, reference_log={'censored_root': False}, reference_audit={'bound': True},
        reference_complete=True, seconds=.1)
    wrong = deepcopy(record)
    wrong['life'] = 16
    with pytest.raises(ValueError, match='differs from'):
        m.merge_reference(cohort, wrong)
    assert cohort['completed_references'] == 0 and 'reference_log' not in root
    m.merge_reference(cohort, record)
    with pytest.raises(ValueError, match='duplicated'):
        m.merge_reference(cohort, record)
    assert cohort['completed_references'] == 1 and root['reference_log'] == record['reference_log']
