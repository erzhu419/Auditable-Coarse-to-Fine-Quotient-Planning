"""Shared expensive construction fixtures.

The genuine K7 production-positive substrate performs the exact private
execution once per pytest session.  Every downstream semantic layer still
replays the complete immutable roots; sharing only removes duplicate fixture
construction across test modules.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def positive(tmp_path_factory):
    from tests import (  # Imported lazily to avoid collection-time cycles.
        test_construction_occurrence_identity_cutoff_semantic_authority_v2
        as occurrence_test,
    )

    yield from occurrence_test._positive_session_resources(tmp_path_factory)  # noqa: SLF001
