#!/usr/bin/env python3
"""時系列ファイルのサマリーカウント"""
from collections import Counter
import yaml


def timestamp_count(timestamps, filename):
    """同じ日付のタイムスタンプをカウントする
    timestamp format: 20161108_144332
    filenameに与えられたファイルにYAML形式で出力する。

    >>> import pandas as pd
    >>> from datetime import datetime
    >>> now = datetime(2020, 4, 6, 0, 56, 32)
    >>> testdata = pd.date_range(start=now,\
                freq='h', periods=100).strftime('%Y%m%d_%H%M%S')
    >>> print(timestamp_count(( i[:8] for i in testdata ), 'summary.yaml'))
    Counter({'20200406': 24, '20200407': 24, '20200408': 24, '20200409': 24, '20200410': 4})
    """
    count = Counter(timestamps)
    with open(filename, 'w') as _f:
        yaml.dump(dict(count), _f)
    return count


if __name__ == '__main__':
    import doctest
    doctest.testmod()
