#!/usr/bin/env python3
"""SAtraceを扱いやすくするクラス Trace()"""
import datetime
import json
from pathlib import Path
from typing import Optional
from types import SimpleNamespace
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.gridspec as gs
from matplotlib.pylab import yticks
from tqdm import tqdm
import pandas as pd


def seaborn_option():
    sns.set(
        context="notebook",
        style="whitegrid",  # "ticks",
        palette='husl',
        font="IPAGothic",
        font_scale=1.5,
        color_codes=False,
        rc={
            'grid.linestyle': ':',
            'grid.color': 'gray',
            'image.cmap': 'viridis'
        })


def config_parse_freq(key: str) -> (int, str):
    """stringの周波数を単位変換してfloatで返す"""
    val = key.split()
    freq = float(val[0])
    unit = val[-1]
    return freq, unit


def read_conf(line: str) -> dict:
    """1行目のデータからconfigを読み取りdictで返す

    データ例(実際は改行なし)
    <1列Trace>                      <3列Trace>
    # 20200627_180505 *RST;         # <20161108_021106> *RST;
    *CLS;                           *CLS;
    :INP:COUP DC;                   :INP:COUP DC;
    :BAND:RES 1 Hz;                 :BAND:RES 1 Hz;
    :AVER:COUNT 10;                 :AVER:COUNT 20;
    :SWE:POIN 1001;                 :SWE:POIN 2001;
    :FREQ:CENT 22.2 kHz;            :FREQ:CENT 22 kHz;
    :FREQ:SPAN 2 kHz;               :FREQ:SPAN 8 kHz;
    :TRAC1:TYPE AVER;               :TRAC1:TYPE MINH;
    :INIT:CONT 0;                   :TRAC2:TYPE AVER;
    :FORM REAL,32;                  :TRAC3:TYPE MAXH;
    :FORM:BORD SWAP;                :INIT:CONT 0;
    :INIT:IMM;                      :FORM REAL,32;
    :POW:ATT 0;                     :FORM:BORD SWAP;
    :DISP:WIND:TRAC:Y:RLEV -30 dBm; :INIT:IMM;
    """
    conf_list = [
        i.split(maxsplit=1)  # split first space
        for i in line.split(';')[:-1]  # chomp last \n
    ]
    conf_dict = {k[0]: k[-1] for k in conf_list}
    return conf_dict


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

    def __init__(self, *args, **kwargs):
        """
        >>> trss = Trace(range(10))
        >>> trss.markers = [0, 2.3, 4.9]
        >>> trss.markers
        [0, 2, 5]
        """
        super().__init__(pd.DataFrame(*args, **kwargs))
        self._markers = None

    @property
    def markers(self):
        """マーカープロパティのゲッター
        selfとして定義されるDataFrameのIndexに最も近い値をマーカーとして内包する。
        """
        return self._markers

    @markers.setter
    def markers(self, values: list[float]):
        """マーカープロパティのセッター
        インデックスの値に最も近いものだけをマーカーとしてセットする
        """
        _index = pd.Series(self.index)
        # self.merkerはpandas.Seriesからキリの良い数値に最も近い数値を探す
        self._markers = [_index.find_closest(m) for m in values]

    def noisefloor(self, *args, **kwargs):
        """ 1/4 quantileをノイズフロアとし、各列に適用して返す"""
        return self.quantile(0.25, *args, **kwargs)

    def sn_ratio(self, *args, **kwargs):
        """ノイズフロアを差し引いてSN比を算出する"""
        return (self - self.noisefloor(*args, **kwargs)).to_trace()

    def bandsignal(self, center, span):
        """centerから±spanのindexに対してのデシベル平均を返す
        >>> aa = np.arange(1, 11).T
        >>> index = np.linspace(0.1, 1, 10)
        >>> trs = Trace(aa, index=index, columns=['a'])
        >>> trs
              a
        0.1   1
        0.2   2
        0.3   3
        0.4   4
        0.5   5
        0.6   6
        0.7   7
        0.8   8
        0.9   9
        1.0  10
        >>> # trs.bandsignal returns dB sum of index 0.4~0.6
        >>> trs.bandsignal(center=0.5, span=0.2)
        a    9.655236
        dtype: float64
        >>> # RuntimeWarning: divide by zero encountered in log10
        """
        start = center - span / 2
        stop = center + span / 2
        df = self.loc[start:stop]
        return df.db2mw().sum()

    def describe_SN(self, tgt_freq: float, percentile=0.95):
        """ 特定周波数の統計値を求める。
        @params
            tgt_freq: float - ターゲット周波数
            percentile: float - 最も高い値から何%の値を返すか。(default 95%)
        @return
            {
                ターゲット周波数(indexの中で最も近い値): float
                受信電力: float
                SN比:  float
                ターゲット受信回数: float
                全受信回数: float
                受信割合: float
            }
        """
        tgt = closest_index(self.index, tgt_freq)
        tr = self.loc[tgt]  # ターゲット周波数のデータ
        trs_sn = self - self.noisefloor()  # SN比
        tr_sn = trs_sn.loc[tgt]
        # カウント
        true_count = (tr_sn >= 10).sum()
        return pd.Series({
            "ターゲット周波数": tgt,
            "受信電力": tr.quantile(percentile),
            "SN比": tr_sn.quantile(percentile),
            "ターゲット受信回数": true_count,
            "全受信回数": len(tr),
            "受信割合": true_count / len(tr)
        })

    def heatmap(
        self,
        title: str,  # 日付 %y/%m/%d
        xlabel: str = 'Frequency[kHz]',
        yzlabel: str = 'Power[dBm]',
        color: str = 'gray',
        xticks_major_gap: Optional[float] = None,
        xticks_minor_gap: Optional[float] = None,
        ylim=(-119, -20),
        linewidth=.2,
        figsize=(8, 12),
        cmap='viridis',
        cmaphigh: float = -60.0,
        cmaplow: float = -100.0,
        cmaplevel: int = 100,
        cmapstep: int = 10,
        extend='both',
        dpi=100,
    ):
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
        # local const
        FREQ = '5min'
        PERIODS = 288
        G = gs.GridSpec(3, 14)

        seaborn_option()

        # __ALLPLOT___________________
        ax1 = plt.subplot(G[0, :-1])
        # Spectrum plot
        ylim = (
            ylim[0] * 0.99,  # 1% loss for graph ytick line
            ylim[1])
        ax = self.plot(legend=False,
                       color=color,
                       linewidth=linewidth,
                       ylim=ylim,
                       figsize=figsize,
                       ax=ax1)
        # Marker plot
        if (self.markers is not None) and (len(self.markers) > 0):
            maxs = self.reindex(self.markers).loc[self.markers].max(1)
            # `self.reindex()` for
            # KeyError: 'Passing list-likes to .loc or [] with
            # any missing labels is no longer supported
            ax = maxs.plot(style='rD',
                           markeredgewidth=1,
                           fillstyle='none',
                           ax=ax1,
                           markersize=5)

        # Generate array of grid & label
        set_xticks(
            ax,
            xticks_major_gap,
            xticks_minor_gap,
            min(self.index),
            max(self.index),
        )

        # Plot modify
        plt.ylabel(yzlabel)
        # Set yzlabel for color bar
        text_xpos = self.index[-1]
        text_ypos = self.min().min()
        plt.text(
            text_xpos * 1.01,
            text_ypos * 0.8,
            f'←{yzlabel}',
            rotation='vertical',
            fontsize=18,
        )
        # Set Marker plot ticks
        ax.xaxis.set_ticks_position('top')  # xラベル上にする
        ax.yaxis.set_ticks_position('left')

        # __MAKE WATERFALL DATA________________
        dfk = self.T.resample(FREQ).first()  # 隙間埋める
        dfk = dfk.reindex(pd.date_range(title, freq=FREQ,
                                        periods=PERIODS))  # 最初/最後埋め
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
        # 範囲外は白抜き
        ax.cmap.set_over("white")
        ax.cmap.set_under("white")
        ax.changed()

        d5 = pd.date_range('00:00', '23:55',
                           freq=FREQ).strftime('%H:%M')  # 5分ごとの文字列
        d5 = np.append(d5, '24:00')  # 24:00は作れないのでappend
        # ...しようとしたけど、上のグラフとラベルかぶるから廃止
        yticks(np.arange(0, PERIODS + 1, 24), d5[::24])
        plt.xlabel(xlabel)
        plt.ylabel(title)

        # __COLOR BAR______________
        ax4 = plt.subplot(G[1:, -1], )
        ax = plt.colorbar(ticks=fine_ticks(interval, cmapstep),
                          cax=ax4)  # カラーバー2区切りで表示

        plt.subplots_adjust(hspace=0)  # グラフ間の隙間なし
        return ax

    def plot_markers(self, *args, **kwargs):
        """marker plot as Diamond"""
        # マーカーがなければ終了
        if not self._markers or len(self._markers) < 1:
            return
        slices = self.loc[self.markers]
        # reindex() put off Keyerror
        ax = slices.plot(style='rD', fillstyle='none', *args, **kwargs)
        return ax

    def plot_noisefloor(self, *args, **kwargs):
        """noisefloor plot as black line"""
        line = self.noisefloor()
        _min, _max = self.index.min(), self.index.max()
        ax = plt.plot([_min, _max], [line, line], 'k--', *args, **kwargs)
        return ax

    def guess_fallout(self, rate: str) -> pd.DatetimeIndex:
        """データ抜けの可能性があるDatetimeIndexを返す"""
        resample = self.T.resample(rate).first()  # rate 300 = 5min resample
        bools = resample.isna().T.any()  # NaNが一つでも含まれる行があればTrue, なければFalse
        nan_idx = bools[bools].index  # Trueのとこのインデックスだけ抽出
        return nan_idx


