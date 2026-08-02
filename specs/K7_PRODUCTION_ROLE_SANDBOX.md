# K7 production-role sandbox

**Contract:** `2.0.11`

Contract `2.0.18` closes the bootstrap-to-entry gap: the sandbox module itself
must have exact ZIP-member origin under the sealed archive FD, post-exec
tightening installs once before role-entry import, both exec syscalls are
live-probed as `EPERM`, and the entry consumes an archive/role/PID/FD-bound
one-shot attestation before loading common or business/worker core modules.
**Profile:** `v075_k7_production_role_sandbox_v2`

The parent freezes a role-specific Landlock ruleset and a seccomp program
bound to the exact interpreter FD before `clone3`. The native child installs
both before its sole `execveat(fd, ..., AT_EMPTY_PATH)` edge. That first filter
rejects `execve`, every descendant-creation syscall, x32 and every crossed
exec-FD/flag value. The fresh-exec entry then stacks a TSYNC filter rejecting
both `execve` and `execveat`.

The worker ruleset permits writes only beneath its bound output directory; the
business ruleset has no path-write exception. Existing broker endpoints and
the business result memfd remain capabilities rather than new path access.
Tests interpret the BPF, cross descriptors and exercise real child processes.

This is a construction authority. Until the native production launcher joins
it to the complete attempt and post-reap envelope, it issues no no-spawn
attestation, shared-resource resolution or formal accounting object.
