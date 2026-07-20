"""Public structural replay API for Phase-3E route envelopes.

This boundary intentionally exposes replay and typed candidate inputs only.  A
structurally valid envelope is not a plan or infeasibility certificate, so the
private construction helper that used certificate terminology is not exported.
"""

from __future__ import annotations

from acfqp import _route_envelope_verifier_impl as _impl


ArtifactVerificationAttestation = _impl.ArtifactVerificationAttestation
RouteEnvelopeVerificationError = _impl.RouteEnvelopeVerificationError
VerifiedRouteInputCatalog = _impl.VerifiedRouteInputCatalog
replay_strict_route_envelope = _impl.replay_strict_route_envelope


__all__ = [
    "ArtifactVerificationAttestation",
    "RouteEnvelopeVerificationError",
    "VerifiedRouteInputCatalog",
    "replay_strict_route_envelope",
]
