""" GMMフィットするクラスとクラスタリングを表示するクラス

Gaussinan Mixture Modelにより2値に分類して、
ヒストグラムの形状を受信している郡と受信していない郡に分ける。

また、それぞれの山の平均値、標準偏差、重み(混合比)といった特徴から
受信、非受信時のS/N比や受信比率を特定する。

Usage:

# 分析初期化
>>> gmm = GMM(data)
cluster = gmm.classify()

# 2値に分類
>>> power = np.arange(-100, -20, 20).reshape(-1, 1)
# array([[-100], [ -80], [ -60], [ -40]])

>>> gmm.predict(power)
array([0, 0, 1, 1])

-80未満は0なので未受信状態、
-80以上は1なので受信状態。

# 2つの郡の平均、標準偏差、重みをテーブルで表示する。
>>> cluster.summary()
|    |          非受信  | 受信 |
| 平均	|       -85.93  | -49.18 |
| 標準偏差 |	5.41    | 7.26 |
| 重み |	    0.89    | 0.11 |

実際はpd.DataFrameで返ってくる

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

_GMM_CLASSIFY_ERROR = "GMM.classify()を先に実行してください。"


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

        - 平均: 山の平均値
        - 標準偏差: σ, 山のばらつき。平均±2σで95%が存在する
        - 重み: 存在の割合
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
        Gaussinan Mixture Modelにより2値に分類して、
        ヒストグラムの形状を受信している郡と受信していない郡に分ける。

        また、それぞれの山の平均値、標準偏差、重み(混合比)といった特徴から
        受信、非受信時のS/N比や受信比率を特定する。

        Usage:
        GMMクラスの初期化

        Args:
            data : 解析対象のデータ

        Gaussian Mixture Model for classifying data into two groups.

        Args:
            data (Iterable): The input data for analysis. Can be a pandas Series,
                numpy array, or other iterable.
        """
        if isinstance(data, pd.Series):
            self.data = data.to_numpy().ravel()
        elif isinstance(data, np.ndarray):
            self.data = data.ravel()
        else:
            self.data = np.array(data).ravel()  # Ensure data is a NumPy array
        self.gmm: Optional[GaussianMixture] = None
        self._cluster: Optional[Cluster] = None  # Store the cluster object

    def classify(self) -> Cluster:
        """
        GMMを用いてデータを2つのクラスターに分類する。
        Fits the GMM to the data and returns the cluster information.
        """
        X = self.data.reshape(-1, 1)
        self.gmm = GaussianMixture(n_components=2, random_state=42)
        self.gmm.fit(X)

        means = self.gmm.means_.flatten()
        stds = np.sqrt(self.gmm.covariances_.flatten())
        weights = self.gmm.weights_

        self._cluster = Cluster(means, stds, weights)
        return self._cluster

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        gmmで分類したラベルを0または1のArrayで返します。
        低い山で1, 高い山で0が返ります。
        pd.Series型を渡すときは `se.values.reshape(-1,1)` をする必要があります。

        Predicts cluster labels (0 or 1) for given input data. Lower mean gets label 1.

        Args:
            X (np.ndarray): The data for prediction, should be a numpy array.
            Must be reshaped to (-1, 1) if it's a single feature.

        Returns:
             np.ndarray: Predicted labels (0 or 1).
        """
        if self.gmm is None:
            raise ValueError(_GMM_CLASSIFY_ERROR)

        if isinstance(X, pd.Series):
            X = X.values.reshape(-1, 1)
        elif isinstance(X, np.ndarray):
            X = X.reshape(-1, 1)

        labels = self.gmm.predict(X)

        # Ensure lower mean is labeled as 1
        if self._cluster is not None and len(self._cluster.means) == 2:
            if self._cluster.means[0] > self._cluster.means[1]:
                labels = np.array([1 if x == 0 else 0 for x in labels])
        return labels

    def plot(self, density=True, alpha=0.8, ax=None, bins=40, **kwargs):
        """
        Plots the histogram, kernel density estimate, and estimated GMM distribution.

        Args:
            ax (matplotlib.axes.Axes, optional): Axes object to plot on. Creates a
                new figure if None. Defaults to None.
             **kwargs: Arguments passed to `pd.Series.hist` for customizing the histogram.
        Returns:
              matplotlib.axes.Axes: Axes object.
        """
        if self.gmm is None:
            raise ValueError(_GMM_CLASSIFY_ERROR)

        # サブプロットで、データとKDEを同時にプロット
        if ax is None:
            fig, ax = plt.subplots()

        pd.Series(self.data).plot.hist(alpha=alpha,
                                       density=density,
                                       ax=ax,
                                       bins=bins,
                                       **kwargs)
        if density:
            # density=Trueとしないと表示が潰れて見えない
            X = self.data.reshape(-1, 1)
            x_plot = np.linspace(X.min(), X.max(), 1000).reshape(-1, 1)
            log_prob = self.gmm.score_samples(x_plot)
            ax.plot(x_plot,
                    np.exp(log_prob),
                    color="gray",
                    ls="--",
                    alpha=alpha)
        return ax
