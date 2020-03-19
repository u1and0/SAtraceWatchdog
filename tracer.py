#!/usr/bin/env python3
"""SAtraceを扱いやすくするクラス Trace()"""
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

    def heatmap(self):
        return sns.heatmap(self.T)
