"""A learned, initially zero readout of NodeQ's existing first message."""
from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F

from .lmta_models_v43 import NodeQ


class FirstMessageNodeQ(NodeQ):
    """Preserve the original goal-free NodeQ and add six learned parameters."""

    def __init__(self):
        super().__init__()
        self.message_weight = nn.Parameter(torch.zeros(5))
        self.message_bias = nn.Parameter(torch.zeros(()))

    def forward(self, x, a):
        first = a @ x
        hidden = F.relu(self.encoder.first(first))
        nodes = F.relu(self.encoder.second(a @ hidden))
        q = self.head(nodes).squeeze(-1)
        message_q = F.linear(first, self.message_weight[None, :],
                             self.message_bias.reshape(1)).squeeze(-1)
        return q + message_q
