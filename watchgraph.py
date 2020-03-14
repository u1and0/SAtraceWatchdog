#!/usr/bin/env python3
"""watchgrapht.py v0.0.0
カレントディレクトリ下のtxtを定期的に監視して、
グラフ化したものをpng出力する
"""
import sys
from time import sleep
import datetime
from glob import iglob
from collections import namedtuple
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
sns.set(style='whitegrid',
        palette='husl',
        font="IPAGothic",
        font_scale=1.5,
        color_codes=False,
        rc={
            'grid.linestyle': ':',
            'grid.color': 'gray',
            'image.cmap': 'viridis'
        })


def config_parse_freq(key: str) -> (int, str):
    """stringの周波数を単位変換してfloatで返す"""
    val = key.split()
    freq = int(val[0])
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
        for i in line.split(';')[2:-2]
        # chomp below...
        # <20161108_021106> *RST;
        # *CLS;
        # :INIT:IMM;
        # last \n
    ]
    conf_dict = {k[0]: k[-1] for k in conf_list}
    conf_dict_colon = {
        # chomp first ':' & replace ':' -> '_' & replace lower case
        # for all keys
        k[1:].replace(':', '_').lower(): v
        for k, v in conf_dict.items()
    }
    tup = namedtuple('Config', conf_dict_colon.keys())
    conf_tuple = tup(**conf_dict_colon)
    return conf_tuple


class Trace:
    def __init__(self, data, firstline):
        self.config = read_conf(firstline)
        # data read
        self.data = pd.read_table(data,
                                  sep='\s+',
                                  index_col=0,
                                  skiprows=1,
                                  skipfooter=1,
                                  names=[
                                      self.config.trac1_type,
                                      self.config.trac2_type,
                                      self.config.trac3_type,
                                  ],
                                  engine='python')
        # data modify
        center, _ = config_parse_freq(self.config.freq_cent)
        span, unit = config_parse_freq(self.config.freq_span)
        points = int(self.config.swe_poin)
        self.data.index = np.linspace(
            center - span / 2,
            center + span / 2,
            points,
        )
        self.data.index.name = unit

    # def plot(self) -> pd.DataFrame:
    #     return self.data.plot()


# def read_trace(data: str) -> pd.DataFrame:
#     """dataを読み取ってグラフ用データを返す
#     dataはファイル名またはdata stringである。
#     > 後者の場合はbase64.b64decode(byte).decode()などとして使用する。
#
#     1行目にスペクトラムアナライザの設定が入っているので、
#     dictionaryで返し、
#     2行目以降をDataFrameに入れる
#     indexの調整をスペアナの設定から自動で行う
#     """
#     with open(data) as f:
#         line = f.readline()  # NA設定読み取り
#     conf_dict = read_conf(line)
#     center_freq, _ = config_parse_freq(conf_dict, ':FREQ:CENT')
#     span_freq, unit = config_parse_freq(conf_dict, ':FREQ:SPAN')
#     points = int(conf_dict[':SWE:POIN'])
#
#     # グラフ化
#     df = pd.read_table(data,
#                        sep='\s+',
#                        index_col=0,
#                        skiprows=1,
#                        skipfooter=1,
#                        names=[
#                            conf_dict[':TRAC1:TYPE'],
#                            conf_dict[':TRAC2:TYPE'],
#                            conf_dict[':TRAC3:TYPE'],
#                        ],
#                        engine='python')
#     df.index = np.linspace(center_freq - span_freq / 2,
#                            center_freq + span_freq / 2, points)
#     df.index.name = unit
#     return df


def main(outdir='.', sleepsec=10):
    pngdir = Path(outdir)
    if not pngdir.exists():
        pngdir.mkdir()
        print(f'{pd.datetime.now()}\
              make directory {pngdir.resolve()}')
    if not pngdir.is_dir():
        raise IOError(f'{pngdir.resolve()} is not directory')
    while True:
        txts = {Path(i).stem for i in iglob('*.txt')}
        # append directory last '/'
        out = str(pngdir.resolve()) + '/'
        pngs = {Path(i).stem for i in iglob(str(out) + '*.png')}

        # txtファイルだけあってpngがないファイルに対して実行
        for base in txts - pngs:
            # df = read_trace(base + '.txt')
            with open(data) as f:
                line = f.readline()  # NA設定読み取り
            trace = Trace(base + '.txt', line)
            df = trace.data

            # iloc <= 1:Minhold 2:Aver 3:Maxhold
            df.iloc[:, 2].plot(color='gray', linewidth=0.5, figsize=(12, 8))
            plt.savefig(out + base + '.png')
            plt.close()  # reset plot
            print('{} Succeeded export image {}{}.png'.format(
                datetime.datetime.now(), out, base))
        sleep(sleepsec)


if __name__ == '__main__':
    main(*sys.argv[1:])
