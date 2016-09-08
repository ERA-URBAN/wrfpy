#!/usr/bin/env python

import argparse
import datetime
import time

def convert_time(string):
    return datetime.datetime.strptime(string, '%Y%m%d%H')

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('integers', metavar='N', type=str,
                    help='an integer for the accumulator')

args = parser.parse_args()
dt = convert_time(args.integers)
print dt
time.sleep(2)
