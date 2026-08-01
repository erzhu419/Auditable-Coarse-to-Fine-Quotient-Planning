from __future__ import annotations

import pytest

from acfqp import construction_operational_context_v3 as context


def test_owned_no_full_replay_context_is_scoped_and_non_nestable() -> None:
    assert context.operational_no_full_replay_enabled_v3() is False
    with context._activate_owned_no_full_replay_v3():  # noqa: SLF001
        assert context.operational_no_full_replay_enabled_v3() is True
        with pytest.raises(
            context.ConstructionOperationalContextV3Error,
            match="cannot be nested",
        ):
            with context._activate_owned_no_full_replay_v3():  # noqa: SLF001
                pass
    assert context.operational_no_full_replay_enabled_v3() is False


def test_context_resets_after_failure() -> None:
    with pytest.raises(RuntimeError, match="injected"):
        with context._activate_owned_no_full_replay_v3():  # noqa: SLF001
            raise RuntimeError("injected")
    assert context.operational_no_full_replay_enabled_v3() is False
