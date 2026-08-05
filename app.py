"""
Yuki CardVault - ระบบจัดการการ์ดสะสมส่วนตัว + สแกนรูปเพื่อระบุการ์ด
------------------------------------------------------------------
- กรอกข้อมูลการ์ดเอง: ชื่อเต็ม (ไทย), เอฟเฟกต์/รายละเอียด, ราคาหลายแหล่ง, ขนาด, รูป
- สแกน/อัปโหลดรูปการ์ด -> จับคู่กับรูปที่ลงทะเบียนไว้ด้วย perceptual hash (ออฟไลน์ ไม่ต้องมี API key)
  แล้วคืน "ชื่อเต็ม + สรุปเอฟเฟกต์" ของการ์ดที่ตรงที่สุด
- REST API + หน้าเว็บ UI ในตัว
- เก็บข้อมูลลง SQLite (cards.db) รูปเก็บใน static/uploads/

รันด้วย:  python app.py   ->  http://127.0.0.1:5000
"""
from __future__ import annotations

import os
import json
import sqlite3
import uuid
from datetime import datetime

from functools import wraps
from flask import Flask, jsonify, request, render_template, g, session, redirect, url_for
from PIL import Image
import imagehash

app = Flask(__name__)
# คีย์เข้ารหัส session และรหัสผ่านหลังบ้าน (แนะนำให้ตั้งผ่าน env จริง)
app.secret_key = os.environ.get("SECRET_KEY", "yuki-cardvault-secret-change-me")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "yuki1234")


def require_admin(fn):
    """ป้องกัน endpoint ที่แก้ไขข้อมูล ต้อง login หลังบ้านก่อน"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return jsonify({"error": "ต้องเข้าสู่ระบบหลังบ้านก่อน (/login)"}), 401
        return fn(*args, **kwargs)
    return wrapper

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "cards.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
# ระยะแฮชรวม (phash+dhash = 128 บิต) ที่ยังถือว่าเป็นการ์ดใบเดียวกัน
MATCH_THRESHOLD = 28

STANDARD_W, STANDARD_H = 6.3, 8.8  # ขนาดการ์ดสะสมมาตรฐาน (ซม.)


# ---------- ฐานข้อมูล ----------

def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS cards (
            id          TEXT PRIMARY KEY,
            name_full   TEXT NOT NULL,
            name_short  TEXT,
            effect      TEXT,
            category    TEXT,
            rarity      TEXT,
            edition     TEXT,            -- ประเภท/รุ่นการ์ด (วินเทจ, โปรโม, ครบรอบ ฯลฯ)
            width_cm    REAL,
            height_cm   REAL,
            prices      TEXT,            -- JSON: [{"source": "...", "price": 0.0}]
            image_file  TEXT,
            phash       TEXT,            -- perceptual hash (hex)
            dhash       TEXT,            -- difference hash (hex)
            created_at  TEXT
        )
        """
    )
    # เผื่อฐานข้อมูลเก่าที่ยังไม่มีคอลัมน์ edition
    cols = [r[1] for r in db.execute("PRAGMA table_info(cards)")]
    if "edition" not in cols:
        db.execute("ALTER TABLE cards ADD COLUMN edition TEXT")
    db.commit()
    db.close()


# ---------- ยูทิลรูป/แฮช ----------

def compute_hashes(path: str) -> tuple[str, str]:
    with Image.open(path) as im:
        im = im.convert("RGB")
        ph = imagehash.phash(im)
        dh = imagehash.dhash(im)
    return str(ph), str(dh)


def hamming(a: str, b: str) -> int:
    """ระยะแฮมมิงระหว่าง hash hex สองตัว (ยิ่งน้อยยิ่งเหมือน)"""
    if not a or not b:
        return 999
    return imagehash.hex_to_hash(a) - imagehash.hex_to_hash(b)


# ---------- ตรรกะวิเคราะห์ ----------

