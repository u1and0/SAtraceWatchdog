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


def snreport(reportfile, center, span):
    reportfile = Path(reportfile)
    a = set(Path(i).stem for i in iglob('*.txt'))
    if reportfile.exists():
        bdf = pd.read_csv(reportfile)
        b = set(datetime.strptime('%y%m%d'))
        new_idx = a - b
    else:
        bdf = pd.DataFrame()
        new_idx = a
    trss = tracer.read_traces(*(f'{i}.txt' for i in new_idx), usecols='AVER')
    # trst = tracer.Trace(trss.sort_index().T)
    n = trss.noisefloor(axis=0)
    s = trss.bandsignal(center, span)
    adf = pd.DataFrame({f'{center}±{span} signal': s, 'noisefloor': n})
    cdf = pd.concat([bdf, adf]).sort_index()
    cdf.to_csv(reportfile)
    return cdf


if __name__ == '__main__':
    import doctest
    doctest.testmod()
