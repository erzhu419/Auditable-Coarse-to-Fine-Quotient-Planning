# K7 production-role launch authority

**Contract:** `2.0.12`
**Profile:** `v075_k7_production_role_launch_authority_v2`

One process-local, one-shot authority joins an executable production manifest,
the exact role launch context, resource capability bundle, interpreter image,
seven role-specific immutable public inputs and, for business only, the sealed
lifecycle secret and private signer locators. Interpreter, input and capability
FD numbers and inodes are pairwise disjoint. All public inputs are replayed
against their exact bytes and full seals; the secret is not read here.

The authority fixes argv and environment and consumes to the native tuple
`(interpreter_fd, sealed_fds, capability_fds, argv, env_rows)`. Descriptor
numbers, argv values and private paths are excluded from its public document.
Consumption performs no launch and authorizes no process or accounting count.
