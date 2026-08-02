# K7 production-role sandbox

**Contract:** `2.0.11`
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
