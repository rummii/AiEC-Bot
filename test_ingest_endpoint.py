#!/usr/bin/env python3
"""
Test the Flask /ingest-audio endpoint with mock uploads
"""
import sys
import os
import io
from pydub import AudioSegment

# Import the app
sys.path.insert(0, '/workspaces/AiEC-Bot')
import app

def test_ingest_audio_endpoint():
    """Test the ingest_audio function with mock file uploads"""
    print("\n" + "="*60)
    print("🧪 TESTING /ingest-audio ENDPOINT")
    print("="*60)
    
    # Create test client
    app.app.config['TESTING'] = True
    client = app.app.test_client()
    
    # Test 1: No file uploaded
    print("\n1️⃣ Test: POST without audio file...")
    response = client.post('/ingest-audio')
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.get_json()}")
    assert response.status_code == 400, "Should return 400 for missing file"
    print("   ✅ Correctly rejects missing file")
    
    # Test 2: Empty filename
    print("\n2️⃣ Test: POST with empty filename...")
    response = client.post('/ingest-audio', data={'file': (io.BytesIO(b''), '')})
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.get_json()}")
    assert response.status_code == 400, "Should return 400 for empty filename"
    print("   ✅ Correctly rejects empty filename")
    
    # Test 3: Valid WAV file (silent)
    print("\n3️⃣ Test: POST with valid silent WAV file...")
    try:
        # Create a 2-second silent WAV file
        audio = AudioSegment.silent(duration=2000)
        wav_buffer = io.BytesIO()
        audio.export(wav_buffer, format="wav")
        wav_buffer.seek(0)
        
        response = client.post('/ingest-audio', 
                               data={'file': (wav_buffer, 'test_silent.wav')})
        print(f"   Status: {response.status_code}")
        data = response.get_json()
        print(f"   Response keys: {list(data.keys())}")
        if 'parsed' in data:
            print(f"   Transcribed text: {data['parsed']}")
        if 'error' in data:
            print(f"   Error: {data['error']}")
        print("   ✅ Request processed")
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Valid OGG file (silent)
    print("\n4️⃣ Test: POST with valid silent OGG file...")
    try:
        # Create a 2-second silent OGG file
        audio = AudioSegment.silent(duration=2000)
        ogg_buffer = io.BytesIO()
        audio.export(ogg_buffer, format="ogg")
        ogg_buffer.seek(0)
        
        response = client.post('/ingest-audio',
                               data={'file': (ogg_buffer, 'test_silent.ogg')})
        print(f"   Status: {response.status_code}")
        data = response.get_json()
        print(f"   Response keys: {list(data.keys())}")
        if 'parsed' in data:
            print(f"   Transcribed text: {data['parsed']}")
        if 'error' in data:
            print(f"   Error: {data['error']}")
        print("   ✅ Request processed")
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: M4A format
    print("\n5️⃣ Test: POST with M4A file...")
    try:
        # Create a 2-second silent M4A file
        audio = AudioSegment.silent(duration=2000)
        m4a_buffer = io.BytesIO()
        audio.export(m4a_buffer, format="mp4")
        m4a_buffer.seek(0)
        
        response = client.post('/ingest-audio',
                               data={'file': (m4a_buffer, 'test_silent.m4a')})
        print(f"   Status: {response.status_code}")
        data = response.get_json()
        print(f"   Response keys: {list(data.keys())}")
        if 'parsed' in data:
            print(f"   Transcribed text: {data['parsed']}")
        if 'error' in data:
            print(f"   Error: {data['error']}")
        print("   ✅ Request processed")
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*60)
    print("✅ All endpoint tests completed!")
    print("="*60)
    print("\n💡 Notes:")
    print("   - Silent audio returns: '[Speech parsed but raw text unclear]'")
    print("   - This is expected behavior for audio without speech")
    print("   - If you're getting errors, check the Flask app logs")
    print("\n")
    return True

if __name__ == '__main__':
    success = test_ingest_audio_endpoint()
    sys.exit(0 if success else 1)
