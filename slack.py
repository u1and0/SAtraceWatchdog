#!/usr/bin/env python3
import requests
from pathlib import Path


class Slack:
    """slack instance"""
    def __init__(self, token, channels):
        self.token = token
        self.channels = channels

    def upload(self, filename, message):
        """slackに画像を投稿する"""
        name = Path(filename).name
        url = "https://slack.com/api/files.upload"
        data = {
            "token": self.token,
            "channels": self.channels,
            "title": name,
            "initial_comment": message
        }
        files = {'file': open(filename, 'rb')}
        requests.post(url, data=data, files=files)

    def message(self, message):
        """slackにメッセージを投稿する"""
        url = "https://slack.com/api/chat.postMessage"
        data = {
            "token": self.token,
            "channel": self.channels,
            "text": message,
        }
        requests.post(url, data=data)
