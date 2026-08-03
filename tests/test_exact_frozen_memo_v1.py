from __future__ import annotations

from acfqp.exact_frozen_memo_v1 import (
    disable_exact_frozen_memoization_v1,
    exact_frozen_memoization_enabled_v1,
)


def test_disable_switch_is_nested_and_context_local() -> None:
    assert exact_frozen_memoization_enabled_v1()
    with disable_exact_frozen_memoization_v1():
        assert not exact_frozen_memoization_enabled_v1()
        with disable_exact_frozen_memoization_v1():
            assert not exact_frozen_memoization_enabled_v1()
        assert not exact_frozen_memoization_enabled_v1()
    assert exact_frozen_memoization_enabled_v1()
