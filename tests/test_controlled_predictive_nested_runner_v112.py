"""Test paired fit dispatch and exact reuse of query-selected outer decisions."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from scripts import run_controlled_predictive_nested_selection_v112 as m


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_nested_runner_v112.checks.json'
    result = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    result['attempts'].append(dict(failed_tests=request.session.testsfailed - before,
        neural_model_fits=0, optimizer_steps=0, neural_candidate_predictions=0,
        new_environment_transitions=0, new_model_prefix_transitions=0,
        scope='Mock new fits and inner scores; exact dispatch over synthetic cached outer decisions.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


def cached_outer():
    roots = [dict(root_id=f'{life}_{query}_{episode}', life=life, query=query, episode=episode)
        for life in m.LIVES for query in m.QUERIES for episode in range(8)]
    models = [dict(heldout_life=life, method=f'POOLED_H{width}_{stage}', metadata=dict(
        heldout_life=life, hidden=width, stage=stage, source_lives=[s for s in m.LIVES if s != life],
        path=f'/retained/{life}_{width}_{stage}.json'))
        for life in m.LIVES for width in m.WIDTHS for stage in m.STAGES]
    decisions = [dict(root_id=root['root_id'], heldout_life=root['life'], method=model['method'],
        event=dict(option=f'{root["query"]}_{model["method"]}', predictions={'retained': [1., 2.]}))
        for root in roots for model in models if model['heldout_life'] == root['life']]
    choices = [dict(heldout_life=life, hidden=width, query=query,
        source_lives=[s for s in m.LIVES if s != life], chosen_stage='FULL' if query == 'reward' else 'HALF',
        chosen_method=f'POOLED_H{width}_{"FULL" if query == "reward" else "HALF"}')
        for life in m.LIVES for width in m.WIDTHS for query in m.QUERIES]
    return roots, models, decisions, choices


def install_sources(tmp_path, monkeypatch):
    outer_path, previous_path, training_path = [tmp_path / name for name in ('outer', 'previous', 'training')]
    for path in (outer_path, previous_path, training_path):
        path.mkdir()
    roots, models, decisions, choices = cached_outer()
    outer = dict(status='complete', settings={'validation_roots_per_query': 8}, cohort={'roots': roots},
        models=models, decisions=decisions, folds=[{'retained': True}], acquisition_accounting={'retained': True})
    (outer_path / 'run.json').write_text(json.dumps(outer))
    (outer_path / 'analysis.json').write_text(json.dumps({'primary_complete': True}))
    (previous_path / 'run.json').write_text(json.dumps(dict(status='complete', inherited_work={'V110': {'fits': 16}})))
    (previous_path / 'analysis.json').write_text(json.dumps(dict(primary_complete=True, actual_executed_work={'fits': 8})))
    (training_path / 'run.json').write_text(json.dumps(dict(status='complete', allocations=[])))
    bank = {life: [dict(source_life=life, query=query, episode=e, is_half=e != 1)
        for e in (0, 1, 4) for query in m.QUERIES] for life in m.LIVES}
    for name, value in [('SOURCE', outer_path), ('PREVIOUS', previous_path), ('TRAIN_SOURCE', training_path)]:
        monkeypatch.setattr(m, name, value)
    monkeypatch.setattr(m, 'snapshot', lambda *args: None)
    monkeypatch.setattr(m, 'load_bank', lambda *args: (deepcopy(bank), dict(checks={'complete': True})))
    monkeypatch.setattr(m, 'selection_acquisition_accounting', lambda *args: {'retained': 'validation charged'})
    monkeypatch.setattr(m, 'select_updates', lambda *args, **kwargs: (deepcopy(choices), dict(checks={'complete': True})))
    return outer


def fake_fit(records, width, stage, sources, half=None):
    assert len(sources) == 2 and {r['source_life'] for r in records} == set(sources)
    selected = [r for r in records if stage == 'FULL' or r['is_half']]
    roster = [[r['source_life'], r['query'], r['episode']] for r in selected if r['episode'] % 5 != 4]
    statistics = [[r['source_life'], r['query'], r['episode']] for r in records if r['is_half'] and r['episode'] % 5 != 4]
    if stage == 'HALF':
        assert half is None
    else:
        assert half['update']['source_lives'] == sources and half['hidden'] == width
        assert half['update']['stage'] == 'HALF'
    payload = dict(hidden=width, checkpoint=256000 if stage == 'HALF' else 512000, family='UNIFORM_SHRINK',
        mean=[1.], scale=[2.], uniform_gamma=.3)
    model = SimpleNamespace(family=payload['family'], checkpoint=payload['checkpoint'],
        parameter_count=123 * width, to_payload=lambda: deepcopy(payload))
    log = dict(source_lives=sources, statistics_roster=statistics, training_roster=roster,
        initialization='original_initialization' if stage == 'HALF' else 'half_parameters',
        optimizer_state='reset_zero_moments', new_optimizer_steps=1000,
        inherited_parameter_steps=0 if stage == 'HALF' else 1000,
        parameter_lineage_steps=1000 if stage == 'HALF' else 2000, checks={'complete': True})
    return model, log


def test_unique_pair_fits_and_cached_outer_dispatch(tmp_path, monkeypatch):
    old = install_sources(tmp_path, monkeypatch)
    calls, scoring_calls = [], []
    def fit(records, width, stage, sources, half):
        calls.append((tuple(sources), width, stage))
        return fake_fit(records, width, stage, sources, half)
    def score(models, roots):
        assert len(models) == 24 and roots == old['cohort']['roots']
        assert all(len(row['metadata']['source_lives']) == 2 for row in models)
        scoring_calls.append(len(models))
        return [], dict(checks={'complete': True})
    monkeypatch.setattr(m, 'fit_stage', fit)
    monkeypatch.setattr(m, 'score_inner_models', score)
    out = tmp_path / 'out'
    m.run(out)
    run = json.loads((out / 'run.json').read_text())
    assert len(calls) == len(set(calls)) == 24 and scoring_calls == [24]
    assert run['status'] == 'complete' and all(run['runner_checks'].values())
    assert run['models'] == old['models'] and run['decisions'][:256] == old['decisions']
    assert len(run['decisions']) == 384 and run['derived_log']['counts']['new_neural_candidate_predictions'] == 0
    assert run['inherited_work'] == {'V110': {'fits': 16}, 'V111': {'fits': 8}}


def test_query_choice_copies_the_exact_saved_event():
    roots, models, decisions, choices = cached_outer()
    derived, log = m.derive_outer_decisions(choices, models, decisions, roots)
    index = {(row['root_id'], row['method']): row['event'] for row in decisions}
    assert len(derived) == 128 and all(log['checks'].values())
    for row in derived:
        assert row['event'] == index[row['root_id'], row['chosen_method']]
        assert ('FULL' in row['chosen_method']) == ('reward' in row['root_id'])
    derived[0]['event']['predictions']['retained'][0] = 9.
    assert decisions[0]['event']['predictions']['retained'][0] == 1.


@pytest.mark.parametrize('corruption', ('missing_choice', 'target_in_model'))
def test_incomplete_or_leaking_selection_is_not_dispatched(corruption):
    roots, models, decisions, choices = cached_outer()
    if corruption == 'missing_choice':
        choices.pop()
    else:
        models[1]['metadata']['source_lives'] = [11, 12, 13]
    with pytest.raises(ValueError):
        m.derive_outer_decisions(choices, models, decisions, roots)


def test_wrong_full_statistics_retains_fit_and_stops_before_scoring(tmp_path, monkeypatch):
    install_sources(tmp_path, monkeypatch)
    def fit(*args):
        model, log = fake_fit(*args)
        if args[2] == 'FULL':
            payload = model.to_payload()
            payload['uniform_gamma'] = .8
            model.to_payload = lambda: payload
        return model, log
    monkeypatch.setattr(m, 'fit_stage', fit)
    monkeypatch.setattr(m, 'score_inner_models', lambda *args: pytest.fail('contaminated update scored'))
    out = tmp_path / 'out'
    with pytest.raises(ValueError, match='frozen paired stages'):
        m.run(out)
    run = json.loads((out / 'run.json').read_text())
    assert not run['runner_checks']['paired_full_initialization']
    assert len(run['inner_models']) == 2 and run['inner_decisions'] == []
