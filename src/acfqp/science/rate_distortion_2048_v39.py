"""Exact public 2048 models for the external rate-distortion reference code.

BA uses only real legal state-action pairs and one zero-value absorbing pair.
The author's rectangular Bellman API receives duplicate computation slots for
illegal actions. Those slots have no BA prior mass and cannot be executed.
The fixed completion does affect the author's same-action distortion geometry.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np

from .controlled_predictive_2048_v1 import DevelopmentClosure, PUBLIC_DEVELOPMENT_BOARDS, build_development_closure

ACTION_LABELS=("DOWN","LEFT","RIGHT","UP","TERMINAL")


@dataclass(frozen=True)
class Exact2048Adapter:
    mdp: Any
    closure: DevelopmentClosure
    legal_mask: np.ndarray
    valid_pair_indices: np.ndarray
    rect_to_valid_pair: np.ndarray
    source_to_state: dict[int,int]
    state_to_source: tuple[int | None,...]
    terminal_state: int
    root_states: tuple[int,...]

    @property
    def num_valid_pairs(self) -> int:
        return int(self.valid_pair_indices.size)

    @property
    def rectangular_alias_indices(self) -> np.ndarray:
        """Each rectangular slot maps to a real legal rectangular pair index."""
        return self.valid_pair_indices[self.rect_to_valid_pair]

    @property
    def uniform_legal_prior(self) -> np.ndarray:
        return np.full(self.num_valid_pairs,1./self.num_valid_pairs,dtype=float)

    def inventory(self) -> dict[str,Any]:
        return {"original_states":len(self.closure.model.layers),"states":self.mdp.num_states,
            "active_states":self.terminal_state,"collapsed_zero_value_terminal_states":len(self.closure.model.layers)-self.terminal_state,
            "legal_state_action_pairs":self.num_valid_pairs,"rectangular_computation_slots":self.mdp.num_state_action_pairs,
            "illegal_computation_slots":int((~self.legal_mask).sum()),"transition_tensor_bytes":self.mdp.transitions.nbytes,
            "legal_pair_distance_bytes":8*self.num_valid_pairs**2,"rectangular_pair_distance_bytes":8*self.mdp.num_state_action_pairs**2,
            "alias_rule":"Each illegal slot copies the state's lexicographically first legal action; the absorbing state uses only TERMINAL.",
            "metric_scope":"Author same-action fixed-point metric on this explicit rectangular completion, restricted to legal pairs; not invariant to completion choice."}


def build_exact_2048_adapter(case_name: str,author_abstraction: Any,*,horizon: int=2,gamma: float=.95,max_nodes: int=30000) -> Exact2048Adapter:
    """Enumerate one public board completely; fixed merge reward and zero terminals."""
    closure=build_development_closure(horizon=horizon,max_nodes=max_nodes,boards={case_name:PUBLIC_DEVELOPMENT_BOARDS[case_name]})
    return adapter_from_closure(closure,author_abstraction,gamma=gamma)


def adapter_from_closure(closure: DevelopmentClosure,author_abstraction: Any,*,gamma: float=.95) -> Exact2048Adapter:
    """Collapse terminal states only; preserve every active state and legal action."""
    model=closure.model
    active=tuple(state for state in sorted(model.layers) if model.terminal[state]=="ACTIVE")
    terminal=len(active); states=terminal+1; actions=len(ACTION_LABELS)
    source_to_state={state:index for index,state in enumerate(active)}
    source_to_state.update({state:terminal for state in model.layers if model.terminal[state]!="ACTIVE"})
    transitions=np.zeros((states,actions,states),dtype=float)
    rewards=np.zeros((states,actions),dtype=float)
    mask=np.zeros((states,actions),dtype=bool)
    for state in active:
        index=source_to_state[state]
        for action_index,action in enumerate(ACTION_LABELS[:-1]):
            outcomes=model.rows.get((state,action))
            if outcomes is None: continue
            mask[index,action_index]=True
            by_successor:dict[int,list[float]]={}
            for outcome in outcomes:
                by_successor.setdefault(source_to_state[outcome.next_state],[]).append(outcome.probability)
            for successor,probabilities in by_successor.items(): transitions[index,action_index,successor]=math.fsum(probabilities)
            rewards[index,action_index]=math.fsum(outcome.probability*outcome.reward for outcome in outcomes)
    mask[terminal,-1]=True; transitions[terminal,-1,terminal]=1.
    valid=np.flatnonzero(mask.reshape(-1))
    lookup={int(pair):index for index,pair in enumerate(valid)}
    rect_to_valid=np.empty(states*actions,dtype=int)
    for state in range(states):
        legal=np.flatnonzero(mask[state])
        if not legal.size: raise ValueError("An active source state has no legal action")
        first=int(legal[0])
        for action in range(actions):
            representative=action if mask[state,action] else first
            rect_to_valid[state*actions+action]=lookup[state*actions+representative]
            if not mask[state,action]:
                transitions[state,action]=transitions[state,representative]
                rewards[state,action]=rewards[state,representative]
    labels=[(model.layers[state],closure.boards[state]) for state in active]+[("terminal",)]
    mdp=author_abstraction.TabularMDP(transitions=transitions,rewards=rewards,gamma=gamma,state_labels=labels,action_labels=list(ACTION_LABELS))
    return Exact2048Adapter(mdp,closure,mask,valid,rect_to_valid,source_to_state,(*active,None),terminal,tuple(source_to_state[root] for root in model.roots))


def author_fixed_point_distortion(adapter: Exact2048Adapter,author_metric: Any,*,tol: float=1e-6,max_iter: int=40,num_workers: int=1,verbose: bool=False) -> np.ndarray:
    """Call the author's stochastic Wasserstein metric, then restrict BA support."""
    rectangular=author_metric.compute_sysadmin_fixed_point_bisimulation_metric(adapter.mdp,tol=tol,max_iter=max_iter,num_workers=num_workers,verbose=verbose)
    return np.asarray(rectangular[np.ix_(adapter.valid_pair_indices,adapter.valid_pair_indices)],dtype=float)


