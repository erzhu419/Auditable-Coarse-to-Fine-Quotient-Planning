#!/usr/bin/env python3
"""Learn from fresh stable-B-only full games and evaluate independent B games."""
import argparse
from acfqp.science.stable_b_v298 import run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
run(args.source_summary, args.output)
