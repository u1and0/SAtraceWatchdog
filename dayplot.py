#!/usr/bin/env python3
"""
1日のまとめプロット
上に全スペクトラム
下にウォータフォール(heatmap)
    csv = trs.T.resample('5T').first()
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gs
from matplotlib.pylab import yticks


def fine_ticks(tick, deg):
    """
    * 引数:
        * tick: labelに使うリスト(リスト型)
        * deg: labelをdegごとに分割する
    * 戻り値: tickの最大、最小値、degから求めたイイ感じのnp.array

    ```
    # TEST
    #In :
        for i in range(10,180,10):
            print(fine_ticks(np.arange(181),i))
    #Out :
        [   0.   10.   20.   30.   40.   50.   60.   70.   80.   90.  100.  110.
          120.  130.  140.  150.  160.  170.  180.]
        [   0.   20.   40.   60.   80.  100.  120.  140.  160.  180.]
        [   0.   30.   60.   90.  120.  150.  180.]
        [   0.   45.   90.  135.  180.]
        [   0.   60.  120.  180.]
        [   0.   60.  120.  180.]
        [   0.   90.  180.]
        [   0.   90.  180.]
        [   0.   90.  180.]
        [   0.  180.]
        [   0.  180.]
        [   0.  180.]
        [   0.  180.]
        [   0.  180.]
        [   0.  180.]
        [   0.  180.]
        [   0.  180.]
    ```
    """
    return np.linspace(tick.min(), tick.max(),
                       int((tick.max() - tick.min()) / deg + 1))


def allplt_wtf(df,
               title,
               xlabel='Frequency[kHz]',
               yzlabel='Power[dBm]',
               cmap='jet',
               cmaphigh: float = -60.0,
               cmaplow: float = -100.0,
               cmaplevel: int = 100,
               cmapstep: float = 10,
               extend='both'):
    """スペクトラムプロット / ウォータフォール
    引数:
        df: データフレーム(pd.DataFrame)
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
    ax = df.T.plot(legend=False,
                   color='gray',
                   linewidth=.2,
                   ylim=(-119, -20),
                   ax=ax1)
    # Marker plot
    maxs = df.T.reindex(df.marker).loc[df.marker].max(1)
    # `df.reindex()` for
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
    dfk = df.resample('5T').first()  # 隙間埋める
    # dfk = df.db2mw().resample('5T').mean().mw2db()  # 隙間埋める
    dfk = dfk.reindex(pd.date_range(title, freq='5T', periods=288))  # 最初/最後埋め
    dfk.index = np.arange(len(dfk))  # 縦軸はdatetime index描画できないのでintにする

    # __PLOT WATERFALL______________
    ax2 = plt.subplot(G[1:, :-1], sharex=ax1, rasterized=True)
    # 容量軽減のためここだけラスターイメージで描く
    interval = np.linspace(cmaplow, cmaphigh, cmaplevel)  # cmapの段階
    x, y, z = dfk.columns.values, dfk.index.values, dfk.values
    # Waterfall plot
    ax = plt.contourf(x, y, z, interval, alpha=.75, cmap=cmap, extend=extend)
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
