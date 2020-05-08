SAtraceの結果を監視→自動可視化するツールです。
txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します。

## Installation



## Usage

```
usage: watchdog.py [-h] [-d DIRECTORY] [-g GLOB] [-s SLEEPSEC]


optional arguments:
  -h, --help            show this help message and exit
  -d DIRECTORY, --directory DIRECTORY
                        出力ディレクトリ
  -g GLOB, --glob GLOB  入力ファイル名にglobパターンを使う
  -s SLEEPSEC, --sleepsec SLEEPSEC
                        チェック間隔(sec)
```

## Overview

Usage:
    $ watchdog.py --directory ../png --glob '2020/*' --sleepsec 300

上のスクリプトは

* ../pngディレクトリにpngファイルを出力します。
* 2020が接頭に着くファイルのみを処理します。
* 300秒ごとにtxtファイルとpngファイルの差分をチェックします。
* スター(\*)はshell上で展開されてしまうのを防ぐためにバックスラッシュエスケープが必要。

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