def analyze(row: sqlite3.Row) -> dict:
    prices = json.loads(row["prices"] or "[]")
    vals = [p["price"] for p in prices if isinstance(p.get("price"), (int, float)) and p["price"] > 0]
    pmin = min(vals) if vals else None
    pmax = max(vals) if vals else None
    pavg = round(sum(vals) / len(vals), 2) if vals else None

    # ระดับมูลค่า (บาท) จากราคาเฉลี่ย
    def tier(thb):
        if thb is None:  return {"tier": "ยังไม่ระบุราคา", "level": 0, "color": "#9ca3af"}
        if thb >= 3000:  return {"tier": "หายากมาก / มูลค่าสูง", "level": 5, "color": "#dc2626"}
        if thb >= 1000:  return {"tier": "มูลค่าสูง", "level": 4, "color": "#ea580c"}
        if thb >= 300:   return {"tier": "ปานกลาง", "level": 3, "color": "#ca8a04"}
        if thb >= 50:    return {"tier": "ทั่วไป", "level": 2, "color": "#16a34a"}
        return {"tier": "ราคาถูก / พบง่าย", "level": 1, "color": "#0891b2"}

    w, h = row["width_cm"], row["height_cm"]
    if w and h:
        area = round(w * h, 1)
        std_area = STANDARD_W * STANDARD_H
        if area >= std_area * 1.15:   size_label = "ใหญ่กว่ามาตรฐาน"
        elif area <= std_area * 0.85: size_label = "เล็กกว่ามาตรฐาน"
        else:                          size_label = "ขนาดมาตรฐาน"
        size = {"width_cm": w, "height_cm": h, "area_cm2": area, "label": size_label}
    else:
        size = {"width_cm": None, "height_cm": None, "area_cm2": None, "label": "ยังไม่ระบุขนาด"}

    return {
        "id": row["id"],
        "name_full": row["name_full"],
        "name_short": row["name_short"],
        "effect": row["effect"],
        "category": row["category"],
        "rarity": row["rarity"],
        "edition": (row["edition"] if "edition" in row.keys() else None),
        "image_url": f"/static/uploads/{row['image_file']}" if row["image_file"] else None,
        "prices": prices,
        "price_summary": {"min": pmin, "max": pmax, "avg": pavg, "sources": len(vals)},
        "value": tier(pavg),
        "size": size,
        "created_at": row["created_at"],
    }


def _save_upload(file_storage) -> str:
    ext = os.path.splitext(file_storage.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise ValueError(f"ชนิดไฟล์ไม่รองรับ: {ext or '(ไม่มีนามสกุล)'}")
    fname = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, fname)
    file_storage.save(path)
    return fname


# ---------- REST API ----------

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "engine": "perceptual-hash (offline)"})


