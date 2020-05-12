#!/usr/bin/env python3
""" txt監視可視化ツール
txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します。
"""
import sys
import os
import argparse
from time import sleep
import datetime
import glob
import json
import logging
from logging import handlers
from pathlib import Path
from collections import namedtuple
import matplotlib.pyplot as plt
from SAtraceWatchdog import tracer
from SAtraceWatchdog.oneplot import plot_onefile
from SAtraceWatchdog.slack import Slack


def set_logger(logdir):
    """コンソール用ロガーハンドラと
    ファイル用ロガーハンドラを作成し、
    ルートロガーに追加する
    """
    # ルートロガーの作成
    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.INFO)

    # フォーマッターの作成
    formatter = logging.Formatter(
        fmt='[%(levelname)s] %(module)-10s : %(asctime)s %(message)s')

    # コンソール用ハンドラの作成
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # コンソール用ハンドラをルートロガーに追加
    root_logger.addHandler(console_handler)

    # ファイル用ハンドラの作成
    timestamp = datetime.datetime.now().strftime('%y%m%d_%H%M%S')
    file_handler = handlers.RotatingFileHandler(
        filename=f'{logdir}/watchdog_{timestamp}.log',
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
    root = Path(__file__).parent
    parser.add_argument('-d',
                        '--directory',
                        help='出力ディレクトリ',
                        default=Path.cwd())
    parser.add_argument('-l',
                        '--logdirectory',
                        help='ログファイル出力ディレクトリ',
                        default=root / 'log')
    parser.add_argument('--debug', help='debug機能有効化', action='store_true')
    args = parser.parse_args()
    return args


def directory_check(directory, log, slackbot):
    """指定されたディレクトリをチェックする
    存在しなければ作成する
    存在はするがディレクトリではないとき、エラーを返す。
    """
    makedir = Path(directory)
    if not makedir.exists():  # 存在しないディレクトリ指定でディレクトリ作成
        makedir.mkdir()
        message = f'ディレクトリの作成に成功しました {makedir.resolve()}'
        log.info(message)
        slackbot.message(message)
    if not makedir.is_dir():  # 存在はするけれどもディレクトリ以外を指定されたらエラー
        message = f'{makedir.resolve()} はディレクトリではありません'
        log.error(message)
        slackbot.message(message)
        raise IOError(message)


def guess_fallout(df):
    """データ抜けの可能性があるDatetimeIndexを返す"""
    resample = df.resample('5T').first()  # 5min resample
    bools = resample.isna().any(1)  # NaN行をTrueにする
    nan_idx = bools[bools].index  # Trueのとこのインデックスだけ抽出
    return nan_idx


def loop(args, log, slackbot):
    """ファイル差分チェックを実行し、pngファイルを保存する
    Ctrl+Cで止めない限り続く
    """
    day_second = 60 * 60 * 24
    last_config = None
    root = Path(__file__).parent
    configfile = root / 'config/config.json'

    while True:
        # config file読込
        # ループごとに毎回jsonを読みに行く
        if not Path(configfile).exists():
            message = f'設定ファイル {configfile} が存在しません'
            log.error(message)
            slackbot.message(message)
            raise FileNotFoundError(message)
        config = load_config(configfile)
        # 前回のconfigとことなる内容が読み込まれたらログに出力
        if not config == last_config:
            last_config = config
            message = f'設定が更新されました {config}'
            log.info(message)
            slackbot.message(message)

        txts = {Path(i).stem for i in glob.iglob(config.glob + '.txt')}
        out = args.directory + '/'  # append directory last '/'
        pngs = {Path(i).stem for i in glob.iglob(out + config.glob + '.png')}

        # ---
        # One file plot
        # ---
        # txtファイルだけあってpngがないファイルに対して実行
        for base in txts - pngs:
            plot_onefile(base + '.txt', directory=args.directory)
            message = '画像の出力に成功しました {}{}.png'.format(out, base)
            if args.debug:
                message = '[DEBUG] ' + message
            log.info(message)
            slackbot.upload(filename=f'{out}{base}.png', message=message)

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
            trss = tracer.read_traces(*files, usecols=config.usecols)

            # データの抜けを検証
            droped_data = guess_fallout(trss.T)
            if any(droped_data):
                message = f'データの抜けが生じている可能性があります {droped_data}'
                log.warning(message)
                slackbot.message(message)

            # Waterfall plot
            trss.heatmap(title=f'{day[:4]}/{day[4:6]}/{day[6:8]}',
                         cmap='viridis')

            # Save file
            waterfall_filename = '{}/waterfall_{}_update.png'.format(
                args.directory, day)
            # _update.pngが存在して、かつ
            file_exist = Path(waterfall_filename).exists()
            # ファイル数が一日分=288ファイルあったら
            # waterfall_{day}_update.pngを削除して、
            # waterfall_{day}.pngを保存する
            number_of_files_in_a_day = day_second / config.transfer_rate
            number_of_files_ok = len(files) >= number_of_files_in_a_day
            if file_exist and number_of_files_ok:
                os.remove(waterfall_filename)
                waterfall_filename = '{}/waterfall_{}.png'.format(
                    args.directory, day)
            if args.directory:
                plt.savefig(waterfall_filename)
                # ファイルに保存するときplt.close()しないと
                # 複数プロットが1pngファイルに表示される
                plt.close()  # reset plot
            message = '画像の出力に成功しました {}'.format(waterfall_filename)
            if args.debug:
                message = '[DEBUG] ' + message
            log.info(message)
            slackbot.upload(filename=waterfall_filename, message=message)

        sleep(config.check_rate)  # Interval for next loop


def load_config(configfile):
    """configの読み込み
    config.json を読み込み、
    config_keysに指定されたワードのみをConfigとして返す
    """
    with open(configfile, 'r') as f:
        config_dict = json.load(f)
    config_keys = [
        'check_rate',
        'glob',
        'marker',
        'transfer_rate',
        'usecols',
    ]
    Config = namedtuple('Config', config_keys)
    authorized_config = Config(**{k: config_dict[k] for k in config_keys})
    return authorized_config


def main():
    """entry point"""
    args = arg_parse()

    # logger, slackbotの設定
    set_logger(logdir=args.logdirectory)
    log = logging.getLogger(__name__)
    slackbot = Slack()
    message = 'ディレクトリの監視を開始しました... arguments: {}'.format(args)
    log.info(message)
    slackbot.message(message)

    # directory 確認、なければ作る
    directory_check(args.directory, log, slackbot)  # 出力先directoryがなければ作る
    directory_check(args.logdirectory, log, slackbot)  # log directoryがなければ作る

    # main loop ディレクトリ監視してtxt->png化
    loop(args, log, slackbot)


if __name__ == '__main__':
    main()
