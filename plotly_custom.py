import plotly.graph_objects as go

# 白背景、グリッド線濃いめのテンプレート
# usage:
# fig.update_layout(template=template)
template = go.layout.Template(layout=go.Layout(
    template="plotly_white",
    xaxis=dict(
        showgrid=True,  # グリッド線を表示する
        gridwidth=2,  # グリッド線の太さ
        gridcolor='lightgray'  # グリッド線の色
    ),
    yaxis=dict(
        showgrid=True,  # グリッド線を表示する
        gridwidth=2,  # グリッド線の太さ
        gridcolor='lightgray'  # グリッド線の色
    ),
    plot_bgcolor='rgba(0,0,0,0)'  # 背景を透明にする
))
