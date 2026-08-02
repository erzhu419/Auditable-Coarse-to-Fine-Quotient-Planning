# K7 transfer and mount raw journals

**Contract:** `2.0.14`
**Profile:** `construction_shared_resource_transfer_mount_journal_v2`

The journal records raw sources for `io.read_bytes`, `io.staged_bytes` and
`io.mounted_bytes_peak`. Purposes and payload identities are frozen before
use. Read and staged values are recomputed as exact transfer sums; staging the
same payload twice creates two charge keys. Mounted capacity is recomputed at
every open/close boundary as the sum of unique visible payload identities and
then reduced by `max`.

Global and path-local sequence numbers are recorder-owned and continuous. The
closed bundle binds occurrence, attempt, decision, measurement window and
inclusive cutoff and emits the exact V2 component schemas in the nine-path
catalogue. Independent replay checks arithmetic and cross-component identity.
It remains raw evidence with `semantic_source_verified=false`; the later live
broker and semantic replayer must establish complete purpose coverage before a
CounterRecord can be issued.
