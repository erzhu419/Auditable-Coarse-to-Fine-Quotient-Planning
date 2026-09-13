"""A small real multi-board H1 contract, including its lifted failure risk."""
from collections import Counter
import json
from pathlib import Path

from acfqp.science.controlled_predictive_2048_v1 import build_development_closure
from acfqp.science.controlled_predictive_action_contract_v67 import build_model,encode_key
from acfqp.science.controlled_predictive_causal_audit_v67 import compute_reference,audit_build
from acfqp.science.controlled_predictive_quotient_v1 import Query,compile_full_state,plan

ROOT=Path(__file__).resolve().parents[1]


def test_real_many_to_one_H1_contract_preserves_full_risk_queries():
    board=(10,9,1,1)+(0,)*12
    closure=build_development_closure(horizon=2,max_nodes=30000,boards={'hand_sparse_contract':board})
    queries={'reward':Query(),'risk':Query(failure_penalty=1.)}
    reference=compute_reference(closure,queries)
    fees=Counter({'ground_'+n:value for n,value in closure.counts.items()});fees.update(reference.counts)
    results,builds={},{}
    for variant in ('BASELINE','CONTRACT'):
        build=build_model(board,2,variant,max_states=30000);builds[variant]=build
        fees.update({'build_'+n:value for n,value in build.counts.items()})
        compiled=compile_full_state(build.model);fees['singleton_compilations']+=1
        solutions={name:plan(compiled,query) for name,query in queries.items()}
        for solution in solutions.values(): fees.update({'plan_'+n:value for n,value in solution.counts.items()})
        results[variant]=audit_build(build,closure,queries,solutions,reference,compiled)
        fees.update(results[variant]['counts'])
    h1=[state for state in closure.model.layers if closure.model.layers[state]==1 and closure.model.terminal[state]=='ACTIVE']
    baseline_keys={encode_key(closure.boards[state],1,builds['BASELINE'].rule) for state in h1}
    contract_keys={encode_key(closure.boards[state],1,builds['CONTRACT'].rule) for state in h1}
    fees['additional_encoder_queries']=2*len(h1)
    ledger=dict(schema='acfqp.controlled_predictive_action_contract_audit_checks.v67',development_work=dict(fees,
        random_samples=0,main_root_evaluations=0,reference_calls=1,
        scope='One H2 hand root outside the old 16 roots; two model arms and two frozen queries. No prior V66 audit suite rerun.'),
        concrete_active_H1_states=len(h1),baseline_H1_keys=len(baseline_keys),contract_H1_keys=len(contract_keys))
    (ROOT/'reports/controlled_predictive_action_contract_v67.audit_checks.json').write_text(json.dumps(ledger,indent=2)+'\n')
    assert len(contract_keys)<len(baseline_keys)==len(h1)
    assert all(result['valid'] for result in results.values()),results
    for name in queries:
        left=results['BASELINE']['queries'][name]['root_metrics'][0]['actual']
        right=results['CONTRACT']['queries'][name]['root_metrics'][0]['actual']
        assert left==right and 0<=right['failure']<=1
        assert results['CONTRACT']['queries'][name]['maximum_value_loss']<=1e-12
