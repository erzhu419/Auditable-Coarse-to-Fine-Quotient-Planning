# K7 successor portable authority replay

Contract `1.97.0` closes the fresh-exec reconstruction gap in the V0-103
successor request.  The historical verifier intentionally required the exact
live parent request object.  That retained-runtime guard remains unchanged,
but it cannot be the authority boundary of a newly executed sealed child.

The portable profile closure accepts exactly four canonical byte inputs:

1. the sealed source archive;
2. the sealed transport profile;
3. the complete lifecycle profile; and
4. the parent-owned successor profile.

It reconstructs the sealed transport from the archive entries and runtime
document, reconstructs the lifecycle profile, reissues the complete V6
accounting/profile authority chain from the frozen registries, and reissues the
successor profile with the official OS-supervisor admission profile.  Every
supplied canonical profile document must then equal the newly issued document
byte for byte.  The resulting closure is process-local and unpickleable.

One canonical V0-103 request can then be replayed without a live parent request
argument.  The route graph is reconstructed against the newly issued accounted
profile, the signer registry is reconstructed from its canonical public
document, and the request is frozen again from all registered fields.  The
fresh request document must equal the supplied bytes exactly.  Unknown fields,
type aliases, crossed nested identities, profile mutations, archive mutations,
and route mutations fail before any business operation.

This contract is a pre-business construction boundary.  It does not prove that
the loaded child code came from the archive, enter an isolated runtime, consume
a cgroup lease, launch a process, execute the K7 schedule, emit either successor
frame, or record any shared-resource value.  It issues no `CounterRecord`,
`WorkVector`, `ComparisonVector`, projection proof, terminal artifact,
certificate, scientific result, or official authority.  Those remain the
responsibility of the sealed bootstrap, atomic parent supervisor, semantic
source verifier, and formal accounting reducer.