def fit_author_abstraction(adapter: Exact2048Adapter,distance: np.ndarray,author_abstraction: Any,*,beta: float,num_abstract: int,
        max_outer: int=200,max_inner: int=50,tolerance: float=1e-6) -> Any:
    """Independent flat BA fit in legal pair space, with no alias reweighting."""
    if distance.shape!=(adapter.num_valid_pairs,adapter.num_valid_pairs):
        raise ValueError("BA distance must contain only the legal pair support")
    return author_abstraction.fit_soft_abstraction(distortion=distance,mu=adapter.uniform_legal_prior,beta=beta,num_abstract=num_abstract,
        max_outer=max_outer,max_inner=max_inner,tolerance=tolerance,solver_kind="flat")


def embed_author_abstraction(adapter: Exact2048Adapter,legal_abstraction: Any,author_abstraction: Any) -> Any:
    """Embed only for the author's Q/AD calls; fit and information use legal input."""
    if legal_abstraction.encoder.shape[0]!=adapter.num_valid_pairs:
        raise ValueError("The fitted encoder must use the legal pair support")
    posterior=np.zeros((adapter.mdp.num_state_action_pairs,legal_abstraction.posterior.shape[1]),dtype=float)
    posterior[adapter.valid_pair_indices]=legal_abstraction.posterior
    return author_abstraction.StateActionAbstraction(beta=legal_abstraction.beta,
        encoder=legal_abstraction.encoder[adapter.rect_to_valid_pair],posterior=posterior,
        decoder=adapter.valid_pair_indices[np.asarray(legal_abstraction.decoder,dtype=int)],
        full_encoder=legal_abstraction.full_encoder[adapter.rect_to_valid_pair],
        full_decoder=adapter.valid_pair_indices[np.asarray(legal_abstraction.full_decoder,dtype=int)],solver_kind=legal_abstraction.solver_kind)


