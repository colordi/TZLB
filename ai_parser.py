"""
AI文本解析模块
使用OpenAI兼容API将自由文本解析为结构化的调查数据
"""
import json
import re
from datetime import date

import requests

from config import API_KEY, API_BASE_URL, MODEL_NAME
from pest_db import PEST_DB_CONFIGS

# 尺蠖类害虫类型（与 app.py 中 CHI_HUO_PEST_TYPES 对应）
_CHI_HUO_TYPES = {"春尺蠖", "国槐尺蠖"}


# ── Prompt 构建 ──────────────────────────────────────────────

def _build_qitahaichong_prompt(text: str, today_date: str) -> str:
    """构建其他害虫专用的提示词（独立函数，替代脆弱的 str.replace 注入）。"""
    return f"""你是一个专业的林业调查数据提取助手，专门处理其他害虫调查记录。

## 输入格式说明
用户输入的文本是林业调查的现场记录，可能包含以下信息：
- 调查日期、地理位置（乡镇、街道、具体地点）
- 点位编号、点位名称
- 虫种（如美国白蛾、杨扇舟蛾、天牛等）
- 地块类型（如公园、道路、庭院等）
- 受害树种（如杨树、柳树、国槐等）
- 受害株数、网幕数等
- 详细情况描述

## 提取规则
1. **必须提取**：点位编号（location_id）、虫种（pest_name）
2. 日期格式化为 YYYY-MM-DD；如果没有日期信息，使用"{today_date}"
3. 无法识别的字段填空字符串
4. **不需要提取**：总虫口数（total_insect_count）和受害程度（damage_level）
5. 如果文本包含多条记录，分别提取

## 输出字段
返回JSON数组，每条记录包含：
- survey_date: 调查日期（YYYY-MM-DD）
- region: 区域（"乡镇"或"城区"或""）
- town_or_street: 乡镇/街道名称
- location_id: 点位编号
- location_name: 点位名称
- occurrence_position: 发生位置
- plot_type: 地块类型
- pest_name: 虫种
- host_plant: 受害树种
- description: 详细情况描述

## 用户输入
---
{text}
---

请直接返回JSON数组，不要包含任何解释文字。
"""


def _build_chihuo_prompt(text: str, today_date: str, pest_name: str) -> str:
    """构建尺蠖类专用的提示词。

    尺蠖调查提取规则：
    - 必须提取：点位编号、虫口数量
    - 智能提取：日期、地理位置、其他数据库字段
    - 虫口数量计算：平均数 × 5（因为调查5棵树）
    """
    return f"""你是一个专业的林业调查数据提取助手，专门处理{pest_name}调查记录。

## 输入格式说明
用户输入的文本通常是简短的点位+数量描述，例如：
- "yf0083平均30头最多50头，yf0109平均25头"
- "YF0001 平均每标准枝15头"
- "2025-01-20 某镇 yf0050平均20头最多35头"

文本可能包含：
- 点位编号（如yf0083、YF0109等，可能是小写）
- 虫口数量（平均X头、最多Y头）
- 调查日期（可选）
- 地理位置信息（乡镇、街道、具体地点等，可选）
- 其他描述信息（可选）

## 提取规则

### 1. 点位编号（location_id）- 必须提取
- 识别点位编号并统一转换为大写（如yf0083→YF0083）
- 点位编号通常是字母+数字组合

### 2. 虫口数量 - 必须提取
- 识别"平均X头"和"最多Y头"
- **total_insect_count = 平均数 × 5**（因为尺蠖调查固定调查5棵树）
- 如果只有平均数，就用平均数×5
- 如果只有最多数，就用最多数×5
- 如果两个都有，优先使用平均数×5

### 3. 描述（description）
- 生成标准格式："{today_date}调查：平均每标准枝上发现{pest_name}X头，最多Y头，需开展防治。"
- 如果只有平均数："{today_date}调查：平均每标准枝上发现{pest_name}X头，需开展防治。"
- 如果只有最多数："{today_date}调查：最多每标准枝上发现{pest_name}Y头，需开展防治。"

### 4. 调查日期（survey_date）
- 如果文本中有日期信息，提取并格式化为YYYY-MM-DD
- 如果没有，使用"{today_date}"

### 5. 地理位置信息 - 智能提取
- region: 如果提到"乡镇"或"城区"，提取对应值；否则默认为"乡镇"
- town_or_street: 识别乡镇名称，支持以下乡镇（包括简称）：
  * 宋庄镇（可能写作"宋庄"）
  * 西集镇（可能写作"西集"）
  * 潞城镇（可能写作"潞城"）
  * 漷县镇（可能写作"漷县"）
  * 张家湾镇（可能写作"张家湾"）
  * 于家务（可能写作"于家务乡"、"于家务镇"）
  * 永乐店镇（可能写作"永乐店"）
  * 马驹桥镇（可能写作"马驹桥"）
  * 台湖镇（可能写作"台湖"）
  如果识别到上述乡镇或相似表达，填充完整的乡镇名称（如识别到"宋庄"，填充"宋庄镇"）
- location_name: 提取点位名称（如果有）
- occurrence_position: 提取具体发生位置描述（如"道路绿化带"、"平原造林"等）

### 6. 其他字段 - 智能提取
- damage_level: 受害程度（如"轻度"、"中度"、"重度"等）
- report_time: 留空（由系统自动生成）

## 输出要求
返回JSON数组，每条记录包含以下字段（没有提取到的字段填空字符串""）：
- location_id: 点位编号（大写，必填）
- total_insect_count: 总虫口数（平均数×5，整数）
- description: 标准化描述
- survey_date: 调查日期（YYYY-MM-DD格式）
- region: 区域（"乡镇"或"城区"或""）
- town_or_street: 乡镇/街道名称
- location_name: 点位名称
- occurrence_position: 发生位置
- damage_level: 受害程度
- report_time: 空字符串

## 用户输入
---
{text}
---

## 输出示例
输入："yf0083平均30头最多50头，yf0109平均25头"
输出：[
  {{"location_id": "YF0083", "total_insect_count": 150, "description": "{today_date}调查：平均每标准枝上发现{pest_name}30头，最多50头，需开展防治。", "survey_date": "{today_date}", "region": "", "town_or_street": "", "location_name": "", "occurrence_position": "", "damage_level": "", "report_time": ""}},
  {{"location_id": "YF0109", "total_insect_count": 125, "description": "{today_date}调查：平均每标准枝上发现{pest_name}25头，需开展防治。", "survey_date": "{today_date}", "region": "", "town_or_street": "", "location_name": "", "occurrence_position": "", "damage_level": "", "report_time": ""}}
]

请直接返回JSON数组，不要包含任何解释文字。
"""


