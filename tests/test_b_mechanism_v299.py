"""Retained B facts, exact segmented replay, and after-current-action targets."""
from fractions import Fraction
import gzip
import json
from pathlib import Path

import numpy as np

from acfqp.domains import standard_2048 as ground
from acfqp.science import b_mechanism_v299 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.native_episode_consolidation_v290 import fit_consolidated
from acfqp.science.retained_critic_v287 import compact_dataset
from test_stable_b_v298 import acquire_b

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'reports/b_mechanism_v299/runtime/driver_tests'


def test_reader_recovers_preaction_boards_for_exact_blind_b_panel(monkeypatch,tmp_path):
    records=[]
    original=acquire_b(monkeypatch,tmp_path,records)
    old=dict(lifecycle=21,parent=1,dataset=compact_dataset(original['dataset']),
        acquisition=original['acquisition'])
    trace=tmp_path/'b_records.jsonl.gz'
    with gzip.open(trace,'wt') as stream:
        for row in records: stream.write(json.dumps(row)+'\n')
    data,roots,receipt=core.load_parent(dict(lifecycle_ids=[21],trace_file=str(trace)),{21:old})
    assert receipt['canonical_rows_read']==len(records)
    assert set(roots[21])==set(core.roster(old))
    np.testing.assert_array_equal(data[21]['afterstates'],original['dataset']['afterstates'])
    assert data[21]['games']==original['dataset']['games']
    for step,row in roots[21].items():
        after,score,changed=ground.swipe_board_v1(tuple(row['board_before_action']),ground.Swipe2048Action(row['action']))
        assert changed and score==row['score']
        assert list(after)==data[21]['afterstates'][step].tolist()


def test_targets_exclude_current_reward_and_keep_terminal_utility_once():
    data=dict(rewards=np.array([1.,2.,3.,4.,5.]),ends=np.array([3,5]),terminal_codes=np.array([1,-1]))
    np.testing.assert_array_equal(core.targets(data,4.,4.),[9.,7.,4.,1.,-4.])


def test_segmented_mean_replay_reproduces_original_fit_and_full_heldout():
    from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
    from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics,RewriteProgram
    from acfqp.science.natural_model_revision_v281 import QUERY
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',3)
    native=NtupleValue(rule,BUILD)
    template=QueryTD(QueryParent(native,QUERY,QUERY,.5),'PRIOR',BUILD); template.freeze()
    board=np.asarray([1,1,0,0]+[0]*12,dtype=np.int32)
    games=[dict(episode=i,steps=n,status='LOST',split='FIT' if i<2 else 'HELDOUT') for i,n in enumerate([2,2,3])]
    data=dict(afterstates=np.tile(board,(7,1)),rewards=np.asarray([.1,.2,.3,.4,.5,.6,.7]),
        ends=np.asarray([2,4,7],dtype=np.int64),terminal_codes=np.full(3,-1,dtype=np.int32),
        fit_game_count=2,fit_step_end=4,fit_end_raw=8,fit_memory={},costs={},games=games)
    base=core.full_score(template,data,BUILD)
    original=QueryTD(template.parent,'PRIOR',BUILD)
    fitted=fit_consolidated(original,data,'EPISODE_MEAN_MC',BUILD)
    final=core.full_score(original,data,BUILD)
    old=dict(lifecycle=0,parent=0,dataset=compact_dataset(data),
        evaluation_snapshot={'estimated_p_four':.5},arms=dict(
            FROZEN=dict(heldout={'game_metrics':core.original_heldout(base)}),
            EPISODE_MEAN_MC=dict(fit=fitted,heldout={'game_metrics':core.original_heldout(final)})))
    roots={i:dict(board_before_action=board.tolist(),action='LEFT',score=4,acquisition_model_p_four=.5)
        for i in core.roster(old)}
    emitted=[]
    result=core.replay_life(template,data,roots,old,BUILD,emitted.append)
    assert result['reproduction']['original_fit_nonpeak_counts_and_examples_exact']
    assert result['reproduction']['original_source_and_mean_full_heldout_exact']
    assert len(result['updates'])==2 and len(result['snapshots'])==3
    assert all(u['local_mse_after']<=u['local_mse_before'] for u in result['updates'])
    delta=np.sum([u['delta_predictions'] for u in result['updates']],axis=0)
    np.testing.assert_allclose(delta,np.array(result['snapshots'][-1]['predictions'])-result['snapshots'][0]['predictions'],atol=1e-14)
    assert template.updates==0 and not template.weights.flags.writeable
    assert [r['kind'] for r in emitted].count('PANEL')==1
    assert [r['kind'] for r in emitted].count('GAME')==2
