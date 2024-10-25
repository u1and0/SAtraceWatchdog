""" GMMフィットするクラスとクラスタリングを表示するクラス

Gaussinan Mixture Modelにより2値に分類して、
ヒストグラムの形状を受信している郡と受信していない郡に分ける。

また、それぞれの山の平均値、標準偏差、重み(混合比)といった特徴から
受信、非受信時のS/N比や受信比率を特定する。

Usage:

# 分析初期化
gmm = GMM(data)

# 2値に分類
cluster = gmm.predict()

# 2つの郡の平均、標準偏差、重みをテーブルで表示する。
cluster.summary()

# ヒストグラムのほか、
# カーネル密度推定（KDE）を行って滑らかな山を描画する。
gmm.plot()
"""

from typing import Tuple, Iterable, Optional
from dataclasses import dataclass
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.mixture import GaussianMixture
# from scipy.stats import gaussian_kde


@dataclass
class Cluster:
    """
    集団を2値に分類した特徴量

    Args:
        means: 平均値
        stds: 標準偏差
        weights: 重み(混合比)

    """
    means: Tuple[float, float]
    stds: Tuple[float, float]
    weights: Tuple[float, float]

    def summary(self) -> pd.DataFrame:
        """
        2つのクラスターの平均、標準偏差、重みを表示する。
        """
        # 高・低の山の結果を表示
        higher_peak_idx = np.argmax(self.means)
        lower_peak_idx = np.argmin(self.means)

        return pd.DataFrame({
            "非受信": {
                "平均": f"{self.means[lower_peak_idx]:.2f}",
                "標準偏差": f"{self.stds[lower_peak_idx]:.2f}",
                "重み": f"{self.weights[lower_peak_idx]:.2f}",
            },
            "受信": {
                "平均": f"{self.means[higher_peak_idx]:.2f}",
                "標準偏差": f"{self.stds[higher_peak_idx]:.2f}",
                "重み": f"{self.weights[higher_peak_idx]:.2f}",
            }
        })


class GMM:

    def __init__(self, data: Iterable):
        """
        GMMクラスの初期化

        Args:
            data : 解析対象のデータ
        """
        self.data = data
        self.gmm: Optional[GaussianMixture] = None
        # self.labels = None  # predictで得られたラベルを格納
        # self.probs = None  # predict_probaで得られた確率を格納

    def predict(self) -> Cluster:
        """
        GMMを用いてデータを2つのクラスターに分類する。
        """
        X = np.array(self.data).reshape(-1, 1)
        self.gmm = GaussianMixture(n_components=2, random_state=42)
        # GMMとして予測して分類
        self.gmm.fit(X)

        # gmmの特徴量をClusterクラスに格納する
        means = self.gmm.means_.flatten()
        stds = np.sqrt(self.gmm.covariances_.flatten())
        weights = self.gmm.weights_
        cluster = Cluster(means, stds, weights)
        return cluster

    def plot(self, density=True, **kwargs):
        """
        ヒストグラムとカーネル密度推定、GMMの推定分布を描画する。
        """
        if self.gmm is None:
            raise ValueError("predictメソッドを先に実行してください。")

        data = pd.Series(self.data)
        X = data.values.reshape(-1, 1)
        x_plot = np.linspace(X.min(), X.max(), 1000).reshape(-1, 1)
        log_prob = self.gmm.score_samples(x_plot)
        # サブプロットで、データとKDEを同時にプロット
        fig, ax = plt.subplots()
        data.plot.hist(bins=40, alpha=.6, density=density, ax=ax,
                       **kwargs)  # axを追加
        ax.plot(x_plot, np.exp(log_prob), "k--", label="推定された分布")
        return ax
