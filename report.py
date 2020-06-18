#!/usr/bin/env python3
"""時系列ファイルのサマリーカウント"""
from glob import iglob
from datetime import datetime
from pathlib import Path
from collections import Counter
import yaml
import pandas as pd
from SAtraceWatchdog import tracer


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
    fileset = {i + '.txt' for i in fileset}
    if Path(reportfile).exists():
        # indexのみ必要
        # あとでstrftime()するためにparse_dateオプションあり
        idx = pd.read_csv(reportfile, usecols=[0], parse_dates=[0]).squeeze()
        old_fileset = {i.strftime('%Y%m%d_%H%M%S') + '.txt' for i in idx}
        fileset -= old_fileset
    return fileset


def sntable(filenameset: set, centers: list, span: float):
    """ centers周りのbandsignal平均値を返す
    """
    trss = tracer.read_traces(*filenameset, usecols='AVER')
    df = pd.DataFrame(
        {f'{i}pm{span} signal': trss.bandsignal(i, span)
         for i in centers})
    df['noisefloor'] = trss.noisefloor(axis=0)
    return df

    # watchdog.py に書く
    # cdf = pd.concat([bdf, adf]).sort_index()
    # cdf.to_csv(reportfile)
    """
    ```python:return bandsignal()
    def sntable(self, center, span):
        usage:
        trss = read_traces(*filenames, usecols='AVER')
        trss.sntable(22, 0.2)

        # trss = read_traces(*(f'{i}.txt' for i in new_idx), usecols='AVER')
        # trst = tracer.Trace(trss.sort_index().T)
        _n = trss.noisefloor(axis=0)
        _s = trss.bandsignal(center, span)
    !   return pd.DataFrame({f'{center}±{span} signal': _s, 'noisefloor': _n})
        # return cdf

    trss = read_traces(*files, 'AVER')
    ! df = pd.DataFrame({f'signal {i}pm0.2':trss.bandsignal(i, 0.2) for i in [22, 23, 24]})
    ! df['noisefloor'] = trss.noisefloor(axis=0)
    ```
    """


if __name__ == '__main__':
    import doctest
    doctest.testmod()
