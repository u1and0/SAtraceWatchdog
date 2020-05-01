#!/usr/bin/env python3
""" txt監視可視化ツール
txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します。

Usage:
    $ watchdog.py --directory ../png --glob '2020/*' --sleepsec 300

上のスクリプトは

* ../pngディレクトリにpngファイルを出力します。
* 2020が接頭に着くファイルのみを処理します。
* 300秒ごとにtxtファイルとpngファイルの差分をチェックします。
* スター(*)はshell上で展開されてしまうのを防ぐためにバックスラッシュエスケープが必要。
"""
import sys
import os
import argparse
from time import sleep
import datetime
import glob
import logging
from pathlib import Path
import matplotlib.pyplot as plt
from SAtraceWatchdog import tracer
from SAtraceWatchdog.oneplot import plot_onefile
from SAtraceWatchdog.dayplot import allplt_wtf


def set_logger():
    """コンソール用ロガーハンドラと
    ファイル用ロガーハンドラを作成し、
    ルートロガーに追加する
    """
    # ルートロガーの作成
    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.INFO)

    # フォーマッターの作成 INFO: 2020/3/21 Succeeded...
    formatter = logging.Formatter(
        fmt='[%(levelname)s] %(module)-10s : %(asctime)s %(message)s')

    # コンソール用ハンドラの作成
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # コンソール用ハンドラをルートロガーに追加
    root_logger.addHandler(console_handler)

    # ファイル用ハンドラの作成
    basename = Path(__file__).parent
    timestamp = datetime.datetime.now().strftime('%y%m%d_%H%M%S')
    file_handler = logging.handlers.RotatingFileHandler(
        filename=f'{basename}/log/watchdog_{timestamp}.log',
        maxBytes=1e6,
        encoding='utf-8',
        backupCount=3)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # ファイル用ハンドラをルートロガーに追加
    root_logger.addHandler(file_handler)


def arg_parse():
    """引数解析
    ディレクトリとチェック間隔(秒)を指定する
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-d',
                        '--directory',
                        help='出力ディレクトリ',
                        default=os.getcwd())
    parser.add_argument('-g',
                        '--glob',
                        help='入力ファイル名にglobパターンを使う',
                        default='*')
    parser.add_argument('-s',
                        '--sleepsec',
                        help='チェック間隔(sec)',
                        type=int,
                        default=10)
    args = parser.parse_args()
    return args


def directory_check(directory):
    """指定されたディレクトリをチェックする
    存在しなければ作成する
    存在はするがディレクトリではないとき、エラーを返す。
    """
    log = logging.getLogger(__name__)
    pngdir = Path(directory)
    if not pngdir.exists():  # 存在しないディレクトリ指定でディレクトリ作成
        pngdir.mkdir()
        log.info(f'Make directory {pngdir.resolve()}')
    if not pngdir.is_dir():  # 存在はするけれどもディレクトリ以外を指定されたらエラー
        message = f'{pngdir.resolve()} is not directory'
        log.error(message)
        raise IOError(message)


def loop(args):
    """ファイル差分チェックを実行し、pngファイルを保存する
    Ctrl+Cで止めない限り続く
    """
    day_second = 60 * 60 * 24
    interval = 300
    number_of_files_in_a_day = day_second / interval

    log = logging.getLogger(__name__)
    log.info('Watching start... arguments: {}'.format(args))
    while True:
        txts = {Path(i).stem for i in glob.iglob(args.glob + '.txt')}
        out = args.directory + '/'  # append directory last '/'
        pngs = {Path(i).stem for i in glob.iglob(out + args.glob + '.png')}

        # ---
        # One file plot
        # ---
        # txtファイルだけあってpngがないファイルに対して実行
        for base in txts - pngs:
            plot_onefile(base + '.txt', directory=args.directory)
            log.info('Succeeded export image {}{}.png'.format(out, base))

        # ---
        # Daily plot
        # ---
        # filename format must be [ %Y%m%d_%H%M%S.txt ]
        days_set = {_[:8] for _ in txts}
        # txts directory 内にある%Y%m%dのsetに対して実行
        for day in days_set:
            # waterfall_{day}.pngが存在すれば最終処理が完了しているので
            # waterfallをプロットしない -> 次のfor iterへ行く
            if Path(f'{args.directory}/waterfall_{day}.png').exists():
                continue
            # waterfall_{day}.pngが存在しなければ最終処理が完了していないので
            # waterfalll_{day}_update.pngを作成する
            files = glob.glob(f'{day}_*.txt')
            trss = tracer.read_traces(*files, usecols=['AVER'])

            # Waterfall plot
            allplt_wtf(tracer.Trace(trss.T),
                       title=f'{day[:4]}/{day[4:6]}/{day[6:8]}',
                       cmap='viridis')

            # Save file
            waterfall_filename = '{}/waterfall_{}_update.png'.format(
                args.directory, day)
            # waterfall_{day}_update.pngを削除して、
            # waterfall_{day}.pngを保存する
            if len(files) >= number_of_files_in_a_day:
                os.remove(waterfall_filename)
                waterfall_filename = '{}/waterfall_{}.png'.format(
                    args.directory, day)
            if args.directory:
                plt.savefig(waterfall_filename)
                # ファイルに保存するときplt.close()しないと
                # 複数プロットが1pngファイルに表示される
                plt.close()  # reset plot
            log.info('Succeeded export image {}'.format(waterfall_filename))

        sleep(args.sleepsec)


def main():
    """Entry point"""
    set_logger()
    args = arg_parse()
    directory_check(args.directory)
    loop(args)


if __name__ == '__main__':
    main()
