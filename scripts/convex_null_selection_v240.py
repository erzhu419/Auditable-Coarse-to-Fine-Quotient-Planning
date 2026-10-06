"""Select the frozen nine unresolved V239 risk comparisons in record order."""
from collections import Counter
from copy import deepcopy


def select(rows):
    selected = []
    for row in rows:
        if row['query_ready']:
            continue
        risk = row['queries']['risk']
        comparison = None
        if not risk['certified'] and risk['policy'] == 'DETOUR_RETURN':
            for family, other in (('S_D_FULL', 'SHORT'), ('D_REC_R', 'DETOUR_RETRY')):
                comparison = next((item for item in risk['comparisons']
                    if not item['certified'] and item['family'] == family
                    and item['chosen'] == 'DETOUR_RETURN' and item['other'] == other), None)
                if comparison is not None:
                    break
        if comparison is None:
            raise ValueError('each frozen unresolved case needs the declared uncertified risk comparison')
        descriptor = {field: deepcopy(row[field]) for field in
            ('life', 'index', 'arm', 'kind', 'case', 'identity', 'certificate_index', 'fees')}
        descriptor.update(query='risk', chosen=comparison['chosen'], other=comparison['other'],
            family=comparison['family'], projected_counts=deepcopy(comparison['projected_counts']),
            old_comparison=deepcopy(comparison))
        selected.append(descriptor)
    if len(selected) != 9 or Counter(row['family'] for row in selected) != {'S_D_FULL': 6, 'D_REC_R': 3}:
        raise ValueError('the frozen selection must contain six S/D and three recovery/retry risk cases')
    return selected
