"""Matched update dispatch and retained-score reuse without real fitting."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from scripts import run_controlled_predictive_incremental_ranking_v107 as m


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_incremental_runner_v107.checks.json'
    data = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    data['attempts'].append(dict(failed_tests=request.session.testsfailed-before,
        new_environment_transitions=0, new_model_prefix_transitions=0, neural_model_fits=0,
        optimizer_steps=0, neural_candidate_predictions=0,
        scope='Mock fit/scoring; actual matched dispatch, artifact statistics and inherited-decision binding.'))
    path.write_text(json.dumps(data, indent=2) + '\n')


def fixture_sources(tmp_path, monkeypatch):
    train, cross = tmp_path / 'train', tmp_path / 'cross'
    train.mkdir(); cross.mkdir()
    old_methods = ['H2_ONLY', 'PREFIX_ONLY_DIRECT'] + list(m.BASE.values()) + [x+'_FROZEN_HALF' for x in m.BASE.values()]
    settings = dict(methods=old_methods, training_lifecycles=[11,12,13,14], lifecycles=[11,12,13,14], budgets=[20,40])
    original = dict(status='complete', settings=settings, models=[{'retained':'model'}],
        decisions=[{'retained':'decision'}], cohort=dict(roots=[dict(root_id='kept',features=[[0.]]*5)],log={}),
        inherited_v105_work={'newly_sampled_environment_transitions':7492903})
    allocations = [dict(life=life, construction=[dict(episode_cutoff=2),dict(episode_cutoff=4)],
        model_metadata={m.BASE[h]+'_FROZEN_HALF':dict(path=f'half_{life}_{h}') for h in m.WIDTHS})
        for life in settings['lifecycles']]
    (train / 'run.json').write_text(json.dumps(dict(status='complete', allocations=allocations)))
    (cross / 'run.json').write_text(json.dumps(original))
    (cross / 'analysis.json').write_text(json.dumps(dict(primary_complete=True,
        actual_executed_work={'new_neural_candidate_predictions':5120})))
    monkeypatch.setattr(m, 'TRAIN_SOURCE', train); monkeypatch.setattr(m, 'CROSS_SOURCE', cross)
    monkeypatch.setattr(m, 'snapshot', lambda _: None)
    def load(*args):
        halves = {str(h):dict(hidden=h,mean=[0.],scale=[1.],uniform_gamma=.3,
            checkpoint=2,family='UNIFORM_SHRINK',optimizer_steps=1000) for h in m.WIDTHS}
        return [dict(episode=0),dict(episode=2)], halves, dict(checks={'first_batch_bound':True})
    monkeypatch.setattr(m, 'load_training', load)
    return original


def fitted(half, cutoff, mode, wrong_stats=False):
    payload = dict(half,checkpoint=cutoff)
    if wrong_stats: payload['mean']=[1.]
    model = SimpleNamespace(parameter_count=half['hidden']*123,to_payload=lambda:deepcopy(payload))
    inherited = 1000 if mode.endswith('WARM') else 0
    log = dict(optimizer_state='reset_zero_moments',new_optimizer_steps=1000,
        inherited_parameter_steps=inherited,parameter_lineage_steps=inherited+1000,
        checks={'frozen_half_statistics':True},models={'UNIFORM_SHRINK':{'final_loss':1.}})
    return model, log


def test_both_updates_use_same_records_and_only_new_models_are_scored(tmp_path, monkeypatch):
    original = fixture_sources(tmp_path, monkeypatch)
    calls = []
    def fit(records, cutoff, half, mode):
        calls.append((deepcopy(records), cutoff, half['hidden'],mode))
        return fitted(half,cutoff,mode)
    def score(models, roots):
        assert len(models)==16 and {row['method'] for row in models}==set(m.NEW_METHODS)
        assert roots==original['cohort']['roots']
        return [dict(root_id='kept',training_life=row['training_life'],method=row['method']) for row in models], dict(
            checks={'new_only':True},counts={'model_root_scores':16})
    monkeypatch.setattr(m, 'fit_update', fit); monkeypatch.setattr(m, 'score_new', score)
    output=tmp_path/'output';m.run(output)
    result=json.loads((output/'run.json').read_text())
    assert len(calls)==16 and all(row[0]==calls[0][0] and row[1]==4 for row in calls)
    assert [(row[2],row[3]) for row in calls]==[(h,mode) for _ in range(4) for h in m.WIDTHS for mode in m.MODES]
    assert result['status']=='complete' and all(result['runner_checks'].values())
    assert result['cohort']==original['cohort'] and result['decisions'][:1]==original['decisions']
    assert result['models'][:1]==original['models'] and result['inherited_decisions']==1
    assert result['inherited_v105_work']==original['inherited_v105_work']
    assert result['inherited_v106_work']==dict(new_neural_candidate_predictions=5120)
    for path in output.glob('life_*/*_model.json'):
        row=json.loads(path.read_text());update=row['update']
        assert update['parameter_lineage_steps']==(2000 if update['mode'].endswith('WARM') else 1000)
        assert row['mean']==[0.] and row['scale']==[1.] and row['uniform_gamma']==.3


def test_changed_statistics_stop_before_cross_scoring_and_preserve_fit(tmp_path, monkeypatch):
    fixture_sources(tmp_path,monkeypatch)
    monkeypatch.setattr(m,'fit_update',lambda records,cutoff,half,mode:fitted(half,cutoff,mode,True))
    monkeypatch.setattr(m,'score_new',lambda *a:pytest.fail('wrong-statistics model was scored'))
    output=tmp_path/'output'
    with pytest.raises(ValueError,match='frozen statistics'):
        m.run(output)
    result=json.loads((output/'run.json').read_text())
    assert result['status']=='running' and not result['runner_checks']['new_model_statistics_match']
    assert len(result['training'][0]['fit_logs'])==1 and len(list(output.glob('life_*/*_model.json')))==1


def test_serialized_new_model_binding_precedes_scoring(tmp_path,monkeypatch):
    path=tmp_path/'model.json'
    path.write_text(json.dumps(dict(checkpoint=4,hidden=4,family='UNIFORM_SHRINK',update={'mode':'wrong'})))
    def load(row):
        return SimpleNamespace(**row,score_candidates=lambda *a:pytest.fail('mismatched update scored'))
    monkeypatch.setattr(m.CandidateModel,'from_payload',load)
    models=[dict(training_life=11,method='new',metadata=dict(path=str(path),episode_cutoff=4,
        hidden=4,family='UNIFORM_SHRINK',mode='FROZEN_STATS_WARM'))]
    decisions,log=m.score_new(models,[dict(root_id='r',features=[[0.]]*5)])
    assert decisions==[] and not log['checks']['new_model_metadata_match']
    assert log['counts']['model_payloads_loaded']==1 and log['counts']['model_root_scores']==0
