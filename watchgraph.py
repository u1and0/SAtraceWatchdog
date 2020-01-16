#!/usr/bin/env python3
"""dataディレクトリ下のtxtを60secごとに監視して、グラフ化したものをpng出力する"""
from time import sleep
from glob import iglob
from pathlib import Path
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

while True:
    datadir = 'data/'
    txts = {Path(i).stem for i in iglob(datadir + '*.txt')}
    pngs = {Path(i).stem for i in iglob(datadir + '*.png')}
    for base in txts - pngs:
        with open(datadir + base + '.txt') as f:
            setting = f.readline()
            set_list = setting.strip(';')
            print(set_list)
        df = pd.read_csv(datadir + base + '.txt',
                         sep='\s+',
                         index_col=0,
                         skiprows=1,
                         skipfooter=1,
                         names=['Min', 'Mean', 'Max'],
                         engine='python')
        df.Mean.plot(color='gray', linewidth=0.5)
        plt.savefig(datadir + base + '.png')
        plt.close()  # reset plot
        print(
            f'{pd.datetime.now()} Succeeded export image {datadir}{base}.png')
    sleep(10)
