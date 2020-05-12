#!/usr/bin/env python3
"""Slack に投稿するモジュール"""
from pathlib import Path
import json
import requests

ROOT = Path(__file__).parent
CONFIGFILE = ROOT / 'config/config.json'
if not CONFIGFILE.exists():
    raise FileNotFoundError(f'{CONFIGFILE} が見つかりません')
with open(CONFIGFILE) as f:
    CONFIG = json.load(f)


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
