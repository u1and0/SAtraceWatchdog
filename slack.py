#!/usr/bin/env python3
import requests
from pathlib import Path


def upload(filename, message, token, channels):
    name = Path(filename).name
    url = "https://slack.com/api/files.upload"
    data = {
        "token": token,
        "channels": channels,
        "title": name,
        "initial_comment": message
    }
    files = {'file': open(filename, 'rb')}
    requests.post(url, data=data, files=files)
