#!/usr/bin/env python3
"""SAtraceを扱いやすくするクラス Trace()"""
import datetime
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
import seaborn as sns
import matplotlib.pyplot as plt


def config_parse_freq(key: str) -> (int, str):
    """stringの周波数を単位変換してfloatで返す"""
    val = key.split()
    freq = float(val[0])
    unit = val[-1]
    return freq, unit


def read_conf(line: str) -> dict:
    """1行目のデータからconfigを読み取りdictで返す

    データ例(実際は改行なし)
    # <20161108_021106> *RST;*CLS;
        :INP:COUP DC;
        :BAND:RES 1 Hz;
        :AVER:COUNT 20;
        :SWE:POIN 2001;
        :FREQ:CENT 22 kHz;
        :FREQ:SPAN 8 kHz;
        :TRAC1:TYPE MINH;
        :TRAC2:TYPE AVER;
        :TRAC3:TYPE MAXH;
        :INIT:CONT 0;
        :FORM REAL,32;
        :FORM:BORD SWAP;
        :INIT:IMM;
    """
    conf_list = [
        i.split(maxsplit=1)  # split first space
        for i in line.split(';')[:-1]  # chomp last \n
    ]
    conf_dict = {k[0]: k[-1] for k in conf_list}
    return conf_dict


def read_trace(data: str, config: dict = None) -> pd.DataFrame:
    """dataを読み取ってグラフ用データを返す
    dataはファイル名またはdata string
    > 後者の場合はbase64.b64decode(byte).decode()などとして使用する。

    1行目にスペクトラムアナライザの設定が入っているので、
    dictionaryで返し、
    2行目以降をDataFrameに入れる
    indexの調整をスペアナの設定から自動で行う
    """
    if config is None:  # configを指定しなければ
        # 自動でdataの1行目をconfigとして読み込む
        with open(data, 'r') as f:
            config = read_conf(f.readline())
    # read DataFrame from filename or string
    df = pd.read_csv(data,
                     sep='\s+',
                     index_col=0,
                     skiprows=1,
                     skipfooter=1,
                     names=[
                         config[':TRAC1:TYPE'],
                         config[':TRAC2:TYPE'],
                         config[':TRAC3:TYPE'],
                     ],
                     engine='python')
    # DataFrame modify
    center, _ = config_parse_freq(config[':FREQ:CENT'])
    span, unit = config_parse_freq(config[':FREQ:SPAN'])
    points = int(config[':SWE:POIN'])
    df.index = np.linspace(
        center - span / 2,
        center + span / 2,
        points,
    )
    df.index.name = unit
    return Trace(df)


def read_traces(*files, columns):
    """複数ファイルにread_trace()して1つのTraceにまとめる"""
    df = pd.DataFrame({
        datetime.datetime.strptime(Path(f).stem, '%Y%m%d_%H%M%S'):  # basename
        read_trace(f).loc[:, columns]  # read data & cut only one column
        for f in files
    })
    return Trace(df)


def title_renamer(filename: str) -> str:
    """ファイル名から %Y/%m/%d %T 形式の日付を返す"""
    basename = Path(filename).stem
    n = str(basename).replace('_', '')
    #  return like %Y%m%d %H:%M%S
    return f'{n[:4]}/{n[4:6]}/{n[6:8]} {n[8:10]}:{n[10:12]}:{n[12:14]}'


class Trace(pd.DataFrame):
    """pd.DataFrameのように扱えるTraceクラス"""
    # marker設定
    # "marker":[19.2, 19.8,22.2,24.2,23.4]
    # のような形式でconfig/marker.jsonファイルに記述する
    _dirname = Path(__file__).parent
    with open(_dirname / 'config/marker.json') as f:
        _config = json.load(f)
    marker = _config['marker']
    marker.sort()

    def __init__(self, dataframe):
        super().__init__(dataframe)

    def noisefloor(self, axis: int = 0, percent: float = 25):
        """ 1/4 medianをノイズフロアとし、各列に適用して返す
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
        """sns.heatmap"""
        return sns.heatmap(self.T, cbar=False, *args, **kwargs)

    def plot_markers(self, *args, **kwargs):
        """marker plot as Diamond"""
        slices = self.reindex(self.marker).loc[self.marker]
        # reindex() put off Keyerror
        ax = slices.plot(style='rD', fillstyle='none', *args, **kwargs)
        return ax

    def plot_noisefloor(self, *args, **kwargs):
        """noisefloor plot as black line"""
        line = self.noisefloor()
        _min, _max = self.index.min(), self.index.max()
        ax = plt.plot([_min, _max], [line, line], 'k--', *args, **kwargs)
        return ax
