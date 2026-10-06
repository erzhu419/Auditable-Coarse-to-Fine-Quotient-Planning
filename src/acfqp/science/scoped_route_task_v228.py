"""Simulator-only A -> B -> A return task with one declared local change."""
from copy import deepcopy
import random

from . import mechanism_switch_task_v205 as truth

OPERATORS, ALPHABETS = truth.OPERATORS, truth.ALPHABETS
STAGES = ('A', 'B', 'A_RETURN')
SOURCE_COUNT = 3
TARGETS_PER_STAGE = 24


def changed_law(law, operator):
    """Change one categorical row; every other row retains its A law."""
    result = deepcopy(law)
    pair = ('DELIVERY', 'RECOVERY') if operator == 'DETOUR_PASS' else ('DELIVERY', 'LOST')
    left, right = pair
    result[operator][left], result[operator][right] = law[operator][right], law[operator][left]
    return result


def world(life):
    """Return public cases and separate oracle laws/identities/metadata.

    Each scope supplies three paid representatives, one per hidden type.  B's
    public representative order differs from A's and its correspondence is
    hidden.  Each target stage has eight cases per hidden type and six per
    public cost pair.  This is a declared source interface, not inferred
    clustering of ordinary unlabeled targets.
    Context marks the declared mechanism scope; A_RETURN returns to A without
    repeating any case id or trajectory.  No hidden type or changed row enters
    a public case.
    """
    labels = list(truth.WEATHER)
    random.Random(248100 + life).shuffle(labels)
    b_labels = list(truth.WEATHER)
    random.Random(248900 + life).shuffle(b_labels)
    if b_labels == labels:
        b_labels = b_labels[1:] + b_labels[:1]
    b_to_a = [labels.index(label) for label in b_labels]
    changed_operator = OPERATORS[life % len(OPERATORS)]
    base_laws = [truth.laws(dict(weather=label)) for label in labels]
    cases = [dict(id=f'v228_l{life:02d}_source_{i}', operating='high',
                  retry_cost='19/20', context='A', stage='SOURCE')
             for i in range(SOURCE_COUNT)]
    laws, identities = deepcopy(base_laws), list(range(SOURCE_COUNT))
    stage_ranges = {}
    for stage_index, stage in enumerate(STAGES):
        if stage == 'B':
            b_source_indexes = list(range(len(cases), len(cases)+SOURCE_COUNT))
            for b_index, a_index in enumerate(b_to_a):
                cases.append(dict(id=f'v228_l{life:02d}_b_source_{b_index}',
                                  operating='high', retry_cost='19/20',
                                  context='B', stage='B_SOURCE'))
                laws.append(changed_law(base_laws[a_index], changed_operator))
                identities.append(b_index)
        types = list(range(SOURCE_COUNT))*8
        costs = [(op, retry) for op in truth.OPERATING for retry in truth.RETRY_COSTS]*6
        random.Random(248200 + 100*stage_index + life).shuffle(types)
        random.Random(248600 + 100*stage_index + life).shuffle(costs)
        start = len(cases)
        context = 'B' if stage == 'B' else 'A'
        for index, (identity, (operating, retry_cost)) in enumerate(zip(types, costs)):
            cases.append(dict(id=f'v228_l{life:02d}_{stage.lower()}_{index:02d}',
                              operating=operating, retry_cost=retry_cost,
                              context=context, stage=stage))
            law = base_laws[b_to_a[identity] if stage == 'B' else identity]
            laws.append(changed_law(law, changed_operator) if stage == 'B' else deepcopy(law))
            identities.append(identity)
        stage_ranges[stage] = [start, len(cases)]
    metadata = dict(changed_operator=changed_operator, source_labels=labels,
                    b_source_labels=b_labels, b_to_a=b_to_a,
                    stage_ranges=stage_ranges,
                    source_indexes=list(range(SOURCE_COUNT)),
                    b_source_indexes=b_source_indexes,
                    changes_per_type=1, public_context=True)
    return cases, laws, identities, metadata
