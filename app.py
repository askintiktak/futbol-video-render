import os
import uuid
import json
import subprocess
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


@app.get("/")
def home():
    return jsonify({
        "status": "ok",
        "service": "futbol-video-render",
        "message": "Render API çalışıyor"
    })


@app.get("/health")
def health():
    return jsonify({
        "status": "healthy"
    })


@app.post("/render")
def render_video():

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "success": False,
            "error": "JSON verisi bulunamadı"
        }), 400

    required_fields = [
        "takim",
        "background",
        "ekran1_ana",
        "ekran1_alt",
        "ekran2_ana",
        "ekran2_vurgu",
        "ekran3_ana",
        "ekran3_alt",
        "ekran4_ana",
        "ekran4_alt",
        "ekran5_ana",
        "ekran5_alt",
        "ekran6_ana",
        "ekran6_vurgu",
        "ekran6_alt"
    ]

    missing = [
        field for field in required_fields
        if field not in data
    ]

    if missing:
        return jsonify({
            "success": False,
            "error": "Eksik alanlar var",
            "missing": missing
        }), 400

    job_id = str(uuid.uuid4())

    # Şimdilik video üretmeden önce n8n -> Render
    # veri aktarımını doğruluyoruz.
    input_file = OUTPUT_DIR / f"{job_id}.json"

    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    return jsonify({
        "success": True,
        "job_id": job_id,
        "takim": data.get("takim"),
        "background": data.get("background"),
        "message": "Render verisi başarıyla alındı",
        "next_step": "FFmpeg render motoru"
    })


@app.get("/outputs/<path:filename>")
def outputs(filename):
    return send_from_directory(
        OUTPUT_DIR,
        filename,
        as_attachment=False
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
