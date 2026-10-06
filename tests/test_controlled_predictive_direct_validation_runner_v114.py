"""Source selection precedes target access and target dispatch copies cached actions."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from scripts import run_controlled_predictive_direct_validation_v114 as m


def target_fixture():
    roots = [dict(root_id=f'{life}_{q}_{episode}', life=life, query=q, episode=episode)
        for life in (15, 16, 17, 18) for q in m.QUERIES for episode in range(8)]
    models = [dict(bundle_id=b, method=f'POOLED_H{w}_{stage}', metadata=dict(
        source_lives=[s for s in m.BUNDLES if s != b], path=f'/old/{b}/{w}_{stage}'))
        for b in m.BUNDLES for w in m.WIDTHS for stage in ('HALF', 'FULL')]
    decisions = [dict(bundle_id=model['bundle_id'], root_id=root['root_id'], target_life=root['life'],
        method=model['method'], event=dict(option=model['method'], predictions={'query': root['query']}))
        for model in models for root in roots]
    selections = [dict(heldout_life=b, hidden=w, query=q, source_lives=[s for s in m.BUNDLES if s != b],
        chosen_stage='FULL' if q == 'reward' else 'HALF',
        chosen_method=f'POOLED_H{w}_{"FULL" if q == "reward" else "HALF"}')
        for b in m.BUNDLES for w in m.WIDTHS for q in m.QUERIES]
    return dict(cohort={'roots': roots}, models=models, decisions=decisions), selections


def test_direct_dispatch_is_exact_and_independent_of_target_outcomes():
    target, selections = target_fixture()
    old = deepcopy(target)
    derived, log = m.derive_target_decisions(selections, target)
    assert len(derived) == 512 and all(log['checks'].values())
    cache = {(d['bundle_id'], d['root_id'], d['method']): d['event'] for d in target['decisions']}
    for d in derived:
        assert d['event'] == cache[d['bundle_id'], d['root_id'], d['chosen_method']]
        assert d['event'] is not cache[d['bundle_id'], d['root_id'], d['chosen_method']]
    assert target == old
    for root in target['cohort']['roots']:
        root['reference_log'] = {'unreadable_for_selection': object()}
    assert m.derive_target_decisions(selections, target)[0] == derived


def test_wrong_bundle_model_cannot_supply_target_action():
    target, selections = target_fixture()
    selections[0]['source_lives'] = [11, 12, 13]
    with pytest.raises(ValueError, match='actual deployment'):
        m.derive_target_decisions(selections, target)


def test_real_sample_identity_uses_board_and_seed_not_reused_episode_labels():
    root = dict(life=11, query='reward', episode=0, source_seed=10591100, board=[0, 1])
    trained = dict(root, source_seed=99100000, board=[1, 0])
    data = dict(allocations=[dict(life=11, construction=[dict(acquisition={'completed_roots': [trained]})])])
    assert all(m.source_overlap(data, [root])['checks'].values())
    trained['board'] = root['board']
    result = m.source_overlap(data, [root])
    assert not result['checks']['boards_disjoint'] and result['board_overlap_count'] == 1
    trained['source_seed'] = root['source_seed']
    assert not m.source_overlap(data, [root])['checks']['seeds_disjoint']


def test_runner_saves_source_choices_before_loading_any_target_file(tmp_path, monkeypatch):
    source_path, target_path, training_path = [tmp_path / name for name in ('source', 'target', 'training')]
    for path in (source_path, target_path, training_path):
        path.mkdir()
    target, choices = target_fixture()
    source_models = [dict(heldout_life=r['bundle_id'], method=r['method'], metadata=r['metadata']) for r in target['models']]
    source = dict(status='complete', cohort=dict(roots=[dict(root_id='source', features=[], reference_log={})]),
        models=source_models, selections=choices)
    target.update(status='complete', settings={}, source='old/source', source_models=source_models,
        frozen_selections=choices, runner_checks={'old_pass': True}, scoring_log={}, inherited_work={})
    for path, run in ((source_path, source), (target_path, target), (training_path, {'status': 'complete'})):
        (path / 'run.json').write_text(json.dumps(run))
        (path / 'analysis.json').write_text(json.dumps({'primary_complete': True, 'actual_executed_work': {'old': 1}}))
    for name,path in [('SOURCE',source_path), ('TARGET',target_path), ('TRAINING',training_path)]:
        monkeypatch.setattr(m, name, path)
    monkeypatch.setattr(m, 'snapshot', lambda *a: None)
    monkeypatch.setattr(m, 'source_overlap', lambda *a: {'checks': {'disjoint': True}})
    order = []
    def score(run, roots, location):
        assert all('reference_log' not in root for root in roots)
        order.append('score')
        return [], {'counts': {}, 'checks': {'passed': True}}
    def choose(decisions, roots):
        assert roots == source['cohort']['roots']
        order.append('select')
        return choices, {'counts': {}, 'checks': {'passed': True}}
    monkeypatch.setattr(m, 'score_source_models', score)
    monkeypatch.setattr(m, 'select_updates', choose)
    real_read = Path.read_text
    out = tmp_path / 'out'
    def read(path, *a, **kw):
        if path.parent == target_path:
            assert order == ['score', 'select'] and (out / 'pre_target_selection.json').exists()
        return real_read(path, *a, **kw)
    monkeypatch.setattr(Path, 'read_text', read)
    m.run(out)
    result = json.loads((out / 'run.json').read_text())
    assert result['status'] == 'complete' and all(result['runner_checks'].values())
    assert result['inherited_target_decisions'] == target['decisions']
    assert result['decisions'][:len(target['decisions'])] == target['decisions']
    assert len(result['decisions']) == len(target['decisions']) + 512
    with pytest.raises(FileExistsError):
        m.run(out)
    assert order == ['score', 'select']
