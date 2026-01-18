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
    placeholders = ["img1", "img2", "img3", "img4"]
    ctx = {name: "" for name in placeholders}
    start_index = 1 if region == "乡镇" else 0
    
    inline_images = [InlineImage(doc, str(p), width=Mm(IMAGE_WIDTH_MM)) for p in image_paths[:MAX_IMAGES]]
    for i, img in enumerate(inline_images):
        slot = i + start_index
        if slot >= len(placeholders):
            break
        ctx[placeholders[slot]] = img
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

@app.route("/api/generate", methods=["POST"])
def generate():
    all_temp_files = []  # 用于记录所有临时文件以便清理
    try:
        data = request.json
        records = data.get("records", [])
        pest_type = data.get("pest_type", "其它")
        
        generated_files = []
        for idx, row in enumerate(records):
            doc = DocxTemplate(TEMPLATE_PATH)
            # 合并数据（排除 images 字段）
            context = {k: v for k, v in row.items() if k != "images"}
            context["pest_type"] = pest_type
            
            # 优先使用用户上传的图片
            uploaded_images = row.get("images", [])
            if uploaded_images:
                row_id = f"row_{idx}_{uuid.uuid4().hex[:8]}"
                image_paths = save_base64_images(uploaded_images, row_id)
                all_temp_files.extend(image_paths)
            else:
                # 回退到基于 location_id 查找图片的旧逻辑
                location_id = context.get("location_id")
                image_paths = find_image_paths(location_id)
            
            context.update(map_images_to_context(doc, image_paths, context.get("region")))
            
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
