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
FROM python:3.8.1-buster as builder
WORKDIR /opt/app
COPY requirements.lock /opt/app
RUN pip install --upgrade -r requirements.lock

# 実行コンテナ
FROM python:3.8.1-slim-buster as runner
COPY --from=builder /usr/local/lib/python3.8/site-packages /usr/local/lib/python3.8/site-packages

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
COPY watchdog.py /usr/bin/SAtraceWatchdog/
COPY slack.py /usr/bin/SAtraceWatchdog/
COPY report.py /usr/bin/SAtraceWatchdog/
RUN chmod -R +x /usr/bin/SAtraceWatchdog

USER watchuser
ENV PYTHONPATH="/usr/bin"
ENV TZ="Asia/Tokyo"
ENTRYPOINT ["/usr/bin/SAtraceWatchdog/watchdog.py"]

LABEL maintainer="u1and0 <e01.ando60@gmail.com>" \
      description="txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します" \
      version="u1and0/satracewatchdog:v0.5.1"
