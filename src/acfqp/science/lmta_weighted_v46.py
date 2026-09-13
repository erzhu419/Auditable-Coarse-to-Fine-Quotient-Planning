"""V46 changes only V44's cached graph operator to float32 IC_SUM."""
import torch

from .lmta_agent_v44 import LMTAAgent as _LMTAAgent
from .lmta_baselines_v44 import BudgetHRLAgent as _BudgetHRLAgent, FlatDQNAgent as _FlatDQNAgent
from .lmta_structure_v45 import weighted_adjacency


class LMTAAgent(_LMTAAgent):
    def set_graph(self, graph):
        self.graph_id = graph.graph['replay_id']
        if self.graph_id not in self.adjacency_cache:
            self.adjacency_cache[self.graph_id] = weighted_adjacency(graph, self.device, torch.float32)
        self.a = self.adjacency_cache[self.graph_id]


class _WeightedBaseline:
    def set_graph(self, graph):
        self.graph_id = graph.graph['replay_id']
        if self.graph_id not in self.graph_adjacencies:
            self.graph_adjacencies[self.graph_id] = weighted_adjacency(graph, self.device, torch.float32)
        self.a = self.graph_adjacencies[self.graph_id]


class FlatDQNAgent(_WeightedBaseline, _FlatDQNAgent):
    pass


class BudgetHRLAgent(_WeightedBaseline, _BudgetHRLAgent):
    pass
