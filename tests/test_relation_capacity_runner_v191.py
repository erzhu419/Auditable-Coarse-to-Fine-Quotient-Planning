"""Synthetic frozen-input phases, observable SOURCE decisions and paid failures."""
import json
import pytest
from scripts import run_controlled_predictive_relation_capacity_v191 as runner


def metrics(roots):
    return dict(roots=roots, components=[.5, .1, .2], utility=.6,
        oracle_components=[.7, .1, .2], oracle_utility=.8, regret_mean=.2,
        positive_regret_roots=roots, fallback_roots=0)


def fake_capacity():
    return dict(status='strict_feasible', upper_bound='1', costs={'lp_solves': 2},
        nodes=[dict(native_lp={'status': 0})], weak_witness=None,
        witness=dict(margin='1/4', evaluation={'all_optimal': True, 'rational_all_optimal': True}))


def fake_inputs(tmp_path, monkeypatch):
    prior = tmp_path/'prior'
    monkeypatch.setattr(runner, 'ROOT', tmp_path); monkeypatch.setattr(runner, 'PREVIOUS', prior)
    runner.save(tmp_path/'reports/v190_runtime_tmp/stage_checks.json',
                dict(valid=False, frozen_source_same=True, frozen_inputs_same=True))
    runner.save(prior/'metadata_binding_amendment/result.json', dict(corrected_valid=True))
    runner.save(prior/'run.json', {'status': 'complete'})
    def root(cohort, index):
        return dict(root_id=f'{cohort}:{index}', source_id=f'g:{index%36}', legal_actions=list(runner.ACTIONS),
            action_components={action: [.5, 0., .2] for action in runner.ACTIONS})
    roots = dict(SOURCE=[root('s', i) for i in range(143)], TARGET=[root('t', i) for i in range(96)])
    runner.save(prior/'roots.json', roots)
    runner.save(prior/'labels.json', roots['TARGET'])
    runner.save(prior/'model.json', {'retained': True})
    runner.save(prior/'choices.json', {'retained': True})
    runner.save(prior/'summary.json', {'retained': True})
    events = []
    monkeypatch.setattr(runner, 'capture_code', lambda output: events.append('capture'))
    def cache(source):
        events.append('cache')
        for row in source:
            row['relation_features'] = {action: [0.]*98 for action in row['legal_actions']}
        return {'relation_roots_cached': len(source)}
    monkeypatch.setattr(runner.relation, 'cache_roots', cache)
    def build(roots, labels):
        events.append(('problem', len(roots)))
        assert {r['root_id'] for r in roots} == {r['root_id'] for r in labels}
        assert all(set(label['action_components']) == set(root['legal_actions']) for root, label in zip(roots, labels))
        return dict(roots=roots, work={'problem_root_records': len(roots)})
    monkeypatch.setattr(runner.core, 'build_problem', build)
    def source(source, model):
        events.append('source_evaluation')
        assert len(source) == 143 and model == {'retained': True}
        return dict(metrics=metrics(143), root_records=[], work={'source_diagnostic_root_records': 143})
    monkeypatch.setattr(runner, 'source_diagnostics', source)
    monkeypatch.setattr(runner, 'retained_target_metrics', lambda roots, choices, summary:
        (events.append('target_bindings') or metrics(96), {'retained_target_root_bindings': 96}))
    def solve(problem):
        events.append(('capacity', len(problem['roots'])))
        return fake_capacity()
    monkeypatch.setattr(runner.core, 'solve_capacity', solve)
    return events


