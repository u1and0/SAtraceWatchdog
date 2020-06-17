#!/usr/bin/env python3
"""SAtraceを扱いやすくするクラス Trace()"""
import datetime
import json
from pathlib import Path
import numpy as np
from scipy import stats
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gs
from matplotlib.pylab import yticks


def config_parse_freq(key: str) -> (int, str):
    """stringの周波数を単位変換してfloatで返す"""
    val = key.split()
    freq = float(val[0])
    unit = val[-1]
    return freq, unit


def read_conf(line: str) -> dict:
    """1行目のデータからconfigを読み取りdictで返す

    データ例(実際は改行なし)
    # <20161108_021106> *RST;*CLS;
        :INP:COUP DC;
        :BAND:RES 1 Hz;
        :AVER:COUNT 20;
        :SWE:POIN 2001;
        :FREQ:CENT 22 kHz;
        :FREQ:SPAN 8 kHz;
        :TRAC1:TYPE MINH;
        :TRAC2:TYPE AVER;
        :TRAC3:TYPE MAXH;
        :INIT:CONT 0;
        :FORM REAL,32;
        :FORM:BORD SWAP;
        :INIT:IMM;
    """
    conf_list = [
        i.split(maxsplit=1)  # split first space
        for i in line.split(';')[:-1]  # chomp last \n
    ]
    conf_dict = {k[0]: k[-1] for k in conf_list}
    return conf_dict


def read_trace(
        data: str,
        config: dict = None,
        usecols=None,  # overwrited arg
        *args,
        **kwargs,
) -> pd.DataFrame:
    """dataを読み取ってグラフ用データを返す
    dataはファイル名またはdata string
    > 後者の場合はbase64.b64decode(byte).decode()などとして使用する。

    1行目にスペクトラムアナライザの設定が入っているので、
    dictionaryで返し、
    2行目以降をDataFrameに入れる
    indexの調整をスペアナの設定から自動で行う

    usecolsオプションはconfigの:TRACE:TYPEパース後の名称を指定する。
    (ex: AVER, MAXH, MINH)
    """
    if config is None:  # configを指定しなければ
        # 自動でdataの1行目をconfigとして読み込む
        with open(data, 'r') as f:
            config = read_conf(f.readline())

    # Set config
    names = [
        config[':TRAC1:TYPE'],
        config[':TRAC2:TYPE'],
        config[':TRAC3:TYPE'],
    ]
    center, _ = config_parse_freq(config[':FREQ:CENT'])
    span, unit = config_parse_freq(config[':FREQ:SPAN'])
    points = int(config[':SWE:POIN'])

    # Read DataFrame from filename or string
    df = pd.read_csv(data,
                     sep='\s+',
                     index_col=0,
                     skiprows=1,
                     skipfooter=1,
                     names=names,
                     engine='python',
                     *args,
                     **kwargs)
    # DataFrameをreadしたあとでindexを変更すると、データがないときにエラー
    #
    # => ValueError: Length mismatch: Expected axis has 0 elements,
    # new values have 4001 elements
    #
    # が出てしまうので、NaNを詰めるようにreindex()する。
    if len(df) < points:
        df = df.reindex(index=range(points), columns=names)

    # indexをconfigに合わせて変更
    df.index = np.linspace(
        center - span / 2,
        center + span / 2,
        points,
    )
    df.index.name = unit
    if usecols:
        df = df[usecols]  # Select cols
    return Trace(df)


def read_traces(*files, usecols, **kwargs):
    """複数ファイルにread_trace()して1つのTraceにまとめる

    usecolsを指定しないとValueError
    ['AVER'], ['MINH'], ['MAXH']などを指定する。
    """
    df = pd.DataFrame({
        datetime.datetime.strptime(Path(f).stem, '%Y%m%d_%H%M%S'):  # basename
        read_trace(f, usecols=usecols, *kwargs).squeeze()
        for f in files
    })
    return Trace(df)


def title_renamer(filename: str) -> str:
    """ファイル名から %Y/%m/%d %T 形式の日付を返す"""
    basename = Path(filename).stem
    n = str(basename).replace('_', '')
    #  return like %Y%m%d %H:%M%S
    return f'{n[:4]}/{n[4:6]}/{n[6:8]} {n[8:10]}:{n[10:12]}:{n[12:14]}'


