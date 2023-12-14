# access LinkAI knowledge base platform
# docs: https://link-ai.tech/platform/link-app/wechat

import time

import requests

from bot.bot import Bot
from bot.chatgpt.chat_gpt_session import ChatGPTSession
from bot.openai.open_ai_image import OpenAIImage
from bot.session_manager import SessionManager
from bridge.context import Context, ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from config import conf


class LinkAIBot(Bot, OpenAIImage):
    # authentication failed
    AUTH_FAILED_CODE = 401
    NO_QUOTA_CODE = 406

    def __init__(self):
        super().__init__()
        self.sessions = SessionManager(ChatGPTSession, model=conf().get("model") or "gpt-3.5-turbo")

    def reply(self, query, context: Context = None) -> Reply:
        if context.type == ContextType.TEXT:
            return self._chat(query, context)
        elif context.type == ContextType.IMAGE_CREATE:
            ok, res = self.create_img(query, 0)
            if ok:
                reply = Reply(ReplyType.IMAGE_URL, res)
            else:
                reply = Reply(ReplyType.ERROR, res)
            return reply
        else:
            reply = Reply(ReplyType.ERROR, "Bot不支持处理{}类型的消息".format(context.type))
            return reply

    def _chat(self, query, context, retry_count=0) -> Reply:
        """
        发起对话请求
        :param query: 请求提示词
        :param context: 对话上下文
        :param retry_count: 当前递归重试次数
        :return: 回复
        """
        if retry_count >= 2:
            # exit from retry 2 times
            logger.warn("[LINKAI] failed after maximum number of retry times")
            return Reply(ReplyType.ERROR, "请再问我一次吧")

        try:
            # load config
            if context.get("generate_breaked_by"):
                logger.info(f"[LINKAI] won't set appcode because a plugin ({context['generate_breaked_by']}) affected the context")
                app_code = None
            else:
                app_code = context.kwargs.get("app_code") or conf().get("linkai_app_code")
            linkai_api_key = conf().get("linkai_api_key")

            session_id = context["session_id"]

            session = self.sessions.session_query(query, session_id)
            model = conf().get("model") or "gpt-3.5-turbo"
            # remove system message
            if session.messages[0].get("role") == "system":
                if app_code or model == "wenxin":
                    session.messages.pop(0)

            body = {
                "app_code": app_code,
                "messages": session.messages,
                "model": model,     # 对话模型的名称, 支持 gpt-3.5-turbo, gpt-3.5-turbo-16k, gpt-4, wenxin
                "temperature": conf().get("temperature"),
                "top_p": conf().get("top_p", 1),
                "frequency_penalty": conf().get("frequency_penalty", 0.0),  # [-2,2]之间，该值越大则更倾向于产生不同的内容
                "presence_penalty": conf().get("presence_penalty", 0.0),  # [-2,2]之间，该值越大则更倾向于产生不同的内容
            }
            logger.info(f"[LINKAI] query={query}, app_code={app_code}, mode={body.get('model')}")
            headers = {"Authorization": "Bearer " + linkai_api_key}

            # do http request
            base_url = conf().get("linkai_api_base", "https://api.link-ai.chat")
            res = requests.post(url=base_url + "/v1/chat/completions", json=body, headers=headers,
                                timeout=conf().get("request_timeout", 180))
            if res.status_code == 200:
                # execute success
                response = res.json()
                reply_content = response["choices"][0]["message"]["content"]
                total_tokens = response["usage"]["total_tokens"]
                logger.info(f"[LINKAI] reply={reply_content}, total_tokens={total_tokens}")
                self.sessions.session_reply(reply_content, session_id, total_tokens)
                return Reply(ReplyType.TEXT, reply_content)

            else:
                response = res.json()
                error = response.get("error")
                logger.error(f"[LINKAI] chat failed, status_code={res.status_code}, "
                             f"msg={error.get('message')}, type={error.get('type')}")

                if res.status_code >= 500:
                    # server error, need retry
                    time.sleep(2)
                    logger.warn(f"[LINKAI] do retry, times={retry_count}")
                    return self._chat(query, context, retry_count + 1)

                return Reply(ReplyType.ERROR, "提问太快啦，请休息一下再问我吧")

        except Exception as e:
            logger.exception(e)
            # retry
            time.sleep(2)
            logger.warn(f"[LINKAI] do retry, times={retry_count}")
            return self._chat(query, context, retry_count + 1)
