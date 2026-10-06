#!/usr/bin/env python3
"""Run frozen conditional Bellman residual methods on retained carrier facts."""
import argparse
from acfqp.science.conditional_bellman_v294 import run

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args()
run(args.source_summary,args.output,dict(native_residual=10,retained_data=4,
    independent_analysis=12,full_pipeline=3,separate_generating_law=3))
