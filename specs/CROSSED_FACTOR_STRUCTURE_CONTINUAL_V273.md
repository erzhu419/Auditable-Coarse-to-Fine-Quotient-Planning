# V273 continual action-support structure protocol

V271 changed a mechanism parameter and V272 changed query weights. V273 keeps
the generator law, query bank, visible factors, source selector, and streams
unchanged, but changes the available action structure in B.

The V270 source L, four target corners, four seeds, 48/16 fit/held-out split,
factor projections, and chronological `A -> B -> A_prime` flow are retained.
In A and A_prime, the recovery state exposes `{RETURN, RETRY}`. In B it exposes
only `{RETURN}`. The phase marker is not a learner feature; the available-action
mask is an interface fact supplied at decision time. Since `RETRY` is disabled
in B, its hypothetical outcome rows are not acquired or fitted. B therefore
has two observed operators and 96 fit rows per target at prefix 48; A and
A_prime have all three operators and 144 rows.

The arms are:

* `RESET_AWARE`: current phase prefix with the current legal-action mask;
* `FROZEN_FACTOR_AWARE`: V270 source posterior with the current mask;
* `CONTINUAL_FACTOR_AWARE`: source plus chronological observed fit rows with
  the current mask;
* `LEGACY_UNMASKED`: frozen source posterior that still permits the old RETRY
  action, reported as an invalid-action negative control.

Invalid actions are counted separately and are not converted into ordinary
regret. The primary diagnostic is B legality at prefix zero and A_prime
recovery. This protocol tests structural applicability and action masking; it
does not claim that a new successor category or new consequence module has been
learned. That support-expansion question is reserved for a separate experiment.

The run is exploratory and does not reopen the original Gate or start U006.
