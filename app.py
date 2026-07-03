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
TELEGRAM_WEBHOOK_URL = get_setting("TELEGRAM_WEBHOOK_URL") or get_setting("PUBLIC_WEBHOOK_URL") or get_setting("WEBHOOK_PUBLIC_URL") or get_setting("TUNNEL_URL")

app = Flask(__name__, template_folder='templates')
CORS(app)

UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "knowledge_base")
KB_FILE = os.path.join(UPLOAD_FOLDER, 'company_data.txt')
AUDIO_FOLDER = os.path.join(UPLOAD_FOLDER, 'audio_logs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

LEADS_DATABASE = []
TELEGRAM_SENDER_TO_LEAD = {}


def _normalize_text_for_match(value):
    cleaned = re.sub(r'[^a-z0-9@._]+', ' ', str(value or '').lower())
    return ' '.join(cleaned.split())


def _append_audio_note_to_lead(index, spoken_text):
    existing = LEADS_DATABASE[index].get('audio_note', '')
    if existing:
        LEADS_DATABASE[index]['audio_note'] = f"{existing} | {spoken_text}"
    else:
        LEADS_DATABASE[index]['audio_note'] = spoken_text


def _find_best_lead_index(context_text):
    if not LEADS_DATABASE:
        return None

    normalized_context = _normalize_text_for_match(context_text)
    if not normalized_context:
        return 0 if len(LEADS_DATABASE) == 1 else None

    best_index = None
    best_score = 0

    for idx, lead in enumerate(LEADS_DATABASE):
        score = 0

        name = str(lead.get('name', '')).strip()
        company = str(lead.get('company', '')).strip()
        email = str(lead.get('email', '')).strip().lower()

        norm_name = _normalize_text_for_match(name)
        norm_company = _normalize_text_for_match(company)

        if norm_name and norm_name in normalized_context:
            score += 8
        if norm_company and norm_company != 'unknown' and norm_company in normalized_context:
            score += 5
        if email and email != 'unknown' and email in context_text.lower():
            score += 10

        for token in norm_name.split():
            if len(token) >= 3 and token in normalized_context:
                score += 2

        for token in norm_company.split():
            if len(token) >= 4 and token in normalized_context:
                score += 1

        if score > best_score or (score == best_score and score > 0 and best_index is not None and idx > best_index):
            best_score = score
            best_index = idx

    # Keep threshold conservative to avoid polluting wrong contact rows.
    if best_index is not None and best_score >= 4:
        return best_index

    if len(LEADS_DATABASE) == 1:
        return 0

    return None


def _handle_telegram_text_command(message):
    text = str(message.get("text") or "").strip()
    if not text:
        return None

    sender = message.get("from") or {}
    sender_key = str(sender.get("id") or "")
    lowered = text.lower()

    bind_match = re.match(r'^(?:/)?bind\s*[:\-]?\s*(.+)$', text, flags=re.IGNORECASE)
    if bind_match:
        query = bind_match.group(1).strip()
        matched_index = _find_best_lead_index(query)

        if matched_index is None:
            msg = (
                "🔗 *Bind Request Not Matched*\n"
                f"📝 *Input:* {query}\n"
                "⚠️ No confident lead match found."
            )
            send_telegram_alert(msg)
            return jsonify({"status": "bind_unmatched", "query": query, "all_leads": LEADS_DATABASE}), 200

        if sender_key:
            TELEGRAM_SENDER_TO_LEAD[sender_key] = matched_index

        target = LEADS_DATABASE[matched_index]
        msg = (
            "🔗 *Telegram Sender Bound*\n"
            f"👤 *Target:* {target.get('name', 'Unknown')}\n"
            f"🏢 *Company:* {target.get('company', 'Unknown')}"
        )
        send_telegram_alert(msg)
        return jsonify({
            "status": "bound",
            "lead_index": matched_index,
            "lead": target,
            "all_leads": LEADS_DATABASE,
        }), 200

    if lowered in {"/unbind", "unbind", "clear bind", "clear"}:
        removed = False
        if sender_key and sender_key in TELEGRAM_SENDER_TO_LEAD:
            del TELEGRAM_SENDER_TO_LEAD[sender_key]
            removed = True

        send_telegram_alert("🧹 *Telegram Sender Unbound*\n👤 Future voice notes will require auto-match again.")
        return jsonify({"status": "unbound", "removed": removed, "all_leads": LEADS_DATABASE}), 200

    if lowered in {"/status", "status", "/who", "who", "/whoami", "whoami", "bind status"}:
        if sender_key and sender_key in TELEGRAM_SENDER_TO_LEAD:
            idx = TELEGRAM_SENDER_TO_LEAD[sender_key]
            if 0 <= idx < len(LEADS_DATABASE):
                target = LEADS_DATABASE[idx]
                send_telegram_alert(
                    "🧭 *Current Telegram Binding*\n"
                    f"👤 *Target:* {target.get('name', 'Unknown')}\n"
                    f"🏢 *Company:* {target.get('company', 'Unknown')}"
                )
                return jsonify({"status": "bound", "lead_index": idx, "lead": target, "all_leads": LEADS_DATABASE}), 200

        send_telegram_alert("🧭 *Current Telegram Binding*\n⚠️ No sender binding is set.")
        return jsonify({"status": "unbound", "all_leads": LEADS_DATABASE}), 200

    return None

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


def _normalize_webhook_url(base_url):
    base_url = _normalize_setting_value(base_url)
    if not base_url:
        return None

    if base_url.endswith("/webhook"):
        return base_url

    return f"{base_url.rstrip('/')}/webhook"


def register_telegram_webhook():
    token = _normalize_setting_value(TELEGRAM_BOT_TOKEN)
    webhook_url = _normalize_webhook_url(TELEGRAM_WEBHOOK_URL)

    if is_placeholder_setting(token) or is_placeholder_setting(webhook_url):
        logger.warning("[TELEGRAM] ⚠️ Webhook registration skipped: missing token or webhook URL.")
        logger.warning(f"[TELEGRAM] - Token configured: {not is_placeholder_setting(token)}")
        logger.warning(f"[TELEGRAM] - Webhook URL configured: {not is_placeholder_setting(webhook_url)}")
        if not is_placeholder_setting(webhook_url):
            logger.warning(f"[TELEGRAM] - Webhook URL: {webhook_url}")
        return False

    try:
        logger.info(f"[TELEGRAM] 🔗 Registering webhook: {webhook_url}")
        response = requests.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": webhook_url, "drop_pending_updates": False, "allowed_updates": ["message"]},
            timeout=10,
        )
        result = response.json()
        if response.status_code == 200 and result.get("ok"):
            logger.info(f"[TELEGRAM] ✅ Webhook registered successfully: {webhook_url}")
            return True

        logger.error(f"[TELEGRAM] ❌ Webhook registration failed: {result}")
        return False
    except Exception as exc:
        logger.error(f"[TELEGRAM] ❌ Webhook registration error: {exc}")
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

