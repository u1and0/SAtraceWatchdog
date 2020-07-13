#!/usr/bin/env python3
"""Slack に投稿するモジュール"""
from pathlib import Path
import json
import requests
from SAtraceWatchdog.tracer import json_load_encode_with_bom

ROOT = Path(__file__).parent
CONFIGFILE = ROOT / 'config/config.json'
if not CONFIGFILE.exists():
    raise FileNotFoundError(f'{CONFIGFILE} が見つかりません')
CONFIG = json_load_encode_with_bom(CONFIGFILE)


class Slack:
    """slack instance"""
    token = CONFIG['token']
    channels = CONFIG['channel_id']

    @classmethod
    def upload(cls, filename, message):
        """slackに画像を投稿する"""
        name = Path(filename).name
        url = "https://slack.com/api/files.upload"
        data = {
            "token": Slack.token,
            "channels": Slack.channels,
            "title": name,
            "initial_comment": message
        }
        files = {'file': open(filename, 'rb')}
        requests.post(url, data=data, files=files)

    @classmethod
    def message(cls, message):
        """slackにメッセージを投稿する"""
        url = "https://slack.com/api/chat.postMessage"
        data = {
            "token": Slack.token,
            "channel": Slack.channels,
            "text": message,
        }
        requests.post(url, data=data)

    @classmethod
    def log(cls, func, message, err=None):
        """logging関数とSlack().message に同じメッセージを投げる"""
        func(message)  # log.info(message), log.error(message), ...
        cls.message(message)
        if err:
            raise err
