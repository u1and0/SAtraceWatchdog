SAtraceの結果を監視→自動可視化するツールです。
txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します。

## Installation

```
$ git clone https://github.com/u1and0/SAtraceWatchdog.git
```

or use docker

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

## Usage

```
usage: watchdog.py [-h] [-d DIRECTORY] [-l LOGDIRECTORY] [--debug]

txt監視可視化ツール txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します。

optional arguments:
-h, --help            show this help message and exit
-d DIRECTORY, --directory DIRECTORY
¦   ¦   ¦   ¦   ¦   出力ディレクトリ
-l LOGDIRECTORY, --logdirectory LOGDIRECTORY
¦   ¦   ¦   ¦   ¦   ログファイル出力ディレクトリ
--debug               debug機能有効化
```

## Overview


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
