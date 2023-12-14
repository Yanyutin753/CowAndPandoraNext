# encoding:utf-8

import random
import string
from typing import Tuple

import plugins
from bridge.bridge import Bridge
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common import const
from config import load_config, global_config
from plugins import *
from auto_share_token import Share_token_config
from custom_instructions import get_messages, modify_messages_user, modify_messages_model

# 定义指令集
COMMANDS = {
    "help": {
        "alias": ["help", "帮助"],
        "desc": "回复此帮助",
    },
    "helpp": {
        "alias": ["help", "帮助"],  # 与help指令共用别名，根据参数数量区分
        "args": ["插件名"],
        "desc": "回复指定插件的详细帮助",
    },
    "auth": {
        "alias": ["auth", "认证"],
        "args": ["口令"],
        "desc": "管理员认证",
    },
    "model": {
        "alias": ["model", "模型"],
        "desc": "查看和设置全局模型",
    },
    "set_openai_api_key": {
        "alias": ["set_openai_api_key"],
        "args": ["api_key"],
        "desc": "设置你的OpenAI私有api_key",
    },
    "reset_openai_api_key": {
        "alias": ["reset_openai_api_key"],
        "desc": "重置为默认的api_key",
    },
    "set_gpt_model": {
        "alias": ["set_gpt_model"],
        "desc": "设置你的私有模型",
    },
    "reset_gpt_model": {
        "alias": ["reset_gpt_model"],
        "desc": "重置你的私有模型",
    },
    "gpt_model": {
        "alias": ["gpt_model"],
        "desc": "查询你使用的模型",
    },
    "id": {
        "alias": ["id", "用户"],
        "desc": "获取用户id",  # wechaty和wechatmp的用户id不会变化，可用于绑定管理员
    },
    "reset": {
        "alias": ["reset", "重置会话"],
        "desc": "重置会话",
    },
}

ADMIN_COMMANDS = {
    "resume": {
        "alias": ["resume", "恢复服务"],
        "desc": "恢复服务",
    },
    "update_token": {
        "alias": ["update_token", "更新chatgpt"],
        "desc": "更新chatgpt",
    },
    "show_ci": {
        "alias": ["show_ci", "查看自定义背景和提示词"],
        "desc": "查看自定义背景和提示词",
    },
    "update_ci_user": {
        "alias": ["update_ci_user", "更新自定义提示词"],
        "desc": "更新自定义提示词",
    },
    "update_ci_model": {
        "alias": ["update_ci_model", "更新自定义提示词"],
        "desc": "更新自定义提示词",
    },
    "stop": {
        "alias": ["stop", "暂停服务"],
        "desc": "暂停服务",
    },
    "reconf": {
        "alias": ["reconf", "重载配置"],
        "desc": "重载配置(不包含插件配置)",
    },
    "resetall": {
        "alias": ["resetall", "重置所有会话"],
        "desc": "重置所有会话",
    },
    "scanp": {
        "alias": ["scanp", "扫描插件"],
        "desc": "扫描插件目录是否有新插件",
    },
    "plist": {
        "alias": ["plist", "插件"],
        "desc": "打印当前插件列表",
    },
    "setpri": {
        "alias": ["setpri", "设置插件优先级"],
        "args": ["插件名", "优先级"],
        "desc": "设置指定插件的优先级，越大越优先",
    },
    "reloadp": {
        "alias": ["reloadp", "重载插件"],
        "args": ["插件名"],
        "desc": "重载指定插件配置",
    },
    "enablep": {
        "alias": ["enablep", "启用插件"],
        "args": ["插件名"],
        "desc": "启用指定插件",
    },
    "disablep": {
        "alias": ["disablep", "禁用插件"],
        "args": ["插件名"],
        "desc": "禁用指定插件",
    },
    "installp": {
        "alias": ["installp", "安装插件"],
        "args": ["仓库地址或插件名"],
        "desc": "安装指定插件",
    },
    "uninstallp": {
        "alias": ["uninstallp", "卸载插件"],
        "args": ["插件名"],
        "desc": "卸载指定插件",
    },
    "updatep": {
        "alias": ["updatep", "更新插件"],
        "args": ["插件名"],
        "desc": "更新指定插件",
    },
    "debug": {
        "alias": ["debug", "调试模式", "DEBUG"],
        "desc": "开启机器调试日志",
    },
}


