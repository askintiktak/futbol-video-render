import os
import uuid
import json
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

    # 1) Önce normal JSON olarak okumayı dene
    data = request.get_json(silent=True)

    # 2) n8n body'yi text/plain veya farklı content-type ile
    # gönderirse ham body'yi JSON olarak parse et
    if data is None:

        raw_body = request.get_data(as_text=True)

        if raw_body:
            try:
                data = json.loads(raw_body)
            except Exception:
                data = None

    # 3) JSON string içinde JSON geldiyse bir kez daha çöz
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            pass

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "JSON verisi bulunamadı",
            "content_type": request.content_type,
            "raw_body": request.get_data(as_text=True)[:500]
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
        field
        for field in required_fields
        if field not in data
    ]

    if missing:
        return jsonify({
            "success": False,
            "error": "Eksik alanlar var",
            "missing": missing
        }), 400

    job_id = str(uuid.uuid4())

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

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
