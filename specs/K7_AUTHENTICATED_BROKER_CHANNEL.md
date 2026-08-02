# K7 authenticated broker channel

**Contract:** `2.0.13`
**Profile:** `v075_k7_authenticated_broker_channel_v2`

Every role packet is received on a blocking `AF_UNIX/SOCK_SEQPACKET` broker
endpoint with `SO_PASSCRED`. Exactly one non-truncated `SCM_CREDENTIALS`
record is accepted. Its PID must equal both the broker's expected native PID
and the live PID read from the retained pidfd; UID/GID, endpoint identity,
binding and canonical frame role are replayed before a typed observation is
issued. `SO_PEERCRED`, extra ancillary records and partial protocol sequences
cannot substitute for this join.

An observation proves only one authenticated packet. It does not prove the
complete five-frame transcript, direct reaps, no-spawn, final peak, receipts or
formal vectors.
