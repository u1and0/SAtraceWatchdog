#!/usr/bin/env python3
""" txt監視可視化ツール
txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します。

Usage:
    $ watchgraph.py --directory ../png --glob '2020/*' --sleepsec 300

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
from glob import iglob
from pathlib import Path
import logging
from SAtraceWatchdog.oneplot import plot_onefile


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
    log = logging.getLogger(__name__)
    while True:
        txts = {Path(i).stem for i in iglob(args.glob + '.txt')}
        out = args.directory + '/'  # append directory last '/'
        pngs = {Path(i).stem for i in iglob(out + args.glob + '.png')}

        # txtファイルだけあってpngがないファイルに対して実行
        for base in txts - pngs:
            plot_onefile(base + '.txt', directory=args.directory)
            log.info('Succeeded export image {}{}.png'.format(out, base))
        sleep(args.sleepsec)


def main():
    """Entry point"""
    set_logger()
    args = arg_parse()
    print(args)
    directory_check(args.directory)
    loop(args)


if __name__ == '__main__':
    main()
