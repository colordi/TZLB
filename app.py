from flask import Flask, render_template, request, jsonify, Response, send_file
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from pathlib import Path
from datetime import datetime
from urllib.parse import quote
import re
import uuid
import base64
import csv
import io
import zipfile
from pest_db import (
    init_all_pest_dbs,
    insert_pest_record,
    insert_pest_records_batch,
    fetch_pest_records,
    PEST_DB_CONFIGS,
)

app = Flask(__name__)

# 基础配置
BASE_DIR = Path(__file__).parent
TEMPLATE_DIR = BASE_DIR / "templates"
IMAGES_DIR = BASE_DIR / "images"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp_images"
MAX_IMAGES = 4
IMAGE_WIDTH_MM = 70

# 害虫类型 → 模板路径映射
TEMPLATE_PATHS = {
    "春尺蠖": TEMPLATE_DIR / "春尺蠖工作单模板.docx",
    "国槐尺蠖": TEMPLATE_DIR / "国槐尺蠖工作单模板.docx",
    "其他害虫": TEMPLATE_DIR / "其他害虫工作单模板.docx",
}

# 确保目录存在
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# 初始化所有害虫数据库
init_all_pest_dbs()

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


def resolve_year(survey_date: str | None) -> str:
    """从调查日期中提取年份，失败则回退到当前年份。"""
    if survey_date:
        match = re.match(r"(\d{4})", str(survey_date))
        if match:
            return match.group(1)
    return str(datetime.now().year)

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/records")
def records_page():
    """数据库可视化页面（统一入口，包含所有害虫类别）。"""
    return render_template("records.html")


# 字段 key → 中文标签映射
_FIELD_LABELS = {
    "survey_date": "调查日期", "region": "区域",
    "town_or_street": "乡镇/街道", "location_id": "点位编号",
    "location_name": "点位名称", "occurrence_position": "发生位置",
    "total_insect_count": "总虫口数", "damage_level": "受害程度",
    "report_time": "上报时间", "description": "详细情况描述",
    "pest_name": "害虫类别", "plot_type": "绿化性质",
    "host_plant": "危害寄主",
}

def _build_pest_definitions() -> list[dict]:
    """从 PEST_DB_CONFIGS 自动构建前端展示定义，避免手工维护。"""
    definitions = []
    for pest_type, config in PEST_DB_CONFIGS.items():
        # 展示字段 = 业务字段 + report_time（去掉 report_time 已在业务字段外）
        display_keys = list(config.fields) + ["report_time"]
        fields = [{"key": k, "label": _FIELD_LABELS.get(k, k)} for k in display_keys]
        definitions.append({
            "pest_type": pest_type,
            "fields": fields,
        })
    return definitions

PEST_DEFINITIONS = _build_pest_definitions()

CHI_HUO_PEST_TYPES = {"春尺蠖", "国槐尺蠖"}
QITA_HAICHONG_PEST_TYPES = {"其他害虫"}
CHI_HUO_REMOVED_FIELDS = {"host_plant", "damaged_count", "web_count"}


def sanitize_chihuo_record(record: dict) -> dict:
    """移除尺蠖类不再使用的字段。"""
    return {key: value for key, value in record.items() if key not in CHI_HUO_REMOVED_FIELDS}


def sanitize_chihuo_records(records: list[dict]) -> list[dict]:
    """批量移除尺蠖类不再使用的字段。"""
    return [sanitize_chihuo_record(record) for record in records]


# 必填字段及其中文标签
REQUIRED_FIELDS = [
    ("town_or_street", "乡镇/街道"),
    ("location_id", "点位编号"),
    ("location_name", "点位名称"),
    ("survey_date", "调查日期"),
    ("description", "详细情况描述"),
]


def validate_required_fields(records: list[dict]) -> list[str]:
    """验证记录列表中的必填字段，返回错误消息列表（空列表表示通过）。"""
    errors = []
    for idx, record in enumerate(records):
        for field_key, field_label in REQUIRED_FIELDS:
            value = record.get(field_key, "")
            if not value or (isinstance(value, str) and not value.strip()):
                errors.append(f"第 {idx + 1} 条记录：{field_label} 不能为空")
    return errors


def fetch_all_records_grouped() -> list[dict]:
    """按虫种获取记录（字段不混用，前端按虫种分表展示）。"""
    groups = []
    for pest in PEST_DEFINITIONS:
        records = fetch_pest_records(pest["pest_type"])
        groups.append({
            "pest_type": pest["pest_type"],
            "fields": pest["fields"],
            "records": records,
            "total": len(records)
        })
    return groups