def read_trace(
    data: str,
    config: dict = None,
    usecols: Optional[str] = None,  # overwrited arg
    *args,
    **kwargs,
) -> Trace:
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
    names = [v for k, v in config.items() if k.startswith(':TRAC')]
    center, _ = config_parse_freq(config[':FREQ:CENT'])
    span, unit = config_parse_freq(config[':FREQ:SPAN'])
    # VISAコマンドのデフォルト値は1001ポイント
    points = int(config[':SWE:POIN']) if ":SWE:POIN" in config.keys() else 1001

    # Read DataFrame from filename or string
    df = pd.read_csv(data,
                     sep=r'\s+',
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
    if usecols is not None:
        df = df[usecols]  # Select cols
    return Trace(df)


def read_traces(*files, usecols: str, **kwargs):
    """複数ファイルにread_trace()して1つのTraceにまとめる

    usecolsを指定しないとValueError
    ['AVER'], ['MINH'], ['MAXH']などを指定する。
    """
    return Trace({
        datetime.datetime.strptime(Path(f).stem, '%Y%m%d_%H%M%S'):  # basename
        read_trace(f, usecols=usecols, *kwargs).squeeze()
        for f in tqdm(files, leave=False)  # remove progress bar after all
    })


def db2mw(a):
    """dB -> mW
    Usage: `df.db2mw()` or `db2mw(df)`
    >>> db2mw(0)
    1.0
    >>> db2mw(10)
    10.0
    >>> np.apply_along_axis(db2mw, 0, np.array([0,3,6,10]))
    array([ 1.        ,  1.99526231,  3.98107171, 10.        ])
    """
    return np.power(10, a / 10)


def mw2db(a):
    """mW -> dB
    Usage: `df.mw2db()` or `mw2db(df)`
    >>> mw = pd.Series(np.arange(11))
    >>> df = pd.DataFrame({'watt': mw, 'dBm': mw.mw2db(),\
                      'dB to watt': mw.mw2db().db2mw()})
    >>> df
        watt        dBm  dB to watt
    0      0       -inf         0.0
    1      1   0.000000         1.0
    2      2   3.010300         2.0
    3      3   4.771213         3.0
    4      4   6.020600         4.0
    5      5   6.989700         5.0
    6      6   7.781513         6.0
    7      7   8.450980         7.0
    8      8   9.030900         8.0
    9      9   9.542425         9.0
    10    10  10.000000        10.0
    """
    return 10 * np.log10(a)


def _find_closest(se: pd.Series, tgt: float):
    """pd.Seriesに含まれる最も近い値を出力する"""
    return se.iloc[(se - tgt).abs().argmin()]


def closest_index(ix: pd.Index, tgt: float) -> float:
    """pd.Indexに含まれる最も近い値を出力する"""
    return ix[np.argmin(np.abs(ix - tgt))]


def to_trace(df: pd.DataFrame) -> Trace:
    return Trace(df)


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
# series.find_closest(value) として登録
setattr(pd.Series, "find_closest", _find_closest)
# Trace化
setattr(pd.Series, "to_trace", to_trace)
setattr(pd.DataFrame, "to_trace", to_trace)

setattr(Trace, 'db2mw', db2mw)
setattr(Trace, 'db2mw', db2mw)
setattr(Trace, 'mw2db', mw2db)
setattr(Trace, 'mw2db', mw2db)
# series.find_closest(value) として登録
setattr(Trace, "find_closest", _find_closest)


def json_load_encode_with_bom(filename):
    """jsonファイルのBOMあり/なしから適切なencodingを判定して、
    適切にjson.loadする。
    """
    with open(filename) as f:
        firstline = f.readline()
    is_with_bom = firstline[0] == '\ufeff'
    encoding = 'utf-8-sig' if is_with_bom else 'utf-8'
    with open(filename, 'r', encoding=encoding) as f:
        # プロパティアクセスするためにSimpleNamespaceを使う
        # config.property.name ができる
        config = json.load(f, object_hook=lambda x: SimpleNamespace(**x))
    return config


def set_xticks(ax, major_gap: Optional[float], minor_gap: Optional[float],
               min_v: float, max_v: float):
    """axのX軸の補助線を設定する

    Args:
    - ax (Axes): The Axes object where tick positions will be set.
    - major_gap (float, optional): Gap size between the primary ticks (major). Defaults to None for no gap adjustment.
    - minor_gap (float, optional): Gap size between secondary ticks (minor). Defaults to None for no gap adjustment.
    - min_v (float): The minimum value on which to set major and minor ticks.
    - max_v (float): The maximum value on which to set major and minor ticks.
    """
    major_is_float = major_gap is not None
    minor_is_float = minor_gap is not None
    if major_is_float and minor_is_float:
        if major_gap < minor_gap:
            raise ValueError(
                'Expected "major_gap" to be larger than or equal to "minor_gap".'
            )
    # shiftはnp.arangeで最大値が切り捨てられてしまうためにあえて小さい数字をいれる
    shift = major_gap if major_gap else 0.000001
    max_v += shift
    if major_gap is not None:
        major_ticks = np.arange(min_v, max_v, major_gap)
        ax.set_xticks(major_ticks)
    if minor_gap is not None:
        minor_ticks = np.arange(min_v, max_v, minor_gap)
        ax.set_xticks(minor_ticks, minor=True)
        ax.grid(which="minor")


if __name__ == '__main__':
    import doctest
    doctest.testmod()
