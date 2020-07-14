#!/usr/bin/env python3
"""
plotしたグラフを表示
--dir(-d)で指定したディレクトリにpng形式で保存

USAGE:
    ./oneplot.py --dir ../pngdir 200420_151550.txt 200420_152040.txt ...

## 1ファイルの呼び出し
コンソール上では
`python oneplot.py -d data data/20161108_020604.txt`

python上では以下のように1ファイルだけ指定
第二引数はディレクトリ。


```python
plot_onefile('data/20161108_020104.txt')`
```

## 複数ファイルの呼び出し
コンソール上では

```sh
$ python oneplot.py -d data data/*.txt`
```

python上ではforを使わないといけない。
oneplot.pyの`main()`ではforが使われているからコンソール上では
上記のようにアスタリスク指定が出来る。

```python
import glob
for i in glob.glob('../data/*.txt')
    plot_onefile(i)
```

"""
from pathlib import Path
import argparse
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from SAtraceWatchdog.tracer import read_trace, title_renamer, Trace

# グラフ描画オプション
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


def plot_onefile(
        filename,
        directory=None,
        column='AVER',
        color='gray',
        linewidth=0.5,
        figsize=(12, 8),
        xstep=9,  # xstepはyと違ってデータの1行目のconfigから読む
        shownoise=True,
        *args,
        **kwargs):
    """スペクトラムファイル1ファイルをプロットします。
    directoryが指定されてたら、その場所に同じベースネームでpng形式に保存します。
    """
    df = read_trace(filename)
    select = Trace(df[column])
    xticks = np.linspace(select.index[0], select.index[-1], xstep)
    ax = select.plot(color=color,
                     linewidth=linewidth,
                     figsize=figsize,
                     title=title_renamer(filename),
                     legend=False,
                     xticks=xticks,
                     *args,
                     **kwargs)
    select.plot_markers(ax=ax, legend=False)
    if shownoise:
        select.plot_noisefloor()
    if directory:
        base = Path(filename).stem
        plt.savefig(f'{directory}/{base}.png')
        # ファイルに保存する時plt.close()しないと
        # 複数プロットが1pngファイルに表示される
        plt.close()  # reset plot
    return ax


def main():
    """entry point
    引数の解釈をして、
    plot_onefile()に指定されたファイル名をforで渡します。
    """
    parser = argparse.ArgumentParser(
        description='スペクトラム情報が記されたテキストファイルをプロットします')
    parser.add_argument(
        'files',
        help='変換ファイル名。複数指定可能',
        nargs='*',
    )
    parser.add_argument(
        '-d',
        '--directory',
        help='保存ディレクトリの指定',
    )
    parser.add_argument(
        '-c',
        '--column',
        help='グラフ化する列指定',
        default='AVER'  # 'MAXH', 'MINH'
    )
    args = parser.parse_args()

    # 引数で渡されたtxtファイルをプロット
    for filename in args.files:
        plot_onefile(filename, directory=args.directory, column=args.column)


if __name__ == '__main__':
    main()
