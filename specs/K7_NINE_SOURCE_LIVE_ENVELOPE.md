# K7 nine-source live envelope

Status: construction contract `2.0.21` (`V0-110B-2E-11`).

The nine shared-resource journals belong to one production attempt and one
measurement window, but they do not contain the same number of local events.
Requiring identical numeric start/cutoff intervals would force padding,
renumbering, or hidden events. The V3 envelope instead:

- preserves each source's own inclusive local closure and cutoff identity;
- binds all nine paths in the exact catalogue order;
- requires one runtime envelope, occurrence, attempt, decision point, and
  measurement-window identity across all sources;
- content-addresses every bound source from its exact component IDs/digests;
  and
- content-addresses the complete nine-source join together with the runtime
  replay and terminal-closure observations.

The envelope contains no reported numeric values. It neither verifies source
semantics nor issues accounting artifacts; those remain separate authorities.
Its purpose is to make different honest local journal lengths compatible
without weakening the single-attempt identity boundary.
