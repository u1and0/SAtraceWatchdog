#!/usr/bin/env python3
"""
plotしたグラフを表示
--save でpng形式で保存
USAGE:
    ./aplot.py --save 200420_151550.txt 200420_152040.txt ...
"""
from pathlib import Path
import argparse
import matplotlib.pyplot as plt
import seaborn as sns
from watchgraph import read_trace
from watchgraph import title_renamer

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


def plot_onefile(filename, directory=None):
    """plot"""
    df = read_trace(filename)
    df.iloc[:, 2].plot(color='gray',
                       linewidth=0.5,
                       figsize=(12, 8),
                       title=title_renamer(filename))
    base = Path(filename).stem
    if directory:
        plt.savefig(directory + '/' + base + '.png')
        plt.close()  # reset plot
    return df


def main():
    """main"""
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
        nargs=1,
    )
    args = parser.parse_args()
    print(args)

    for filename in args.files:
        dirs = args.directory[0] if args.directory is not None else None
        plot_onefile(filename, dirs)


if __name__ == '__main__':
    main()
