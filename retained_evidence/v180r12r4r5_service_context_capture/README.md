# V180r12r4r5 service-context capture

`service_context_capture.json` is one complete, read-only observation made on
`jtl110gpu2` inside the collected transient unit
`acfqp-v180r12r4r5-freeze-capture-20260829.service`.  The unit used
`Slice=app.slice` and `Delegate=yes`; it did not create a campaign ATTEMPT or
run measurement or verification.

The capture invoked the same cgroup-parent and runtime-capability observers as
the source-bound runner.  Its canonical file is 1,459 bytes with SHA-256
`53508b200ae3b0279bda887cec804a8dd06f7d800734fe3d760f1712ea866fd3`.
Relative to the ordinal10 frozen idle-SSH facts, the complete parent snapshot
differs only in `self_membership` and `subtree_control`; the complete runtime
snapshot is identical.  This capture is successor freeze input and postmortem
evidence.  It is not ordinal10 runtime-native evidence and does not repair the
missing ordinal10 per-field failure diagnostic.
