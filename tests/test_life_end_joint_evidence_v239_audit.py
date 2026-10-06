from copy import deepcopy
from fractions import Fraction as F

from scripts import audit_life_end_joint_evidence_v239 as audit


def test_all_paid_interface_detects_omitted_source_counts():
    operators = {audit.evidence.S: ['DELIVERY']*5,
                 audit.evidence.D: ['DELIVERY']*4+['LOST'], audit.evidence.R: ['DELIVERY']*4}
    case, family = dict(operating='low', retry_cost='17/20'), 'S_D_FULL'
    raw = {operator: {cat: values.count(cat) for cat in audit.evidence.ALPHABETS[operator]}
           for operator, values in operators.items()}
    uniform = {operator: dict.fromkeys(categories, F(1, len(categories)))
               for operator, categories in audit.evidence.ALPHABETS.items()}
    counts, _ = audit.evidence.named_projection(family, raw, uniform)
    embedding = audit.global_audit.embedded_counts(counts)
    mle = {op: {cat: F(count, sum(row.values())) if sum(row.values()) else F(1, len(row))
                 for cat, count in row.items()} for op, row in embedding.items()}
    chosen, other, query = 'DETOUR_RETURN', 'SHORT', 'risk'
    gap = audit.evidence.utility(case, query, other, mle)-audit.evidence.utility(case, query, chosen, mle)
    arithmetic = audit.global_audit.arithmetic
    minimum = sum((arithmetic.logarithm(audit.evidence.predictive_weight(tuple(row.values())))[0]
                   for row in counts.values()), F(0))
    cert = dict(query=query, chosen=chosen, other=other, family=family, projected_counts=counts,
        embedded_counts=embedding, threshold=960, regret_threshold=F(1, 20), log_mixture_lower=minimum,
        log_threshold_upper=arithmetic.logarithm(960)[1], witness_kind='bad_null_mle',
        bad_null_kernel=mle, bad_null_gap=gap, status='unknown', certified=False,
        partitions=0, leaves=[], log_bad_likelihood_upper=None, log_e_lower=None)
    failed = []
    check = lambda name, condition: failed.append(name) if not condition else None
    tape = dict(case=case, operators=operators)
    audit.audit_comparison(tape, query, chosen, other, cert, check)
    assert not failed
    omitted_source = deepcopy(cert)
    omitted_source['projected_counts']['S']['DELIVERY'] = 1
    audit.audit_comparison(tape, query, chosen, other, omitted_source, check)
    assert 'canonical_full_paid_sufficient_counts' in failed


def test_query_cannot_pass_when_one_required_comparison_is_unknown():
    failed = []
    check = lambda name, condition: failed.append(name) if not condition else None
    audit.audit_query_and(dict(certified=False), [True, False, True], check)
    assert not failed
    audit.audit_query_and(dict(certified=True), [True, False, True], check)
    assert failed == ['complete_query_comparison_and']