# 定义帮助函数
def get_help_text(isadmin, isgroup):
    help_text = "通用指令：\n"
    for cmd, info in COMMANDS.items():
        if cmd == "auth":  # 不提示认证指令
            continue
        if cmd == "id" and conf().get("channel_type", "wx") not in ["wxy", "wechatmp"]:
            continue
        alias = ["#" + a for a in info["alias"][:1]]
        help_text += f"{','.join(alias)} "
        if "args" in info:
            args = [a for a in info["args"]]
            help_text += f"{' '.join(args)}"
        help_text += f": {info['desc']}\n"

    # 插件指令
    plugins = PluginManager().list_plugins()
    help_text += "\n目前可用插件有："
    for plugin in plugins:
        if plugins[plugin].enabled and not plugins[plugin].hidden:
            namecn = plugins[plugin].namecn
            help_text += "\n%s:" % namecn
            help_text += PluginManager().instances[plugin].get_help_text(verbose=False).strip()

    if ADMIN_COMMANDS and isadmin:
        help_text += "\n\n管理员指令：\n"
        for cmd, info in ADMIN_COMMANDS.items():
            alias = ["#" + a for a in info["alias"][:1]]
            help_text += f"{','.join(alias)} "
            if "args" in info:
                args = [a for a in info["args"]]
                help_text += f"{' '.join(args)}"
            help_text += f": {info['desc']}\n"
    return help_text


