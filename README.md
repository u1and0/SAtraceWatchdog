SAtraceの結果を監視→自動可視化するツールです。
txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します。

## Installation

```
$ git clone https://github.com/u1and0/SAtraceWatchdog.git
```

or use docker

```
$ docker pull u1and0/satracewatchdog:latest
```

## Usage

```
usage: watchdog.py [-h] [-d DIRECTORY] [-l LOGDIRECTORY] [--debug]

txt監視可視化ツール txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します。

optional arguments:
-h, --help            show this help message and exit
-d DIRECTORY, --directory DIRECTORY
                    出力ディレクトリ
-l LOGDIRECTORY, --logdirectory LOGDIRECTORY
                    ログファイル出力ディレクトリ
--debug               debug機能有効化
```

...or use docker

```
$ docker run -d \
             -v `pwd`/data:/data \
             -v `pwd`/png:/png \
             -v `pwd`/log:/log \
             -v `pwd`/config:/usr/bin/SAtraceWatchdog/config \
             u1and0/SAtraceWatchdog \
             --directory /png \
             --log-directory /log \
```


## Overview
* txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します。
* 設定はconfig.jsonで行います。
  * SAtraceWatchdogを再立ち上げする必要はありません。自動で反映されます。
* ほとんどの通知をslackチャンネルに送信します。

## Features
### 入力ファイルと出力ファイル
* 現在ディレクトリ(以下、txtディレクトリ)のtxtファイルを定期的に調べて、出力ディレクトリ(以下、pngディレクトリ)にpng形式のファイルを出力します。
* txtディレクトリにあってpngディレクトリにないファイル名(拡張子は無視)を出力します。

### 設定
* 設定ファイルはconfig/config.jsonにまとめられています。
  * `token`: slackトークン
  * `channel_id`: slack チャンネルID
  * `check_rate`: 確認間隔(sec)
  * `glob`: テキストファイルを抜き出すglobパターン
  * `marker`: マーカーをつける周波数リスト
  * `transfer_rate`: テキストファイル送信間隔(sec)
  * `usecols`: 使用する列名
  * `cmaphigh`: カラーバーの最高値
  * `cmaplow`: カラーバーの最低値

### ログ
* logディレクトリに、監視開始日時の名前でログファイルを作成します。
> (例) `log/watchdog_200430_072050.log`
* ログファイルには各通知、エラーメッセージなどが記録されます。
> (例) `[INFO] watchdog   : 2020-06-14 22:04:21,559 画像の出力に成功しました ../png/waterfall_20151111_update.png`
> (例) `[WARNING] watchdog   : 2020-06-14 22:04:22,005 データが抜けています DatetimeIndex(['2015-11-11 14:50:00'], dtype='datetime64[ns]', freq='5T')`

### エラー通知
* slack botを使用してエラーメッセージなどをslackへ通知します。
* 設定ファイルはconfig/config.jsonを参照してください。

### サマリー
* statsディレクトリに日にちごとのデータファイルカウントの結果を出力します。
* ファイル名: `watchdog_summary.yaml`
> (例) '20151111': 7, '20161108': 12
> 2015年11月11日に7ファイル、2016年11月08日に12ファイルが出力されたことを示します。
* 一行に各時間に対するconfigファイルに記されたマーカーの±0.2kHz範囲のdB平均値を表にします。
* ファイル名: `watchdog_SN.csv`


## Update
* v0.4.0          [add] SN report csv
* v0.3.0          [add] Output count report, Config color map high/low.
* v0.2.6          [fix] default directory path
* v0.2.5          [fix] `read_traces()` use `reindex()` if datafile has no data value
* v0.2.4          [fix] no data error raise
* v0.2.3          [fix] slack.upload() -> slack.message()
* v0.2.2          no slack upload()
* v0.2.1          [mod] load config if configfile exist
* v0.2.0          一定時間更新がないとWarningを送信します
* v0.1.0          [fix] log output piped to slackbot
* v0.0.0          [merge] develop -> master



### Others
5分ごとのグラフ化(自動)
→SAtraceWatchdog.watchdog.py

1txtの可視化(自動)
→SAtraceWatchdog.oneplot.py

1日の サマリープロット(自動)
→SAtraceWatchdog.dayplot.py

動的可視化(手動)
→SAtraceGview.gview.py

選択的可視化(手動)
→SAtraceGview.gview.py
