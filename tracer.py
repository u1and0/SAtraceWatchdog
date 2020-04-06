#!/usr/bin/env python3
"""SAtraceを扱いやすくするクラス Trace()"""
import numpy as np
import pandas as pd
from scipy import stats
import seaborn as sns


class Trace(pd.DataFrame):
    def __init__(self, dataframe):
        super().__init__(dataframe)

    def noisefloor(self, axis: int = 0, percent: float = 25):
        """
        1/4 medianをノイズフロアとし、各列に適用して返す
        引数:
            df: 行が周波数、列が日時(データフレーム型)
            axis: 0 or 1.
                0: 列に適用(デフォルト)
                1: 行に適用
        戻り値:
            df: ノイズフロア(データフレーム型)
        """
        return self.apply(lambda x: stats.scoreatpercentile(x, percent), axis)

    def heatmap(self, *args, **kwargs):
        return sns.heatmap(self.T, *args, **kwargs)

    def mw2db(self):
        """mW -> dB
        Usage: `df.mw2db()` or `mw2db(df)`

        ```python:TEST
        mw = pd.Series(np.arange(11))
        df = pd.DataFrame({'watt': mw, 'dBm': mw.mw2db(), 'dB to watt': mw.mw2db().db2mw()})
        print(df)
        #[Out]#     dB to watt        dBm  watt
        #[Out]# 0          0.0       -inf     0
        #[Out]# 1          1.0   0.000000     1
        #[Out]# 2          2.0   3.010300     2
        #[Out]# 3          3.0   4.771213     3
        #[Out]# 4          4.0   6.020600     4
        #[Out]# 5          5.0   6.989700     5
        #[Out]# 6          6.0   7.781513     6
        #[Out]# 7          7.0   8.450980     7
        #[Out]# 8          8.0   9.030900     8
        #[Out]# 9          9.0   9.542425     9
        #[Out]# 10        10.0  10.000000    10
        ```"""
        return Trace( 10 * np.log10(self) )


    def db2mw(self):
        """dB -> mW
        Usage: `df.db2mw()` or `db2mw(df)` """
        return Trace( np.power(10, self / 10) )