# ── 响应解析工具 ─────────────────────────────────────────────

def _strip_markdown_fences(text: str) -> str:
    """清理 AI 返回文本中可能包裹的 markdown 代码块标记。"""
    text = text.strip()
    # 去除开头的 ```json 或 ```
    text = re.sub(r"^```(?:json|JSON)?\s*\n?", "", text)
    # 去除结尾的 ```
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _extract_content(response: requests.Response) -> str:
    """从 API 响应中提取生成的文本内容。

    兼容两种格式：
    - 标准 JSON 响应
    - SSE 流式响应（某些 API 代理不遵守 stream=False，仍返回 data: 格式）
    """
    raw = response.text.strip()

    # SSE 流式格式：以 "data:" 开头
    if raw.startswith("data:"):
        content_parts = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if not data_str or data_str == "[DONE]":
                continue
            try:
                data_obj = json.loads(data_str)
                if "choices" in data_obj and data_obj["choices"]:
                    choice = data_obj["choices"][0]
                    if "delta" in choice and "content" in choice.get("delta", {}):
                        content_parts.append(choice["delta"]["content"])
                    elif "message" in choice and "content" in choice.get("message", {}):
                        content_parts.append(choice["message"]["content"])
            except json.JSONDecodeError:
                continue
        return "".join(content_parts)

    # 标准 JSON 响应
    result = response.json()
    return result["choices"][0]["message"]["content"]


# ── 主函数 ────────────────────────────────────────────────────

def parse_text_with_ai(text: str, pest_type: str = "") -> list[dict]:
    """使用OpenAI兼容API解析文本为结构化调查记录。

    Args:
        text: 用户输入的自由文本
        pest_type: 害虫类型（需为 PEST_DB_CONFIGS 中已注册的类型）

    Returns:
        解析后的记录列表
    """
    if not API_KEY or API_KEY == "your-api-key-here":
        raise ValueError("请先在 config.py 中配置有效的 API_KEY")

    today_date = date.today().strftime("%Y-%m-%d")

    # 根据害虫类型选择提示词
    if pest_type in _CHI_HUO_TYPES:
        prompt_content = _build_chihuo_prompt(text, today_date, pest_type)
    elif pest_type == "其他害虫":
        prompt_content = _build_qitahaichong_prompt(text, today_date)
    else:
        raise ValueError(f"不支持的害虫类型: {pest_type}")

    # 调用 API
    url = f"{API_BASE_URL.rstrip('/')}/chat/completions"

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "你是一个专业的数据提取助手，只返回JSON格式的结果，不要包含任何解释文字。"
            },
            {
                "role": "user",
                "content": prompt_content
            }
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
        "stream": False,
    }

    try:
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
            },
            json=payload,
            timeout=120,
        )
        response.raise_for_status()

        generated_text = _extract_content(response)
        generated_text = _strip_markdown_fences(generated_text)

        records = json.loads(generated_text)

        # 确保返回的是列表
        if isinstance(records, dict):
            records = [records]

        return records

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API请求失败: {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"AI返回的数据格式错误: {e}")
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"解析AI响应失败: {e}")


if __name__ == "__main__":
    test_text = """
    2025年1月15日，在某镇的道路绿化带发现美国白蛾网幕3个，
    受害杨树5株，点位编号L001，已进行剪除处理。
    """
    try:
        result = parse_text_with_ai(test_text, "其他害虫")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"错误: {e}")