@plugins.register(
    name="Godcmd",
    desire_priority=999,
    hidden=True,
    desc="为你的机器人添加指令集，有用户和管理员两种角色，加载顺序请放在首位，初次运行后插件目录会生成配置文件, 填充管理员密码后即可认证",
    version="1.0",
    author="lanvent",
)
class Godcmd(Plugin):
    def __init__(self):
        super().__init__()

        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        gconf = super().load_config()
        if not gconf:
            if not os.path.exists(config_path):
                gconf = {"password": "", "admin_users": []}
                with open(config_path, "w") as f:
                    json.dump(gconf, f, indent=4)
        if gconf["password"] == "":
            self.temp_password = "".join(random.sample(string.digits, 4))
            logger.info("[Godcmd] 因未设置口令，本次的临时口令为%s。" % self.temp_password)
        else:
            self.temp_password = None
        custom_commands = conf().get("clear_memory_commands", [])
        for custom_command in custom_commands:
            if custom_command and custom_command.startswith("#"):
                custom_command = custom_command[1:]
                if custom_command and custom_command not in COMMANDS["reset"]["alias"]:
                    COMMANDS["reset"]["alias"].append(custom_command)

        self.password = gconf["password"]
        self.admin_users = gconf["admin_users"]  # 预存的管理员账号，这些账号不需要认证。itchat的用户名每次都会变，不可用
        self.isrunning = True  # 机器人是否运行中

        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        logger.info("[Godcmd] inited")

    def on_handle_context(self, e_context: EventContext):
        context_type = e_context["context"].type
        if context_type != ContextType.TEXT:
            if not self.isrunning:
                e_context.action = EventAction.BREAK_PASS
            return

        content = e_context["context"].content
        logger.debug("[Godcmd] on_handle_context. content: %s" % content)
        if content.startswith("#"):
            if len(content) == 1:
                reply = Reply()
                reply.type = ReplyType.ERROR
                reply.content = f"空指令，输入#help查看指令列表\n"
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            # msg = e_context['context']['msg']
            channel = e_context["channel"]
            user = e_context["context"]["receiver"]
            session_id = e_context["context"]["session_id"]
            isgroup = e_context["context"].get("isgroup", False)
            bottype = Bridge().get_bot_type("chat")
            bot = Bridge().get_bot("chat")
            # 将命令和参数分割
            content = content[1:].strip()  # 移除前缀
            command_parts = content.split(maxsplit=1)
            cmd = command_parts[0]
            # 检查是否有参数
            if len(command_parts) > 1:
                if cmd == 'update_ci_user' or cmd == 'update_ci_model':
                    args = [command_parts[1]]  # 使用剩余的内容作为参数
                else:
                    args = command_parts[1].split()  # 用空格分割参数
            else:
                args = []  # 没有参数
            isadmin = False
            if user in self.admin_users:
                isadmin = True
            ok = False
            result = "string"
            if any(cmd in info["alias"] for info in COMMANDS.values()):
                cmd = next(c for c, info in COMMANDS.items() if cmd in info["alias"])
                if cmd == "auth":
                    ok, result = self.authenticate(user, args, isadmin, isgroup)
                elif cmd == "help" or cmd == "helpp":
                    if len(args) == 0:
                        ok, result = True, get_help_text(isadmin, isgroup)
                    else:
                        # This can replace the helpp command
                        plugins = PluginManager().list_plugins()
                        query_name = args[0].upper()
                        # search name and namecn
                        for name, plugincls in plugins.items():
                            if not plugincls.enabled:
                                continue
                            if query_name == name or query_name == plugincls.namecn:
                                ok, result = True, PluginManager().instances[name].get_help_text(isgroup=isgroup, isadmin=isadmin, verbose=True)
                                break
                        if not ok:
                            result = "插件不存在或未启用"
                elif cmd == "model":
                    if not isadmin and not self.is_admin_in_group(e_context["context"]):
                        ok, result = False, "需要管理员权限执行"
                    elif len(args) == 0:
                        ok, result = True, "当前模型为: " + str(conf().get("model"))
                    elif len(args) == 1:
                        if args[0] not in const.MODEL_LIST:
                            ok, result = False, "模型名称不存在"
                        else:
                            conf()["model"] = args[0]
                            Bridge().reset_bot()
                            ok, result = True, "模型设置为: " + str(conf().get("model"))
                elif cmd == "id":
                    ok, result = True, user
                elif cmd == "set_openai_api_key":
                    if len(args) == 1:
                        user_data = conf().get_user_data(user)
                        user_data["openai_api_key"] = args[0]
                        ok, result = True, "你的OpenAI私有api_key已设置为" + args[0]
                    else:
                        ok, result = False, "请提供一个api_key"
                elif cmd == "reset_openai_api_key":
                    try:
                        user_data = conf().get_user_data(user)
                        user_data.pop("openai_api_key")
                        ok, result = True, "你的OpenAI私有api_key已清除"
                    except Exception as e:
                        ok, result = False, "你没有设置私有api_key"
                elif cmd == "set_gpt_model":
                    if len(args) == 1:
                        user_data = conf().get_user_data(user)
                        user_data["gpt_model"] = args[0]
                        ok, result = True, "你的GPT模型已设置为" + args[0]
                    else:
                        ok, result = False, "请提供一个GPT模型"
                elif cmd == "gpt_model":
                    user_data = conf().get_user_data(user)
                    model = conf().get("model")
                    if "gpt_model" in user_data:
                        model = user_data["gpt_model"]
                    ok, result = True, "你的GPT模型为" + str(model)
                elif cmd == "reset_gpt_model":
                    try:
                        user_data = conf().get_user_data(user)
                        user_data.pop("gpt_model")
                        ok, result = True, "你的GPT模型已重置"
                    except Exception as e:
                        ok, result = False, "你没有设置私有GPT模型"
                elif cmd == "reset":
                    if bottype in [const.OPEN_AI, const.CHATGPT, const.CHATGPTONAZURE, const.LINKAI, const.BAIDU, const.XUNFEI]:
                        bot.sessions.clear_session(session_id)
                        channel.cancel_session(session_id)
                        ok, result = True, "会话已重置"
                    else:
                        ok, result = False, "当前对话机器人不支持重置会话"
                logger.debug("[Godcmd] command: %s by %s" % (cmd, user))
            elif any(cmd in info["alias"] for info in ADMIN_COMMANDS.values()):
                if isadmin:
                    if isgroup:
                        ok, result = False, "群聊不可执行管理员指令"
                    else:
                        cmd = next(c for c, info in ADMIN_COMMANDS.items() if cmd in info["alias"])
                        if cmd == "stop":
                            self.isrunning = False
                            ok, result = True, "服务已暂停"
                        elif cmd == "resume":
                            self.isrunning = True
                            ok, result = True, "服务已恢复"
                        elif cmd == "update_token":
                            print("开始修改分享token")
                            share_token = Share_token_config()
                            ok, result = True, f"分享token已修改完成{share_token}"
                        elif cmd == "show_ci":
                            print("开始获取CI值")
                            about_user_message, about_model_message = get_messages()
                            ok, result = True, f"""自定义背景为：{about_user_message}----自定义提示词为：{about_model_message}"""
                        elif cmd == "update_ci_user":
                            print("开始更新自定义背景")
                            about_user_message = args[0]
                            modify_messages_user(about_user_message)
                            about_user_message, about_model_message = get_messages()
                            ok, result = True, f"""背景词为：{about_user_message}"""
                        elif cmd == "update_ci_model":
                            print("开始更新自定义背景")
                            about_model_message = args[0]
                            modify_messages_model(about_model_message)
                            about_user_message, about_model_message = get_messages()
                            ok, result = True, f"""自定义提示词为：{about_model_message}"""
                        elif cmd == "reconf":
                            load_config()
                            ok, result = True, "配置已重载"
                        elif cmd == "resetall":
                            if bottype in [const.OPEN_AI, const.CHATGPT, const.CHATGPTONAZURE, const.LINKAI,
                                           const.BAIDU, const.XUNFEI]:
                                channel.cancel_all_session()
                                bot.sessions.clear_all_session()
                                ok, result = True, "重置所有会话成功"
                            else:
                                ok, result = False, "当前对话机器人不支持重置会话"
                        elif cmd == "debug":
                            logger.setLevel("DEBUG")
                            ok, result = True, "DEBUG模式已开启"
                        elif cmd == "plist":
                            plugins = PluginManager().list_plugins()
                            ok = True
                            result = "插件列表：\n"
                            for name, plugincls in plugins.items():
                                result += f"{plugincls.name}_v{plugincls.version} {plugincls.priority} - "
                                if plugincls.enabled:
                                    result += "已启用\n"
                                else:
                                    result += "未启用\n"
                        elif cmd == "scanp":
                            new_plugins = PluginManager().scan_plugins()
                            ok, result = True, "插件扫描完成"
                            PluginManager().activate_plugins()
                            if len(new_plugins) > 0:
                                result += "\n发现新插件：\n"
                                result += "\n".join([f"{p.name}_v{p.version}" for p in new_plugins])
                            else:
                                result += ", 未发现新插件"
                        elif cmd == "setpri":
                            if len(args) != 2:
                                ok, result = False, "请提供插件名和优先级"
                            else:
                                ok = PluginManager().set_plugin_priority(args[0], int(args[1]))
                                if ok:
                                    result = "插件" + args[0] + "优先级已设置为" + args[1]
                                else:
                                    result = "插件不存在"
                        elif cmd == "reloadp":
                            if len(args) != 1:
                                ok, result = False, "请提供插件名"
                            else:
                                ok = PluginManager().reload_plugin(args[0])
                                if ok:
                                    result = "插件配置已重载"
                                else:
                                    result = "插件不存在"
                        elif cmd == "enablep":
                            if len(args) != 1:
                                ok, result = False, "请提供插件名"
                            else:
                                ok, result = PluginManager().enable_plugin(args[0])
                        elif cmd == "disablep":
                            if len(args) != 1:
                                ok, result = False, "请提供插件名"
                            else:
                                ok = PluginManager().disable_plugin(args[0])
                                if ok:
                                    result = "插件已禁用"
                                else:
                                    result = "插件不存在"
                        elif cmd == "installp":
                            if len(args) != 1:
                                ok, result = False, "请提供插件名或.git结尾的仓库地址"
                            else:
                                ok, result = PluginManager().install_plugin(args[0])
                        elif cmd == "uninstallp":
                            if len(args) != 1:
                                ok, result = False, "请提供插件名"
                            else:
                                ok, result = PluginManager().uninstall_plugin(args[0])
                        elif cmd == "updatep":
                            if len(args) != 1:
                                ok, result = False, "请提供插件名"
                            else:
                                ok, result = PluginManager().update_plugin(args[0])
                        logger.debug("[Godcmd] admin command: %s by %s" % (cmd, user))
                else:
                    ok, result = False, "需要管理员权限才能执行该指令"
            else:
                trigger_prefix = conf().get("plugin_trigger_prefix", "$")
                if trigger_prefix == "#":  # 跟插件聊天指令前缀相同，继续递交
                    return
                ok, result = False, f"未知指令：{cmd}\n查看指令列表请输入#help \n"

            reply = Reply()
            if ok:
                reply.type = ReplyType.INFO
            else:
                reply.type = ReplyType.ERROR
            reply.content = result
            e_context["reply"] = reply

            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
        elif not self.isrunning:
            e_context.action = EventAction.BREAK_PASS

    def authenticate(self, userid, args, isadmin, isgroup) -> Tuple[bool, str]:
        if isgroup:
            return False, "请勿在群聊中认证"

        if isadmin:
            return False, "管理员账号无需认证"

        if len(args) != 1:
            return False, "请提供口令"

        password = args[0]
        if password == self.password:
            self.admin_users.append(userid)
            global_config["admin_users"].append(userid)
            return True, "认证成功"
        elif password == self.temp_password:
            self.admin_users.append(userid)
            global_config["admin_users"].append(userid)
            return True, "认证成功，请尽快设置口令"
        else:
            return False, "认证失败"

    def get_help_text(self, isadmin=False, isgroup=False, **kwargs):
        return get_help_text(isadmin, isgroup)


    def is_admin_in_group(self, context):
        if context["isgroup"]:
            return context.kwargs.get("msg").actual_user_id in global_config["admin_users"]
        return False