@app.route('/webhook-status', methods=['GET'])
def webhook_status():
    """Check Telegram webhook status"""
    token = _normalize_setting_value(TELEGRAM_BOT_TOKEN)
    webhook_url = _normalize_webhook_url(TELEGRAM_WEBHOOK_URL)
    
    status = {
        "webhook_configured": not is_placeholder_setting(token) and not is_placeholder_setting(webhook_url),
        "token_configured": not is_placeholder_setting(token),
        "webhook_url_configured": not is_placeholder_setting(webhook_url),
        "webhook_url": webhook_url if not is_placeholder_setting(webhook_url) else "NOT SET",
        "help": "If webhook_configured is false, voice messages won't be received. Set TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_URL in config.py or environment variables."
    }
    
    # Try to get actual webhook info from Telegram
    if not is_placeholder_setting(token):
        try:
            response = requests.get(
                f"https://api.telegram.org/bot{token}/getWebhookInfo",
                timeout=5
            ).json()
            if response.get("ok"):
                webhook_info = response.get("result", {})
                status["telegram_webhook_info"] = {
                    "url": webhook_info.get("url"),
                    "has_custom_certificate": webhook_info.get("has_custom_certificate", False),
                    "pending_update_count": webhook_info.get("pending_update_count", 0),
                    "ip_address": webhook_info.get("ip_address"),
                    "last_error_date": webhook_info.get("last_error_date"),
                    "last_error_message": webhook_info.get("last_error_message"),
                    "allowed_updates": webhook_info.get("allowed_updates")
                }
        except Exception as e:
            status["telegram_webhook_info_error"] = str(e)
    
    return jsonify(status)

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
        logger.info(f"[INGEST] Processing uploaded file: {filename}")
        wav_path = os.path.join(AUDIO_FOLDER, "converted.wav")
        try:
            audio = AudioSegment.from_file(saved_path)
        except Exception as e:
            ext = os.path.splitext(filename)[1].replace('.', '').lower() or 'm4a'
            logger.warning(f"[INGEST] Auto-detection failed, retrying with format '{ext}': {e}")
            audio = AudioSegment.from_file(saved_path, format=ext)
            
        logger.info(f"[INGEST] Audio loaded, duration: {len(audio)}ms, converting to WAV...")
        audio.export(wav_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            try:
                logger.info("[INGEST] Calling Google Speech Recognition API...")
                spoken_text = recognizer.recognize_google(audio_data)
                logger.info(f"[INGEST] Successfully transcribed: {spoken_text[:50]}...")
            except sr.UnknownValueError:
                logger.warning("[INGEST] Google Speech Recognition could not understand audio")
                spoken_text = "[Speech parsed but raw text unclear]"
            except sr.RequestError as e:
                logger.error(f"[INGEST] Google Speech Recognition API error: {e}")
                spoken_text = "[Speech Recognition API unavailable]"

        if os.path.exists(wav_path): os.remove(wav_path)
        if os.path.exists(saved_path): os.remove(saved_path)

        target_name = "Global Unlinked Record"
        appended_to_lead = False
        if anchor_raw is not None and str(anchor_raw).strip() != "":
            try:
                idx = int(str(anchor_raw).strip())
                logger.info(f"[INGEST] Anchor index provided: {idx}, total leads: {len(LEADS_DATABASE)}")
                if 0 <= idx < len(LEADS_DATABASE):
                    _append_audio_note_to_lead(idx, spoken_text)
                    appended_to_lead = True
                    target_name = f"{LEADS_DATABASE[idx]['name']} ({LEADS_DATABASE[idx]['company']})"
                    logger.info(f"[INGEST] ✅ Appended to lead: {target_name}")
                    
                    msg = f"🎙️ *Voice Note Bound to Context*\n👤 *Target:* {LEADS_DATABASE[idx]['name']}\n📋 *Insight:* \"_{spoken_text}_\""
                    send_telegram_alert(msg)
                else:
                    logger.warning(f"[INGEST] Anchor index {idx} out of range (leads: {len(LEADS_DATABASE)})")
            except ValueError as e:
                logger.warning(f"[INGEST] Invalid anchor index: {anchor_raw} - {e}")
        else:
            logger.info(f"[INGEST] No anchor index provided")

        logger.info(f"[INGEST] Writing to KB_FILE: {KB_FILE}")
        with open(KB_FILE, 'a', encoding='utf-8') as f:
            entry = f"\n\n=== RECORD PROFILE BIND: {target_name.upper()} ===\n• Timestamp: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}\n• Transcript: {spoken_text}\n• Appended to Lead: {appended_to_lead}"
            f.write(entry)
            logger.info(f"[INGEST] ✅ Written to KB_FILE")
            
        logger.info(f"[INGEST] Returning response with parsed text: {spoken_text[:50]}...")
        return jsonify({'message': 'Success', 'all_leads': LEADS_DATABASE, 'parsed': spoken_text, 'anchor_index': anchor_raw, 'appended_to_lead': appended_to_lead})
    except Exception as e:
        logger.error(f"[AUDIO INGEST] Error: {str(e)}")
        if os.path.exists(saved_path): os.remove(saved_path)
        if os.path.exists(wav_path): os.remove(wav_path)
        return jsonify({'error': f"Pipeline crash: {str(e)}"}), 500

def download_telegram_file(file_id):
    token = _normalize_setting_value(TELEGRAM_BOT_TOKEN)
    if is_placeholder_setting(token):
        raise ValueError("Telegram bot token not configured")

    logger.info(f"[TELEGRAM] Downloading voice file: {file_id}")
    try:
        file_res = requests.get(
            f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}",
            timeout=15
        ).json()
    except Exception as e:
        logger.error(f"[TELEGRAM] Failed to call getFile API: {e}")
        raise ValueError(f"Telegram getFile API error: {e}")

    if not file_res.get("ok"):
        logger.error(f"[TELEGRAM] getFile API returned error: {file_res}")
        raise ValueError(f"Telegram getFile failed: {file_res}")

    file_path = file_res["result"]["file_path"]
    audio_url = f"https://api.telegram.org/file/bot{token}/{file_path}"

    filename = secure_filename(os.path.basename(file_path))
    if not filename:
        filename = f"telegram_voice_{uuid.uuid4().hex}.ogg"

    saved_path = os.path.join(AUDIO_FOLDER, filename)
    try:
        logger.info(f"[TELEGRAM] Downloading audio from: {audio_url[:50]}...")
        with requests.get(audio_url, stream=True, timeout=20) as response:
            response.raise_for_status()
            with open(saved_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        logger.info(f"[TELEGRAM] Voice file saved: {saved_path}")
    except Exception as e:
        logger.error(f"[TELEGRAM] Failed to download voice file: {e}")
        if os.path.exists(saved_path):
            os.remove(saved_path)
        raise ValueError(f"Failed to download voice file: {e}")

    return saved_path


def transcribe_audio_file(file_path):
    wav_path = os.path.join(AUDIO_FOLDER, f"telegram_{uuid.uuid4().hex}.wav")
    try:
        # Check if file exists and has size
        if not os.path.exists(file_path):
            logger.error(f"[TRANSCRIBE] File does not exist: {file_path}")
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        file_size = os.path.getsize(file_path)
        logger.info(f"[TRANSCRIBE] File exists, size: {file_size} bytes")
        
        # Try to detect format from file extension or default to ogg
        ext = os.path.splitext(file_path)[1].replace('.', '').lower() or 'ogg'
        logger.info(f"[TRANSCRIBE] Processing audio file: {file_path} (format: {ext}, size: {file_size})")
        
        try:
            logger.info(f"[TRANSCRIBE] Attempting auto-detection...")
            audio = AudioSegment.from_file(file_path)
            logger.info(f"[TRANSCRIBE] Auto-detection succeeded")
        except Exception as e:
            logger.warning(f"[TRANSCRIBE] Auto-detection failed, retrying with explicit format '{ext}': {e}")
            # Explicitly specify format if auto-detection fails
            try:
                audio = AudioSegment.from_file(file_path, format=ext)
                logger.info(f"[TRANSCRIBE] Explicit format loading succeeded")
            except Exception as e2:
                logger.error(f"[TRANSCRIBE] Explicit format loading also failed: {e2}")
                raise
        
        logger.info(f"[TRANSCRIBE] Audio loaded successfully")
        duration_ms = len(audio)
        logger.info(f"[TRANSCRIBE] Audio duration: {duration_ms}ms, frames: {audio.frame_count}, channels: {audio.channels}, sample_rate: {audio.frame_rate}")
        
        logger.info(f"[TRANSCRIBE] Converting to WAV...")
        audio.export(wav_path, format="wav")
        
        if not os.path.exists(wav_path):
            logger.error(f"[TRANSCRIBE] WAV export failed - file not created")
            raise RuntimeError("WAV export failed")
        
        wav_size = os.path.getsize(wav_path)
        logger.info(f"[TRANSCRIBE] WAV file created, size: {wav_size} bytes")

        recognizer = sr.Recognizer()
        logger.info(f"[TRANSCRIBE] Created recognizer")
        
        with sr.AudioFile(wav_path) as source:
            logger.info(f"[TRANSCRIBE] Reading audio from WAV file...")
            audio_data = recognizer.record(source)
            logger.info(f"[TRANSCRIBE] Audio recorded, frame_count: {len(audio_data.frame_data)}")
            
            try:
                logger.info("[TRANSCRIBE] Calling Google Speech Recognition API...")
                text = recognizer.recognize_google(audio_data)
                logger.info(f"[TRANSCRIBE] ✅ Successfully transcribed: {text[:100]}...")
                return text
            except sr.UnknownValueError as e:
                logger.warning(f"[TRANSCRIBE] Google Speech Recognition could not understand audio: {e}")
                return "[Speech parsed but raw text unclear]"
            except sr.RequestError as e:
                logger.error(f"[TRANSCRIBE] Google Speech Recognition API error: {e}")
                return "[Speech Recognition API unavailable]"
    except Exception as e:
        logger.error(f"[TRANSCRIBE] Fatal error: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"[TRANSCRIBE] Traceback: {traceback.format_exc()}")
        raise
    finally:
        logger.info(f"[TRANSCRIBE] Cleanup: removing temporary files")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"[TRANSCRIBE] Removed: {file_path}")
            except Exception as e:
                logger.warning(f"[TRANSCRIBE] Failed to remove {file_path}: {e}")
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
                logger.info(f"[TRANSCRIBE] Removed: {wav_path}")
            except Exception as e:
                logger.warning(f"[TRANSCRIBE] Failed to remove {wav_path}: {e}")


register_telegram_webhook()


@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.get_json(force=True, silent=True) or {}
    if not data or "message" not in data:
        return jsonify({"status": "ignored", "reason": "no message"}), 200

    message = data.get("message", {})
    logger.info(f"[WEBHOOK] Received message with keys: {list(message.keys())}")

    text_command_response = _handle_telegram_text_command(message)
    if text_command_response is not None:
        return text_command_response

    if "voice" not in message:
        logger.info(f"[WEBHOOK] No voice in message, ignoring")
        return jsonify({"status": "ignored", "reason": "no voice or command"}), 200

    voice_info = message.get("voice", {})
    logger.info(f"[WEBHOOK] Voice message detected: {list(voice_info.keys())}")
    
    file_id = voice_info.get("file_id")
    if not file_id:
        logger.warning(f"[WEBHOOK] Voice message missing file_id")
        return jsonify({"status": "ignored", "reason": "missing file_id"}), 200

    logger.info(f"[WEBHOOK] Processing voice file_id: {file_id}")
    try:
        saved_path = download_telegram_file(file_id)
        logger.info(f"[WEBHOOK] File downloaded, calling transcribe_audio_file()...")
        transcription = transcribe_audio_file(saved_path)
        logger.info(f"[WEBHOOK] Transcription result: {transcription[:100]}")
    except ValueError as exc:
        logger.warning(f"[TELEGRAM WEBHOOK] Configuration error: {exc}")
        return jsonify({"status": "failed", "error": str(exc)}), 503
    except Exception as exc:
        logger.exception("[TELEGRAM WEBHOOK] Unexpected processing error")
        return jsonify({"status": "failed", "error": str(exc)}), 500

    sender = message.get("from") or {}
    sender_key = str(sender.get("id") or "")
    sender_context = " ".join([
        str(sender.get("first_name") or ""),
        str(sender.get("last_name") or ""),
        str(sender.get("username") or ""),
    ]).strip()

    matched_index = None
    if sender_key and sender_key in TELEGRAM_SENDER_TO_LEAD:
        cached_index = TELEGRAM_SENDER_TO_LEAD[sender_key]
        if 0 <= cached_index < len(LEADS_DATABASE):
            matched_index = cached_index

    if matched_index is None:
        context_text = f"{transcription} {sender_context}".strip()
        matched_index = _find_best_lead_index(context_text)

    target_label = "Unlinked Telegram Entry"
    appended_to_lead = False
    if matched_index is not None:
        logger.info(f"[TELEGRAM WEBHOOK] Appending to lead index: {matched_index}")
        _append_audio_note_to_lead(matched_index, transcription)
        appended_to_lead = True
        target_label = LEADS_DATABASE[matched_index].get("name", "Unknown")
        if sender_key:
            TELEGRAM_SENDER_TO_LEAD[sender_key] = matched_index
        logger.info(f"[TELEGRAM WEBHOOK] ✅ Appended transcription to lead: {target_label}")
    else:
        logger.warning(f"[TELEGRAM WEBHOOK] No lead matched for transcription")

    msg = (
        "🎙️ *Telegram Voice Note Received*\n"
        f"👤 *Target:* {target_label}\n"
        f"📋 *Summary:* _{transcription}_"
    )
    send_telegram_alert(msg)

    logger.info(f"[TELEGRAM WEBHOOK] Writing to KB_FILE: {KB_FILE}")
    with open(KB_FILE, 'a', encoding='utf-8') as f:
        entry = (
            f"\n\n=== TELEGRAM VOICE RECORD ===\n"
            f"• Timestamp: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}\n"
            f"• Transcript: {transcription}\n"
            f"• Appended to Lead: {appended_to_lead}\n"
        )
        f.write(entry)
        logger.info(f"[TELEGRAM WEBHOOK] ✅ Written to KB_FILE")

    logger.info(f"[TELEGRAM WEBHOOK] Successfully processed voice note")
    return jsonify({"status": "synced", "transcription": transcription, "all_leads": LEADS_DATABASE, "appended_to_lead": appended_to_lead, "target_label": target_label}), 200


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == 'transcribe':
        print(transcribe_audio_file(sys.argv[2]))
    else:
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
