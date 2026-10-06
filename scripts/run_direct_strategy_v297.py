#!/usr/bin/env python3
"""Optimize stateful programs on complete games and test fresh frozen actors."""
import argparse
from acfqp.science.direct_strategy_v297 import run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-summary',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    run(args.source_summary,args.output,dict(native_strategy=5,direct_search=6,independent_analysis=11))


if __name__=='__main__':main()
