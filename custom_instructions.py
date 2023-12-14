import requests
import json
import os


def modify_messages_user(about_user_message):
    # 获取当前代码文件的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 创建指向config.json的相对路径
    config_path = os.path.join(current_dir, 'config.json')

    # 打开并读取config.json文件
    with open(config_path, 'r') as file:
        config_data = json.load(file)
    token = config_data["open_ai_api_key"]
    _, about_model_message = get_messages()
    print(about_user_message, about_model_message, token)

    url = 'https://ai.fakeopen.com/api/user_system_messages'
    headers = {
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Authorization': f'Bearer {token}'
    }
    data = {
        "about_user_message": about_user_message,
        "about_model_message": about_model_message,
        "enabled": True
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()


def modify_messages_model(about_model_message):
    # 获取当前代码文件的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 创建指向config.json的相对路径
    config_path = os.path.join(current_dir, 'config.json')

    # 打开并读取config.json文件
    with open(config_path, 'r') as file:
        config_data = json.load(file)
    token = config_data["open_ai_api_key"]
    about_user_message, _ = get_messages()

    url = 'https://ai.fakeopen.com/api/user_system_messages'
    headers = {
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Authorization': f'Bearer {token}'
    }
    data = {
        "about_user_message": about_user_message,
        "about_model_message": about_model_message,
        "enabled": True
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()


def get_messages():
    # 获取当前代码文件的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 创建指向config.json的相对路径
    config_path = os.path.join(current_dir, 'config.json')

    # 打开并读取config.json文件
    with open(config_path, 'r') as file:
        config_data = json.load(file)
    token = config_data["open_ai_api_key"]

    url = 'https://ai.fakeopen.com/api/user_system_messages'
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': '*/*'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        about_user_message = data.get("about_user_message")
        about_model_message = data.get("about_model_message")
        return about_user_message, about_model_message
    else:
        return None, None
