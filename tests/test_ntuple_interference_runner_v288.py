"""Retained-label and direct-leaf boundaries for the V288 runner."""
from collections import Counter
import gzip
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from acfqp.science import ntuple_interference_runner_v288 as core

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'reports/ntuple_interference_v288/runtime/driver_tests'


def test_retained_labels_exclude_first_reward_and_require_two_complete_batches():
    BUILD.mkdir(parents=True,exist_ok=True)
    path=BUILD/'finite_labels.jsonl.gz'
    state=dict(state_id='L00-A-0',phase='A',legal_actions=['LEFT'],immediate_scores={'LEFT':64})
    rows=[dict(state_id=state['state_id'],action='LEFT',batch=batch,replica_index=i,
        first_score=64,total_score=64+4*i,status='LOST',steps=10,
        suffix_utility=4*i/2048.-4.) for batch in ('discovery','validation') for i in range(32)]
    def write():
        with gzip.open(path,'wt') as f:
            for row in rows:f.write(json.dumps(row)+'\n')
    write()
    result=core.read_labels({'states':[state],'trace_file':str(path)})
    assert result['labels'][state['state_id'],'LEFT']['discovery']==[4*i/2048.-4. for i in range(32)]
    assert result['counts']['retained_A_rollouts']==64
    assert result['counts']['retained_A_environment_transitions']==640
    rows[0]['suffix_utility']+=64/2048.
    write()
    with pytest.raises(ValueError,match='current action'):core.read_labels({'states':[state],'trace_file':str(path)})
    rows.pop(0);write()
    with pytest.raises(ValueError,match='complete independent'):core.read_labels({'states':[state],'trace_file':str(path)})


def test_queries_use_direct_leaf_in_query_units_not_h2_proxy():
    board=[0]*16;board[0]=board[1]=1
    state=dict(state_id='L00-A-0',lifecycle=0,parent=0,group='uniform',board=board,
        legal_actions=['LEFT'],immediate_scores={'LEFT':4},full_tail_scores={'LEFT':999.})
    model=SimpleNamespace(value=lambda b:7.,feature_indices=lambda b:np.arange(32,dtype=np.int64))
    leaf=SimpleNamespace(radix=11,model=model,failure_shift=2.,success_shift=1.)
    labels={(state['state_id'],'LEFT'):{'discovery':[-4.]*32,'validation':[-4.]*32}}
    counts=Counter();rows=core.build_queries(leaf,state,labels,counts)
    assert rows[0]['prediction']==10. and rows[0]['raw_prediction']==7.
    assert rows[0]['afterstate'][0]==2 and rows[0]['first_score']==4
    assert counts==dict(deterministic_swipe_reconstructions=1,direct_leaf_predictions=1,feature_occurrences_encoded=32)


def test_pair_matrix_keeps_protected_targets_and_resets_every_hypothetical_update():
    queries=[dict(state_id=f'L00-A-{i}',action='LEFT',features=list(range(32*i,32*(i+1))),
        prediction=2.+i,discovery=[4.]*32,validation=[5.]*32) for i in range(2)]
    before=json.loads(json.dumps(queries));counts=Counter()
    pairs=core.build_pairs(queries,counts)
    assert len(pairs)==4 and queries==before
    protected=[p for p in pairs if p['donor_state_id']!=p['target_state_id']]
    assert all(p['kernel']==0 and p['mean_label_delta_mse']==0 and p['empirical_noise_penalty']==0 for p in protected)
    assert counts['feature_pair_inner_products']==counts['isolated_update_pair_diagnostics']==4
