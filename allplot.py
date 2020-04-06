#!/usr/bin/env python3
"""すべてのtxtファイルをheatmap用中間ファイルにまとめる

globですべてのtxtをread_traces()に渡しTrace化する。
時系列順に直すためtranspose()し、インデックスを時系列順に並べ替える。
"""
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
