#!/usr/bin/env python3
"""すべてのtxtファイルをheatmap用中間ファイルにまとめる"""
import glob
from SAtraceWatchdog.tracer import read_traces


def main():
    """Entry point"""
    txts = glob.glob('*.txt')
    trs = read_traces(*txts, columns='AVER')
    csv = trs.T.sort_index()
    csv.to_csv('waterfall.csv')
    return csv


if __name__ == '__main__':
    print(main())
