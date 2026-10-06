#!/usr/bin/env python3
"""Fit four fixed-data critics and test new complete H2 games."""
import argparse
from acfqp.science.episode_consolidation_v290 import run

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args()
run(args.source_summary,args.output)
