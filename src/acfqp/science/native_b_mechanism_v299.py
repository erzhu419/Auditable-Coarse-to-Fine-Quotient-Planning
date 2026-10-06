"""Read-only retained-board value, feature-sharing and exact H2 attribution."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter, process_time

import numpy as np

from .controlled_predictive_frozen_leaf_planning_v135 import COUNT_NAMES as PLANNING_COUNTS
from .controlled_predictive_paired_ntuple_v130 import _same_query

COUNT_NAMES=PLANNING_COUNTS+('prediction_terminal_checks','feature_extractions',
    'feature_occurrences','feature_digit_reads','feature_address_multiply_adds',
    'query_shift_additions','second_action_comparisons','root_action_comparisons',
    'fixed_probability_products','fixed_probability_sums','reselected_second_actions')
_LIBRARIES={}


def _backend(runtime,setup):
    runtime=Path(runtime).resolve()
    if not runtime.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V299 builds belong inside the research worktree')
    key=str(runtime),os.getpid()
    if key not in _LIBRARIES:
        runtime.mkdir(parents=True,exist_ok=True)
        source=Path(__file__).with_suffix('.cpp')
        path=runtime/f'native_b_mechanism_v299_{os.getpid()}.so'
        subprocess.run(['g++','-std=c++17','-O3','-shared','-fPIC','-ffp-contract=off',str(source),
            str(source.with_name('controlled_predictive_ntuple_kernel_v120.cpp')),
            str(source.with_name('controlled_predictive_contextual_ntuple_v134.cpp')),
            '-o',str(path)],check=True,capture_output=True,text=True,env=dict(os.environ,TMPDIR=str(runtime)))
        setup.update(cpp_compilations=1,cpp_translation_units_compiled=3)
        library=ctypes.CDLL(str(path))
        ip=np.ctypeslib.ndpointer(dtype=np.int32,flags='C_CONTIGUOUS')
        lp=np.ctypeslib.ndpointer(dtype=np.int64,flags='C_CONTIGUOUS')
        dp=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS')
        up=np.ctypeslib.ndpointer(dtype=np.uint64,flags='C_CONTIGUOUS')
        ci,cd=ctypes.c_int,ctypes.c_double
        library.mechanism_features_v299.argtypes=[ip,ci,ip,ci,lp,up]
        library.mechanism_features_v299.restype=None
        library.mechanism_predict_v299.argtypes=[ip,ci,ip,ci,dp,cd,cd,cd,dp,up]
        library.mechanism_predict_v299.restype=None
        library.mechanism_h2_v299.argtypes=[ip,ci,ip,ci,dp,dp,ip,lp,ip,
            cd,cd,cd,cd,cd,ci,dp,dp,dp,dp,ip,ip,up]
        library.mechanism_h2_v299.restype=None
        _LIBRARIES[key]=library
    else:
        setup['cpp_library_cache_hits']+=1
    return _LIBRARIES[key]


def _boards(leaf,boards,terminal):
    result=np.ascontiguousarray(boards,dtype=np.int32)
    if result.size==0:result=result.reshape(0,16)
    if result.ndim!=2 or result.shape[1]!=16 or np.any(result<0):
        raise ValueError('V299 uses batches of 16 nonnegative board ranks')
    if not terminal and np.any(result>=leaf.radix):
        raise ValueError('winning boards have analytic values and no n-tuple addresses')
    return result


def _result(output,counts,setup,started,cpu):
    return dict(**output,counts={key:int(value) for key,value in zip(COUNT_NAMES,counts) if value},
        setup_counts=dict(setup),seconds=perf_counter()-started,cpu_seconds=process_time()-cpu)


def predict(leaf,boards,runtime):
    started,cpu=perf_counter(),process_time()
    boards=_boards(leaf,boards,True);setup=Counter();library=_backend(runtime,setup)
    predictions=np.empty(len(boards),dtype=np.float64)
    counts=np.zeros(len(COUNT_NAMES),dtype=np.uint64)
    library.mechanism_predict_v299(boards,len(boards),leaf.model.patterns,leaf.radix,leaf.weights,
        float(leaf.target_query.get('goal_bonus',0.)),leaf.failure_shift,leaf.success_shift,predictions,counts)
    return _result(dict(predictions=predictions),counts,setup,started,cpu)


def features(leaf,boards,runtime):
    started,cpu=perf_counter(),process_time()
    boards=_boards(leaf,boards,False);setup=Counter();library=_backend(runtime,setup)
    output=np.empty((len(boards),32),dtype=np.int64)
    counts=np.zeros(len(COUNT_NAMES),dtype=np.uint64)
    library.mechanism_features_v299(boards,len(boards),leaf.model.patterns,leaf.radix,output,counts)
    return _result(dict(features=output),counts,setup,started,cpu)


def decompose_h2(source_leaf,current_leaf,root_boards,model_p,runtime):
    """Keep SOURCE second actions fixed to separate value change from maximization."""
    started,cpu=perf_counter(),process_time()
    source,current=source_leaf,current_leaf
    if (source.radix!=current.radix or source.kind!=current.kind
            or not _same_query(source.source_query,current.source_query)
            or not _same_query(source.target_query,current.target_query)
            or (source.failure_shift,source.success_shift)!=(current.failure_shift,current.success_shift)
            or not np.array_equal(source.model.patterns,current.model.patterns)
            or not np.array_equal(source.model.table,current.model.table)
            or not np.array_equal(source.model.scores,current.model.scores)
            or not np.array_equal(source.model.cells,current.model.cells)):
        raise ValueError('H2 attribution holds the query, n-tuple features and learned rewrite fixed')
    boards=_boards(source,root_boards,True);n=len(boards)
    probabilities=np.ascontiguousarray(np.broadcast_to(model_p,(n,)),dtype=np.float64)
    if np.any(~np.isfinite(probabilities)) or np.any((probabilities<0.)|(probabilities>1.)):
        raise ValueError('the learned rank-two probabilities must lie in [0,1]')
    setup=Counter();library=_backend(runtime,setup)
    source_q,current_q,fixed_q=[np.full((n,4),-np.inf,dtype=np.float64) for _ in range(3)]
    legal=np.zeros((n,4),dtype=np.int32);selected=np.full((n,3),-1,dtype=np.int32)
    counts=np.zeros(len(COUNT_NAMES),dtype=np.uint64)
    raw_query=source.source_query if source.kind=='PRIOR' else source.target_query
    library.mechanism_h2_v299(boards,n,source.model.patterns,source.radix,source.weights,
        current.weights,source.model.table,source.model.scores,source.model.cells,
        float(raw_query.get('goal_bonus',0.)),float(source.target_query.get('goal_bonus',0.)),
        float(source.target_query.get('failure_penalty',0.)),source.failure_shift,source.success_shift,
        int(source.kind=='PRIOR' and not _same_query(source.source_query,source.target_query)),
        probabilities,source_q,current_q,fixed_q,legal,selected,counts)
    return _result(dict(source_q=source_q,current_q=current_q,frozen_second_q=fixed_q,
        legal=legal.astype(bool),source_actions=selected[:,0],current_actions=selected[:,1],
        frozen_second_actions=selected[:,2]),counts,setup,started,cpu)
