#!/usr/bin/env python3
"""Compare retained stable-B MC and H2 control targets on fresh full games."""
import argparse
from acfqp.science.b_control_v300 import run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
run(args.source_summary, args.output)
