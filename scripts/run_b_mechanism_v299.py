#!/usr/bin/env python3
"""Deterministic V298 B replay and H2 mechanism decomposition."""
import argparse
from acfqp.science.b_mechanism_v299 import run
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source-summary',required=True)
p.add_argument('--output',required=True)
a=p.parse_args()
run(a.source_summary,a.output,dict(native=9,driver=3,analysis=8,audit=14))
