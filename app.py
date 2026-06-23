import os
import requests
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from google import genai
from google.genai import types
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Persistent paths for cloud compatibility
UPLOAD_FOLDER = '/tmp/knowledge_base' if os.environ.get('RENDER') else 'knowledge_base'
KB_FILE = os.path.join(UPLOAD_FOLDER, 'company_data.txt')
AUDIO_FOLDER = os.path.join(UPLOAD_FOLDER, 'audio_logs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Credentials configuration from environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8624026555:AAHzsOh95QmuqhoPOYuVhcfkOeIfJG87P54")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6027602817")

# Initialize Gemini Client
client = genai.Client()

VCARD_DATA = """BEGIN:VCARD
VERSION:3.0
N:Jet;;;;
FN:Jet
ORG:Monitor Gear
TITLE:Creative Director
TEL;TYPE=CELL,VOICE:+639000000000
EMAIL;TYPE=PREF,INTERNET:jet@monitorgear.com
NOTE:Connected via Gemini Sales Agent
END:VCARD"""

def send_telegram_alert(device_info):
    """Fires an instant notification to your phone via Telegram."""
    if not TELEGRAM_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    message = (
        "🚨 **Lead QR Code Scanned!**\n\n"
        f"📱 Device: {device_info}\n"
        "⚡ *Action Required:* Open your voice recorder or prepare to dictate your interaction summary."
    )
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[Error] Failed to send Telegram notification: {e}")

def get_knowledge_base():
    if os.path.exists(KB_FILE):
        with open(KB_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    return "No company information available yet."

@app.route('/connect', methods=['GET'])
def lead_scanned_qr():
    user_agent = request.headers.get("User-Agent", "Unknown Device")
    send_telegram_alert(user_agent)
    return Response(
        VCARD_DATA,
        mimetype="text/vcard",
        headers={"Content-Disposition": "attachment; filename=jet_contact.vcf"}
    )

# --- NEW: Audio Ingestion Pipeline Route ---
@app.route('/ingest-audio', methods=['POST'])
def ingest_audio():
    """
    Receives a raw meeting voice note, transcribes and extracts lead data via Gemini,
    and appends the structured results straight to your knowledge database.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No audio file found in request'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty file submission'}), 400

    filename = secure_filename(file.filename)
    saved_path = os.path.join(AUDIO_FOLDER, filename)
    file.save(saved_path)
    
    # Format a highly structural parsing blueprint for Gemini Flash
    parsing_prompt = (
        "You are an expert sales intelligence assistant parsing a raw conference meeting voice recording.\n"
        "Analyze the uploaded audio track and extract all explicit business lead items.\n\n"
        "Format your output exactly using this layout:\n"
        "--- LEAD PROFILE METADATA ---\n"
        "• Name: [Lead Name or Unknown]\n"
        "• Company: [Company Name or Unknown]\n"
        "• Contact Points: [Email/Phone discussed]\n"
        "• Immediate Pain Point/Interest: [Core topic discussed]\n"
        "• Assigned Action Items: [Follow-up task details]\n"
    )

    try:
        # Upload the saved audio directly into Gemini's multi-modal processing queue
        print(f"📦 Uploading voice session tracking file: {filename}")
        audio_media = client.files.upload(file=saved_path)
        
        # Run inference against the media track using gemini-2.5-flash
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[audio_media, parsing_prompt]
        )
        
        extracted_profile = response.text
        
        # Permanently write this structured target right into your file system database
        with open(KB_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n\n=== NEW LEAD PROFILE ATTACHED ===\n{extracted_profile}")
            
        return jsonify({
            'message': 'Audio analyzed and structural target committed.',
            'profile_extracted': extracted_profile
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        filename = secure_filename(file.filename)
        content = file.read().decode('utf-8', errors='ignore')
        with open(KB_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n\n--- Document: {filename} ---\n{content}")
        return jsonify({'message': f'Successfully added {filename} to knowledge base.'})

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json or {}
    user_message = data.get('message', '')
    context = get_knowledge_base()
    
    system_instruction = (
        "You are a helpful, direct, and authentic company AI assistant.\n"
        "Your job is ONLY to answer questions using the company context provided below.\n"
        "If the answer cannot be found in the context, politely reply: "
        "'I am sorry, but I can only answer questions related to the company using my current knowledge base.'\n"
        f"--- COMPANY CONTEXT ---\n{context}"
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2
            )
        )
        return jsonify({'reply': response.text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
