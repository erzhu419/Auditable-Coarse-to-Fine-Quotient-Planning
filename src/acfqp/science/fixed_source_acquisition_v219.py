"""Compare settled target acquisition rules under identical retained source counts."""
from . import joint_acquisition_v218 as prior

OPERATORS, ALPHABETS = prior.OPERATORS, prior.ALPHABETS
empty, vectors, queries = prior.empty, prior.vectors, prior.queries


def base_arm(arm):
    return {'MEAN': 'MEMBER', 'SET': 'FULL'}.get(arm, arm)


def make_plan(member, anchors, case, arm, work, identity=None, force_member=False):
    return prior.make_plan(member, anchors, case, base_arm(arm), work, identity, force_member)


def choose(member, anchors, case, arm, plan, spent, work):
    return prior.choose(member, anchors, case, base_arm(arm), plan, spent, work)
