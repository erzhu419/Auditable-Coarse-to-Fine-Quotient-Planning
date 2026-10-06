"""Stateful four-parameter root action preferences over an immutable SOURCE H2."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter, process_time

import numpy as np

from .native_value_stream_v286 import ENVIRONMENT_COUNTS, PLANNING_COUNTS, _parameters, _work

STRATEGY_COUNTS = ('mode_guard_checks', 'mode_entries', 'mode_exits', 'active_choices',
    'source_fallback_choices', 'action_changes', 'feature_evaluations', 'feature_cell_reads',
    'feature_distance_evaluations', 'feature_normalization_divisions',
    'dot_product_multiplications', 'dot_product_additions', 'strategy_score_additions',
    'strategy_memory_writes', 'corner_rank_checks', 'corner_distance_evaluations',
    'zero_source_games', 'game_memory_resets')
_LIBRARIES = {}


def _backend(runtime, setup):
    runtime = Path(runtime).resolve()
    if not runtime.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V297 builds belong inside the research worktree')
    key = str(runtime), os.getpid()
    if key not in _LIBRARIES:
        runtime.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        path = runtime/f'native_strategy_v297_{os.getpid()}.so'
        subprocess.run(['g++','-std=c++17','-O3','-shared','-fPIC','-ffp-contract=off',str(source),
            str(source.with_name('controlled_predictive_frozen_leaf_planning_v135.cpp')),
            str(source.with_name('controlled_predictive_ntuple_kernel_v120.cpp')),
            str(source.with_name('controlled_predictive_contextual_ntuple_v134.cpp')),
            '-o',str(path)],check=True,capture_output=True,text=True,env=dict(os.environ,TMPDIR=str(runtime)))
        setup.update(cpp_compilations=1,cpp_translation_units_compiled=4)
        library=ctypes.CDLL(str(path))
        ip=np.ctypeslib.ndpointer(dtype=np.int32,flags='C_CONTIGUOUS')
        lp=np.ctypeslib.ndpointer(dtype=np.int64,flags='C_CONTIGUOUS')
        dp=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS')
        up=np.ctypeslib.ndpointer(dtype=np.uint64,flags='C_CONTIGUOUS')
        ci,cd=ctypes.c_int,ctypes.c_double
        library.strategy_evaluate_v297.argtypes=[up,ci,dp,ip,ip,ci,ci,dp,ip,lp,ip,
            cd,cd,cd,cd,cd,ci,cd,cd,ci,lp,ip,up,up,up,up]
        library.strategy_evaluate_v297.restype=ci
        library.strategy_selection_v297.argtypes=[ip,ip,ip,dp,ci,ci,dp,ip,dp,up]
        library.strategy_selection_v297.restype=ci
        _LIBRARIES[key]=library
    else:
        setup['cpp_library_cache_hits']+=1
    return _LIBRARIES[key]


def _theta(values):
    theta=np.ascontiguousarray(values,dtype=np.float64)
    if theta.shape!=(4,) or np.any(~np.isfinite(theta)) or np.any(np.abs(theta)>1.):
        raise ValueError('V297 uses four finite action preferences in [-1,1]')
    return theta


class NativeStrategy:
    def __init__(self,leaf,runtime):
        if leaf.weights.flags.writeable:
            raise ValueError('V297 requires an immutable SOURCE value leaf')
        started=perf_counter()
        self.leaf,self.setup_counts=leaf,Counter()
        self.library=_backend(runtime,self.setup_counts)
        self.counts={kind:Counter() for kind in ('environment','planning','strategy')}
        self.setup_seconds=perf_counter()-started

    def evaluate(self,theta4,model_p_four,environment_p_four,seeds,max_steps=8192):
        started,cpu=perf_counter(),process_time()
        theta,seeds=_theta(theta4),np.ascontiguousarray(seeds,dtype=np.uint64)
        n=len(seeds)
        results,final=np.empty((n,3),dtype=np.int64),np.empty((n,16),dtype=np.int32)
        game_work=np.zeros((n,len(STRATEGY_COUNTS)),dtype=np.uint64)
        environment=np.zeros(len(ENVIRONMENT_COUNTS),dtype=np.uint64)
        planning=np.zeros(len(PLANNING_COUNTS),dtype=np.uint64)
        strategy=np.zeros(len(STRATEGY_COUNTS),dtype=np.uint64)
        updates=self.leaf.updates
        code=self.library.strategy_evaluate_v297(seeds,n,theta,*_parameters(self.leaf),
            model_p_four,environment_p_four,max_steps,results,final,game_work,environment,planning,strategy)
        if code:
            raise ValueError('V297 selected an illegal actual standard-world action')
        if self.leaf.updates!=updates or self.leaf.weights.flags.writeable:
            raise ValueError('V297 execution changed the frozen SOURCE learner')
        goal,failure=(float(self.leaf.target_query.get(k,0.)) for k in ('goal_bonus','failure_penalty'))
        rows=[]
        for seed,result,board,behavior in zip(seeds,results,final,game_work):
            score,steps,status=map(int,result)
            rows.append(dict(seed=int(seed),score=score,steps=steps,
                status={1:'WON',-1:'LOST',2:'CUTOFF'}[status],final_board=board.tolist(),
                utility=score/2048.+(goal if status==1 else -failure if status==-1 else 0.),
                strategy_counts={key:int(value) for key,value in zip(STRATEGY_COUNTS,behavior)}))
        counts=dict(environment=_work(ENVIRONMENT_COUNTS,environment),
            planning=_work(PLANNING_COUNTS,planning),strategy=_work(STRATEGY_COUNTS,strategy))
        counts['planning']['choose_calls']=sum(row['steps'] for row in rows)
        for kind,work in counts.items():self.counts[kind].update(work)
        return dict(game_summaries=rows,counts=counts,seconds=perf_counter()-started,cpu_seconds=process_time()-cpu)

    def _selection(self,board,afterstates,legal,root_values,source_action,theta,state=(-1,0,-1)):
        """Finite selector reference: no world execution or new random draws."""
        board=np.ascontiguousarray(board,dtype=np.int32)
        moved=np.ascontiguousarray(afterstates,dtype=np.int32)
        legal=np.ascontiguousarray(legal,dtype=np.int32)
        values=np.ascontiguousarray(root_values,dtype=np.float64)
        state=np.ascontiguousarray(state,dtype=np.int32).copy()
        features=np.zeros((4,4));counts=np.zeros(len(STRATEGY_COUNTS),dtype=np.uint64)
        action=self.library.strategy_selection_v297(board,moved,legal,values,source_action,
            self.leaf.radix,_theta(theta),state,features,counts)
        return dict(action=action,state=state.tolist(),features=features,
                    counts=_work(STRATEGY_COUNTS,counts))