@app.route("/api/cards", methods=["GET"])
def list_cards():
    q = (request.args.get("q") or "").strip()
    db = get_db()
    if q:
        rows = db.execute(
            "SELECT * FROM cards WHERE name_full LIKE ? OR name_short LIKE ? OR effect LIKE ? ORDER BY created_at DESC",
            (f"%{q}%", f"%{q}%", f"%{q}%"),
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM cards ORDER BY created_at DESC").fetchall()
    return jsonify({"count": len(rows), "cards": [analyze(r) for r in rows]})


@app.route("/api/cards/<card_id>", methods=["GET"])
def get_card(card_id):
    row = get_db().execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone()
    if not row:
        return jsonify({"error": "ไม่พบการ์ด"}), 404
    return jsonify(analyze(row))


@app.route("/api/cards", methods=["POST"])
@require_admin
def create_card():
    """สร้างการ์ดใหม่ รองรับ multipart (มีไฟล์รูป) หรือ JSON
    ฟิลด์: name_full*, name_short, effect, category, rarity, width_cm, height_cm, prices(JSON), image(ไฟล์)
    """
    form = request.form if request.form else request.json or {}
    name_full = (form.get("name_full") or "").strip()
    if not name_full:
        return jsonify({"error": "ต้องระบุ name_full (ชื่อเต็ม)"}), 400

    image_file = phash = dhash = None
    if "image" in request.files and request.files["image"].filename:
        try:
            image_file = _save_upload(request.files["image"])
            phash, dhash = compute_hashes(os.path.join(UPLOAD_DIR, image_file))
        except Exception as e:
            return jsonify({"error": f"อัปโหลดรูปไม่สำเร็จ: {e}"}), 400

    prices = form.get("prices") or "[]"
    if not isinstance(prices, str):
        prices = json.dumps(prices, ensure_ascii=False)

    def num(key):
        v = form.get(key)
        try:    return float(v) if v not in (None, "") else None
        except: return None

    cid = uuid.uuid4().hex[:12]
    get_db().execute(
        """INSERT INTO cards (id,name_full,name_short,effect,category,rarity,edition,width_cm,height_cm,prices,image_file,phash,dhash,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (cid, name_full, form.get("name_short"), form.get("effect"), form.get("category"),
         form.get("rarity"), form.get("edition"), num("width_cm"), num("height_cm"), prices, image_file, phash, dhash,
         datetime.now().isoformat(timespec="seconds")),
    )
    get_db().commit()
    row = get_db().execute("SELECT * FROM cards WHERE id=?", (cid,)).fetchone()
    return jsonify(analyze(row)), 201


@app.route("/api/cards/<card_id>", methods=["PUT", "PATCH"])
@require_admin
def update_card(card_id):
    db = get_db()
    row = db.execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone()
    if not row:
        return jsonify({"error": "ไม่พบการ์ด"}), 404
    form = request.form if request.form else request.json or {}

    fields, params = [], []
    for key in ("name_full", "name_short", "effect", "category", "rarity", "edition"):
        if key in form:
            fields.append(f"{key}=?"); params.append(form.get(key))
    for key in ("width_cm", "height_cm"):
        if key in form:
            try:    v = float(form.get(key)) if form.get(key) not in (None, "") else None
            except: v = None
            fields.append(f"{key}=?"); params.append(v)
    if "prices" in form:
        prices = form.get("prices")
        if not isinstance(prices, str):
            prices = json.dumps(prices, ensure_ascii=False)
        fields.append("prices=?"); params.append(prices)

    if "image" in request.files and request.files["image"].filename:
        try:
            image_file = _save_upload(request.files["image"])
            ph, dh = compute_hashes(os.path.join(UPLOAD_DIR, image_file))
            fields += ["image_file=?", "phash=?", "dhash=?"]; params += [image_file, ph, dh]
        except Exception as e:
            return jsonify({"error": f"อัปโหลดรูปไม่สำเร็จ: {e}"}), 400

    if fields:
        params.append(card_id)
        db.execute(f"UPDATE cards SET {','.join(fields)} WHERE id=?", params)
        db.commit()
    row = db.execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone()
    return jsonify(analyze(row))


@app.route("/api/cards/<card_id>", methods=["DELETE"])
@require_admin
def delete_card(card_id):
    db = get_db()
    row = db.execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone()
    if not row:
        return jsonify({"error": "ไม่พบการ์ด"}), 404
    if row["image_file"]:
        try: os.remove(os.path.join(UPLOAD_DIR, row["image_file"]))
        except OSError: pass
    db.execute("DELETE FROM cards WHERE id=?", (card_id,))
    db.commit()
    return jsonify({"deleted": card_id})


@app.route("/api/identify", methods=["POST"])
def identify():
    """อัปโหลดรูป -> จับคู่กับการ์ดที่ลงทะเบียนไว้ -> คืนชื่อเต็ม + เอฟเฟกต์
    ส่งไฟล์ field ชื่อ 'image'
    """
    if "image" not in request.files or not request.files["image"].filename:
        return jsonify({"error": "กรุณาแนบไฟล์รูป (field: image)"}), 400
    try:
        tmp = _save_upload(request.files["image"])
        tmp_path = os.path.join(UPLOAD_DIR, tmp)
        q_ph, q_dh = compute_hashes(tmp_path)
    except Exception as e:
        return jsonify({"error": f"อ่านรูปไม่สำเร็จ: {e}"}), 400

    # ไม่เก็บรูปที่ใช้ค้นหา (ลบทิ้ง)
    try: os.remove(tmp_path)
    except OSError: pass

    rows = get_db().execute("SELECT * FROM cards WHERE phash IS NOT NULL").fetchall()
    if not rows:
        return jsonify({"error": "ยังไม่มีการ์ดที่มีรูปในคลัง กรุณาเพิ่มการ์ดก่อน"}), 404

    scored = []
    for r in rows:
        dist = hamming(q_ph, r["phash"]) + hamming(q_dh, r["dhash"])  # 0..128
        conf = round(max(0.0, 1 - dist / 128) * 100, 1)
        scored.append((dist, conf, r))
    scored.sort(key=lambda x: x[0])

    best_dist, best_conf, best = scored[0]
    result = {
        "matched": best_dist <= MATCH_THRESHOLD,
        "confidence": best_conf,
        "distance": best_dist,
        "card": analyze(best),
        "alternatives": [
            {"name_full": r["name_full"], "confidence": c, "id": r["id"]}
            for d, c, r in scored[1:4]
        ],
    }
    if not result["matched"]:
        result["note"] = "ไม่พบการ์ดที่ตรงพอ (นี่คือใบที่ใกล้เคียงที่สุด) ลองถ่ายให้ชัด/ตรงมุมขึ้น หรือเพิ่มการ์ดนี้เข้าคลัง"
    return jsonify(result)


@app.route("/api/stats")
def stats():
    rows = get_db().execute("SELECT * FROM cards").fetchall()
    total = len(rows)
    with_img = sum(1 for r in rows if r["image_file"])
    analyzed = [analyze(r) for r in rows]
    priced = [a["price_summary"]["avg"] for a in analyzed if a["price_summary"]["avg"]]
    return jsonify({
        "total_cards": total,
        "with_image": with_img,
        "total_value_thb": round(sum(priced), 2) if priced else 0,
        "avg_value_thb": round(sum(priced) / len(priced), 2) if priced else 0,
    })


@app.route("/api/auth")
def auth_status():
    return jsonify({"admin": bool(session.get("admin"))})


# ---------- หน้าเว็บ ----------

@app.route("/")
def index():
    """หน้าบ้าน — สาธารณะ ดูอย่างเดียว"""
    return render_template("showcase.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """หลังบ้าน — เข้าได้ผ่าน /login เท่านั้น"""
    error = None
    if request.method == "POST":
        pw = (request.form.get("password") or "").strip()
        if pw == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))
        error = "รหัสผ่านไม่ถูกต้อง"
    if session.get("admin"):
        return redirect(url_for("admin"))
    return render_template("login.html", error=error)


@app.route("/admin")
def admin():
    """หน้าจัดการ — ต้อง login ก่อน ไม่งั้นเด้งไป /login"""
    if not session.get("admin"):
        return redirect(url_for("login"))
    return render_template("admin.html")


@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=True)