def author_bellman_update(adapter: Exact2048Adapter,legal_q: np.ndarray,author_planning: Any) -> np.ndarray:
    """Apply the unmodified author Bellman update to legal Q via exact aliases."""
    values=np.asarray(legal_q,dtype=float)
    if values.shape!=(adapter.num_valid_pairs,): raise ValueError("Q must be indexed by legal pairs")
    updated=author_planning.bellman_update(adapter.mdp,values[adapter.rect_to_valid_pair])
    return updated[adapter.valid_pair_indices]


def greedy_legal_policy(adapter: Exact2048Adapter,grounded_rect_q: np.ndarray) -> np.ndarray:
    """Select only real legal actions, including when all grounded values tie."""
    values=np.asarray(grounded_rect_q,dtype=float).reshape(adapter.legal_mask.shape)
    return np.argmax(np.where(adapter.legal_mask,values,-np.inf),axis=1)


def evaluate_original_policy(adapter: Exact2048Adapter,policy: np.ndarray) -> dict[str,Any]:
    """Independent finite-horizon evaluation on original, uncollapsed legal rows."""
    policy=np.asarray(policy,dtype=int)
    if policy.shape!=(adapter.mdp.num_states,) or np.any(policy<0) or np.any(policy>=adapter.mdp.num_actions):
        raise ValueError("Policy must contain one action index per rectangular state")
    if not np.all(adapter.legal_mask[np.arange(adapter.mdp.num_states),policy]):
        raise ValueError("Policy selects an illegal computation slot")
    model=adapter.closure.model; values={}
    for state in sorted(model.layers,key=lambda item:(model.layers[item],item)):
        if model.terminal[state]!="ACTIVE": values[state]=0.; continue
        action=ACTION_LABELS[int(policy[adapter.source_to_state[state]])]
        values[state]=math.fsum(outcome.probability*(outcome.reward+adapter.mdp.gamma*values[outcome.next_state]) for outcome in model.rows[state,action])
    tabular=[values[state] for state in adapter.state_to_source[:-1]]+[0.]
    roots={name:values[state] for name,state in zip(adapter.closure.root_names,model.roots,strict=True)}
    return {"source_state_values":values,"tabular_state_values":tabular,"root_values":roots,
        "mean_root_value":math.fsum(roots.values())/len(roots),"mean_tabular_state_value":math.fsum(tabular)/len(tabular)}


def exact_original_solution(adapter: Exact2048Adapter) -> dict[str,Any]:
    """Independent discounted legal DP for checking the author's ground baseline."""
    model=adapter.closure.model; values={}; q={}; policy=np.full(adapter.mdp.num_states,len(ACTION_LABELS)-1,dtype=int)
    for state in sorted(model.layers,key=lambda item:(model.layers[item],item)):
        if model.terminal[state]!="ACTIVE": values[state]=0.; continue
        candidates={}
        for action_index,action in enumerate(ACTION_LABELS[:-1]):
            if (state,action) not in model.rows: continue
            value=math.fsum(outcome.probability*(outcome.reward+adapter.mdp.gamma*values[outcome.next_state]) for outcome in model.rows[state,action])
            candidates[action_index]=value; q[adapter.source_to_state[state]*adapter.mdp.num_actions+action_index]=value
        choice=min(candidates,key=lambda index:(-candidates[index],index)); policy[adapter.source_to_state[state]]=choice; values[state]=candidates[choice]
    q[adapter.terminal_state*adapter.mdp.num_actions+len(ACTION_LABELS)-1]=0.
    return {"legal_q":np.asarray([q[int(pair)] for pair in adapter.valid_pair_indices]),"policy":policy,
        **evaluate_original_policy(adapter,policy)}