def fine_ticks(tick, deg):
    """
    * 引数:
        * tick: labelに使うリスト(リスト型)
        * deg: labelをdegごとに分割する
    * 戻り値: tickの最大、最小値、degから求めたイイ感じのnp.array

    ```
    # TEST
    # In :
        for i in range(10,180,10):
            print(fine_ticks(np.arange(181),i))
    # Out :
        [  0.   10.   20.   30.   40.   50.   60.   70.   80.   90.  100.  110.
          120.  130.  140.  150.  160.  170.  180.]
        [  0.   20.   40.   60.   80.  100.  120.  140.  160.  180.]
        [  0.   30.   60.   90.  120.  150.  180.]
        [  0.   45.   90.  135.  180.]
        [  0.   60.  120.  180.]
        [  0.   60.  120.  180.]
        [  0.   90.  180.]
        [  0.   90.  180.]
        [  0.   90.  180.]
        [  0.  180.]
        [  0.  180.]
        [  0.  180.]
        [  0.  180.]
        [  0.  180.]
        [  0.  180.]
        [  0.  180.]
        [  0.  180.]
    ```
    """
    return np.linspace(tick.min(), tick.max(),
                       int((tick.max() - tick.min()) / deg + 1))


class Trace(pd.DataFrame):
    """pd.DataFrameのように扱えるTraceクラス"""
    # marker設定
    # "marker":[19.2, 19.8,22.2,24.2,23.4]
    # のような形式でconfig/config.jsonファイルに記述する
    _dirname = Path(__file__).parent
    _configfile = _dirname / 'config/config.json'
    marker = []

    def __init__(self, dataframe):
        super().__init__(dataframe)
        if Path(Trace._configfile).exists():
            with open(Trace._configfile, 'r') as f:
                _config = json.load(f)
            Trace.marker = _config['marker']
            Trace.marker.sort()

    def noisefloor(self, axis: int = 0, percent: float = 25):
        """ 1/4 medianをノイズフロアとし、各列に適用して返す
        引数:
            df: 行が周波数、列が日時(データフレーム型)
            axis: 0 or 1.
                0: 列に適用(デフォルト)
                1: 行に適用
        戻り値:
            df: ノイズフロア(データフレーム型)
        """
        return self.apply(lambda x: stats.scoreatpercentile(x, percent), axis)

    def bandsignal(self, center, span, axis=0):
        """centerから±spanのindexに対しての平均を返す

        >>> np.random.seed(3)
        >>> aa = np.random.randint(0, 100, 10)
        >>> aa
        array([24,  3, 56, 72,  0, 21, 19, 74, 41, 10])

        >>> index = np.linspace(0.1, 1, 10)
        >>> index
        array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1. ])

        >>> trss = Trace(pd.Series(aa, index=index))
        >>> trss.bandsignal(center=0.5, span=0.1)
        """
        df = Trace(self.loc[center - span:center + span])
        mean = df.db2mw().mean()
        return mw2db(mean)

    def heatmap(self,
                title,
                xlabel='Frequency[kHz]',
                yzlabel='Power[dBm]',
                cmap='jet',
                cmaphigh: float = -60.0,
                cmaplow: float = -100.0,
                cmaplevel: int = 100,
                cmapstep: int = 10,
                extend='both'):
        """スペクトラムプロット / ウォータフォール
        引数:
            self: Trace(pd.DataFrame)
                * index: datetime
                * columns: frequency(float type)
            title: string(ウォータフォールのylabelの位置につく)
        戻り値: なし(上にスペクトラムプロット、下にウォータフォール)

        * 全プロットを重ねてラインプロット
        * 注目周波数だけを赤色のマーカーでマーカープロット
        * 一日5分間隔で測定されたデータを整形する(resample, reindexメソッド)
        * ウォータフォールをイメージプロット(countourf plot)"""
        fig = plt.figure(figsize=(8, 12))
        G = gs.GridSpec(3, 14)

        # __ALLPLOT___________________
        ax1 = plt.subplot(G[0, :-1])
        # Spectrum plot
        ax = self.plot(legend=False,
                       color='gray',
                       linewidth=.2,
                       ylim=(-119, -20),
                       ax=ax1)
        # Marker plot
        maxs = self.reindex(self.marker).loc[self.marker].max(1)
        # `self.reindex()` for
        # KeyError: 'Passing list-likes to .loc or [] with
        # any missing labels is no longer supported
        ax = maxs.plot(style='rD',
                       markeredgewidth=1,
                       fillstyle='none',
                       ax=ax1,
                       markersize=5)

        plt.ylabel(yzlabel)
        ax.xaxis.set_ticks_position('top')  # xラベル上にする

        # __MAKE WATERFALL DATA________________
        dfk = self.T.resample('5T').first()  # 隙間埋める
        # dfk = df.db2mw().resample('5T').mean().mw2db()  # 隙間埋める
        dfk = dfk.reindex(pd.date_range(title, freq='5T',
                                        periods=288))  # 最初/最後埋め
        dfk.index = np.arange(len(dfk))  # 縦軸はdatetime index描画できないのでintにする

        # __PLOT WATERFALL______________
        ax2 = plt.subplot(G[1:, :-1], sharex=ax1, rasterized=True)
        # 容量軽減のためここだけラスターイメージで描く
        interval = np.linspace(cmaplow, cmaphigh, cmaplevel)  # cmapの段階
        x, y, z = dfk.columns.values, dfk.index.values, dfk.values
        # Waterfall plot
        ax = plt.contourf(x,
                          y,
                          z,
                          interval,
                          alpha=.75,
                          cmap=cmap,
                          extend=extend)
        d5 = pd.date_range('00:00', '23:55',
                           freq='5T').strftime('%H:%M')  # 5分ごとの文字列
        d5 = np.append(d5, '24:00')  # 24:00は作れないのでappend
        # ...しようとしたけど、上のグラフとラベルかぶるから廃止
        yticks(np.arange(0, 289, 24), d5[::24])
        plt.xlabel(xlabel)
        plt.ylabel(title)

        # __COLOR BAR______________
        ax4 = plt.subplot(G[1:, -1], )
        ax = plt.colorbar(ticks=fine_ticks(interval, cmapstep),
                          cax=ax4)  # カラーバー2区切りで表示
        ax.set_label(yzlabel)

        plt.subplots_adjust(hspace=0)  # グラフ間の隙間なし
        return ax

    def plot_markers(self, *args, **kwargs):
        """marker plot as Diamond"""
        slices = self.squeeze().reindex(self.marker).loc[self.marker]
        # reindex() put off Keyerror
        ax = slices.plot(style='rD', fillstyle='none', *args, **kwargs)
        return ax

    def plot_noisefloor(self, *args, **kwargs):
        """noisefloor plot as black line"""
        line = self.noisefloor()
        _min, _max = self.index.min(), self.index.max()
        ax = plt.plot([_min, _max], [line, line], 'k--', *args, **kwargs)
        return ax

    def guess_fallout(self, rate: str):
        """データ抜けの可能性があるDatetimeIndexを返す"""
        resample = self.T.resample(rate).first()  # rate 300 = 5min resample
        bools = resample.isna().any(1)  # NaN行をTrueにする
        nan_idx = bools[bools].index  # Trueのとこのインデックスだけ抽出
        return nan_idx


