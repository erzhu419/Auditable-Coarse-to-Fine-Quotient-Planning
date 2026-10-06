"""Offline factual TD/MC critics and fixed heldout-return scoring."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter, process_time

import numpy as np

LEARNING_COUNTS = ('td_updates','value_predictions','table_lookups','table_updates','table_update_occurrences')
TARGET_COUNTS = ('goal_checks','analytic_next_tails','terminal_target_assignments',
    'td_next_reward_additions','suffix_games','suffix_target_assignments',
    'suffix_reward_additions','raw_target_subtractions','prediction_shift_additions',
    'skipped_winning_afterstates','target_buffer_doubles_peak')
_LIBRARIES = {}


def _backend(build_dir, counts):
    build_dir=Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V287 builds belong inside the research worktree')
    key=str(build_dir),os.getpid()
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True,exist_ok=True)
        source=Path(__file__).with_suffix('.cpp')
        path=build_dir/f'native_retained_critic_v287_{os.getpid()}.so'
        subprocess.run(['g++','-std=c++17','-O3','-shared','-fPIC','-ffp-contract=off',
            str(source),str(source.with_name('controlled_predictive_ntuple_kernel_v120.cpp')),
            '-o',str(path)],check=True,capture_output=True,text=True,
            env=dict(os.environ,TMPDIR=str(build_dir)))
        counts.update(cpp_compilations=1,cpp_translation_units_compiled=2)
        library=ctypes.CDLL(str(path))
        ip=np.ctypeslib.ndpointer(dtype=np.int32,flags='C_CONTIGUOUS')
        lp=np.ctypeslib.ndpointer(dtype=np.int64,flags='C_CONTIGUOUS')
        dp=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS')
        up=np.ctypeslib.ndpointer(dtype=np.uint64,flags='C_CONTIGUOUS')
        ci,cd=ctypes.c_int,ctypes.c_double
        library.fit_retained_v287.argtypes=[ip,dp,lp,ip,ci,ip,ci,dp,cd,cd,cd,cd,cd,ci,up,up,lp,dp]
        library.fit_retained_v287.restype=None
        library.score_retained_v287.argtypes=[ip,dp,lp,ip,ci,ci,ip,ci,dp,cd,cd,cd,cd,dp,up,up]
        library.score_retained_v287.restype=None
        _LIBRARIES[key]=library
    else:
        counts['cpp_library_cache_hits']+=1
    return _LIBRARIES[key]


def _arrays(dataset):
    return [np.ascontiguousarray(dataset[key],dtype=dtype) for key,dtype in (
        ('afterstates',np.int32),('rewards',np.float64),('ends',np.int64),('terminal_codes',np.int32))]


def _parameters(leaf):
    return [leaf.model.patterns,leaf.radix,leaf.weights,
        float(leaf.target_query.get('goal_bonus',0.)),float(leaf.target_query.get('failure_penalty',0.)),
        leaf.failure_shift,leaf.success_shift]


def _work(names,values):
    return {name:int(value) for name,value in zip(names,values) if value}


def _charge(leaf,work):
    leaf.model.counts.update(work)
    leaf.model.updates+=work.get('td_updates',0)
    leaf.counts.update({f'inner_{name}':value for name,value in work.items()})
    leaf.counts['td_updates']+=work.get('td_updates',0)


def fit_retained(leaf,dataset,method,build_dir,alpha=.0025):
    if method not in ('TD','MC'):
        raise ValueError('V287 fits the frozen TD or MC method')
    if not leaf.weights.flags.writeable:
        raise ValueError('the fitted shadow critic must be writable')
    started,cpu_started=perf_counter(),process_time()
    setup_counts=Counter(); library=_backend(build_dir,setup_counts)
    arrays=_arrays(dataset)
    n_games=int(dataset['fit_game_count']); fit_end=int(dataset['fit_step_end'])
    if (int(arrays[2][n_games-1]) if n_games else 0)!=fit_end:
        raise ValueError('the fit boundary must end the frozen prefix of complete games')
    learning,targets=np.zeros(5,dtype=np.uint64),np.zeros(len(TARGET_COUNTS),dtype=np.uint64)
    indices,values=np.empty((2,2),dtype=np.int64),np.empty((2,4),dtype=np.float64)
    library.fit_retained_v287(*arrays,n_games,*_parameters(leaf),alpha,int(method=='MC'),
        learning,targets,indices,values)
    work=_work(LEARNING_COUNTS,learning)
    _charge(leaf,work)
    def example(index):
        if not work.get('td_updates',0):
            return None
        game,step=map(int,indices[index]); target,raw_target,error,before=map(float,values[index])
        return dict(episode=game,step=step,target=target,raw_target=raw_target,error=error,
                    raw_prediction_before_update=before)
    return dict(method=method,fitted_games=n_games,fitted_steps=fit_end,
        trained_afterstates=work.get('td_updates',0),learning_counts=work,
        target_counts=_work(TARGET_COUNTS,targets),first_update=example(0),last_update=example(1),
        setup_counts=dict(setup_counts),seconds=perf_counter()-started,cpu_seconds=process_time()-cpu_started)


def score_retained(leaf,dataset,build_dir):
    started,cpu_started=perf_counter(),process_time()
    setup_counts=Counter(); library=_backend(build_dir,setup_counts)
    arrays=_arrays(dataset)
    first,n_games=int(dataset['fit_game_count']),len(arrays[2])
    output=np.empty((n_games-first,6),dtype=np.float64)
    predictions,targets=np.zeros(5,dtype=np.uint64),np.zeros(len(TARGET_COUNTS),dtype=np.uint64)
    library.score_retained_v287(*arrays,first,n_games,*_parameters(leaf),output,predictions,targets)
    work=_work(LEARNING_COUNTS,predictions)
    _charge(leaf,work)
    games=[]
    for index,row in enumerate(output,first):
        count,bias,mse,mae,prediction,target=map(float,row)
        games.append(dict(episode=index,start=int(arrays[2][index-1]) if index else 0,
            end=int(arrays[2][index]),count=int(count),bias=bias,mse=mse,mae=mae,
            mean_prediction=prediction,mean_factual_future_utility=target))
    return dict(game_metrics=games,metrics={key:sum(g[key] for g in games)/len(games)
        for key in ('bias','mse','mae')},prediction_counts=work,target_counts=_work(TARGET_COUNTS,targets),
        setup_counts=dict(setup_counts),seconds=perf_counter()-started,cpu_seconds=process_time()-cpu_started)
