#!/usr/bin/env python3
"""watchgrapht.py v0.0.0
カレントディレクトリ下のtxtを定期的に監視して、
グラフ化したものをpng出力する
"""
import sys
from time import sleep
from glob import iglob
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


def config_parse_freq(conf_dict: dict, key: str):
    """stringの周波数を単位変換してfloatで返す"""
    val = conf_dict[key].split()
    freq = int(val[0])
    unit = val[-1]
    return freq, unit


def read_conf(line):
    """1行目のデータからconfigを読み取りdictで返す"""
    conf_list = [i.split(maxsplit=1)
                 for i in line.split(';')[:-1]]  # chomp last \n
    conf_dict = {k[0]: k[-1] for k in conf_list}
    return conf_dict


def main(outdir='.', sleepsec=10):
    pngdir = Path(outdir)
    if not pngdir.exists():
        pngdir.mkdir()
        print(f'{pd.datetime.now()}\
              make directory {pngdir.resolve()}')
    if not pngdir.is_dir():
        raise IOError('Directory {} does not exist'.format(outdir))
    while True:
        txts = {Path(i).stem for i in iglob('*.txt')}
        # append directory last '/'
        out = outdir + '/' if not outdir[-1] == '/' else outdir
        pngs = {Path(i).stem for i in iglob(out + '*.png')}

        # txtファイルだけあってpngがないファイルに対して実行
        for base in txts - pngs:
            # NA設定読み取り
            with open(base + '.txt') as f:
                line = f.readline()
            conf_dict = read_conf(line)
            center_freq, _ = config_parse_freq(conf_dict, ':FREQ:CENT')
            span_freq, unit = config_parse_freq(conf_dict, ':FREQ:SPAN')
            points = int(conf_dict[':SWE:POIN'])

            # グラフ化
            df = pd.read_table(base + '.txt',
                               sep='\s+',
                               index_col=0,
                               skiprows=1,
                               skipfooter=1,
                               names=[
                                   conf_dict[':TRAC1:TYPE'],
                                   conf_dict[':TRAC2:TYPE'],
                                   conf_dict[':TRAC3:TYPE']
                               ],
                               engine='python')
            df.index = np.linspace(center_freq - span_freq / 2,
                                   center_freq + span_freq / 2, points)
            df.index.name = unit

            # iloc <= 1:Minhold 2:Aver 3:Maxhold
            df.iloc[:, 2].plot(color='gray', linewidth=0.5, figsize=(12, 8))
            plt.savefig(out + base + '.png')
            plt.close()  # reset plot
            print(f'{pd.datetime.now()}\
                Succeeded export image {out}{base}.png')
        sleep(sleepsec)


if __name__ == '__main__':
    main(*sys.argv[1:])
