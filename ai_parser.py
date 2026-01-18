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
    "land_type": "地块类型（如平原造林、道路绿化等）",
    "host_plant": "危害寄主（如杨树、柳树等）",
    "damaged_count": "受害株数（数字）",
    "web_count": "网幕数（数字）",
    "description": "详细情况描述",
    "note": "备注信息"
}


def build_prompt(text: str) -> str:
    """构建AI解析的提示词"""
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


def parse_text_with_ai(text: str) -> list[dict]:
    """
    使用OpenAI兼容API解析文本
    
    Args:
        text: 用户输入的自由文本
        
    Returns:
        解析后的记录列表
    """
    if not API_KEY or API_KEY == "your-api-key-here":
        raise ValueError("请先在 config.py 中配置有效的 API_KEY")
    
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
                "content": build_prompt(text)
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
