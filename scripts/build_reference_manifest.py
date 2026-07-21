#!/usr/bin/env python3
"""Build and verify the local archive of references cited by the design notes.

The inventory is intentionally explicit.  A paper is deduplicated by DOI first,
then arXiv/venue identifier, and finally title.  The generated manifests record
the exact bytes and repository commits used by this project.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference"


PAPERS = [
    {
        "id": "arXiv:1606.07374",
        "title": "Multi-Stage Temporal Difference Learning for 2048-like Games",
        "source_url": "https://arxiv.org/abs/1606.07374",
        "download_url": "https://arxiv.org/pdf/1606.07374",
        "pdf": "papers/arxiv_1606.07374.pdf",
        "page": "pages/arxiv_1606.07374.html",
        "copy_kind": "arXiv author manuscript",
        "repo_keys": ["tnmichael309/2048AI"],
    },
    {
        "id": "DOI:10.1038/s41586-020-03051-4; arXiv:1911.08265",
        "title": "Mastering Atari, Go, Chess and Shogi by Planning with a Learned Model",
        "source_url": "https://arxiv.org/abs/1911.08265",
        "download_url": "https://arxiv.org/pdf/1911.08265",
        "pdf": "papers/arxiv_1911.08265.pdf",
        "page": "pages/arxiv_1911.08265.html",
        "copy_kind": "arXiv author manuscript",
        "repo_keys": [],
        "repo_status": "No official paper-code repository confirmed; third-party MuZero implementations are excluded.",
    },
    {
        "id": "arXiv:2301.04104",
        "title": "Mastering Diverse Domains through World Models",
        "source_url": "https://arxiv.org/abs/2301.04104",
        "download_url": "https://arxiv.org/pdf/2301.04104",
        "pdf": "papers/arxiv_2301.04104.pdf",
        "page": "pages/arxiv_2301.04104.html",
        "copy_kind": "arXiv author manuscript",
        "repo_keys": ["danijar/dreamerv3"],
    },
    {
        "id": "arXiv:1609.05140",
        "title": "The Option-Critic Architecture",
        "source_url": "https://arxiv.org/abs/1609.05140",
        "download_url": "https://arxiv.org/pdf/1609.05140",
        "pdf": "papers/arxiv_1609.05140.pdf",
        "page": "pages/arxiv_1609.05140.html",
        "copy_kind": "arXiv author manuscript",
        "repo_keys": ["jeanharb/option_critic"],
    },
    {
        "id": "PMLR:v139/choi21b",
        "title": "Variational Empowerment as Representation Learning for Goal-Conditioned Reinforcement Learning",
        "source_url": "https://proceedings.mlr.press/v139/choi21b.html",
        "download_url": "https://proceedings.mlr.press/v139/choi21b/choi21b.pdf",
        "pdf": "papers/pmlr_v139_choi21b.pdf",
        "page": "pages/pmlr_v139_choi21b.html",
        "copy_kind": "publisher open-access PDF",
        "repo_keys": [],
        "repo_status": "No author or official repository confirmed.",
    },
    {
        "id": "PMLR:v162/hansen-estruch22a",
        "title": "Bisimulation Makes Analogies in Goal-Conditioned Reinforcement Learning",
        "source_url": "https://proceedings.mlr.press/v162/hansen-estruch22a.html",
        "download_url": "https://proceedings.mlr.press/v162/hansen-estruch22a/hansen-estruch22a.pdf",
        "pdf": "papers/pmlr_v162_hansen-estruch22a.pdf",
        "page": "pages/pmlr_v162_hansen-estruch22a.html",
        "copy_kind": "publisher open-access PDF",
        "repo_keys": ["philippe-eecs/GCB"],
    },
    {
        "id": "arXiv:2506.00328",
        "title": "BASIL: Best-Action Symbolic Interpretable Learning for Evolving Compact RL Policies",
        "source_url": "https://arxiv.org/html/2506.00328v1",
        "download_url": "https://arxiv.org/pdf/2506.00328",
        "pdf": "papers/arxiv_2506.00328.pdf",
        "page": "pages/arxiv_2506.00328v1.html",
        "copy_kind": "arXiv current PDF; cited HTML is version 1",
        "repo_keys": [],
        "repo_status": "No code URL in the paper and no official repository confirmed.",
    },
    {
        "id": "arXiv:2601.06604",
        "title": "Object-Centric World Models Meet Monte Carlo Tree Search",
        "source_url": "https://arxiv.org/abs/2601.06604",
        "download_url": "https://arxiv.org/pdf/2601.06604",
        "pdf": "papers/arxiv_2601.06604.pdf",
        "page": "pages/arxiv_2601.06604.html",
        "copy_kind": "arXiv author manuscript",
        "repo_keys": [],
        "repo_status": "No code-release URL in the paper and no official repository confirmed.",
    },
    {
        "id": "NeurIPS2021:454cecc4829279e64d624cd8a8c9ddf1",
        "title": "Learning Markov State Abstractions for Deep Reinforcement Learning",
        "source_url": "https://papers.nips.cc/paper/2021/hash/454cecc4829279e64d624cd8a8c9ddf1-Abstract.html",
        "download_url": "https://papers.nips.cc/paper_files/paper/2021/file/454cecc4829279e64d624cd8a8c9ddf1-Paper.pdf",
        "pdf": "papers/neurips_2021_markov_state_abstractions.pdf",
        "page": "pages/neurips_2021_markov_state_abstractions.html",
        "copy_kind": "publisher open-access PDF",
        "repo_keys": ["camall3n/markov-state-abstractions"],
    },
    {
        "id": "arXiv:1408.6315",
        "title": "2048 is (PSPACE) Hard, but Sometimes Easy",
        "source_url": "https://arxiv.org/abs/1408.6315",
        "download_url": "https://arxiv.org/pdf/1408.6315",
        "pdf": "papers/arxiv_1408.6315.pdf",
        "page": "pages/arxiv_1408.6315.html",
        "copy_kind": "arXiv author manuscript",
        "repo_keys": [],
        "repo_status": "No corresponding public repository confirmed.",
    },
    {
        "id": "DOI:10.1287/opre.1050.0216",
        "title": "Robust Control of Markov Decision Processes with Uncertain Transition Matrices",
        "source_url": "https://doi.org/10.1287/opre.1050.0216",
        "download_url": "https://people.eecs.berkeley.edu/~elghaoui/Pubs/RobMDP_OR2005.pdf",
        "pdf": "papers/doi_10.1287_opre.1050.0216.pdf",
        "page": "pages/doi_10.1287_opre.1050.0216.html",
        "page_download_url": "https://people.eecs.berkeley.edu/~elghaoui/pubs_rob_mdp.html",
        "copy_kind": "author-hosted published article",
        "archive_note": "The cited INFORMS PDF returned HTTP 403; archived from the coauthor's Berkeley page.",
        "repo_keys": [],
        "repo_status": "No corresponding public repository confirmed.",
    },
    {
        "id": "arXiv:0807.1173",
        "title": "A Counterexample Guided Abstraction-Refinement Framework for Markov Decision Processes",
        "source_url": "https://arxiv.org/abs/0807.1173",
        "download_url": "https://arxiv.org/pdf/0807.1173",
        "pdf": "papers/arxiv_0807.1173.pdf",
        "page": "pages/arxiv_0807.1173.html",
        "copy_kind": "arXiv author manuscript",
        "repo_keys": [],
        "repo_status": "No exact paper artifact confirmed; PRISM is not substituted without evidence.",
    },
    {
        "id": "PMLR:v216/dadvar23a",
        "title": "Conditional Abstraction Trees for Sample-Efficient Reinforcement Learning",
        "source_url": "https://proceedings.mlr.press/v216/dadvar23a.html",
        "download_url": "https://proceedings.mlr.press/v216/dadvar23a/dadvar23a.pdf",
        "pdf": "papers/pmlr_v216_dadvar23a.pdf",
        "page": "pages/pmlr_v216_dadvar23a.html",
        "copy_kind": "publisher open-access PDF",
        "repo_keys": ["AAIR-lab/CAT-RL"],
    },
    {
        "id": "arXiv:2606.06123",
        "title": "Adaptive State-Action Abstractions via Rate-Distortion",
        "source_url": "https://arxiv.org/abs/2606.06123",
        "download_url": "https://arxiv.org/pdf/2606.06123",
        "pdf": "papers/arxiv_2606.06123.pdf",
        "page": "pages/arxiv_2606.06123.html",
        "copy_kind": "arXiv author manuscript",
        "repo_keys": ["ferosas/adaptive-state-action-abstraction"],
    },
    {
        "id": "arXiv:2605.17058",
        "title": "Learning Multi-Timescale Abstractions for Hierarchical Combinatorial Planning",
        "source_url": "https://arxiv.org/abs/2605.17058",
        "download_url": "https://arxiv.org/pdf/2605.17058",
        "pdf": "papers/arxiv_2605.17058.pdf",
        "page": "pages/arxiv_2605.17058.html",
        "copy_kind": "arXiv author manuscript",
        "repo_keys": [],
        "repo_status": "The paper has no code URL and no exact public repository was found.",
    },
    {
        "id": "AAAI98-109",
        "title": "Tree Based Discretization for Continuous State Space Reinforcement Learning",
        "source_url": "https://m.aaai.org/Library/AAAI/1998/aaai98-109.php",
        "download_url": "https://www.cs.cmu.edu/~mmv/papers/will-aaai98.pdf",
        "pdf": "papers/aaai_1998_tree_based_discretization.pdf",
        "page": "pages/aaai_1998_tree_based_discretization.html",
        "page_download_url": "https://www.cs.cmu.edu/~coral/old/publications/b2hd-will-aaai98.html",
        "copy_kind": "author-hosted manuscript",
        "archive_note": "The cited legacy AAAI host did not resolve; archived from the authors' CMU publication page.",
        "repo_keys": [],
        "repo_status": "No corresponding public repository confirmed.",
    },
    {
        "id": "DOI:10.1016/S0004-3702(02)00376-4",
        "title": "Equivalence Notions and Model Minimization in Markov Decision Processes",
        "source_url": "https://doi.org/10.1016/S0004-3702(02)00376-4",
        "download_url": "https://engineering.purdue.edu/~givan/papers/mm.pdf",
        "pdf": "papers/doi_10.1016_S0004-3702_02_00376-4.pdf",
        "page": "pages/doi_10.1016_S0004-3702_02_00376-4.html",
        "copy_kind": "author-hosted manuscript",
        "repo_keys": [],
        "repo_status": "No corresponding public repository confirmed.",
    },
    {
        "id": "DOI:10.1609/icaps.v23i1.13605",
        "title": "Counterexample-Guided Cartesian Abstraction Refinement",
        "source_url": "https://ojs.aaai.org/index.php/ICAPS/article/view/13605",
        "download_url": "https://ojs.aaai.org/index.php/ICAPS/article/download/13605/13454",
        "pdf": "papers/doi_10.1609_icaps.v23i1.13605.pdf",
        "page": "pages/doi_10.1609_icaps.v23i1.13605.html",
        "copy_kind": "publisher open-access PDF",
        "repo_keys": ["aibasel/downward"],
    },
    {
        "id": "PMLR:v119/jin20d",
        "title": "Reward-Free Exploration for Reinforcement Learning",
        "source_url": "https://proceedings.mlr.press/v119/jin20d.html",
        "download_url": "https://proceedings.mlr.press/v119/jin20d/jin20d.pdf",
        "pdf": "papers/pmlr_v119_jin20d.pdf",
        "page": "pages/pmlr_v119_jin20d.html",
        "copy_kind": "publisher open-access PDF",
        "repo_keys": [],
        "repo_status": "No repository association is asserted by this registry.",
    },
    {
        "id": "PMLR:v162/wagenmaker22b",
        "title": "Reward-Free RL is No Harder Than Reward-Aware RL in Linear Markov Decision Processes",
        "source_url": "https://proceedings.mlr.press/v162/wagenmaker22b.html",
        "download_url": "https://proceedings.mlr.press/v162/wagenmaker22b/wagenmaker22b.pdf",
        "pdf": "papers/pmlr_v162_wagenmaker22b.pdf",
        "page": "pages/pmlr_v162_wagenmaker22b.html",
        "copy_kind": "publisher open-access PDF",
        "repo_keys": [],
        "repo_status": "No repository association is asserted by this registry.",
    },
    {
        "id": "PMLR:v37/jiang15",
        "title": "Abstraction Selection in Model-based Reinforcement Learning",
        "source_url": "https://proceedings.mlr.press/v37/jiang15.html",
        "download_url": "https://proceedings.mlr.press/v37/jiang15.pdf",
        "pdf": "papers/pmlr_v37_jiang15.pdf",
        "page": "pages/pmlr_v37_jiang15.html",
        "copy_kind": "publisher open-access PDF",
        "repo_keys": [],
        "repo_status": "No repository association is asserted by this registry.",
    },
    {
        "id": "PMLR:v97/rakelly19a",
        "title": "Efficient Off-Policy Meta-Reinforcement Learning via Probabilistic Context Variables",
        "source_url": "https://proceedings.mlr.press/v97/rakelly19a.html",
        "download_url": "https://proceedings.mlr.press/v97/rakelly19a/rakelly19a.pdf",
        "pdf": "papers/pmlr_v97_rakelly19a.pdf",
        "page": "pages/pmlr_v97_rakelly19a.html",
        "copy_kind": "publisher open-access PDF",
        "repo_keys": ["katerakelly/oyster"],
    },
    {
        "id": "PMLR:v54/farahmand17a",
        "title": "Value-Aware Loss Function for Model-based Reinforcement Learning",
        "source_url": "https://proceedings.mlr.press/v54/farahmand17a.html",
        "download_url": "https://proceedings.mlr.press/v54/farahmand17a/farahmand17a.pdf",
        "pdf": "papers/pmlr_v54_farahmand17a.pdf",
        "page": "pages/pmlr_v54_farahmand17a.html",
        "copy_kind": "publisher open-access PDF",
        "repo_keys": [],
        "repo_status": "No repository association is asserted by this registry.",
    },
    {
        "id": "PMLR:v97/shyam19a",
        "title": "Model-Based Active Exploration",
        "source_url": "https://proceedings.mlr.press/v97/shyam19a.html",
        "download_url": "https://proceedings.mlr.press/v97/shyam19a/shyam19a.pdf",
        "pdf": "papers/pmlr_v97_shyam19a.pdf",
        "page": "pages/pmlr_v97_shyam19a.html",
        "copy_kind": "publisher open-access PDF",
        "repo_keys": ["nnaisense/max"],
    },
    {
        "id": "PMLR:v97/gelada19a",
        "title": "DeepMDP: Learning Continuous Latent Space Models for Representation Learning",
        "source_url": "https://proceedings.mlr.press/v97/gelada19a.html",
        "download_url": "https://proceedings.mlr.press/v97/gelada19a/gelada19a.pdf",
        "pdf": "papers/pmlr_v97_gelada19a.pdf",
        "page": "pages/pmlr_v97_gelada19a.html",
        "copy_kind": "publisher open-access PDF",
        "repo_keys": ["jbuckman/dmdp-donutworld"],
    },
    {
        "id": "arXiv:1803.11347",
        "title": "Learning to Adapt in Dynamic, Real-World Environments through Meta-Reinforcement Learning",
        "source_url": "https://arxiv.org/abs/1803.11347",
        "download_url": "https://arxiv.org/pdf/1803.11347",
        "pdf": "papers/arxiv_1803.11347.pdf",
        "page": "pages/arxiv_1803.11347.html",
        "copy_kind": "arXiv author manuscript",
        "repo_keys": [],
        "repo_status": "No repository association is asserted by this registry.",
    },
]


PAGES = [
    {
        "id": "web:2048-wikipedia",
        "title": "2048 (video game)",
        "source_url": "https://en.wikipedia.org/wiki/2048_(video_game)",
        "page": "pages/wikipedia_2048.html",
    },
    {
        "id": "web:sheep-a-sheep-wikipedia",
        "title": "羊了个羊",
        "source_url": "https://zh.wikipedia.org/wiki/羊了个羊",
        "page": "pages/wikipedia_zh_sheep_a_sheep.html",
    },
    {
        "id": "web:solvable-sheep-game",
        "title": "有解的羊了个羊 demo",
        "source_url": "https://solvable-sheep-game.streakingman.com/",
        "page": "pages/solvable_sheep_game.html",
        "repo_keys": ["StreakingMan/solvable-sheep-game"],
    },
    {
        "id": "web:2048-original-support",
        "title": "Original 2048 support",
        "source_url": "https://www.2048original.com/support.html",
        "page": "pages/2048original_support.html",
        "repo_keys": ["gabrielecirulli/2048"],
    },
    {
        "id": "web:barto-publications",
        "title": "A. G. Barto's publications",
        "source_url": "https://people.cs.umass.edu/~barto/pubs-Barto.html",
        "page": "pages/barto_publications.html",
        "quality_note": "Background index only; not a precise citation for a homomorphism or bisimulation claim.",
    },
]


REPOSITORIES = [
    ("chrisvander/2048-Expectimax", "https://github.com/chrisvander/2048-Expectimax.git", "repos/chrisvander__2048-Expectimax", "explicit Markdown reference", "MIT"),
    ("erzhu419/Laplace-semi-MDP", "https://github.com/erzhu419/Laplace-semi-MDP.git", "repos/erzhu419__Laplace-semi-MDP", "explicit Markdown reference and legacy baseline", "MIT"),
    ("ferosas/adaptive-state-action-abstraction", "https://github.com/ferosas/adaptive-state-action-abstraction.git", "repos/ferosas__adaptive-state-action-abstraction", "paper appendix experiment repository", "MIT"),
    ("AAIR-lab/CAT-RL", "https://github.com/AAIR-lab/CAT-RL.git", "repos/AAIR-lab__CAT-RL", "repository URL printed in paper", "GPL-3.0"),
    ("camall3n/markov-state-abstractions", "https://github.com/camall3n/markov-state-abstractions.git", "repos/camall3n__markov-state-abstractions", "repository URL printed in paper", "MIT"),
    ("jeanharb/option_critic", "https://github.com/jeanharb/option_critic.git", "repos/jeanharb__option_critic", "coauthor's exact-paper implementation", "NOASSERTION; no license file"),
    ("philippe-eecs/GCB", "https://github.com/philippe-eecs/GCB.git", "repos/philippe-eecs__GCB", "paper project page code link", "NOASSERTION; no license file"),
    ("tnmichael309/2048AI", "https://github.com/tnmichael309/2048AI.git", "repos/tnmichael309__2048AI", "paper-author implementation cited by paper", "nonstandard permissive license text"),
    ("danijar/dreamerv3", "https://github.com/danijar/dreamerv3.git", "repos/danijar__dreamerv3", "author reimplementation, not original DeepMind experiment artifact", "MIT"),
    ("gabrielecirulli/2048", "https://github.com/gabrielecirulli/2048.git", "repos/gabrielecirulli__2048", "official original-game source used for rule provenance", "MIT"),
    ("aibasel/downward", "https://github.com/aibasel/downward.git", "repos/aibasel__downward", "current official implementation platform named by ICAPS paper; not archival 2013 snapshot", "GPL-3.0"),
    ("StreakingMan/solvable-sheep-game", "https://github.com/StreakingMan/solvable-sheep-game.git", "repos/StreakingMan__solvable-sheep-game", "source linked by cited demo page", "GPL-3.0"),
    ("katerakelly/oyster", "https://github.com/katerakelly/oyster.git", "repos/katerakelly__oyster", "code repository linked by the PEARL paper page; cloned snapshot contains an MIT LICENSE", "MIT"),
    ("nnaisense/max", "https://github.com/nnaisense/max.git", "repos/nnaisense__max", "code repository linked by the MAX paper page", "NOASSERTION; verify after clone"),
    ("jbuckman/dmdp-donutworld", "https://github.com/jbuckman/dmdp-donutworld.git", "repos/jbuckman__dmdp-donutworld", "code repository linked by the DeepMDP paper page", "NOASSERTION; verify after clone"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(relative_path: str, expected_pdf: bool = False) -> dict:
    path = REFERENCE / relative_path
    record = {"path": relative_path, "exists": path.is_file()}
    if not path.is_file():
        return record
    head = path.read_bytes()[:5]
    record.update({"bytes": path.stat().st_size, "sha256": sha256(path)})
    if expected_pdf:
        record["valid_pdf_magic"] = head == b"%PDF-"
    return record


def git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def normalize_url(url: str) -> str:
    parts = urlsplit(url)
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if k != "utm_source"])
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, query, ""))


def entity_for_url(url: str) -> str | None:
    normalized = normalize_url(url)
    arxiv = re.search(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})", normalized)
    if arxiv:
        return f"arXiv:{arxiv.group(1)}"
    pmlr_entities = {
        "v37/jiang15": "PMLR:v37/jiang15",
        "v54/farahmand17a": "PMLR:v54/farahmand17a",
        "v97/gelada19a": "PMLR:v97/gelada19a",
        "v97/rakelly19a": "PMLR:v97/rakelly19a",
        "v97/shyam19a": "PMLR:v97/shyam19a",
        "v119/jin20d": "PMLR:v119/jin20d",
        "v139/choi21b": "PMLR:v139/choi21b",
        "v162/hansen-estruch22a": "PMLR:v162/hansen-estruch22a",
        "v162/wagenmaker22b": "PMLR:v162/wagenmaker22b",
        "v216/dadvar23a": "PMLR:v216/dadvar23a",
    }
    for path_fragment, entity in pmlr_entities.items():
        if f"proceedings.mlr.press/{path_fragment}" in normalized:
            return entity
    if "454cecc4829279e64d624cd8a8c9ddf1" in normalized:
        return "NeurIPS2021:454cecc4829279e64d624cd8a8c9ddf1"
    if "10.1287/opre.1050.0216" in normalized:
        return "DOI:10.1287/opre.1050.0216"
    if "aaai98-109" in normalized.lower():
        return "AAAI98-109"
    if "S0004370202003764" in normalized or "S0004-3702" in normalized:
        return "DOI:10.1016/S0004-3702(02)00376-4"
    if "/ICAPS/article/view/13605" in normalized:
        return "DOI:10.1609/icaps.v23i1.13605"
    if "github.com/chrisvander/2048-Expectimax" in normalized:
        return "repo:chrisvander/2048-Expectimax"
    if "github.com/erzhu419/Laplace-semi-MDP" in normalized:
        return "repo:erzhu419/Laplace-semi-MDP"
    if "github.com/katerakelly/oyster" in normalized:
        return "repo:katerakelly/oyster"
    if "github.com/nnaisense/max" in normalized:
        return "repo:nnaisense/max"
    if "github.com/jbuckman/dmdp-donutworld" in normalized:
        return "repo:jbuckman/dmdp-donutworld"
    mapping = {
        "en.wikipedia.org/wiki/2048_%28video_game%29": "web:2048-wikipedia",
        "zh.wikipedia.org/wiki/%E7%BE%8A%E4%BA%86%E4%B8%AA%E7%BE%8A": "web:sheep-a-sheep-wikipedia",
        "solvable-sheep-game.streakingman.com/": "web:solvable-sheep-game",
        "www.2048original.com/support.html": "web:2048-original-support",
        "people.cs.umass.edu/~barto/pubs-Barto.html": "web:barto-publications",
    }
    for needle, entity in mapping.items():
        if needle in normalized:
            return entity
    return None


def markdown_occurrences() -> list[dict]:
    url_pattern = re.compile(r"https?://[^)>\"\s]+")
    occurrences = []
    for path in sorted((ROOT / "markdown").glob("*.md")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for raw in url_pattern.findall(line):
                raw = raw.rstrip(".,;:")
                occurrences.append(
                    {
                        "file": str(path.relative_to(ROOT)),
                        "line": line_number,
                        "url": raw,
                        "normalized_url": normalize_url(raw),
                        "entity": entity_for_url(raw),
                    }
                )
    return occurrences


def markdown_local_links() -> list[dict]:
    pattern = re.compile(r"\]\(<(?P<target>/home/[^>]+)>\)")
    records = []
    for source in sorted((ROOT / "markdown").glob("*.md")):
        for source_line, text in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            for match in pattern.finditer(text):
                raw_target = match.group("target")
                line_match = re.match(r"^(?P<path>.*):(?P<line>\d+)$", raw_target)
                target_path = Path(line_match.group("path") if line_match else raw_target)
                target_line = int(line_match.group("line")) if line_match else None
                exists = target_path.is_file()
                line_valid = None
                if exists and target_line is not None:
                    line_count = sum(
                        1 for _ in target_path.open(encoding="utf-8", errors="replace")
                    )
                    line_valid = 1 <= target_line <= line_count
                records.append(
                    {
                        "source_file": str(source.relative_to(ROOT)),
                        "source_line": source_line,
                        "raw_target": raw_target,
                        "target_path": str(target_path),
                        "target_line": target_line,
                        "exists": exists,
                        "line_valid": line_valid,
                    }
                )
    return records


def main() -> int:
    now = datetime.now(timezone.utc).isoformat()
    paper_records = []
    failures = []
    for paper in PAPERS:
        record = dict(paper)
        record["pdf_artifact"] = file_record(paper["pdf"], expected_pdf=True)
        record["page_artifact"] = file_record(paper["page"])
        if not record["pdf_artifact"].get("valid_pdf_magic"):
            failures.append(f"missing/invalid PDF: {paper['id']}")
        if not record["page_artifact"].get("exists"):
            failures.append(f"missing source page: {paper['id']}")
        paper_records.append(record)

    page_records = []
    for page in PAGES:
        record = dict(page)
        record["page_artifact"] = file_record(page["page"])
        if not record["page_artifact"].get("exists"):
            failures.append(f"missing page: {page['id']}")
        page_records.append(record)

    occurrences = markdown_occurrences()
    uncovered = [item for item in occurrences if item["entity"] is None]
    local_links = markdown_local_links()
    broken_local_links = [
        item
        for item in local_links
        if not item["exists"] or item["line_valid"] is False
    ]
    if uncovered:
        failures.append(f"{len(uncovered)} Markdown URL occurrences are not classified")
    if broken_local_links:
        failures.append(f"{len(broken_local_links)} Markdown local links are broken")

    classified_direct_entities = {
        item["entity"] for item in occurrences if item["entity"] is not None
    }
    explicit_repository_entities = {
        entity for entity in classified_direct_entities if entity.startswith("repo:")
    }
    download_manifest = {
        "schema_version": 1,
        "generated_at_utc": now,
        "deduplication_order": ["DOI", "arXiv ID", "venue ID", "normalized title"],
        "summary": {
            "paper_entities": len(PAPERS),
            "general_page_entities": len(PAGES),
            "explicit_repository_entities": len(explicit_repository_entities),
            "archived_repository_entities": len(REPOSITORIES),
            "total_external_entities_cited_directly": len(classified_direct_entities),
            "markdown_url_occurrences": len(occurrences),
            "uncovered_url_occurrences": len(uncovered),
            "markdown_local_link_occurrences": len(local_links),
            "broken_local_link_occurrences": len(broken_local_links),
        },
        "papers": paper_records,
        "general_pages": page_records,
        "markdown_occurrences": occurrences,
        "uncovered_occurrences": uncovered,
        "local_link_occurrences": local_links,
        "broken_local_link_occurrences": broken_local_links,
        "source_quality_notes": [
            "Roadmap.md reuses numeric reference labels across conversation sections; raw URLs, not rendered label resolution, are authoritative for this archive.",
            "PRECONSTRUCTION_AUDIT.md also reuses numeric reference labels in separate conversation sections.",
            "Barto's publication index is background only and is not a precise homomorphism/bisimulation citation.",
            "Tracking query parameters are retained in occurrence records but removed during URL normalization.",
            "One malformed absolute Roadmap.md link in GPT_question.md was repaired on 2026-07-19.",
        ],
    }
    (REFERENCE / "download_manifest.json").write_text(
        json.dumps(download_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    repo_records = []
    for key, origin, relative_path, relationship, license_note in REPOSITORIES:
        path = REFERENCE / relative_path
        record = {
            "key": key,
            "origin": origin,
            "path": relative_path,
            "relationship": relationship,
            "license_note": license_note,
            "exists": (path / ".git").is_dir(),
        }
        if record["exists"]:
            record.update(
                {
                    "head": git(path, "rev-parse", "HEAD"),
                    "branch": git(path, "rev-parse", "--abbrev-ref", "HEAD"),
                    "remote": git(path, "remote", "get-url", "origin"),
                    "shallow": git(path, "rev-parse", "--is-shallow-repository") == "true",
                    "license_files": sorted(
                        str(item.relative_to(path))
                        for item in path.iterdir()
                        if item.is_file() and item.name.lower().startswith(("license", "copying"))
                    ),
                }
            )
        else:
            failures.append(f"missing repository: {key}")
        repo_records.append(record)

    repo_manifest = {
        "schema_version": 1,
        "generated_at_utc": now,
        "policy": "Only explicit references or paper/author/page-supported associations are cloned; third-party guesses are excluded.",
        "repositories": repo_records,
        "no_confirmed_official_repository": [
            "arXiv:1911.08265 (MuZero)",
            "PMLR:v139/choi21b (Variational Empowerment)",
            "arXiv:2506.00328 (BASIL)",
            "arXiv:2601.06604 (Object-Centric World Models)",
            "arXiv:1408.6315 (2048 PSPACE-hardness)",
            "DOI:10.1287/opre.1050.0216 (Robust MDP)",
            "arXiv:0807.1173 (MDP CEGAR)",
            "arXiv:2605.17058 (LMTA)",
            "AAAI98-109 (Continuous U Tree)",
            "DOI:10.1016/S0004-3702(02)00376-4 (MDP minimization)",
            "PMLR:v119/jin20d (reward-free exploration)",
            "PMLR:v162/wagenmaker22b (linear reward-free RL)",
            "PMLR:v37/jiang15 (abstraction selection)",
            "PMLR:v54/farahmand17a (value-aware model learning)",
            "arXiv:1803.11347 (meta model-based RL)",
        ],
        "isolation_note": "Reference clones are unmodified research inputs. GPL and NOASSERTION code must not be copied into the project package without a separate license review.",
    }
    (REFERENCE / "repo_clone_manifest.json").write_text(
        json.dumps(repo_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(json.dumps({"papers": len(PAPERS), "pages": len(PAGES), "repos": len(REPOSITORIES), "url_occurrences": len(occurrences), "failures": failures}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
