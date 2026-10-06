#!/usr/bin/env python3
"""Inspect accumulated V287 MC learning without new environment acquisition."""
import argparse
from acfqp.science.cumulative_critic_v289 import run

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary',required=True)
parser.add_argument('--query-trace',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args()
run(args.source_summary,args.query_trace,args.output)
