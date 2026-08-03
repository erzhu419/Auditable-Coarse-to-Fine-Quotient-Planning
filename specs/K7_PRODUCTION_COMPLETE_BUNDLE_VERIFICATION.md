# K7 production-complete bundle independent verification

Contract `2.0.31` / V0-110B-2E-21 adds a standalone evaluation-lane verifier
which does not call the formal materializer or terminal producer.  Starting
from independently held production roots and portable bytes, it reconstructs
the 202 records, 182 projection terms, eight comparison axes, root-cap proof
and route-attempt terminal identities.  Its typed verification attestation
binds the exact artifact role, context and evaluation work.

This is semantic re-derivation rather than hash-only integrity checking.
ID-only bundles, incompatible roles, altered records/projections/caps,
terminal relabelling, omitted evaluation work and context transplants fail
closed.  Evaluation work remains separate from the operational route vector.
The verifier does not turn a noncertificate attempt into a certificate and
does not unlock official execution, scalar economics or any Gate.
