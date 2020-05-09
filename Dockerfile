# txt監視可視化ツール
# txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します。
# Usage: docker run -d
#           -v `pwd`:/data\
#           -v ../png:/png\
#           -v ../log:/log\
#           u1and0/SAtraceWatchdog\
#           --directory /png\
#           --log-directory /log\
#           --glob '2020*'\
#           --sleepsec 300

FROM python:3.8-slim
RUN pip install --upgrade --no-cache-dir pandas matplotlib seaborn
RUN pip install --upgrade --no-cache-dir requests
RUN apt-get update &&\
    apt-get install -y fonts-ipafont fontconfig &&\
    fc-cache -fv

COPY ./__init__.py /usr/bin/SAtraceWatchdog/
COPY ./oneplot.py /usr/bin/SAtraceWatchdog/
COPY ./tracer.py /usr/bin/SAtraceWatchdog/
COPY ./watchdog.py /usr/bin/SAtraceWatchdog/
COPY ./slack.py /usr/bin/SAtraceWatchdog/
RUN chmod -R +x /usr/bin/SAtraceWatchdog
ENV PYTHONPATH="/usr/bin"
ENTRYPOINT ["/usr/bin/SAtraceWatchdog/watchdog.py"]
# recommend option
# --directory /png --log-directory /log --glob '2020*' --sleepsec 300

LABEL maintainer="u1and0 <e01.ando60@gmail.com>" \
      description="txtファイルとpngファイルの差分をチェックして、グラフ化されていないファイルだけpng化します" \
      version="SAtraceWatchdog:v0.0.0"
