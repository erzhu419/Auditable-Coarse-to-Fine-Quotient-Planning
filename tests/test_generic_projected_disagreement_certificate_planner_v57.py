import pytest

from acfqp.generic_projected_disagreement_certificate_planner_v57 import (
    GenericProjectedDisagreementCertificatePlannerV57Error,
    run_projected_disagreement_certificate_episode_v57,
)


def test_v57_rejects_nonissuer_candidate_before_any_ground_query():
    with pytest.raises(GenericProjectedDisagreementCertificatePlannerV57Error):
        run_projected_disagreement_certificate_episode_v57(
            object(),
            object(),
            (),
            reusable_model=None,
            model_source_episode_index=0,
            episode_index=7,
            maximum_abstract_depth=12,
            maximum_execution_steps=96,
        )
