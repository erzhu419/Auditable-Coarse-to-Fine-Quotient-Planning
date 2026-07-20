from __future__ import annotations

import acfqp.phase3e_accounting as accounting
import acfqp.route_envelope_verifier as envelope_verifier


def test_public_accounting_does_not_export_retired_pass_label() -> None:
    assert not hasattr(accounting, "PRECONSTRUCTION_PASS")
    assert "PRECONSTRUCTION_CORE_PARTIAL" in accounting.__all__


def test_public_envelope_api_exposes_replay_not_certificate_helper() -> None:
    assert not hasattr(envelope_verifier, "certify_route_envelope_candidate")
    assert not hasattr(envelope_verifier, "StrictRouteCertificateCandidate")
    assert "replay_strict_route_envelope" in envelope_verifier.__all__
