import json
import requests

from secret import settings


SLACK_WEB_HOOK_URL = settings.SLACK_WEB_HOOK_URL
SLACK_USER_ID = settings.SLACK_USER_ID
TOKEN = settings.TOKEN
CHANNEL_ID = settings.CHANNEL_ID


def notify_slack(message: str = 'Completed.', mention: bool = True) -> None:
    web_hook_url = SLACK_WEB_HOOK_URL
    user_id = SLACK_USER_ID

    text = message

    if mention:
        text = '<{}>'.format(user_id) + text

    data = {'text': text,
            'username': '!!!! 汚部屋 警報 !!!!',
            'link_names': 1,  # 名前をリンク化
            }

    requests.post(web_hook_url, data=json.dumps(data))
    print('Completed to notify to slack.')  # TODO: make it logger


def upload_to_slack(file_path: str):
    token = TOKEN
    cannel_id = CHANNEL_ID

    files = {'file': open(file_path, 'rb')}
    param = {'token': token, 'channels': cannel_id}
    res = requests.post(url="https://slack.com/api/files.upload",
                        params=param,
                        files=files)
