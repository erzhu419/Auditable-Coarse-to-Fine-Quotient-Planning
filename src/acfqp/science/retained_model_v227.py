"""Keep compatible model knowledge when terminal execution falls back to a member."""
from . import limited_source_v226 as prior

ARMS, OPERATORS, ALPHABETS = prior.ARMS, prior.OPERATORS, prior.ALPHABETS
SOURCE_BETA = prior.SOURCE_BETA
MEMBER_THRESHOLD, POOL_THRESHOLD = prior.MEMBER_THRESHOLD, prior.POOL_THRESHOLD
empty, vectors, queries = prior.empty, prior.vectors, prior.queries
prepare, make_plan, choose, advance = prior.prepare, prior.make_plan, prior.choose, prior.advance
clear_cache = prior.clear_cache


def finish(member, anchors, case, arm, work, state, plan):
    """Resolve original execution eligibility while retaining the observed model."""
    fallback = len(plan['candidates']) != 1 and not plan['query_ready']
    execution = (make_plan(member, anchors, case, arm, work, state, force_member=True)
                 if fallback else plan)
    certified = execution['utility_lower'] >= 2
    identified = len(execution['candidates']) == 1 and certified
    transferred = (certified and execution['mode'] == 'library'
                   and (identified or execution['query_ready']))
    stop = ('member_budget' if fallback else 'query_set' if transferred and not identified
            else 'identified' if identified else 'member_certified' if certified else 'budget')
    knowledge = plan if plan['mode'] == 'library' and plan['candidates'] else execution
    return dict(execution_plan=execution, knowledge_plan=knowledge, queries=queries(knowledge),
                fallback=fallback, certified=certified, identified=identified,
                transferred=transferred, stop=stop, knowledge_mode=knowledge['mode'],
                knowledge_candidates=list(knowledge['candidates']),
                knowledge_query_ready=knowledge['query_ready'])
