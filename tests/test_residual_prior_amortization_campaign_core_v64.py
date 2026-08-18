import pytest

from acfqp.residual_prior_amortization_campaign_core_v64 import (
    ResidualPriorAmortizationCampaignCoreV64Error,
)


def test_v64_has_typed_amortization_failure():
    assert issubclass(ResidualPriorAmortizationCampaignCoreV64Error, ValueError)
