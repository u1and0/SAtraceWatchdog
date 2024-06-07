# txt監視可視化ツール
# txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します。
# Usage: docker run -d \
#           -v `pwd`/data:/data \
#           -v `pwd`/png:/png \
#           -v `pwd`/log:/log \
#           -v `pwd`/stats:/stats \
#           -v `pwd`/config:/usr/bin/SAtraceWatchdog/config \
#           u1and0/SAtraceWatchdog \
#           --directory /png \
#           --log-directory /log \

# ビルドコンテナ
FROM python:3.12.3-bullseye as builder
WORKDIR /opt/app
COPY requirements.txt /opt/app
RUN pip install --upgrade -r requirements.txt

# 実行コンテナ
FROM python:3.12.3-slim-bullseye as runner
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Font & Timezone setting
RUN apt-get update &&\
    apt-get install -y fonts-ipafont \
                        fontconfig \
                        tzdata &&\
    fc-cache -fv &&\
    apt-get clean

RUN useradd -r watchuser
COPY __init__.py /usr/bin/SAtraceWatchdog/
COPY oneplot.py /usr/bin/SAtraceWatchdog/
COPY tracer.py /usr/bin/SAtraceWatchdog/
COPY main.py /usr/bin/SAtraceWatchdog/
COPY slack.py /usr/bin/SAtraceWatchdog/
COPY report.py /usr/bin/SAtraceWatchdog/
RUN chmod -R +x /usr/bin/SAtraceWatchdog

USER watchuser
ENV PYTHONPATH="/usr/bin"
ENV TZ="Asia/Tokyo"
ENTRYPOINT ["/usr/bin/SAtraceWatchdog/main.py"]

LABEL maintainer="u1and0 <e01.ando60@gmail.com>" \
      description="txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します" \
      version="u1and0/satracewatchdog:v0.6.10"
