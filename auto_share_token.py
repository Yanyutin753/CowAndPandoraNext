from os import path

import requests
import re

from pandora.openai.auth import Auth0

import json
import os


def Share_token_config():
    # 获取当前代码文件的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 创建指向config.json的相对路径
    config_path = os.path.join(current_dir, 'plugins', '..', 'config.json')

    # 打开并读取config.json文件
    with open(config_path, 'r') as file:
        config_data = json.load(file)

    username = config_data["open_ai_name"]
    password = config_data["open_ai_password"]
    unique_name = config_data["unique_name"]

    proxy = config_data["proxy"]  # 可以链接到v2rayN的http代理，用于访问openai
    expires_in = 0

    print('Login begin: {}'.format(username))

    token_info = {
        'token': 'None',
        'share_token': 'None',
    }


    try:
        token_info['token'] = Auth0(username, password, proxy).auth(False)
        print('Login success: {}'.format(username))
    except Exception as e:
        err_str = str(e).replace('\n', '').replace('\r', '').strip()
        print('Login failed: {}, {}'.format(username, err_str))
        token_info['token'] = err_str

    data = {
        'unique_name': unique_name,
        'access_token': token_info['token'],
        'expires_in': expires_in,
        'show_conversations': True,
    }
    resp = requests.post('https://ai.fakeopen.com/token/register', data=data)
    if resp.status_code == 200:
        token_info['share_token'] = resp.json()['token_key']
        print('share token: {}'.format(token_info['share_token']))
    else:
        err_str = resp.text.replace('\n', '').replace('\r', '').strip()
        print('share token failed: {}'.format(err_str))
        token_info['share_token'] = err_str

    if re.match(r'^(fk-|pk-)', token_info['share_token']):

        with open(config_path, 'r') as file:
            config_data = json.load(file)

        config_data["open_ai_api_key"] = token_info['share_token']

        # 将更新后的内容写回config.json文件
        with open(config_path, 'w') as file:
            json.dump(config_data, file, indent=4)

        print(f"open_ai_api_key has been updated to: {token_info['share_token']}")

    return token_info['share_token']