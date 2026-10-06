from fractions import Fraction as F
from scripts import audit_joint_query_qualification_v235 as audit


def test_count_embedding_keeps_binary_mixture_separate_from_full_simplex():
    counts = {'D_DEL': {'DELIVERY': 4, 'OTHER': 3}}
    embedded = audit.embedded_counts(counts)
    assert embedded[audit.evidence.D] == {'DELIVERY': 4, 'LOST': 3, 'RECOVERY': 0}
    assert audit.evidence.predictive_weight((4, 3)) != audit.evidence.predictive_weight((4, 3, 0))


def test_all_policy_projection_embeddings_preserve_global_query_gaps():
    case = dict(operating='high', retry_cost='19/20')
    for query in ('goal', 'risk'):
        for chosen in audit.POLICIES:
            for other in audit.POLICIES:
                if chosen == other:
                    continue
                family = audit.evidence.relevant_family(query, chosen, other)
                assert audit.preserved_gap(case, query, chosen, other, family)


def test_wrong_risk_collapse_is_rejected_by_corner_identity():
    case = dict(operating='low', retry_cost='17/20')
    assert not audit.preserved_gap(case, 'risk', 'SHORT', 'DETOUR_RETURN', 'S_D_DEL')
