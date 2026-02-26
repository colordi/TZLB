"""
AI文本解析模块
使用OpenAI兼容API将自由文本解析为结构化的调查数据
"""
import json
import requests
from config import API_KEY, API_BASE_URL, MODEL_NAME

# 需要提取的字段定义
FIELDS_SCHEMA = {
    "survey_date": "调查日期（格式：YYYY-MM-DD）",
    "region": "区域（乡镇/城区）",
    "town_or_street": "乡镇或街道名称",
    "location_id": "点位编号",
    "location_name": "点位名称",
    "occurrence_position": "发生位置（具体地点描述）",
    "plot_type": "绿化性质（如公园、道路、庭院等）",
    "land_type": "地块类型（如平原造林、道路绿化等）",
    "pest_name": "害虫类别（如美国白蛾等）",
    "host_plant": "危害寄主（如杨树、柳树等）",
    "damaged_count": "受害株数（数字）",
    "web_count": "网幕数（数字）",
    "description": "详细情况描述",
    "note": "备注信息"
}


def build_prompt(text: str) -> str:
    """构建AI解析的提示词（通用）"""
    fields_desc = "\n".join([f"- {k}: {v}" for k, v in FIELDS_SCHEMA.items()])
    
    prompt = f"""你是一个专业的林业调查数据提取助手。请从以下文本中提取林业调查记录信息。

需要提取的字段：
{fields_desc}

规则：
1. 如果文本包含多条记录，请分别提取每条记录
2. 无法识别的字段请留空字符串
3. 日期请统一格式化为 YYYY-MM-DD
4. 数字字段请提取纯数字
5. 返回JSON数组格式

用户输入的文本：
---
{text}
---

请直接返回JSON数组，不要包含其他解释文字。格式示例：
[{{"survey_date": "2025-01-18", "region": "乡镇", "town_or_street": "某镇", ...}}]
"""
    return prompt


def build_chihuo_prompt(text: str, today_date: str, pest_name: str) -> str:
    """构建尺蠖类专用的提示词

    尺蠖调查提取规则：
    - 必须提取：点位编号、虫口数量
    - 智能提取：日期、地理位置、其他数据库字段
    - 虫口数量计算：平均数 × 5（因为调查5棵树）
    """
    prompt = f"""你是一个专业的林业调查数据提取助手，专门处理{pest_name}调查记录。

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
    return prompt


def parse_text_with_ai(text: str, pest_type: str = "") -> list[dict]:
    """
    使用OpenAI兼容API解析文本
    
    Args:
        text: 用户输入的自由文本
        pest_type: 害虫类型（如"春尺蠖"时使用专用解析逻辑）
        
    Returns:
        解析后的记录列表
    """
    from datetime import date
    
    if not API_KEY or API_KEY == "your-api-key-here":
        raise ValueError("请先在 config.py 中配置有效的 API_KEY")
    
    # 获取当天日期
    today_date = date.today().strftime("%Y-%m-%d")
    
    # 根据害虫类型选择提示词
    if pest_type in {"春尺蠖", "国槐尺蠖"}:
        prompt_content = build_chihuo_prompt(text, today_date, pest_type)
    elif pest_type == "其他害虫":
        # 其他害虫使用通用提取并在原通用prompt上稍作增补说明，以更好提取新增字段
        base_prompt = build_prompt(text)
        prompt_content = base_prompt.replace("规则：", f"规则：\n0. 此为【{pest_type}】调查记录提取，请特别注意提取'绿化性质'（plot_type）、'地块类型'（land_type）、'害虫类别'（pest_name）和'危害寄主'（host_plant）。并且忽略总虫口数与受害程度的提取。")
    else:
        prompt_content = build_prompt(text)
    
    # 构建OpenAI兼容的API端点
    base_url = API_BASE_URL.rstrip("/")
    url = f"{base_url}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
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
        "stream": False  # 禁用流式响应
    }
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        
        response_text = response.text.strip()
        
        # 处理SSE流式响应格式（以 data: 开头）
        if response_text.startswith("data:"):
            # 解析流式响应，合并所有data块的内容
            content_parts = []
            for line in response_text.split("\n"):
                line = line.strip()
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str and data_str != "[DONE]":
                        try:
                            data_obj = json.loads(data_str)
                            # 提取delta或message中的content
                            if "choices" in data_obj and len(data_obj["choices"]) > 0:
                                choice = data_obj["choices"][0]
                                if "delta" in choice and "content" in choice["delta"]:
                                    content_parts.append(choice["delta"]["content"])
                                elif "message" in choice and "content" in choice["message"]:
                                    content_parts.append(choice["message"]["content"])
                        except json.JSONDecodeError:
                            continue
            generated_text = "".join(content_parts)
        else:
            # 标准JSON响应
            result = response.json()
            generated_text = result["choices"][0]["message"]["content"]
        
        # 清理可能的markdown代码块标记
        generated_text = generated_text.strip()
        if generated_text.startswith("```json"):
            generated_text = generated_text[7:]
        if generated_text.startswith("```"):
            generated_text = generated_text[3:]
        if generated_text.endswith("```"):
            generated_text = generated_text[:-3]
        generated_text = generated_text.strip()
        
        # 解析JSON
        records = json.loads(generated_text)
        
        # 确保返回的是列表
        if isinstance(records, dict):
            records = [records]
            
        return records
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API请求失败: {str(e)}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"AI返回的数据格式错误: {str(e)}")
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"解析AI响应失败: {str(e)}")


# 保持向后兼容的别名
parse_text_with_gemini = parse_text_with_ai


if __name__ == "__main__":
    # 测试代码
    test_text = """
    2025年1月15日，在某镇的道路绿化带发现美国白蛾网幕3个，
    受害杨树5株，点位编号L001，已进行剪除处理。
    """
    try:
        result = parse_text_with_ai(test_text)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"错误: {e}")
