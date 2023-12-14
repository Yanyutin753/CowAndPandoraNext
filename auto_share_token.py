import requests
import re
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
        TokensTool_url = config_data["TokensTool_url"]

    resp = requests.get(TokensTool_url)
    if resp.status_code == 200:
        pool_token = resp.json()['data']
        print('share token: {}'.format(pool_token))
    else:
        err_str = resp.text.replace('\n', '').replace('\r', '').strip()
        print('share token failed: {}'.format(err_str))
        pool_token = err_str

    if re.match(r'^(fk-|pk-)', pool_token):

        with open(config_path, 'r') as file:
            config_data = json.load(file)

        config_data["open_ai_api_key"] = pool_token

        # 将更新后的内容写回config.json文件
        with open(config_path, 'w') as file:
            json.dump(config_data, file, indent=4, ensure_ascii=False)

        print(f"open_ai_api_key has been updated to: {pool_token}")

    return pool_token
