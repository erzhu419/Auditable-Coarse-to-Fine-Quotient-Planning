# V180r12r4r2 ordinal8 formal failure

`ordinal8_failure_artifacts.tar.gz.base64` is a lossless transport encoding of
the nine exact, canonical JSON files retained from:

`jtl110gpu2:/home/erzhu419/mine_code/acfqp-v180r12r4r2-ordinal8/.tmp/exact-freeze`

The bundle contains only the launch manifest, materialization terminal, outer
service attempt/failure, inner launch attempt/failure, campaign attempt,
`EVENTS/000000.json`, and campaign failure. The freeze module verifies every
restored raw byte count and SHA-256 before using the documents, then verifies
their canonical/self identities and joins. The archive itself is not treated
as an additional scientific identity.

For manual inspection, decode and list without writing project files:

```bash
base64 -d ordinal8_failure_artifacts.tar.gz.base64 | tar -tzf -
```

The formal prefix ended after `ATTEMPT_OPEN`. No CounterRecord, WorkVector,
ComparisonVector, terminal, or independent replay was produced. The retained
failure used the historical code `SUPERVISOR_BIRTH_FAILURE`, although no child
was created and the exact error was the pre-birth cgroup topology/limits
contract rejection. The retained launch manifest records parent
`controllers` and `subtree_control` as `cpu,memory,pids`; the frozen runner it
binds required both parent fields to equal `memory,pids`.
