"""No sampling dispatch; preserve recovery failures and inherited cost once."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from scripts import run_controlled_predictive_crossed_ranking_v106 as m


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_crossed_runner_v106.checks.json'
    data = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    data['attempts'].append(dict(failed_tests=request.session.testsfailed-before,
        new_environment_transitions=0, new_model_prefix_transitions=0, new_neural_model_fits=0,
        neural_candidate_predictions=0, scope='Mock recovery/scoring; real dispatch, failure retention and source-cost binding.'))
    path.write_text(json.dumps(data, indent=2) + '\n')


def source(tmp_path, monkeypatch, primary=True):
    folder = tmp_path / 'v105'; folder.mkdir()
    original = dict(status='complete', settings=dict(lifecycles=[11,12,13,14]))
    inherited = dict(newly_sampled_environment_transitions=7492903,
        new_model_prefix_transitions=324480, new_neural_model_fits=16)
    (folder / 'run.json').write_text(json.dumps(original))
    (folder / 'analysis.json').write_text(json.dumps(dict(primary_complete=primary, actual_executed_work=inherited)))
    monkeypatch.setattr(m, 'SOURCE', folder)
    monkeypatch.setattr(m, 'snapshot', lambda _: None)
    return folder, original, inherited


def test_incomplete_source_prevents_recovery_and_scoring(tmp_path, monkeypatch):
    source(tmp_path, monkeypatch, primary=False)
    monkeypatch.setattr(m, 'load_cohort', lambda *a: pytest.fail('incomplete source recovered'))
    monkeypatch.setattr(m, 'score_models', lambda *a: pytest.fail('incomplete source scored'))
    with pytest.raises(ValueError, match='completed full V105'):
        m.run(tmp_path / 'output')


def test_failed_exact_reproduction_keeps_partial_costs_and_decisions(tmp_path, monkeypatch):
    folder, original, inherited = source(tmp_path, monkeypatch)
    roots = [dict(root_id='life_11_reward_0', features=[[0.]])]
    recovery = dict(checks={'inputs':True}, counts={'roots':1})
    partial = [dict(root_id=roots[0]['root_id'], method='fixed', training_life=11)]
    scoring = dict(checks={'diagonal_scores_exact':False}, counts={'neural_candidate_predictions':5})
    monkeypatch.setattr(m, 'load_cohort', lambda *a: (roots, recovery))
    monkeypatch.setattr(m, 'score_models', lambda *a: ([{'training_life':11}], partial, scoring))
    output = tmp_path / 'output'
    with pytest.raises(ValueError, match='original decision reproduction'):
        m.run(output)
    result = json.loads((output / 'run.json').read_text())
    assert result['status'] == 'running' and result['decisions'] == partial
    assert result['scoring_log'] == scoring and result['inherited_v105_work'] == inherited
    with pytest.raises(FileExistsError):
        m.run(output)


def test_success_uses_retained_inputs_and_preserves_source_metadata(tmp_path, monkeypatch):
    folder, original, inherited = source(tmp_path, monkeypatch)
    frozen = deepcopy(original)
    roots = [dict(root_id='life_11_reward_0', features=[[0.]])]
    log = dict(checks={'exact':True}, counts={'roots':1})
    called = []
    def recover(actual_source, output, run):
        assert actual_source == folder and run == original
        called.append('recover'); return roots, log
    def score(actual_source, run, recovered):
        assert actual_source == folder and run == original and recovered is roots
        called.append('score'); return [{'training_life':11}], [{'root_id':roots[0]['root_id']}], dict(
            checks={'exact':True}, counts={'neural_candidate_predictions':5})
    monkeypatch.setattr(m, 'load_cohort', recover)
    monkeypatch.setattr(m, 'score_models', score)
    output = tmp_path / 'output'; m.run(output)
    result = json.loads((output / 'run.json').read_text())
    assert result['status'] == 'complete' and called == ['recover','score']
    assert result['inherited_v105_work'] == inherited
    assert result['cohort'] == dict(roots=roots, log=log)
    assert all(result['settings'][key] == 0 for key in
        ('new_environment_transitions', 'new_model_prefix_transitions', 'new_neural_model_fits'))
    assert json.loads((folder / 'run.json').read_text()) == frozen