def db2mw(a):
    """dB -> mW
    Usage: `df.db2mw()` or `db2mw(df)`
    """
    return np.power(10, a / 10)


def mw2db(a):
    """mW -> dB
    Usage: `df.mw2db()` or `mw2db(df)`

    ```python:TEST
    mw = pd.Series(np.arange(11))
    df = pd.DataFrame({'watt': mw, 'dBm': mw.mw2db(),
                      'dB to watt': mw.mw2db().db2mw()})
    ```
    print(df)
    # [Out]#     dB to watt        dBm  watt
    # [Out]# 0          0.0       -inf     0
    # [Out]# 1          1.0   0.000000     1
    # [Out]# 2          2.0   3.010300     2
    # [Out]# 3          3.0   4.771213     3
    # [Out]# 4          4.0   6.020600     4
    # [Out]# 5          5.0   6.989700     5
    # [Out]# 6          6.0   7.781513     6
    # [Out]# 7          7.0   8.450980     7
    # [Out]# 8          8.0   9.030900     8
    # [Out]# 9          9.0   9.542425     9
    # [Out]# 10        10.0  10.000000    10
    ```
    """
    return 10 * np.log10(a)


# import tracer
#    either
# tracer.db2mw(df)
#    or
# df.db2mw()
# will be ok
setattr(pd.Series, 'db2mw', db2mw)
setattr(pd.DataFrame, 'db2mw', db2mw)
setattr(pd.Series, 'mw2db', mw2db)
setattr(pd.DataFrame, 'mw2db', mw2db)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
