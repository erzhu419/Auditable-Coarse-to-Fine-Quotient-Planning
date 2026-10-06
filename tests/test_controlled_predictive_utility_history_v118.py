"""Whitelist inherited source evidence without importing outer evaluation data."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_utility_history_v118 import source_capsule

WORK = Counter()
POISON = 'FORBIDDEN_OUTER_EVIDENCE'


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_utility_history_v118.checks.json'
    log = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    log['attempts'].append(dict(failures=request.session.testsfailed-before,
        development_work=dict(WORK), newly_sampled_environment_transitions=0,
        new_synthetic_transitions=0, neural_model_fits=0,
        scope='handwritten source payloads and poisoned outer-evaluation fields'))
    path.write_text(json.dumps(log, indent=2) + '\n')


def input_run():
    result = dict(schema='acfqp.consolidation.v117.run', status='complete',
        settings=dict(lifecycles=[0,1,2,3],source_games_per_phase=18),
        supplied_dynamics=dict(program={'merge':'equal'}), lifecycles=[],
        actual_wall_seconds=POISON, outercost=POISON, predictions=POISON)
    for life in range(4):
        phases = []
        for batch, (name,p4) in enumerate([('A',.1),('B',.3),('A_RETURN',.1)]):
            models = {mode: dict(mode=mode,trees={'GREEDY':{'values':[[batch,life,0.]]}})
                for mode in ('SHARED','SPLIT')}
            models['SELECTED'] = deepcopy(models['SHARED'])
            cp = dict(phase=name,router_p4=p4,router_module_id=batch%2,
                router_payload={'modules':[{'id':batch%2}]},models=models,
                fit_logs={mode:{'counts':{'tree_fits':3}} for mode in ('SHARED','SPLIT')},
                selected_origin={'batch':batch,'mode':'SHARED'},
                selection={'selected_candidate':'NEW_SHARED'},
                validation={'prediction_counts':{'KEEP':{'prediction_record_requests':10}},
                    'records':POISON,'predictions':POISON},
                predictive_tests=POISON,control_evaluations=POISON,prediction_counts=POISON)
            phases.append(dict(name=name,p4=p4,source_games=[{'role':'FIT','steps':10}],
                checkpoint=cp,outercost=POISON))
        result['lifecycles'].append(dict(life=life,phases=phases,
            final_router={'observations_seen':30},actual_wall_seconds=POISON))
    return result


def extract(run):
    WORK['synthetic_capsule_calls'] += 1
    return source_capsule(run)


def test_capsule_excludes_poisoned_outer_fields_and_keeps_only_declared_sources():
    run = input_run()
    capsule = extract(run)
    assert POISON not in json.dumps(capsule)
    assert set(capsule) == {'schema','source_schema','source_status','settings','supplied_dynamics','lifecycles'}
    assert capsule['schema'] == 'acfqp.utility_source.v118'
    assert capsule['source_schema'] == run['schema'] and capsule['source_status'] == 'complete'
    for life in capsule['lifecycles']:
        assert set(life) == {'life','phases','final_router'}
        for phase in life['phases']:
            cp = phase['checkpoint']
            assert set(phase) == {'name','p4','source_games','checkpoint'}
            assert set(cp) == {'phase','router_p4','router_module_id','router_payload','models','fit_logs',
                'mse_selected_origin','mse_selection','source_validation_prediction_counts'}
            assert set(cp['models']) == {'SHARED','SPLIT','MSE_SELECTED'}
            assert cp['source_validation_prediction_counts']['KEEP']['prediction_record_requests'] == 10


def test_selected_parameters_origin_and_all_mutable_source_payloads_are_independent():
    run = input_run()
    original = deepcopy(run)
    capsule = extract(run)
    for source,saved in zip(run['lifecycles'],capsule['lifecycles']):
        for old,new in zip(source['phases'],saved['phases']):
            assert new['checkpoint']['models']['MSE_SELECTED'] == old['checkpoint']['models']['SELECTED']
            assert new['checkpoint']['mse_selected_origin'] == old['checkpoint']['selected_origin']
    capsule['settings']['lifecycles'].append(9)
    capsule['supplied_dynamics']['program']['merge'] = 'different'
    life = capsule['lifecycles'][0]
    life['final_router']['observations_seen'] = 0
    phase = life['phases'][0]
    phase['source_games'][0]['steps'] = 999
    cp = phase['checkpoint']
    cp['models']['MSE_SELECTED']['trees']['GREEDY']['values'][0][0] = 999
    cp['fit_logs']['SHARED']['counts']['tree_fits'] = 999
    cp['router_payload']['modules'][0]['id'] = 999
    cp['mse_selected_origin']['batch'] = 999
    cp['mse_selection']['selected_candidate'] = 'KEEP'
    cp['source_validation_prediction_counts']['KEEP']['prediction_record_requests'] = 999
    assert run == original


def test_incomplete_or_missing_source_roster_is_rejected():
    for kind in ('status','lives','phases'):
        run = input_run()
        if kind == 'status':
            run['status'] = 'running'
        elif kind == 'lives':
            run['lifecycles'].pop()
        else:
            run['lifecycles'][0]['phases'].pop()
        with pytest.raises(ValueError,match='V118 requires'):
            extract(run)
