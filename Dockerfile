# txt監視可視化ツール
# txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します。
# Usage: docker run -d \
#           -v `pwd`/data:/data \
#           -v `pwd`/png:/png \
#           -v `pwd`/log:/log \
#           -v `pwd`/config:/usr/bin/SAtraceWatchdog/config \
#           u1and0/SAtraceWatchdog \
#           --directory /png \
#           --log-directory /log \

FROM python:3.8-slim
COPY requirements.txt requirements.txt
RUN pip install --upgrade --no-cache-dir -r requirements.txt
RUN apt-get update &&\
    apt-get install -y fonts-ipafont \
                        fontconfig \
                        tzdata &&\
    fc-cache -fv &&\
    apt-get clean
ENV TZ Asia/Tokyo

COPY __init__.py /usr/bin/SAtraceWatchdog/
COPY oneplot.py /usr/bin/SAtraceWatchdog/
COPY tracer.py /usr/bin/SAtraceWatchdog/
COPY watchdog.py /usr/bin/SAtraceWatchdog/
COPY slack.py /usr/bin/SAtraceWatchdog/
COPY report.py /usr/bin/SAtraceWatchdog/
RUN chmod -R +x /usr/bin/SAtraceWatchdog
ENV PYTHONPATH="/usr/bin"
ENTRYPOINT ["/usr/bin/SAtraceWatchdog/watchdog.py"]

LABEL maintainer="u1and0 <e01.ando60@gmail.com>" \
      description="txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します" \
      version="u1and0/satracewatchdog:v0.0.0"
