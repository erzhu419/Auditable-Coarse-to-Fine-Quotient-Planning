#!/usr/bin/env python3
"""Run the frozen A/B/A retained-parameter sequence."""
import argparse
from acfqp.science.continual_v303 import run

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args()
run(args.source_summary,args.output)
