# AI服务配置文件
# 优先从环境变量读取，未设置时使用下方默认值

import os

# OpenAI兼容API配置
# 支持OpenAI官方、Azure OpenAI、以及各类兼容API代理
API_KEY = os.environ.get("AI_API_KEY", "sk-ant-oat01-tRDH3pbbhdKXgxd5HtqFCbeusSqGOPp6GAk9d2OnUfwEiCFN13j7t5ppHad927_xVZ5ezQMwHVLGkKmVUMhu_DNsOCfF7AA")
API_BASE_URL = os.environ.get("AI_API_BASE_URL", "https://code.newcli.com/codex/v1")
MODEL_NAME = os.environ.get("AI_MODEL_NAME", "gpt-5.1-codex-mini")

# 示例配置：
# OpenAI官方：
#   API_BASE_URL = "https://api.openai.com/v1"
#   MODEL_NAME = "gpt-4o-mini"
#
# 其他兼容代理：
#   API_BASE_URL = "https://your-proxy.com/v1"
#   MODEL_NAME = "gpt-4o" 或代理支持的模型名
