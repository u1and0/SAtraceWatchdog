#!/usr/bin/env python3
""" txt監視可視化ツール
txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します。
"""
import sys
from typing import Dict, List, Any, Optional
import argparse
from time import sleep
from datetime import datetime
import glob
import logging
from logging import handlers
from functools import partial
from pathlib import Path
from collections import namedtuple, defaultdict
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from SAtraceWatchdog import tracer
from SAtraceWatchdog.oneplot import plot_onefile
from SAtraceWatchdog.slack import Slack
from SAtraceWatchdog import report

VERSION = 'v1.0.0'
DAY_SECOND = 60 * 60 * 24
ROOT = Path(__file__).parent


class Watch:
    """Watch txt directory and png directory.
    Exist txt file but png file, then make png file.
    Exist txt file and png file, then ignore process.

    # Process endless loop
    ( start )<-+
    =>parse()  |
    =>loop()   |
    =>sleep()--+
    =>stop()
    ( end )
    """
    configfile = ROOT / 'config/config.json'
    # アップデートファイル保持
    config = None  # Watch.loop() の毎回のループで読み込み
    last_config: Optional[Dict[str, Any]] = None
    last_files: Dict[str, List] = defaultdict(lambda: [])
    # アップデート記録保持
    no_update_count = 0
    no_update_threshold = 1

    def __init__(self, args):
        """watchdog init"""
        self.debug = args.debug
        # directory, filepathの設定
        self.directory = Watch.directory_check(args.directory)
        self.logdirectory = Watch.directory_check(args.logdirectory)
        self.statsdirectory = Watch.directory_check(args.statsdirectory)
        if self.debug:
            print(f'[DEBUG] PNG DIR: {self.directory}')
            print(f'[DEBUG] LOG DIR: {self.logdirectory}')
            print(f'[DEBUG] STATS DIR: {self.statsdirectory}')
        self.stats_file = self.statsdirectory / 'watchdog_SN.xlsx'
        # loggerの設定
        self.set_logger()
        self.log = logging.getLogger(__name__)

    @staticmethod
    def directory_check(directory):
        """指定されたディレクトリをチェックする
        存在しなければ作成する
        存在はするがディレクトリではないとき、エラーを返す。
        """
        makedir = Path(directory)
        if not makedir.exists():  # 存在しないディレクトリ指定でディレクトリ作成
            makedir.mkdir()
            message = f'ディレクトリの作成に成功しました {makedir.resolve()}'
            print(message)  # loggerが設定できてないのでstdout に print
        if not makedir.is_dir():  # 存在はするけれどもディレクトリ以外を指定されたらエラー
            message = f'{makedir.resolve()} はディレクトリではありません'
            raise IOError(message)
        return makedir

    def load_config(self):
        """configの読み込み
        config.json を読み込み、
        config_keysに指定されたワードのみをConfigとして返す
        """
        if not Path(Watch.configfile).exists():
            raise FileNotFoundError(f'設定ファイル {Watch.configfile} が存在しません')
        config_dict = tracer.json_load_encode_with_bom(Watch.configfile)
        config_keys = [
            'check_rate',
            'glob',
            'transfer_rate',
            'usecols',
            'markers',
            # oneplot.plot_onefile option *args, **kwargs
            'color',
            'linewidth',
            'figsize',
            'shownoise',
            # oneplot.plot_onefile option ax.set_xticks()
            'xticks_major_gap',  # xticks_major_gap:x軸に引く主補助線の間隔,
            'xticks_minor_gap',  # xticks_minor_gap:x軸に引く副補助線の間隔,
            # oneplot.plot_onefile option
            # yticks=np.linspace(ymin,ymax,ystep)
            'ymin',
            'ymax',
            'ystep',
            # tracer.Trace.heatmap() args
            'h_figsize',
            'cmap',
            'cmaphigh',
            'cmaplow',
            'cmaplevel',
            'cmapstep',
        ]
        Config = namedtuple('Config', config_keys)
        authorized_config = Config(**{k: config_dict[k] for k in config_keys})
        return authorized_config

    def set_logger(self):
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
        timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
        file_handler = handlers.RotatingFileHandler(
            filename=f'{self.logdirectory}/watchdog_{timestamp}.log',
            maxBytes=1e6,
            encoding='utf-8',
            backupCount=3)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        # ファイル用ハンドラをルートロガーに追加
        root_logger.addHandler(file_handler)

    def filename_resolver(self, yyyymmdd: str, remove_flag: bool) -> Path:
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
        pre = f'{self.directory}/waterfall_{yyyymmdd}'
        filename = Path(pre + '_update.png')
        if remove_flag:  # ファイル数が一日分=288ファイルあったら
            # waterfall_{yyyymmdd}_update.pngを削除して、
            filename.unlink(missing_ok=True)  # ignore FileNotFoundError
            # waterfall_{yyyymmdd}.pngというファイル名を返す
            filename = Path(pre + '.png')
        return filename

    def loop(self):
        """pngファイルの出力とログ出力の無限ループ"""
        # config file読込
        # ループごとに毎回jsonを読みに行く
        Watch.config = self.load_config()
        # 前回のconfigとことなる内容が読み込まれたらログに出力
        if not Watch.config == Watch.last_config:
            Watch.last_config = Watch.config
            Slack().log(self.log.info, f'設定が更新されました {Watch.config}')

        # ファイル名差分確認
        pattern = Watch.config.glob
        out = self.directory
        txts = {Path(i).stem for i in glob.iglob(f'{pattern}.txt')}
        pngs = {Path(i).stem for i in glob.iglob(f'{out}/{pattern}.png')}
        update_files = txts - pngs

        # Count report
        _counts = report.timestamp_count(
            timestamps=(i[:8] for i in txts),  # 8 <= number of yyyymmdd
            filename=self.statsdirectory / 'watchdog_summary.yaml')
        if self.debug:
            Slack().log(print, f'[DEBUG] FILE COUNTS {_counts}')

        # ---
        # One file plot
        # ---
        # txtファイルだけあってpngがないファイルに対して実行

        for base in update_files:
            try:
                plot_onefile(
                    base + '.txt',
                    directory=self.directory,
                    color=Watch.config.color,
                    linewidth=Watch.config.linewidth,
                    figsize=Watch.config.figsize,
                    shownoise=Watch.config.shownoise,
                    xticks_major_gap=Watch.config.xticks_major_gap,
                    xticks_minor_gap=Watch.config.xticks_minor_gap,
                    ylim=(
                        Watch.config.ymin,
                        Watch.config.ymax,
                    ),
                    yticks=np.arange(
                        Watch.config.ymin,
                        Watch.config.ymax + Watch.config.ystep,
                        Watch.config.ystep,
                    ),
                    ylabel='dBm',
                )
            except ZeroDivisionError as _e:
                Slack().log(self.log.warning,
                            f'{base}: {_e}, txtファイルは送信されてきましたがデータが足りません')
            else:
                filename = f"{self.directory}/{base}.png"
                msg = f'画像の出力に成功しました {filename}'
                Slack().log(self.log.info, msg)
                Slack().upload(msg, filename)
            finally:
                plt.close()
            # Reset count
            Watch.no_update_count = 0
            Watch.no_update_threshold = 2
        else:  # update_filesが空で、更新がないとき
            Watch.no_update_count += 1
            if Watch.no_update_count > Watch.no_update_threshold:
                msg = self.no_update_warning()
                Slack().mention(self.log.warning, msg)
                Watch.no_update_threshold *= 2

        # ---
        # Daily plot
        # ---
        # filename format must be [ %Y%m%d_%H%M%S.txt ]
        days_set = {_[:8] for _ in txts}
        if self.debug:
            Slack().log(print, f'[DEBUG] day_set: {days_set}')
        # txts directory 内にある%Y%m%dのsetに対して実行
        for day in days_set:
            # waterfall_{day}.pngが存在すれば最終処理が完了しているので
            # waterfallをプロットしない -> 次のfor iterへ行く
            if Path(f'{self.directory}/waterfall_{day}.png').exists():
                continue
            # waterfall_{day}.pngが存在しなければ最終処理が完了していないので
            # waterfalll_{day}_update.pngを作成する

            files = glob.glob(f'{day}_*.txt')
            if self.debug:
                Slack().log(
                    print, '[DEBUG] {}--LAST FILES-- {}'.format(
                        day, len(set(Watch.last_files[day]))))
                Slack().log(print,
                            f'[DEBUG] {day}--NOW FILES-- {len(set(files))}')

            # waterfall_update.pngが存在して、
            # かつ
            # ファイルに更新がなければ次のfor iterへ行く
            noupdate = set(Watch.last_files[day]) == set(files)
            exists = Path(
                f'{self.directory}/waterfall_{day}_update.png').exists()
            if exists and noupdate:
                continue
            Watch.last_files[day] = files

            # ファイルに更新があれば更新したwaterfall_update.pngを出力
            trss = tracer.read_traces(*files, usecols=Watch.config.usecols)
            trss.set_merkers(Watch.config.markers)
            _n = DAY_SECOND // Watch.config.transfer_rate  # => 288
            num_of_files_ok = len(files) >= _n
            if self.debug:
                Slack().log(print, f'[DEBUG] limit: {_n}')
                Slack().log(print, f'[DEBUG] length: {len(files)}')
            filename: Path = self.filename_resolver(
                yyyymmdd=day, remove_flag=num_of_files_ok)
            trss.heatmap(
                title=f'{day[:4]}/{day[4:6]}/{day[6:8]}',
                color=Watch.config.color,
                xticks_major_gap=Watch.config.xticks_major_gap,
                xticks_minor_gap=Watch.config.xticks_minor_gap,
                linewidth=Watch.config.linewidth,
                figsize=Watch.config.h_figsize,
                ylim=(
                    Watch.config.ymin,
                    Watch.config.ymax,
                ),
                cmap=Watch.config.cmap,
                cmaphigh=Watch.config.cmaphigh,
                cmaplow=Watch.config.cmaplow,
                cmaplevel=Watch.config.cmaplevel,
                cmapstep=Watch.config.cmapstep,
            )
            plt.savefig(filename)
            # ファイルに保存するときplt.close()しないと
            # 複数プロットが1pngファイルに表示される
            plt.close()  # reset plot
            # logdi = self.log.debug if self.debug else
            msg = f'画像の出力に成功しました {filename}'
            Slack().log(self.log.info, msg)
            Slack().upload(msg, str(filename))

            # データの抜けを検証"""
            rate = '{}min'.format(Watch.config.transfer_rate // 60)
            droped_data = trss.guess_fallout(rate=rate)
            if len(droped_data) > 0:
                Slack().log(self.log.warning, f'データが抜けています {droped_data}')

    def sleep(self):
        """Interval for next loop"""
        if self.debug:
            Slack().log(print,
                        f'[DEBUG] sleeping... {Watch.config.check_rate}')
        # remove progress bar after all
        for _ in tqdm(range(Watch.config.check_rate), leave=False):
            sleep(1)

    def no_update_warning(self) -> str:
        """更新がしばらくないときにWarning上げるメッセージを作成する"""
        no_uptime = Watch.no_update_count * Watch.config.transfer_rate
        if no_uptime < 60:
            message = f'最後の更新から{no_uptime}秒'
        elif no_uptime < 3600:
            message = f'最後の更新から{no_uptime//60}分'
        else:
            message = f'最後の更新から{no_uptime//3600}時'
        message += '間更新がありません。データの送信状況を確認してください。'
        return message

    def stop(self, status: int, err):
        """status=0でWatch.loop()を正常終了する。
        status=1でWatch.loop()を異常終了する。
        """
        if status == 0:
            Slack().log(self.log.info, message=err)
        else:
            Slack().log(self.log.critical, message=err)
        sys.exit(status)

    def error(self, err):
        """Tracebackをエラーに含める"""
        trace_error = partial(self.log.error, exc_info=True)
        Slack().log(trace_error, err)


def parse():
    """引数解析"""
    parser = argparse.ArgumentParser(description=__doc__)
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
    args = parse()
    if args.version:
        print('SAtraceWatchdog ', VERSION)
        sys.exit(0)
    watchdog = Watch(args)
    Slack().log(watchdog.log.info,
                f'ディレクトリの監視を開始しました。 SAtraceWatchdog {VERSION}')
    while True:
        try:
            watchdog.loop()
            watchdog.sleep()
        except KeyboardInterrupt:
            msg = 'キーボード入力により監視を正常終了しました。'
            Slack().log(watchdog.log.info, msg)
            watchdog.stop(0, msg)
        except FileNotFoundError as _e:
            Slack().log(watchdog.log.error, f"エラーが発生しました。 {_e}")
            watchdog.stop(1, _e)
        except BaseException as _e:  # それ以外のエラーはエラー後sleep秒だけ待って再試行
            Slack().log(watchdog.log.error, f"エラーが発生しました。 {_e}")
            watchdog.sleep()


if __name__ == '__main__':
    main()
