#!/usr/bin/env python3
"""Fit retained B reward/risk heads and compare new complete-game utility."""
import argparse
from acfqp.science.split_risk_v301 import run

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args()
run(args.source_summary,args.output)
