#!/usr/bin/env python3
"""Slack に投稿するモジュール"""
import os
from slack_sdk import WebClient
from SAtraceWatchdog.tracer import json_load_encode_with_bom

CONFIGFILE = os.getenv("WATCH_CONFIG", "./config/config.json")
if not os.path.exists(CONFIGFILE):
    raise FileNotFoundError(f'{CONFIGFILE} が見つかりません')
CONFIG = json_load_encode_with_bom(CONFIGFILE)


class Slack:
    """Post info and error to slack channel"""
    _token: str = CONFIG.token
    _channel: str = CONFIG.channel_id
    _users: list[str] = CONFIG.users
    slack_post: bool = CONFIG.slack_post
    client = WebClient(_token)

    @classmethod
    def upload(cls, message: str, filename: str):
        """slackに画像を投稿する"""
        cls.client.files_upload_v2(
            channel=cls._channel,
            file=filename,
            title=filename,
        )

    @classmethod
    def message(cls, message):
        """slackにメッセージを投稿する"""
        cls.client.chat_postMessage(
            channel=cls._channel,
            text=message,
        )

    @classmethod
    def log(cls, func, message, err=None):
        """logging関数とSlack().message に同じメッセージを投げる
        usage:
            Slack().log(self.log.info, f'画像の出力に成功しました {filename}')
        """
        func(message)  # log.info(message), log.error(message), ...
        if cls.slack_post:
            cls.message(message)
        if err:
            raise err

    @classmethod
    def mention(cls, func, message, err=None):
        """特定のユーザーにメンションする
        logging関数とSlack().message に同じメッセージを投げる
        usage:
            Slack().log(self.log.info, f'画像の出力に成功しました {filename}')
        """
        for user in cls._users:
            message = f"<@{user}> {message}"
        func(message)  # log.info(message), log.error(message), ...
        if cls.slack_post:
            cls.message(message)
        if err:
            raise err
