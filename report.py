#!/usr/bin/env python3
"""時系列ファイルのサマリーカウント"""
from datetime import datetime
from pathlib import Path
from collections import Counter
import yaml
import pandas as pd


def timestamp_count(timestamps, filename):
    """同じ日付のタイムスタンプをカウントする
    timestamp format: 20161108_144332
    filenameに与えられたファイルにYAML形式で出力する。

    >>> import pandas as pd
    >>> from datetime import datetime
    >>> now = datetime(2020, 4, 6, 0, 56, 32)
    >>> testdata = pd.date_range(start=now,\
                freq='H', periods=100).strftime('%Y%m%d_%H%M%S')
    >>> print(timestamp_count(( i[:8] for i in testdata ), 'summary.yaml'))
    Counter({'20200406': 24, '20200407': 24,
            '20200408': 24, '20200409': 24, '20200410': 4})
    """
    count = Counter(timestamps)
    with open(filename, 'w') as _f:
        yaml.dump(dict(count), _f)
    return count


def newindex(reportfile, fileset: set):
    """古いreportfile内のdatetimeインデックスから
    現在のファイルセットから解析済みファイルセットを差し引いた
    ファイルセットを返す
    """
    if Path(reportfile).exists():
        # indexのみ必要
        # あとでstrftime()するためにparse_dateオプションあり
        idx = pd.read_csv(reportfile, usecols=[0], parse_dates=[0]).squeeze()
        old_fileset = {i.strftime('%Y%m%d_%H%M%S') for i in idx}
        fileset -= old_fileset
    return fileset


def snreport(traces, filename):
    """snreport doc"""
    if Path(filename).exists():
        traces = pd.concat([  # Concat [olddata, newdata]
            pd.read_csv(filename, index_col=0, parse_dates=True),
            traces,
        ])
    traces.sort_index(inplace=True)
    traces.to_excel(filename)  # Save file
    return traces


if __name__ == '__main__':
    import doctest
    doctest.testmod()
