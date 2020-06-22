#!/usr/bin/env python3
""" txt監視可視化ツール
txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します。
"""
import sys
import copy
import argparse
from time import sleep
import datetime
import glob
import json
import logging
from logging import handlers
from pathlib import Path
from collections import namedtuple, defaultdict
import pandas as pd
import matplotlib.pyplot as plt
from SAtraceWatchdog import tracer
from SAtraceWatchdog.oneplot import plot_onefile
from SAtraceWatchdog.slack import Slack
from SAtraceWatchdog import report


def dirs_factory():
    # directory, filepathの設定
    _directories = [
        ARGS.directory,
        ARGS.logdirectory,
        ARGS.statsdirectory,
    ]
    Dirs = namedtuple('Dirs', ['png', 'log', 'stats'])
    return Dirs(
        png=Watch.directory_check(ARGS.directories),
        log=Watch.directory_check(ARGS.logdirectory),
        stats=Watch.directory_check(ARGS.statsdirectory,
        )
    # directories=dict()
    # for _k, _d in zip(_key, _directories):
    #     directories[_k]=Watch.directory_check(_d)
    # if ARGS.debug:
    #     print(f'png dir: {self.directories["directories"]}')
    #     print(f'log dir: {self.logdirectory}')
    #     print(f'stats dir: {ARGS.statsdirectory}')
    # return directories


class Watch:
    """watchdog class"""
    def __init__(self, dirs):
        """watchdog init"""
        self.last_config=None
        self.last_files=defaultdict(lambda: [])
        self.last_base=None
        self.no_update_count=0
        self.no_update_threshold=1
        self.configfile=ROOT / 'config/config.json'
        self.config=None  # Watch.loop() の毎回のループで読み込み

        self.summary_file=ARGS.statsdirectory / 'watchdog_summary.yaml'
        self.stats_file=ARGS.statsdirectory / 'watchdog_SN.csv'
        # loggerの設定
        Watch.set_logger()
        self.log=logging.getLogger(__name__)

    @staticmethod
    def directory_check(directory):
        """指定されたディレクトリをチェックする
        存在しなければ作成する
        存在はするがディレクトリではないとき、エラーを返す。
        """
        makedir=Path(directory)
        if not makedir.exists():  # 存在しないディレクトリ指定でディレクトリ作成
            makedir.mkdir()
            message=f'ディレクトリの作成に成功しました {makedir.resolve()}'
            print(message)  # loggerが設定できてないのでstdout に print
        if not makedir.is_dir():  # 存在はするけれどもディレクトリ以外を指定されたらエラー
            message=f'{makedir.resolve()} はディレクトリではありません'
            raise IOError(message)
        return makedir

    def load_config(self):
        """configの読み込み
        config.json を読み込み、
        config_keysに指定されたワードのみをConfigとして返す
        """
        with open(self.configfile, 'r') as f:
            config_dict=json.load(f)
        config_keys=[
            'check_rate',
            'glob',
            'marker',
            'transfer_rate',
            'usecols',
            'cmaphigh',
            'cmaplow',
        ]
        Config=namedtuple('Config', config_keys)
        authorized_config=Config(**{k: config_dict[k] for k in config_keys})
        return authorized_config

    @classmethod
    def set_logger(cls):
        """コンソール用ロガーハンドラと
        ファイル用ロガーハンドラを作成し、
        ルートロガーに追加する
        """
        # ルートロガーの作成
        root_logger=logging.getLogger('')
        root_logger.setLevel(logging.INFO)

        # フォーマッターの作成
        formatter=logging.Formatter(
            fmt='[%(levelname)s] %(module)-10s : %(asctime)s %(message)s')

        # コンソール用ハンドラの作成
        console_handler=logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # コンソール用ハンドラをルートロガーに追加
        root_logger.addHandler(console_handler)

        # ファイル用ハンドラの作成
        timestamp=datetime.datetime.now().strftime('%y%m%d_%H%M%S')
        file_handler=handlers.RotatingFileHandler(
            filename=f'{ARGS.logdirectory}/watchdog_{timestamp}.log',
            maxBytes=1e6,
            encoding='utf-8',
            backupCount=3)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        # ファイル用ハンドラをルートロガーに追加
        root_logger.addHandler(file_handler)

    @staticmethod
    def filename_resolver(yyyymmdd: str, remove_flag: bool) -> str:
        """Decide waterfall filenamene
        return:
            waterfall_yymmdd_update.png
                or
            waterfall_yymmdd.png

        ファイル数が一日分=288ファイルあったら
            waterfall_{yyyymmdd}_update.pngを削除して、
            waterfall_{yyyymmdd}.pngを返す
        ファイル数が一日分=288ファイルなければ
            waterfall_{yyyymmdd}_update.pngを返す
        """
        pre=f'{ARGS.directory}/waterfall_{yyyymmdd}'
        filename=Path(pre + '_update.png')
        if remove_flag:  # ファイル数が一日分=288ファイルあったら
            # waterfall_{yyyymmdd}_update.pngを削除して、
            filename.unlink(missing_ok=True)  # ignore FileNotFoundError
            # waterfall_{yyyymmdd}.pngというファイル名を返す
            filename=Path(pre + '.png')
        return filename

    def loop(self):
        """pngファイルの出力とログ出力の無限ループ"""
        # config file読込
        # ループごとに毎回jsonを読みに行く
        if not Path(self.configfile).exists():
            Slack().log(self.log.error,
                        f'設定ファイル {self.configfile} が存在しません',
                        err=FileNotFoundError)
        self.config=self.load_config()
        # 前回のconfigとことなる内容が読み込まれたらログに出力
        if not self.config == self.last_config:
            self.last_config=self.config
            Slack().log(self.log.info, f'設定が更新されました {self.config}')

        # ファイル名差分確認
        pattern=self.config.glob
        out=ARGS.directory
        txts={Path(i).stem for i in glob.iglob(f'{pattern}.txt')}
        pngs={Path(i).stem for i in glob.iglob(f'{out}/{pattern}.png')}
        update_files=txts - pngs

        # Count report
        _counts=report.timestamp_count(
            timestamps=(i[:8] for i in txts),  # 8 <= number of yyyymmdd
            filename=self.summary_file)
        if ARGS.debug:
            Slack().log(self.log.debug, f'FILE COUNTS {_counts}')

        # SN report
        new_fileset={
            i + '.txt'
            for i in report.newindex(self.stats_file, copy.copy(txts))
        }
        if new_fileset:
            trs=tracer.read_traces(*new_fileset, usecols=self.config.usecols)
            sndf=trs.sntable(centers=self.config.marker, span=0.2)
            if self.stats_file.exists():
                sndf=pd.concat([  # Concat [olddata, newdata]
                    pd.read_csv(self.stats_file, index_col=0,
                                parse_dates=True),
                    sndf,
                ])
            sndf.sort_index(inplace=True)
            sndf.to_csv(self.stats_file)  # Save file
            Slack().log(self.log.info, f'S/N レポート{self.stats_file}を出力しました')
            if ARGS.debug:
                Slack().log(self.log.debug,
                            f'Print S/N report\n{sndf}')

        # ---
        # One file plot
        # ---
        # txtファイルだけあってpngがないファイルに対して実行
        try:
            for base in update_files:
                plot_onefile(base + '.txt', directory=ARGS.directory)
                Slack().log(self.log.info,
                            f'画像の出力に成功しました {ARGS.directory}/{base}.png')
                # Reset count
                self.no_update_count=0
                self.no_update_threshold=2
            else:  # update_filesが空で、更新がないとき
                self.no_update_count += 1
                if self.no_update_count > self.no_update_threshold:
                    self.no_update_warning()
                    self.no_update_threshold *= 2

            # ---
            # Daily plot
            # ---
            # filename format must be [ %Y%m%d_%H%M%S.txt ]
            days_set={_[:8] for _ in txts}
            if ARGS.debug:
                Slack().log(self.log.debug, f'day_set: {days_set}')
            # txts directory 内にある%Y%m%dのsetに対して実行
            for day in days_set:
                # waterfall_{day}.pngが存在すれば最終処理が完了しているので
                # waterfallをプロットしない -> 次のfor iterへ行く
                if Path(f'{ARGS.directory}/waterfall_{day}.png').exists():
                    continue
                # waterfall_{day}.pngが存在しなければ最終処理が完了していないので
                # waterfalll_{day}_update.pngを作成する

                files=glob.glob(f'{day}_*.txt')
                if ARGS.debug:
                    print(f'{day}--LAST FILES-- ',
                          len(set(self.last_files[day])))
                    print(f'{day}--FILES-- ', len(set(files)))

                # waterfall_update.pngが存在して、
                # かつ
                # ファイルに更新がなければ次のfor iterへ行く
                noupdate=set(self.last_files[day]) == set(files)
                exists=Path(
                    f'{ARGS.directory}/waterfall_{day}_update.png').exists()
                if exists and noupdate:
                    continue
                self.last_files[day]=files

                # ファイルに更新があれば更新したwaterfall_update.pngを出力
                trss=tracer.read_traces(*files, usecols=self.config.usecols)
                _n=DAY_SECOND // self.config.transfer_rate  # => 288
                num_of_files_ok=len(files) >= _n
                if ARGS.debug:
                    Slack().log(self.log.debug, f'limit: {_n}')
                    Slack().log(self.log.debug, f'length: {len(files)}')
                filename=self.filename_resolver(yyyymmdd=day,
                                                  remove_flag=num_of_files_ok)
                trss.heatmap(title=f'{day[:4]}/{day[4:6]}/{day[6:8]}',
                             cmap='viridis',
                             cmaphigh=self.config.cmaphigh,
                             cmaplow=self.config.cmaplow)
                plt.savefig(filename)
                # ファイルに保存するときplt.close()しないと
                # 複数プロットが1pngファイルに表示される
                plt.close()  # reset plot
                Slack().log(self.log.debug if ARGS.debug else self.log.info,
                            f'画像の出力に成功しました {filename}')

                # データの抜けを検証"""
                rate='{}T'.format(self.config.transfer_rate // 60)
                droped_data=trss.guess_fallout(rate=rate)
                if any(droped_data):
                    Slack().log(self.log.warning, f'データが抜けています {droped_data}')
        except ValueError as e:
            Slack().log(self.log.error,
                        f'{base}: {e}, txtファイルは送信されてきましたがデータが足りません')

    def sleep(self):
        """Interval for next loop"""
        if ARGS.debug:
            Slack().log(self.log.debug,
                        f'sleeping... {self.config.check_rate}')
        sleep(self.config.check_rate)

    def no_update_warning(self):
        """更新がしばらくないときにWarning上げる"""
        no_uptime=self.no_update_count * self.config.transfer_rate
        if no_uptime < 60:
            message=f'最後の更新から{no_uptime}秒'
        elif no_uptime < 3600:
            message=f'最後の更新から{no_uptime//60}分'
        else:
            message=f'最後の更新から{no_uptime//3600}時'
        message += '間更新がありません。データの送信状況を確認してください。'
        Slack().log(self.log.warning, message)

    def stop(self):
        """Ctrl-CによりWatchdogを正常終了する"""
        Slack().log(self.log.info, 'キーボード入力により監視を終了しました。')
        sys.exit(0)


def parse_args():
    """コマンドライン引数を返す"""
    parser=argparse.ArgumentParser(description=__doc__)
    # path操作関連の型はstr型ではなく、原則pathlib.PosixPath型を使用する
    parser.add_argument('-d',
                        '--directory',
                        help='画像ファイル出力ディレクトリ',
                        default=Path.cwd())
    parser.add_argument('-l',
                        '--logdirectory',
                        help='ログファイル出力ディレクトリ',
                        default=ROOT / 'log')
    parser.add_argument('-s',
                        '--statsdirectory',
                        help='統計ファイル出力ディレクトリ',
                        default=ROOT / 'stats')
    parser.add_argument('--debug', help='debug機能有効化', action='store_true')
    parser.add_argument('-v', '--version', action='store_true')
    return parser.parse_args()


def main():
    """ファイル差分チェックを実行し、pngファイルを保存する
    Ctrl+Cで止めない限り続く
    """
    root=Path(__file__).parent
    args=parse_args()
    if args.version:
        print('SAtraceWatchdog ', VERSION)
        return  # VERSION を表示して終了
    dirs=dirs_factory(args)
    watchdog=Watch(dirs)
    Slack().log(watchdog.log.info,
                f'ディレクトリの監視を開始しました。 SAtraceWatchdog {VERSION}')
    try:
        while True:
            watchdog.loop()
            watchdog.sleep()
    except KeyboardInterrupt:
        watchdog.stop()


if __name__ == '__main__':
    VERSION='v0.4.0'
    DAY_SECOND=60 * 60 * 24
    main()
