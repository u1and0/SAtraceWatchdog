#!/usr/bin/env python3
"""すべてのtxtファイルをheatmap用中間ファイルにまとめる

globですべてのtxtをread_traces()に渡しTrace化する。
時系列順に直すためtranspose()し、インデックスを時系列順に並べ替える。
"""
import glob
import seaborn as sns
from SAtraceWatchdog.tracer import read_traces

FILENAME = 'waterfall.csv'


def plot_matrix(df):
    """plot"""
    ax = sns.heatmap(df)
    return ax


def shape_matrix(data_store, export_filename, fill=False):
    """matrix to csv file

    args:
        data_store: Directory stored txt files
        export_filename: Matrix data file
    """
    txts = glob.iglob(data_store + '/*.txt')
    trs = read_traces(*txts, columns='AVER')
    csv = trs.T.sort_index()
    if not fill:
        csv = trs.T.resample('5T').first()
    csv.to_csv(export_filename)
    return csv


def main():
    """Entry point"""
    df = shape_matrix(data_store='./data', export_filename=FILENAME)
    ax = plot_matrix(df)
    return ax


if __name__ == '__main__':
    main()
