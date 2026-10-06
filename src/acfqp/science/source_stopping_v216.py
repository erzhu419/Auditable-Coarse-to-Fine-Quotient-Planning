"""Stop paid source acquisition at its certificate, preserving target rules."""
from . import query_calibration_v215 as prior

OPERATORS, ALPHABETS = prior.OPERATORS, prior.ALPHABETS
empty, vectors, queries = prior.empty, prior.vectors, prior.queries


def base_arm(arm):
    return 'CALIBRATE' if arm in ('EARLY', 'FULL') else arm


def make_plan(member, anchors, case, arm, work, identity=None, force_member=False):
    return prior.make_plan(member, anchors, case, base_arm(arm), work, identity, force_member)


def choose(member, anchors, case, arm, plan, spent, work, source=False):
    if source and arm in ('EARLY', 'ORACLE'):
        if spent == 1152:
            return None
        pilot_done = all(sum(member[op].values()) >= 32 for op in OPERATORS)
        if pilot_done and plan['utility_lower'] >= 2:
            return None
    return prior.choose(member, anchors, case, base_arm(arm), plan, spent, work, source)
