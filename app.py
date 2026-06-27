import os
import re
import uuid
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime
import speech_recognition as sr
from pydub import AudioSegment
import logging

# Explicit local configuration import
try:
    import config
except ImportError:
    config = None

# Set up Flask logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _normalize_setting_value(value):
    if value is None:
        return None

    normalized = str(value).strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {'"', "'"}:
        normalized = normalized[1:-1].strip()

    return normalized or None


def get_setting(name, default=None):
    value = _normalize_setting_value(os.environ.get(name))
    if value is not None:
        return value

    if config is not None:
        return _normalize_setting_value(getattr(config, name, default)) or default

    return default


def is_placeholder_setting(value):
    if value is None:
        return True

    cleaned = str(value).strip().lower()
    placeholder_markers = (
        "your_actual",
        "your_telegram_bot_token_here",
        "your_telegram_chat_id_here",
        "your_bot_token_here",
        "your_chat_id_here",
        "your_deepseek_key_here",
    )
    return not cleaned or any(marker in cleaned for marker in placeholder_markers)


TELEGRAM_BOT_TOKEN = get_setting("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = get_setting("TELEGRAM_CHAT_ID")
DEEPSEEK_API_KEY = get_setting("DEEPSEEK_API_KEY")

app = Flask(__name__, template_folder='templates')
CORS(app)

UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "knowledge_base")
KB_FILE = os.path.join(UPLOAD_FOLDER, 'company_data.txt')
AUDIO_FOLDER = os.path.join(UPLOAD_FOLDER, 'audio_logs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

LEADS_DATABASE = []

def send_telegram_alert(message, lead_name=None):
    """Dispatches a real-time notification payload to the external Telegram anchor."""
    token = _normalize_setting_value(TELEGRAM_BOT_TOKEN)
    chat_id = _normalize_setting_value(TELEGRAM_CHAT_ID)

    if is_placeholder_setting(token) or is_placeholder_setting(chat_id):
        print("--> Telegram Alert Skipped: Valid credentials not found in config.py")
        print("--> Telegram Alert Skipped: missing TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID in Render environment or config.py")
        logger.warning("[TELEGRAM] Skipped because the bot token or chat ID is missing or still a placeholder.")
        return False

    logger.info(f"[TELEGRAM] Attempting to send alert: {message[:50]}...")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        status = "✅ SUCCESS" if response.status_code == 200 else f"❌ FAILED ({response.status_code})"
        logger.info(f"[TELEGRAM] {status}: {response.text[:100]}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"[TELEGRAM] ❌ Transport Error: {e}")
        return False

def parse_vcard(vcard_text):
    name, company, email = "Unknown", "Unknown", "Unknown"
    fn_match = re.search(r'FN:(.*)', vcard_text, re.IGNORECASE)
    if fn_match: name = fn_match.group(1).strip()
    org_match = re.search(r'ORG:(.*)', vcard_text, re.IGNORECASE)
    if org_match: company = org_match.group(1).strip()
    email_match = re.search(r'EMAIL.*:(.*)', vcard_text, re.IGNORECASE)
    if email_match: email = email_match.group(1).strip()
    return name, company, email

@app.route('/', methods=['GET'])
def index_dashboard():
    return render_template('index.html')

@app.route('/scan', methods=['POST'])
@app.route('/intake-qr', methods=['POST'])
def intake_qr():
    data = request.json or {}
    qr_payload = data.get('qr_payload') or data.get('data', '')
    if "BEGIN:VCARD" in qr_payload:
        name, company, email = parse_vcard(qr_payload)
    else:
        name, company, email = "Scanned Text QR", "Unknown", qr_payload[:40]

    lead_entry = {
        "timestamp": datetime.now().strftime("%I:%M %p"),
        "name": name,
        "company": company,
        "email": email,
        "source": "QR Scanner",
        "audio_note": ""
    }
    LEADS_DATABASE.append(lead_entry)
    
    msg = f"🔔 *New QR Lead Intercepted!*\n👤 *Name:* {name}\n🏢 *Company:* {company}\n📧 *Email:* {email}"
    send_telegram_alert(msg)
    
    return jsonify({"status": "success", "all_leads": LEADS_DATABASE})

@app.route('/manual_save', methods=['POST'])
def intake_manual():
    data = request.json or {}
    lead_entry = {
        "timestamp": datetime.now().strftime("%I:%M %p"),
        "name": data.get('name', 'Unknown'),
        "company": data.get('company', 'Unknown'),
        "email": data.get('email', 'Unknown'),
        "source": "Manual Input",
        "audio_note": ""
    }
    LEADS_DATABASE.append(lead_entry)
    
    msg = f"✍️ *Manual Lead Override Logged*\n👤 *Name:* {lead_entry['name']}\n🏢 *Company:* {lead_entry['company']}\n📧 *Email:* {lead_entry['email']}"
    send_telegram_alert(msg)
    
    return jsonify({"status": "success", "all_leads": LEADS_DATABASE})

@app.route('/ingest-audio', methods=['POST'])
def ingest_audio():
    if 'file' not in request.files:
        return jsonify({'error': 'No audio file found'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty file name'}), 400
        
    anchor_raw = request.form.get('anchor_index', None)
    filename = secure_filename(file.filename)
    saved_path = os.path.join(AUDIO_FOLDER, filename)
    file.save(saved_path)

    try:
        wav_path = os.path.join(AUDIO_FOLDER, "converted.wav")
        try:
            audio = AudioSegment.from_file(saved_path)
        except Exception:
            ext = os.path.splitext(filename)[1].replace('.', '').lower() or 'm4a'
            audio = AudioSegment.from_file(saved_path, format=ext)
            
        audio.export(wav_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            try:
                spoken_text = recognizer.recognize_google(audio_data)
            except Exception:
                spoken_text = "[Speech parsed but raw text unclear]"

        if os.path.exists(wav_path): os.remove(wav_path)
        if os.path.exists(saved_path): os.remove(saved_path)

        target_name = "Global Unlinked Record"
        if anchor_raw is not None and str(anchor_raw).strip() != "":
            try:
                idx = int(str(anchor_raw).strip())
                if 0 <= idx < len(LEADS_DATABASE):
                    existing = LEADS_DATABASE[idx].get('audio_note', '')
                    if existing:
                        LEADS_DATABASE[idx]['audio_note'] = f"{existing} | {spoken_text}"
                    else:
                        LEADS_DATABASE[idx]['audio_note'] = spoken_text
                    target_name = f"{LEADS_DATABASE[idx]['name']} ({LEADS_DATABASE[idx]['company']})"
                    
                    msg = f"🎙️ *Voice Note Bound to Context*\n👤 *Target:* {LEADS_DATABASE[idx]['name']}\n📋 *Insight:* \"_{spoken_text}_\""
                    send_telegram_alert(msg)
            except ValueError:
                pass

        with open(KB_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n\n=== RECORD PROFILE BIND: {target_name.upper()} ===\n• Timestamp: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}\n• Transcript: {spoken_text}")
            
        return jsonify({'message': 'Success', 'all_leads': LEADS_DATABASE, 'parsed': spoken_text})
    except Exception as e:
        if os.path.exists(saved_path): os.remove(wav_path)
        return jsonify({'error': f"Pipeline crash: {str(e)}"}), 500

def download_telegram_file(file_id):
    if not TELEGRAM_BOT_TOKEN or "YOUR_ACTUAL" in TELEGRAM_BOT_TOKEN:
        raise ValueError("Telegram bot token not configured")

    file_res = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}",
        timeout=15
    ).json()

    if not file_res.get("ok"):
        raise ValueError(f"Telegram getFile failed: {file_res}")

    file_path = file_res["result"]["file_path"]
    audio_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

    filename = secure_filename(os.path.basename(file_path))
    if not filename:
        filename = f"telegram_voice_{uuid.uuid4().hex}.ogg"

    saved_path = os.path.join(AUDIO_FOLDER, filename)
    with requests.get(audio_url, stream=True, timeout=20) as response:
        response.raise_for_status()
        with open(saved_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    return saved_path


def transcribe_audio_file(file_path):
    wav_path = os.path.join(AUDIO_FOLDER, f"telegram_{uuid.uuid4().hex}.wav")
    try:
        audio = AudioSegment.from_file(file_path)
        audio.export(wav_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            try:
                return recognizer.recognize_google(audio_data)
            except Exception:
                return "[Speech parsed but raw text unclear]"
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)


@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.get_json(force=True, silent=True) or {}
    if data and "message" in data and "voice" in data["message"]:
        file_id = data["message"]["voice"]["file_id"]

        try:
            saved_path = download_telegram_file(file_id)
            transcription = transcribe_audio_file(saved_path)
        except Exception as exc:
            return jsonify({"status": "failed", "error": str(exc)}), 500

        if LEADS_DATABASE:
            existing = LEADS_DATABASE[-1].get("audio_note", "")
            if existing:
                LEADS_DATABASE[-1]["audio_note"] = f"{existing} | {transcription}"
            else:
                LEADS_DATABASE[-1]["audio_note"] = transcription

            msg = (
                f"🎙️ *Telegram Voice Note Bound to Context*\n"
                f"👤 *Target:* {LEADS_DATABASE[-1]['name']}\n"
                f"📋 *Summary:* _{transcription}_"
            )
            send_telegram_alert(msg)

        with open(KB_FILE, 'a', encoding='utf-8') as f:
            f.write(
                f"\n\n=== TELEGRAM VOICE RECORD ===\n"
                f"• Timestamp: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}\n"
                f"• Transcript: {transcription}\n"
            )

        return jsonify({"status": "synced", "transcription": transcription, "all_leads": LEADS_DATABASE}), 200

    return jsonify({"status": "ignored"}), 200


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == 'transcribe':
        print(transcribe_audio_file(sys.argv[2]))
    else:
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
