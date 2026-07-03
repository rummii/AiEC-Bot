# Voice Text Tracking Guide

## Where Your Voice Text SHOULD Appear

### 1. **Knowledge Base File** (company_data.txt)
Every voice note is written here, with timestamp and lead info.

**Location:**
```
knowledge_base/company_data.txt
```

**Example entry:**
```
=== RECORD PROFILE BIND: BOB SMITH (ACME CORP) ===
• Timestamp: 2026-07-03 07:15 PM
• Transcript: I discussed the Q3 budget requirements
• Appended to Lead: True
```

**Check it:** `cat knowledge_base/company_data.txt`

---

### 2. **LEADS_DATABASE** (In-Memory)
When audio is linked to a lead via anchor_index or Telegram auto-match, it should appear in the lead's `audio_note` field.

**Check it in Flask logs:**
```
[INGEST] ✅ Appended to lead: Bob Smith (ACME Corp)
[TELEGRAM WEBHOOK] ✅ Appended transcription to lead: Bob Smith
```

**Or in the JSON response:**
```json
{
  "appended_to_lead": true,
  "target_label": "Bob Smith",
  "all_leads": [
    {
      "name": "Bob Smith",
      "audio_note": "I discussed the Q3 budget requirements"
    }
  ]
}
```

---

## Processing Flow & Logging

### For Web Form Upload (`/ingest-audio` endpoint)

```
1. File received → [INGEST] Processing uploaded file: test.wav
2. Audio loaded → [INGEST] Audio loaded, duration: 5000ms, converting to WAV...
3. Calling API → [INGEST] Calling Google Speech Recognition API...
4. Success → [INGEST] Successfully transcribed: Hello world...
5. Appending → [INGEST] ✅ Appended to lead: Bob Smith (ACME Corp)
6. Writing → [INGEST] ✅ Written to KB_FILE
7. Response → [INGEST] Returning response with parsed text...
```

**Critical checks:**
- ✅ Is `appended_to_lead: true` in response?
- ✅ Does logs show `Successfully transcribed:`?
- ✅ Does logs show `✅ Appended to lead:`?

---

### For Telegram Voice Message (`/webhook` endpoint)

```
1. Voice received → [TELEGRAM] Downloading voice file: ABCDEFxyz123...
2. Downloaded → [TELEGRAM] Voice file saved: /path/to/telegram_xxx.ogg
3. Converting → [TRANSCRIBE] Processing audio file: telegram_xxx.ogg
4. Success → [TRANSCRIBE] Successfully transcribed: Hello there...
5. Matching → [TELEGRAM WEBHOOK] No lead matched / Appending to lead index: 0
6. Writing → [TELEGRAM WEBHOOK] ✅ Written to KB_FILE
7. Alert → Sends Telegram message back to chat
```

**Critical checks:**
- ✅ Does logs show `Successfully transcribed:`?
- ✅ Does logs show `✅ Appended transcription to lead:`?
- ✅ Telegram bot sends you an alert message?

---

## Troubleshooting: Text Not Appearing

### Issue: Text transcribed but NOT added to lead

**Cause 1: No anchor_index provided (Web Upload)**
```
[INGEST] No anchor index provided
```
**Fix:** When uploading via web form, include the lead index (0, 1, 2, etc.)

**Cause 2: Anchor index out of range**
```
[INGEST] Anchor index 5 out of range (leads: 2)
```
**Fix:** Make sure you have enough leads in the database

**Cause 3: Invalid anchor index**
```
[INGEST] Invalid anchor index: abc - ...
```
**Fix:** Anchor must be a number, not text

### Issue: Text NOT transcribed at all

**Cause 1: API call failed**
```
[INGEST] Google Speech Recognition API error: ...
```
**Fix:** Check network, API rate limits, or audio quality

**Cause 2: Audio too quiet**
```
[INGEST] Google Speech Recognition could not understand audio
```
**Fix:** Use louder/clearer audio

**Cause 3: Audio conversion failed**
```
[INGEST] Auto-detection failed, retrying with format 'ogg': ...
```
**Fix:** Make sure file format is actually OGG/WAV/M4A/MP3

---

## How to Debug

### 1. Start the app and watch logs
```bash
bash run_app.sh
```

### 2. Upload audio file and capture the full log output

### 3. Check if text appears in KB_FILE
```bash
tail -20 knowledge_base/company_data.txt
```

### 4. Check the JSON response
The Flask response includes:
- `"appended_to_lead": true/false` ← Key indicator!
- `"target_label": "Lead Name"` ← Where it was added
- `"parsed": "transcribed text"` ← The actual text

### 5. Check LEADS_DATABASE via API
```bash
curl http://localhost:5000/ -s | grep audio_note
```

---

## Quick Verification Script

```bash
#!/bin/bash
echo "🔍 Checking voice text storage..."
echo ""
echo "1. KB_FILE entries:"
tail -20 knowledge_base/company_data.txt | grep -E "(TRANSCRIPT|RECORD|Transcript)"
echo ""
echo "2. Recent changes:"
ls -lt knowledge_base/company_data.txt
```

---

## Expected Behavior by Scenario

### ✅ Success: Web Upload with anchor_index=0
```
Logs show:
  ✅ Appended to lead: Alice Johnson (TechCorp)
  ✅ Written to KB_FILE

Response:
  appended_to_lead: true
  target_label: Alice Johnson
  parsed: "Let me check the schedule"

KB_FILE shows:
  === RECORD PROFILE BIND: ALICE JOHNSON (TECHCORP) ===
  • Transcript: Let me check the schedule
  • Appended to Lead: True
```

### ⚠️ Partial: Web Upload without anchor_index
```
Logs show:
  No anchor index provided
  ✅ Written to KB_FILE

Response:
  appended_to_lead: false
  parsed: "Let me check the schedule"

KB_FILE shows:
  === RECORD PROFILE BIND: GLOBAL UNLINKED RECORD ===
  • Transcript: Let me check the schedule
  • Appended to Lead: False
```

### ✅ Success: Telegram Voice (Auto-matched)
```
Logs show:
  Successfully transcribed: "Let me check the schedule"
  ✅ Appended transcription to lead: Bob Smith
  ✅ Written to KB_FILE
  
Response:
  appended_to_lead: true
  target_label: Bob Smith
  transcription: "Let me check the schedule"
  
Telegram bot sends alert message to you
```

---

## Key Takeaway

**Voice text IS being processed** — the question is WHERE it's being stored:

1. **Always in KB_FILE** ✅ (company_data.txt)
2. **In LEADS_DATABASE if:**
   - Web form includes a valid `anchor_index`, OR
   - Telegram auto-matches to a lead based on voice content

If you're not seeing text appear where expected, **check the Flask logs** for the exact step where it stops.