@app.route("/api/records", methods=["GET"])
def get_records():
    """获取数据库记录（按虫种分组返回）。"""
    try:
        groups = fetch_all_records_grouped()
        total = sum(group["total"] for group in groups)
        return jsonify({
            "success": True,
            "total": total,
            "pests": groups
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/records/export", methods=["GET"])
def export_records_csv():
    """导出数据库记录为 CSV（按虫种导出，字段不混用）。"""
    try:
        pest_type = request.args.get("pest_type", "").strip()
        matched = [p for p in PEST_DEFINITIONS if p["pest_type"] == pest_type]
        if not matched:
            if not pest_type and len(PEST_DEFINITIONS) == 1:
                matched = [PEST_DEFINITIONS[0]]
            else:
                return jsonify({"success": False, "error": "请指定有效的 pest_type 参数"}), 400
        pest = matched[0]
        records = pest["fetcher"]()
        fields = pest["fields"]
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([field["label"] for field in fields])
        for row in records:
            writer.writerow([row.get(field["key"], "") for field in fields])

        csv_content = "\ufeff" + output.getvalue()
        filename = f"林业调查数据库_{pest['pest_type']}_{datetime.now().strftime('%Y%m%d')}.csv"
        response = Response(csv_content, mimetype="text/csv; charset=utf-8-sig")
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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

        if pest_type not in PEST_DB_CONFIGS:
            return jsonify({"success": False, "error": f"不支持的害虫类型: {pest_type}"}), 400
        
        records = parse_text_with_ai(text, pest_type)
        return jsonify({"success": True, "records": records})
        
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    except Exception as e:
        return jsonify({"success": False, "error": f"解析失败: {str(e)}"}), 500

@app.route("/api/save-to-db", methods=["POST"])
def save_to_db():
    """手动保存数据到数据库"""
    try:
        data = request.json
        records = data.get("records", [])
        pest_type = data.get("pest_type", "")

        if pest_type not in PEST_DB_CONFIGS:
            return jsonify({
                "success": False,
                "error": f"不支持的害虫类型: {pest_type}"
            }), 400

        if not records:
            return jsonify({
                "success": False,
                "error": "没有数据需要保存"
            }), 400

        if pest_type in CHI_HUO_PEST_TYPES:
            records = sanitize_chihuo_records(records)

        # 必填字段验证
        validation_errors = validate_required_fields(records)
        if validation_errors:
            return jsonify({
                "success": False,
                "error": "请填写以下必填字段：\n" + "\n".join(validation_errors)
            }), 400

        # 统一批量保存
        success_count, fail_count, errors = insert_pest_records_batch(
            pest_type, records, replace_on_conflict=True
        )

        return jsonify({
            "success": True,
            "saved": success_count,
            "failed": fail_count,
            "total": len(records),
            "errors": errors
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# 前端字段名 → Word模板变量名的映射
_DOC_FIELD_MAPPING = {
    "description": "detailed_description",
}


def _render_single_doc(
    template_path: Path,
    row: dict,
    idx: int,
    pest_type: str,
    task_type: str,
    all_temp_files: list[Path],
) -> str:
    """渲染单条记录为 Word 文档，返回生成的文件名。"""
    doc = DocxTemplate(template_path)

    # 构建模板上下文（排除 images 字段）
    context = {k: v for k, v in row.items() if k != "images"}
    context["pest_type"] = pest_type
    context["task_type"] = task_type
    context["year"] = resolve_year(context.get("survey_date"))
    context["serial_number"] = str(idx + 1).zfill(3)

    # 字段映射：前端字段名 → Word模板变量名
    for frontend_key, template_key in _DOC_FIELD_MAPPING.items():
        if frontend_key in context:
            context[template_key] = context[frontend_key]

    # 处理图片：优先用户上传，回退到 location_id 匹配
    uploaded_images = row.get("images", [])
    if uploaded_images:
        row_id = f"row_{idx}_{uuid.uuid4().hex[:8]}"
        image_paths = save_base64_images(uploaded_images, row_id)
        all_temp_files.extend(image_paths)
    else:
        image_paths = find_image_paths(context.get("location_id"))

    context.update(map_images_to_context(doc, image_paths, context.get("region")))
    doc.render(context)

    # 生成文件名并保存
    town = context.get("town_or_street") or "未知"
    loc = context.get("location_name") or "未命名"
    date = context.get("survey_date") or "无日期"
    sn = context.get("location_id") or context.get("serial_number") or str(uuid.uuid4())[:8]

    current_year = datetime.now().year
    filename = f"{current_year}林业有害生物防治工作单（{town}）-{loc}-{date}-{sn}.docx"
    doc.save(OUTPUT_DIR / filename)
    return filename


def _build_file_response(generated_files: list[str]) -> Response:
    """根据文件数量构建下载响应（单文件直下 / 多文件 ZIP 打包）。"""
    if len(generated_files) == 1:
        filename = generated_files[0]
        encoded = quote(filename)
        response = send_file(
            OUTPUT_DIR / filename,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded}"
        return response

    # 多文件打包 ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename in generated_files:
            zf.write(OUTPUT_DIR / filename, filename)
    zip_buffer.seek(0)

    current_year = datetime.now().year
    zip_filename = f"{current_year}林业工作单批量导出_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    encoded = quote(zip_filename)
    response = send_file(
        zip_buffer,
        as_attachment=True,
        download_name=zip_filename,
        mimetype="application/zip",
    )
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded}"
    return response


@app.route("/api/generate", methods=["POST"])
def generate():
    all_temp_files: list[Path] = []
    try:
        data = request.json
        records = data.get("records", [])
        pest_type = data.get("pest_type", "")
        task_type = data.get("task_type", "")

        if pest_type not in PEST_DB_CONFIGS:
            return jsonify({"success": False, "error": f"不支持的害虫类型: {pest_type}"}), 400

        if pest_type in CHI_HUO_PEST_TYPES:
            records = sanitize_chihuo_records(records)

        validation_errors = validate_required_fields(records)
        if validation_errors:
            return jsonify({
                "success": False,
                "error": "请填写以下必填字段：\n" + "\n".join(validation_errors)
            }), 400

        template_path = TEMPLATE_PATHS.get(pest_type)
        if not template_path:
            return jsonify({"success": False, "error": f"未找到 {pest_type} 的工作单模板"}), 400

        # 逐条渲染文档并保存到数据库
        generated_files = []
        for idx, row in enumerate(records):
            filename = _render_single_doc(
                template_path, row, idx, pest_type, task_type, all_temp_files
            )
            generated_files.append(filename)
            insert_pest_record(pest_type, row, replace_on_conflict=True)

        cleanup_temp_images(all_temp_files)
        return _build_file_response(generated_files)

    except Exception as e:
        cleanup_temp_images(all_temp_files)
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5001)
