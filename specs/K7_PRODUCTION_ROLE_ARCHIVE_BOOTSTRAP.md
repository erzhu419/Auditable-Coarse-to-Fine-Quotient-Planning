# K7 production role archive bootstrap

**Milestone:** `V0-110B-2D-2A`

**Contract:** `2.0.8`

**Post-exec amendment:** contract `2.0.18` installs and live-probes the
archive-loaded role's post-exec `execve`/`execveat` denial before importing the
fixed role entry. A process-local one-shot attestation binds the archive OFD,
source bytes, role and PID and must be consumed before common/core imports.
**Profiles:** `v075_k7_production_role_bootstrap_v2`,
`v075_k7_production_role_manifest_v2`,
`v075_k7_broker_process_entry_common_v2`

## Purpose

This slice replaces the deliberately absent V0-110B-2D-1 process wrappers
with a fresh, content-addressed source archive and two executable
`python -I -S -B -c` role bootstraps. It closes the source-to-process-entry
provenance boundary only. It does not launch either role, authorize a live
broker, or issue shared-resource accounting evidence.

## Fresh source and identity chain

The v2 manifest is issued only from a newly frozen successor request whose
source archive contains the worker wrapper, business wrapper, shared input
reconstructor and bootstrap source. For every required member it joins the
live workspace bytes to the archive member digest and byte count. The v1
manifest remains historical and cannot be relabelled.

The manifest binds the exact request and route identities, interpreter bytes,
repository locator digest, private signer inode identities, fixed role entry
module/symbol, bootstrap digest, ordered sealed-input roles and the separate
capability-FD lane. Public replay reconstructs this graph from canonical bytes
without reading the workspace or serializing private signer paths. A role
launch context additionally binds the exact IPC binding and role; changing the
request, role, manifest, context or source bytes changes the corresponding
content identity.

## Strict archive bootstrap

Each frozen bootstrap starts with no project module loaded and requires the
exact isolated/no-site/no-environment/no-bytecode interpreter flags. It checks:

- the complete environment namespace and fixed role;
- distinct sealed and capability descriptor lanes;
- immutable seals and bounded sizes for every public input;
- `AF_UNIX/SOCK_SEQPACKET` channel and role-specific result-FD access mode;
- the worker-only directory FD;
- the sole extra interpreter-identity FD;
- interpreter and source-archive byte counts and SHA-256 digests; and
- absence of a workspace path from `sys.path`.

It sets every inherited role descriptor `FD_CLOEXEC` before importing project
code, inserts only `/proc/self/fd/<archive-fd>` into `sys.path`, imports the
fixed wrapper and verifies the module origin lies inside that archive. Typed
bootstrap-local failures use fixed exit codes and emit no protocol or private
diagnostic.

The attempt-process launch-site provenance pin now supports this strict ZIP
origin. Ordinary imports retain `resolve(strict=True) + read_bytes`; a ZIP
import is accepted only when the exact `zipimporter`, `ModuleSpec` name,
origin and archive path agree, and the raw member bytes are obtained through
that loader. The pinned code object, globals mapping, byte digest and count are
unchanged in meaning.

## Private secret boundary

The common role reconstructor reads and canonically replays the seven public
sealed inputs. For the business-only lifecycle secret it verifies only the
regular-file kind, positive bounded size and complete immutable seal set. It
does not copy or `pread` the secret. The descriptor remains available for the
business core's single commitment-verifying content read.

## Claim boundary and successor

This milestone proves that the fixed role entries are present in a fresh
source identity and can be reached by an isolated archive-only exec. It does
not prove a production role launch, cgroup membership, role-specific
Landlock/seccomp, `SCM_CREDENTIALS`, the five-frame broker join, output
readback, direct reaps, final same-OFD peak or cleanup.

Consequently it issues no shared-resource resolution, `CounterRecord`,
`WorkVector`, `ComparisonVector`, projection proof, terminal, certificate or
scientific result. Official execution remains false; scalar/break-even remain
null; all counter-completeness, workload-economics and sample-efficiency Gates
remain `NOT_RUN`.

The next slice must join these bootstraps to an issuer-owned resource session,
role-specific sandbox and native broker runtime before any of the nine shared
resource paths can become exact accounting evidence.
