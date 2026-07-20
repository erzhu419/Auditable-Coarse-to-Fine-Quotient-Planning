"""Collection entry for the Phase-3E route-guard attack cases."""

from __future__ import annotations

import phase3e_route_guard_cases as _cases

from acfqp.auditable_router import LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL


_cases.LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL = (
    LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL
)

test_guarded_local_certificate_recomputes_transaction_actual_work = (
    _cases.test_guarded_local_certificate_recomputes_transaction_actual_work
)
test_negative_causal_result_cannot_select_local_even_with_cheap_bound = (
    _cases.test_negative_causal_result_cannot_select_local_even_with_cheap_bound
)
test_failed_local_work_is_retained_before_certified_fallback = (
    _cases.test_failed_local_work_is_retained_before_certified_fallback
)
