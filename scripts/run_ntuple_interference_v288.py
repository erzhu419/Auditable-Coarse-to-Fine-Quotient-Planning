#!/usr/bin/env python3
"""Diagnose isolated updates on two retained independent suffix batches."""
import argparse
from acfqp.science.ntuple_interference_runner_v288 import run

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args()
run(args.source_summary,args.output)
