"""Source-only V117 knowledge and acquisition history for frozen V118 reuse."""
from copy import deepcopy


def source_capsule(run_v117):
    """Copy source evidence while excluding every inherited outer evaluation."""
    if run_v117['status'] != 'complete':
        raise ValueError('V118 requires a complete V117 source run')
    lives = run_v117['lifecycles']
    if len(lives) != 4 or {life['life'] for life in lives} != {0, 1, 2, 3}:
        raise ValueError('V118 requires all four V117 source lifecycles')
    result = dict(schema='acfqp.utility_source.v118', source_schema=run_v117['schema'],
        source_status=run_v117['status'], settings=deepcopy(run_v117['settings']),
        supplied_dynamics=deepcopy(run_v117['supplied_dynamics']), lifecycles=[])
    for life in lives:
        if [phase['name'] for phase in life['phases']] != ['A', 'B', 'A_RETURN']:
            raise ValueError('V118 requires the three ordered V117 source phases')
        saved = dict(life=life['life'], phases=[], final_router=deepcopy(life['final_router']))
        for phase in life['phases']:
            checkpoint = phase['checkpoint']
            cp = {key: deepcopy(checkpoint[key]) for key in (
                'phase', 'router_p4', 'router_module_id', 'router_payload')}
            cp['models'] = {name: deepcopy(checkpoint['models'][name]) for name in ('SHARED', 'SPLIT')}
            cp['models']['MSE_SELECTED'] = deepcopy(checkpoint['models']['SELECTED'])
            cp['fit_logs'] = {name: deepcopy(checkpoint['fit_logs'][name]) for name in ('SHARED', 'SPLIT')}
            cp['mse_selected_origin'] = deepcopy(checkpoint['selected_origin'])
            cp['mse_selection'] = deepcopy(checkpoint['selection'])
            cp['source_validation_prediction_counts'] = deepcopy(checkpoint['validation']['prediction_counts'])
            saved['phases'].append(dict(name=phase['name'], p4=phase['p4'],
                source_games=deepcopy(phase['source_games']), checkpoint=cp))
        result['lifecycles'].append(saved)
    return result
