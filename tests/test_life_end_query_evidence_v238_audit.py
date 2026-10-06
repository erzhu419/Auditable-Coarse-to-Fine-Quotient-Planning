from copy import deepcopy
from fractions import Fraction as F

from scripts import audit_life_end_query_evidence_v238 as audit


def raw_fixture():
    sources, targets = [], []
    for context, index, slot in (('A', 0, 0), ('B', 27, 3)):
        for j, op in enumerate(audit.OPERATORS):
            increments = dict.fromkeys(audit.evidence.ALPHABETS[op], 0)
            increments['DELIVERY'] = 1
            sources.append(dict(life=0, context=context, index=index, slot=slot, operator=op,
                seed=100+index+j, draw_start=0, draw_end=1, increments=increments))
    for stage, context, index in (('A', 'A', 3), ('B', 'B', 30), ('A_RETURN', 'A', 54)):
        for arm in ('ORACLE_GAP', 'ORACLE_BALANCED'):
            batches = []
            for op in audit.OPERATORS:
                category = 'LOST' if stage == 'A' else 'DELIVERY'
                if stage == 'A_RETURN' and op == audit.evidence.D:
                    category = 'RECOVERY'
                increments = dict.fromkeys(audit.evidence.ALPHABETS[op], 0)
                increments[category] = 1
                batches.append(dict(operator=op, draw_start=0, draw_end=1, increments=increments))
            targets.append(dict(life=0, index=index, case=dict(context=context, stage=stage), identity=0,
                arm=arm, spent=3, seeds=dict.fromkeys(audit.OPERATORS, 200+index), batches=batches))
    return audit.raw_paid_banks(sources, targets)


def endpoint_tape(context, banks):
    tape = dict(life=0, arm='ORACLE_GAP', case=dict(context=context), identity=0,
                operators={}, provenance={})
    metadata = dict(changed_operator=audit.evidence.D, b_to_a=[0])
    expected = audit.endpoint_batches(tape, banks, metadata)
    for op, batches in expected.items():
        queue, segments = [], []
        for segment, increments in batches:
            start = len(queue)
            for cat, amount in increments.items():
                queue.extend([cat]*amount)
            segments.append(dict(segment, queue_start=start, queue_end=len(queue)))
        tape['operators'][op], tape['provenance'][op] = queue, segments
    return tape, expected


def test_a_endpoint_uses_all_own_same_identity_return_observations():
    tape, expected = endpoint_tape('A', raw_fixture())
    assert audit.raw_segments_match(tape, expected)
    assert [item['index'] for item in tape['provenance'][audit.evidence.D]] == [0, 3, 54]
    assert tape['operators'][audit.evidence.D] == ['DELIVERY', 'LOST', 'RECOVERY']


def test_b_endpoint_rejects_adding_ignored_a_return_to_inheritance():
    banks = raw_fixture()
    tape, expected = endpoint_tape('B', banks)
    assert audit.raw_segments_match(tape, expected)
    assert [item['index'] for item in tape['provenance'][audit.evidence.S]] == [0, 3, 27, 30]
    assert [item['index'] for item in tape['provenance'][audit.evidence.D]] == [27, 30]
    op = audit.evidence.S
    segment, increments = banks['targets'][0, 'ORACLE_GAP', 'A', 0, op][-1]
    start = len(tape['operators'][op])
    tape['operators'][op].append('DELIVERY')
    tape['provenance'][op].append(dict(segment, queue_start=start, queue_end=start+1))
    assert not audit.raw_segments_match(tape, expected)


def test_endpoint_rejects_coupled_other_arm_target_metadata():
    tape, expected = endpoint_tape('A', raw_fixture())
    tape['provenance'][audit.evidence.S][1]['arm'] = 'ORACLE_BALANCED'
    assert not audit.raw_segments_match(tape, expected)


def test_certificate_audit_rejects_training_in_validation_denominator():
    training = {op: ['DELIVERY']*4 for op in audit.OPERATORS}
    validation = {audit.evidence.S: ['DELIVERY'], audit.evidence.D: ['LOST'], audit.evidence.R: []}
    split = dict(training=training, validation=validation)
    case, query, chosen, other = dict(operating='low', retry_cost='17/20'), 'risk', 'DETOUR_RETURN', 'SHORT'
    family = 'S_D_FULL'
    a, k = (audit.predictive.named_counts(family, split[name]) for name in ('training', 'validation'))
    embedding = audit.global_audit.embedded_counts(k)
    mle = {op: {cat: F(count, sum(row.values())) if sum(row.values()) else F(1, len(row))
                 for cat, count in row.items()} for op, row in embedding.items()}
    gap = audit.evidence.utility(case, query, other, mle)-audit.evidence.utility(case, query, chosen, mle)
    numerator = sum((audit.arithmetic.logarithm(audit.predictive.posterior_predictive(
        tuple(a[name][cat] for cat in row), tuple(row.values())))[0] for name, row in k.items()), F(0))
    cert = dict(query=query, chosen=chosen, other=other, family=family, training_counts=a,
        validation_counts=k, embedded_counts=embedding, threshold=960, regret_threshold=F(1, 20),
        log_predictive_lower=numerator, log_threshold_upper=audit.arithmetic.logarithm(960)[1],
        witness_kind='bad_null_mle', bad_null_kernel=mle, bad_null_gap=gap, status='unknown',
        certified=False, partitions=0, leaves=[], log_bad_likelihood_upper=None, log_e_lower=None)
    failed = []
    audit.audit_certificate(split, case, query, chosen, other, cert,
                            lambda name, condition: failed.append(name) if not condition else None)
    assert not failed
    mutated = deepcopy(cert)
    mutated['embedded_counts'][audit.evidence.S]['DELIVERY'] += 4
    audit.audit_certificate(split, case, query, chosen, other, mutated,
                            lambda name, condition: failed.append(name) if not condition else None)
    assert 'source_training_and_validation_only_sufficient_counts' in failed
