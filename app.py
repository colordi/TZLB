from flask import Flask, render_template, request, jsonify, send_from_directory
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from pathlib import Path
import re
import uuid
import base64
import tempfile
import os

app = Flask(__name__)

# 基础配置
BASE_DIR = Path(__file__).parent
TEMPLATE_PATH = BASE_DIR / "工作单模板.docx"
IMAGES_DIR = BASE_DIR / "images"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp_images"
MAX_IMAGES = 4
IMAGE_WIDTH_MM = 70

# 确保目录存在
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

def extract_number_from_name(path: Path) -> int:
    m = re.search(r"-(\d+)", path.stem)
    return int(m.group(1)) if m else 0

def find_image_paths(location_id) -> list[Path]:
    if not IMAGES_DIR.exists():
        return []
    prefix = str(location_id)
    candidates = [p for p in IMAGES_DIR.iterdir() if p.is_file() and p.name.startswith(prefix)]
    return sorted(candidates, key=extract_number_from_name)

def save_base64_images(base64_list: list[str], row_id: str) -> list[Path]:
    """将 Base64 图片数据保存为临时文件并返回路径列表"""
    paths = []
    for i, b64_data in enumerate(base64_list[:MAX_IMAGES]):
        try:
            # 提取 Base64 数据部分（去除 data:image/xxx;base64, 前缀）
            if "," in b64_data:
                b64_data = b64_data.split(",", 1)[1]
            
            img_bytes = base64.b64decode(b64_data)
            # 生成唯一文件名
            filename = f"{row_id}_{i}_{uuid.uuid4().hex[:8]}.jpg"
            filepath = TEMP_DIR / filename
            filepath.write_bytes(img_bytes)
            paths.append(filepath)
        except Exception as e:
            print(f"[警告] 保存图片时出错: {e}")
    return paths

def map_images_to_context(doc: DocxTemplate, image_paths: list[Path], region: str | None) -> dict:
    """将图片路径映射到模板上下文中的img1-img4占位符"""
    placeholders = ["img1", "img2", "img3", "img4"]
    ctx = {name: "" for name in placeholders}
    
    inline_images = [InlineImage(doc, str(p), width=Mm(IMAGE_WIDTH_MM)) for p in image_paths[:MAX_IMAGES]]
    for i, img in enumerate(inline_images):
        if i >= len(placeholders):
            break
        ctx[placeholders[i]] = img
    return ctx

def cleanup_temp_images(paths: list[Path]):
    """清理临时图片文件"""
    for p in paths:
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/parse-text", methods=["POST"])
def parse_text():
    """使用AI解析自由文本为结构化数据"""
    try:
        from ai_parser import parse_text_with_ai
        
        data = request.json
        text = data.get("text", "").strip()
        pest_type = data.get("pest_type", "")  # 获取害虫类型
        
        if not text:
            return jsonify({"success": False, "error": "请输入需要解析的文本"}), 400
        
        records = parse_text_with_ai(text, pest_type)
        return jsonify({"success": True, "records": records})
        
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    except Exception as e:
        return jsonify({"success": False, "error": f"解析失败: {str(e)}"}), 500

@app.route("/api/generate", methods=["POST"])
def generate():
    all_temp_files = []  # 用于记录所有临时文件以便清理
    
    # 前端字段名 -> Word模板变量名的映射
    FIELD_MAPPING = {
        "pest_type": "pest",           # 害虫类型 -> 危害虫种
        "task_type": "task",           # 统防任务
        "host_plant": "host",          # 危害寄主
        "damaged_count": "affected_plants_count",  # 受害株数
        "land_type": "plot_type",      # 地块类型 -> 绿地性质
        "web_count": "screen_count",   # 网幕数 -> 网幕个数
        "description": "detailed_description",  # 描述 -> 详细描述
        "note": "note",                # 备注
    }
    
    try:
        data = request.json
        records = data.get("records", [])
        pest_type = data.get("pest_type", "其它")
        task_type = data.get("task_type", "")
        
        generated_files = []
        for idx, row in enumerate(records):
            doc = DocxTemplate(TEMPLATE_PATH)
            # 合并数据（排除 images 字段）
            context = {k: v for k, v in row.items() if k != "images"}
            context["pest_type"] = pest_type
            context["task_type"] = task_type
            
            # 自动生成序号（001, 002, 003...）
            context["serial_number"] = str(idx + 1).zfill(3)
            
            # 应用字段映射：将前端字段名转换为Word模板变量名
            for frontend_key, template_key in FIELD_MAPPING.items():
                if frontend_key in context:
                    context[template_key] = context[frontend_key]
            
            # 优先使用用户上传的图片
            uploaded_images = row.get("images", [])
            print(f"[DEBUG] Row {idx}: received {len(uploaded_images)} images")
            if uploaded_images:
                row_id = f"row_{idx}_{uuid.uuid4().hex[:8]}"
                image_paths = save_base64_images(uploaded_images, row_id)
                print(f"[DEBUG] Row {idx}: saved {len(image_paths)} images to temp")
                all_temp_files.extend(image_paths)
            else:
                # 回退到基于 location_id 查找图片的旧逻辑
                location_id = context.get("location_id")
                image_paths = find_image_paths(location_id)
            
            print(f"[DEBUG] Row {idx}: image_paths = {image_paths}")
            context.update(map_images_to_context(doc, image_paths, context.get("region")))
            print(f"[DEBUG] Row {idx}: context img keys = {[k for k in context if k.startswith('img')]}")
            
            doc.render(context)
            
            # 生成文件名
            town = context.get("town_or_street", "未知")
            loc = context.get("location_name", "未命名")
            date = context.get("survey_date", "无日期")
            sn = context.get("location_id") or context.get("serial_number") or str(uuid.uuid4())[:8]
            
            filename = f"2025林业有害生物防治工作单（{town}）-{loc}-{date}-{sn}.docx"
            output_path = OUTPUT_DIR / filename
            doc.save(output_path)
            generated_files.append(filename)
        
        # 清理临时文件
        cleanup_temp_images(all_temp_files)
            
        return jsonify({"success": True, "files": generated_files})
    except Exception as e:
        # 出错时也清理临时文件
        cleanup_temp_images(all_temp_files)
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)
