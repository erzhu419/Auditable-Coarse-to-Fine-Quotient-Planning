"""Allocate the unchanged paid source budget to current certificate bottlenecks."""
from . import query_sufficient_v214 as prior

OPERATORS, ALPHABETS = prior.OPERATORS, prior.ALPHABETS
empty, vectors, queries = prior.empty, prior.vectors, prior.queries


def base_arm(arm):
    return 'SET' if arm == 'CALIBRATE' else arm


def make_plan(member, anchors, case, arm, work, identity=None, force_member=False):
    return prior.make_plan(member, anchors, case, base_arm(arm), work, identity, force_member)


def choose(member, anchors, case, arm, plan, spent, work, source=False):
    if source and arm in ('CALIBRATE', 'ORACLE'):
        if spent == 1152:
            return None
        counts = {op: sum(member[op].values()) for op in OPERATORS}
        least = min(OPERATORS, key=lambda op: (counts[op], OPERATORS.index(op)))
        if counts[least] < 32:
            return dict(operator=least, reason='calibration_pilot', counts=counts)
        if plan['utility_lower'] < 2:
            detail = prior.prior.choose(member, [], case, 'LOCAL', plan, spent, work, source=True)['detail']
            return dict(operator=detail['operator'], reason='calibration_certificate', detail=detail)
        return dict(operator=least, reason='calibration_balance', counts=counts)
    return prior.choose(member, anchors, case, base_arm(arm), plan, spent, work, source)
