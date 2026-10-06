#!/usr/bin/env python3
"""Run the frozen observed-module sharing comparison on retained carrier facts."""
import argparse
from acfqp.science.routed_bellman_v295 import run

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args()
run(args.source_summary,args.output,dict(native_routed=4,observed_route_data=4,
    independent_analysis=11,full_pipeline=2))
