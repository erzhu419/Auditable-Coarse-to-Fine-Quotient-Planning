from fractions import Fraction as F
from scripts import audit_joint_query_evidence_v235 as audit


def test_predictive_mixture_uses_projected_jeffreys_not_full_dirichlet_marginal():
    assert audit.predictive_weight((1, 0)) == F(1, 2)
    assert audit.predictive_weight((1, 0, 0)) == F(1, 3)
    assert audit.predictive_weight((2, 1)) == F(1, 16)
    assert audit.predictive_weight((1, 1, 1)) == F(1, 105)


def test_exact_ratio_classification_and_zero_likelihood():
    assert audit.likelihood_ratio((2, 1), (F(1, 2), F(1, 2))) == F(1, 2)
    assert audit.likelihood_ratio((1, 0), (0, 1)) is None
    assert audit.likelihood_ratio((0, 0), (0, 1)) == 1


def test_all_supported_query_families_are_distinct_and_needed():
    assert len(audit.FAMILY_ROWS) == 8
    assert audit.relevant_family('risk', 'SHORT', 'DETOUR_RETURN') == 'S_D_FULL'
    assert audit.relevant_family('goal', 'SHORT', 'DETOUR_RETURN') == 'S_D_DEL'
    assert audit.relevant_family('risk', 'DETOUR_RETRY', 'DETOUR_RETURN') == 'D_REC_R'
    assert audit.relevant_family('goal', 'DETOUR_RETRY', 'WAIT') == 'D_FULL_R'


def test_shared_prefix_gap_cancels_full_detour_delivery_and_operating():
    case = dict(operating='high', retry_cost='19/20')
    kernel = {
        audit.S: {'DELIVERY': '1/2', 'LOST': '1/2'},
        audit.D: {'DELIVERY': '3/5', 'LOST': '1/5', 'RECOVERY': '1/5'},
        audit.R: {'DELIVERY': '3/4', 'LOST': '1/4'},
    }
    gap = (audit.utility(case, 'risk', 'DETOUR_RETRY', kernel)
           -audit.utility(case, 'risk', 'DETOUR_RETURN', kernel))
    assert gap == F(1, 5)*(8*F(3, 4)-4-F(19, 20))