def test_amended_inputs_frozen_before_alllegal_three_scope_diagnostics(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    result = runner.run(tmp_path/'out')
    assert events == ['capture', 'cache', ('problem', 143), ('problem', 96), ('problem', 239),
                      'source_evaluation', 'target_bindings', ('capacity', 143), ('capacity', 96), ('capacity', 239)]
    assert [row['phase'] for row in result['phase_history']] == ['protocol_frozen', 'problems_frozen',
        'capacity_SOURCE', 'capacity_TARGET', 'capacity_JOINT', 'complete']
    assert [row['input_reads'] for row in result['phase_history']] == [0, 8, 8, 8, 8, 8]
    inputs = json.loads((tmp_path/'out/input_manifest.json').read_text())
    assert [row['phase'] for row in inputs] == ['protocol_frozen']*8
    assert [row['saved_ref'].split('/')[-1] for row in inputs] == [
        'v190_stage_checks.json', 'v190_metadata_amendment.json', 'v190_run.json', 'v190_roots.json',
        'v190_labels.json', 'v190_model.json', 'v190_choices.json', 'v190_summary.json']
    assert result['new_capacity_attempts'] == result['new_capacity_scopes'] == 3
    assert result['new_lp_solves'] == 6
    assert all(result[name] == 0 for name in ('new_environment_samples', 'new_source_games',
        'new_native_weight_updates', 'new_predictors_fitted', 'new_reference_kernels', 'new_exact_label_roots', 'new_boards_generated'))
    summary = json.loads((tmp_path/'out/summary.json').read_text())
    assert summary['scopes']['JOINT']['learned']['positive_regret_roots'] == 239
    assert summary['scopes']['SOURCE']['native_lp_status_counts'] == {'0': 1}


def test_failed_second_scope_keeps_first_scope_and_paid_attempt_stops_joint(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    def solve(problem):
        n = len(problem['roots']); events.append(('capacity', n))
        if n == 96:
            error = RuntimeError('synthetic native dual cannot balance')
            error.record = dict(status='execution_error', costs={'lp_solves': 3, 'symbolic_balance_solves': 1})
            raise error
        return fake_capacity()
    monkeypatch.setattr(runner.core, 'solve_capacity', solve)
    with pytest.raises(RuntimeError, match='cannot balance'):
        runner.run(tmp_path/'out')
    result = json.loads((tmp_path/'out/run.json').read_text())
    assert result['status'] == 'failed' and result['failure']['capacity_scope'] == 'TARGET'
    assert result['new_capacity_attempts'] == 2 and result['new_capacity_scopes'] == 1 and result['new_lp_solves'] == 5
    assert result['costs']['failed_capacity'] == dict(scope='TARGET', counts={'lp_solves': 3, 'symbolic_balance_solves': 1})
    assert ('capacity', 239) not in events
    assert set(json.loads((tmp_path/'out/capacities.json').read_text())) == {'SOURCE'}
    assert json.loads((tmp_path/'out/failed_capacity.json').read_text())['status'] == 'execution_error'


def test_unsettled_amendment_stops_before_cache_or_capacity(tmp_path, monkeypatch):
    events = fake_inputs(tmp_path, monkeypatch)
    runner.save(tmp_path/'prior/metadata_binding_amendment/result.json', dict(corrected_valid=False))
    with pytest.raises(ValueError, match='incomplete'):
        runner.run(tmp_path/'out')
    result = json.loads((tmp_path/'out/run.json').read_text())
    assert events == ['capture'] and result['new_capacity_attempts'] == 0
    assert result['costs']['input_counts']['json_read_operations'] == 3


def test_source_uses_full_component_chooser_without_labels_in_observable(monkeypatch):
    root = dict(root_id='s', source_id='group', life=0, canonical_board=[0]*16,
        legal_actions=['DOWN', 'LEFT'], immediate_rewards={'DOWN': 0., 'LEFT': 0.},
        fallback_action='DOWN', action_map={'DOWN': 'DOWN', 'LEFT': 'LEFT'},
        layout_features={}, action_features={}, relation_features={'DOWN': [0.]*98, 'LEFT': [1.]*98},
        action_components={'DOWN': [.7, .6, .1], 'LEFT': [.4, 0., .5]})
    def choose(model, observable, counts):
        assert 'action_components' not in observable
        assert observable['relation_features'] == root['relation_features']
        counts.update(relation_decisions=1)
        return dict(canonical_action='DOWN', fallback=False, predicted_components={'DOWN': [.7, .6, .1], 'LEFT': [.4, 0., .5]})
    monkeypatch.setattr(runner.learning, 'choose_action', choose)
    result = runner.source_diagnostics([root], {'retained': True})
    assert result['root_records'][0]['oracle_action'] == 'LEFT'
    assert result['root_records'][0]['regret'] == pytest.approx(.7)
    assert result['root_records'][0]['decision']['predicted_components']['LEFT'] == [.4, 0., .5]
    assert result['metrics']['positive_regret_roots'] == 1 and result['work']['relation_decisions'] == 1


def test_target_uses_retained_choices_and_zero_margin_policy_remains_unknown(monkeypatch):
    monkeypatch.setattr(runner.learning, 'choose_action', lambda *args: pytest.fail('TARGET chooser rerun'))
    roots = [{'root_id': 't', 'legal_actions': ['LEFT']}]
    choices = {'RELATION': [{'root_id': 't', 'canonical_action': 'LEFT'}]}
    summary = dict(root_records=[dict(root_id='t', models={'RELATION': {'action': 'LEFT'}})],
        models={'RELATION': {'components': [.5, .1, .2], 'utility': .6, 'positive_regret_roots': 1, 'fallback_roots': 0},
                'ORACLE': {'components': [.7, .1, .2], 'utility': .8}})
    target, counts = runner.retained_target_metrics(roots, choices, summary)
    assert target['regret_mean'] == pytest.approx(.2) and counts['retained_target_choice_bindings'] == 1
    capacity = dict(status='no_positive_margin', upper_bound='0', nodes=[], costs={}, witness=None,
                    weak_witness=dict(evaluation={'all_optimal': False}))
    result = runner.summarize({scope: {'roots': roots} for scope in runner.SCOPES},
        {scope: capacity for scope in runner.SCOPES}, {'metrics': metrics(1)}, target)
    assert result['complete']
    assert all(row['actual_tie_policy_attainability'] == 'unknown' for row in result['scopes'].values())
