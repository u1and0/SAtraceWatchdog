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
from collections import namedtuple, defaultdict
import matplotlib.pyplot as plt
from SAtraceWatchdog import tracer
from SAtraceWatchdog.oneplot import plot_onefile
from SAtraceWatchdog.slack import Slack
from SAtraceWatchdog.report import timestamp_count


class Watch:
    """watchdog class"""
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).parent
    parser.add_argument('-d',
                        '--directory',
                        help='出力ディレクトリ',
                        default=os.getcwd())
    parser.add_argument('-l',
                        '--logdirectory',
                        help='ログファイル出力ディレクトリ',
                        default=root / 'log')
    parser.add_argument('--debug', help='debug機能有効化', action='store_true')
    args = parser.parse_args()
    slackbot = Slack()

    def __init__(self):
        """watchdog init"""
        self.last_config = None
        self.last_files = defaultdict(lambda: [])
        self.last_base = None
        self.no_update_count = 0
        self.no_update_threshold = 1
        self.configfile = Watch.root / 'config/config.json'
        self.config = None

        # loggerの設定
        Watch.directory_check(Watch.args.directory)
        Watch.directory_check(Watch.args.logdirectory)
        Watch.set_logger()
        self.log = logging.getLogger(__name__)

        # logger, slackbotの設定
        message = 'ディレクトリの監視を開始しました...'
        self.log.info(message)
        Watch.slackbot.message(message)

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
            print(message)
        if not makedir.is_dir():  # 存在はするけれどもディレクトリ以外を指定されたらエラー
            message = f'{makedir.resolve()} はディレクトリではありません'
            raise IOError(message)

    def load_config(self):
        """configの読み込み
        config.json を読み込み、
        config_keysに指定されたワードのみをConfigとして返す
        """
        with open(self.configfile, 'r') as f:
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

    @classmethod
    def set_logger(cls):
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
            filename=f'{cls.args.logdirectory}/watchdog_{timestamp}.log',
            maxBytes=1e6,
            encoding='utf-8',
            backupCount=3)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        # ファイル用ハンドラをルートロガーに追加
        root_logger.addHandler(file_handler)

    def filename_resolver(self, yyyymmdd, number_of_files):
        """Decide waterfall filenamene
        return:
            waterfall_yymmdd_update.png
                or
            waterfall_yymmdd.png

        _update.pngが存在して、
            かつ
        ファイル数が一日分=288ファイルあったら
            waterfall_{yyyymmdd}_update.pngを削除して、
            waterfall_{yyyymmdd}.pngを保存する
        """
        filename = f'{Watch.args.directory}/waterfall_{yyyymmdd}_update.png'
        # _update.pngが存在して、かつ
        file_exist = Path(filename).exists()
        # ファイル数が一日分=288ファイルあったら
        number_of_files_in_a_day = DAY_SECOND / self.config.transfer_rate
        number_of_files_ok = number_of_files >= number_of_files_in_a_day
        if file_exist and number_of_files_ok:
            # waterfall_{yyyymmdd}_update.pngを削除して、
            os.remove(filename)
            # waterfall_{yyyymmdd}.pngというファイル名を返す
            filename = f'{Watch.args.directory}/waterfall_{yyyymmdd}.png'
        return filename

    def loop(self):
        """pngファイルの出力とログ出力の無限ループ"""
        # config file読込
        # ループごとに毎回jsonを読みに行く
        if not Path(self.configfile).exists():
            message = f'設定ファイル {self.configfile} が存在しません'
            self.log.error(message)
            Watch.slackbot.message(message)
            raise FileNotFoundError(message)
        self.config = self.load_config()
        # 前回のconfigとことなる内容が読み込まれたらログに出力
        if not self.config == self.last_config:
            self.last_config = self.config
            message = f'設定が更新されました {self.config}'
            self.log.info(message)
            Watch.slackbot.message(message)

        # ファイル名差分確認
        pattern = self.config.glob
        out = Watch.args.directory + '/'  # append directory last '/'
        txts = {Path(i).stem for i in glob.iglob(pattern + '.txt')}
        pngs = {Path(i).stem for i in glob.iglob(out + pattern + '.png')}
        update_files = txts - pngs

        # Count report
        _counts = timestamp_count(
            timestamps=(i[:8] for i in txts),  # 8 <= number of yyyymmdd
            filename=Watch.args.logdirectory / 'watchdog_summary.yaml')
        if Watch.args.debug:
            message = f'[DEBUG] FILE COUNTS {_counts}'
            self.log.info(message)
            Watch.slackbot.message(message=message)

        # ---
        # One file plot
        # ---
        # txtファイルだけあってpngがないファイルに対して実行
        try:
            for base in update_files:
                plot_onefile(base + '.txt', directory=Watch.args.directory)
                message = f'画像の出力に成功しました {Watch.args.directory}/{base}.png'
                if Watch.args.debug:
                    message = '[DEBUG] ' + message
                self.log.info(message)
                Watch.slackbot.message(message=message)
                # Reset count
                self.no_update_count = 0
                self.no_update_threshold = 2
            else:  # update_filesが空で、更新がないとき
                self.no_update_count += 1
                if self.no_update_count > self.no_update_threshold:
                    self.no_update_warning()
                    self.no_update_threshold *= 2

            # ---
            # Daily plot
            # ---
            # filename format must be [ %Y%m%d_%H%M%S.txt ]
            days_set = {_[:8] for _ in txts}
            # txts directory 内にある%Y%m%dのsetに対して実行
            for day in days_set:
                # waterfall_{day}.pngが存在すれば最終処理が完了しているので
                # waterfallをプロットしない -> 次のfor iterへ行く
                if Path(f'{Watch.args.directory}/waterfall_{day}.png').exists(
                ):
                    continue
                # waterfall_{day}.pngが存在しなければ最終処理が完了していないので
                # waterfalll_{day}_update.pngを作成する

                files = glob.glob(f'{day}_*.txt')
                if Watch.args.debug:
                    print('--LAST FILES-- ', set(self.last_files[day]))
                    print('--FILES-- ', set(files))

                # ファイルに更新がなければwaterfall_update.pngは出力しない
                if set(self.last_files[day]) == set(files):
                    continue

                # ファイルに更新があれば更新したwaterfall_update.pngを出力
                self.last_files[day] = files
                trss = tracer.read_traces(*files, usecols=self.config.usecols)
                filename = self.filename_resolver(yyyymmdd=day,
                                                  number_of_files=len(files))
                trss.heatmap(title=f'{day[:4]}/{day[4:6]}/{day[6:8]}',
                             cmap='viridis')
                plt.savefig(filename)
                # ファイルに保存するときplt.close()しないと
                # 複数プロットが1pngファイルに表示される
                plt.close()  # reset plot
                message = f'画像の出力に成功しました {filename}'
                if Watch.args.debug:
                    message = '[DEBUG] ' + message
                self.log.info(message)
                Watch.slackbot.message(message=message)

                # データの抜けを検証"""
                droped_data = Watch.guess_fallout(trss.T)
                if any(droped_data):
                    message = f'データが抜けています {droped_data}'
                    self.log.warning(message)
                    Watch.slackbot.message(message)
        except ValueError as e:
            message = f'{base}: {e}, txtファイルは送信されてきましたがデータが足りません'
            self.log.error(message)
            Watch.slackbot.message(message)

    def sleep(self):
        """Interval for next loop"""
        if Watch.args.debug:
            self.log.info(f'[DEBUG] sleeping... {self.config.check_rate}')
        sleep(self.config.check_rate)

    def no_update_warning(self):
        """更新がしばらくないときにWarning上げる"""
        no_uptime = self.no_update_count * self.config.transfer_rate
        if no_uptime < 60:
            message = f'最後の更新から{no_uptime}秒間更新がありません。データの送信状況を確認してください。'
        elif no_uptime < 3600:
            message = f'最後の更新から{no_uptime//60}分間更新がありません。データの送信状況を確認してください。'
        else:
            message = f'最後の更新から{no_uptime//3600}時間更新がありません。データの送信状況を確認してください。'
        self.log.warning(message)
        Watch.slackbot.message(message)

    @staticmethod
    def guess_fallout(df):
        """データ抜けの可能性があるDatetimeIndexを返す"""
        resample = df.resample('5T').first()  # 5min resample
        bools = resample.isna().any(1)  # NaN行をTrueにする
        nan_idx = bools[bools].index  # Trueのとこのインデックスだけ抽出
        return nan_idx


def main():
    """entry point"""
    watchdog = Watch()
    """ファイル差分チェックを実行し、pngファイルを保存する
    Ctrl+Cで止めない限り続く
    """
    while True:
        watchdog.loop()
        watchdog.sleep()


if __name__ == '__main__':
    DAY_SECOND = 60 * 60 * 24
    main()
