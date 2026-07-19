# Third-party notices

## Laplace-semi-MDP compatibility capsule

`third_party/laplace_smdp_940598d/` is a minimal, quarantined snapshot of
[Laplace-semi-MDP](https://github.com/erzhu419/Laplace-semi-MDP) at commit
`940598d8648d7c65f77f3f3c736d749e8e3750bf`.

The copied upstream files are licensed under the MIT License included in that
directory. `UPSTREAM.json` records the provenance and SHA-256 digest of every
copied file. The manifest and the new project's compatibility checker are new
project files, not upstream source.

This capsule intentionally excludes upstream model weights, generated outputs
other than two small golden fixtures, scheduler configuration, downloaded
papers, cloned third-party repositories, caches, and uncommitted working-tree
changes. It is a reproducibility reference, not the production interface for
the new quotient-planning implementation.

## Research reference clones

`reference/repos/` contains shallow, unmodified reading copies of repositories
that are either cited explicitly or linked directly by a cited paper, author,
official project, or cited demo page. They are not package dependencies and no
source is copied from them into `src/acfqp/`.

Exact origins, commits, relationship evidence, and license observations are in
`reference/repo_clone_manifest.json`. GPL-licensed repositories remain isolated.
Two repositories have no explicit license (`NOASSERTION`); possession of a
reference clone is not permission to copy, modify, or redistribute their code.
