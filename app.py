import os
import uuid
import json
import subprocess
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
TEXT_DIR = BASE_DIR / "texts"

OUTPUT_DIR.mkdir(exist_ok=True)
TEXT_DIR.mkdir(exist_ok=True)

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
AUDIO = BASE_DIR / "stadium.mp3"


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


def read_json_body():
    data = request.get_json(silent=True)

    if data is None:
        raw = request.get_data(as_text=True)

        if raw:
            try:
                data = json.loads(raw)
            except Exception:
                data = None

    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            pass

    return data


def write_text(job_id, name, value):
    folder = TEXT_DIR / job_id
    folder.mkdir(exist_ok=True)

    path = folder / f"{name}.txt"

    with open(path, "w", encoding="utf-8") as f:
        f.write(str(value or ""))

    return path


def drawtext(text_file, start, end, y, size, color="white"):
    return (
        f"drawtext="
        f"fontfile='{FONT}':"
        f"textfile='{text_file}':"
        f"expansion=none:"
        f"fontcolor={color}:"
        f"fontsize={size}:"
        f"x=(w-text_w)/2:"
        f"y={y}:"
        f"enable='between(t,{start},{end})'"
    )


@app.post("/render")
def render_video():

    data = read_json_body()

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "JSON verisi bulunamadı"
        }), 400

    job_id = str(uuid.uuid4())

    background_name = Path(
        data.get("background", "fenerbahce.png")
    ).name

    background = BASE_DIR / background_name

    # Henüz ilgili takım görseli yoksa
    # test için Fenerbahçe görselini kullan.
    if not background.exists():
        background = BASE_DIR / "fenerbahce.png"

    if not background.exists():
        return jsonify({
            "success": False,
            "error": "Arka plan görseli bulunamadı"
        }), 400

    if not AUDIO.exists():
        return jsonify({
            "success": False,
            "error": "stadium.mp3 bulunamadı"
        }), 400

    fields = [
        "ekran1_ana",
        "ekran1_alt",
        "ekran2_ana",
        "ekran2_vurgu",
        "ekran2_alt",
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

    text_files = {}

    for field in fields:
        text_files[field] = write_text(
            job_id,
            field,
            data.get(field, "")
        )

    output_name = f"{job_id}.mp4"
    output_path = OUTPUT_DIR / output_name

    filters = [
        "scale=1200:2134:force_original_aspect_ratio=increase",
        "crop=1200:2134",
        (
            "zoompan="
            "z='min(zoom+0.00015,1.08)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            "d=900:"
            "s=1080x1920:"
            "fps=30"
        ),

        # Koyu bilgi kartı
        (
            "drawbox="
            "x=70:y=650:w=940:h=440:"
            "color=black@0.65:"
            "t=fill"
        ),

        # EKRAN 1 — 0-3
        drawtext(text_files["ekran1_ana"], 0, 3, 735, 68),
        drawtext(text_files["ekran1_alt"], 0, 3, 850, 52, "yellow"),

        # EKRAN 2 — 3-8
        drawtext(text_files["ekran2_ana"], 3, 8, 720, 68),
        drawtext(text_files["ekran2_vurgu"], 3, 8, 825, 60, "yellow"),
        drawtext(text_files["ekran2_alt"], 3, 8, 925, 38),

        # EKRAN 3 — 8-13
        drawtext(text_files["ekran3_ana"], 8, 13, 750, 68),
        drawtext(text_files["ekran3_alt"], 8, 13, 865, 44, "yellow"),

        # EKRAN 4 — 13-19
        drawtext(text_files["ekran4_ana"], 13, 19, 750, 58),
        drawtext(text_files["ekran4_alt"], 13, 19, 865, 42, "yellow"),

        # EKRAN 5 — 19-25
        drawtext(text_files["ekran5_ana"], 19, 25, 750, 58),
        drawtext(text_files["ekran5_alt"], 19, 25, 865, 40, "yellow"),

        # EKRAN 6 — 25-30
        drawtext(text_files["ekran6_ana"], 25, 30, 715, 58),
        drawtext(text_files["ekran6_vurgu"], 25, 30, 820, 58, "yellow"),
        drawtext(text_files["ekran6_alt"], 25, 30, 930, 38),

        "format=yuv420p"
    ]

    video_filter = ",".join(filters)

    command = [
        "ffmpeg",
        "-y",

        "-loop", "1",
        "-i", str(background),

        "-stream_loop", "-1",
        "-i", str(AUDIO),

        "-filter_complex",
        (
            f"[0:v]{video_filter}[v];"
            "[1:a]"
            "volume=0.75,"
            "afade=t=in:st=0:d=0.5,"
            "afade=t=out:st=29:d=1"
            "[a]"
        ),

        "-map", "[v]",
        "-map", "[a]",

        "-t", "30",

        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",

        "-c:a", "aac",
        "-b:a", "160k",

        "-movflags", "+faststart",

        str(output_path)
    ]

    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=280
        )

    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "job_id": job_id,
            "error": "FFmpeg zaman aşımına uğradı"
        }), 504

    if process.returncode != 0:
        return jsonify({
            "success": False,
            "job_id": job_id,
            "error": "FFmpeg render başarısız",
            "ffmpeg": process.stderr[-5000:]
        }), 500

    if not output_path.exists():
        return jsonify({
            "success": False,
            "job_id": job_id,
            "error": "MP4 dosyası oluşturulamadı"
        }), 500

    base_url = request.host_url.rstrip("/")

    return jsonify({
        "success": True,
        "job_id": job_id,
        "takim": data.get("takim"),
        "background": background.name,
        "video_url": f"{base_url}/outputs/{output_name}",
        "message": "Video başarıyla oluşturuldu"
    })


@app.get("/outputs/<path:filename>")
def outputs(filename):
    return send_from_directory(
        OUTPUT_DIR,
        filename,
        mimetype="video/mp4",
        as_attachment=False
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
