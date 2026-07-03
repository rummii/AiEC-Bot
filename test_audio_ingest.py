#!/usr/bin/env python3
"""
Diagnostic test to check audio ingest pipeline
"""
import os
import sys
import io
from pydub import AudioSegment
import speech_recognition as sr

def test_audio_pipeline():
    """Test the complete audio processing pipeline"""
    print("\n" + "="*60)
    print("🔍 AUDIO INGEST PIPELINE DIAGNOSTIC")
    print("="*60)
    
    # Test 1: Check pydub availability
    print("\n1️⃣ Checking pydub/ffmpeg...")
    try:
        # Try to create a simple audio segment
        audio = AudioSegment.silent(duration=1000)
        print("   ✅ pydub working, can generate audio")
    except Exception as e:
        print(f"   ❌ pydub issue: {e}")
        return False
    
    # Test 2: Check WAV export
    print("\n2️⃣ Checking WAV export...")
    try:
        temp_wav = "/tmp/test_export.wav"
        audio.export(temp_wav, format="wav")
        if os.path.exists(temp_wav):
            print(f"   ✅ WAV export working (size: {os.path.getsize(temp_wav)} bytes)")
            os.remove(temp_wav)
        else:
            print("   ❌ WAV file not created")
            return False
    except Exception as e:
        print(f"   ❌ WAV export failed: {e}")
        return False
    
    # Test 3: Check speech_recognition library
    print("\n3️⃣ Checking speech_recognition...")
    try:
        recognizer = sr.Recognizer()
        print(f"   ✅ speech_recognition v{sr.__version__} loaded")
        print(f"   📋 Recognizer settings:")
        print(f"      - energy_threshold: {recognizer.energy_threshold}")
        print(f"      - dynamic_energy_threshold: {recognizer.dynamic_energy_threshold}")
    except Exception as e:
        print(f"   ❌ speech_recognition issue: {e}")
        return False
    
    # Test 4: Test with silent audio file
    print("\n4️⃣ Testing speech recognition with silent audio...")
    try:
        temp_wav = "/tmp/test_silent.wav"
        silent = AudioSegment.silent(duration=2000)  # 2 seconds of silence
        silent.export(temp_wav, format="wav")
        
        with sr.AudioFile(temp_wav) as source:
            audio_data = recognizer.record(source)
            print(f"   ℹ️ Audio data recorded (frame_count: {len(audio_data.frame_data)})")
        
        try:
            result = recognizer.recognize_google(audio_data)
            print(f"   ℹ️ Transcription result: {result}")
        except sr.UnknownValueError:
            print("   ⚠️ Audio was too silent to transcribe (expected for silence)")
        except sr.RequestError as e:
            print(f"   ❌ Google Speech API error: {e}")
            print("      This could be: network issue, API quota exceeded, or authentication problem")
        
        os.remove(temp_wav)
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False
    
    # Test 5: Check network connectivity to Google
    print("\n5️⃣ Checking Google Speech Recognition API connectivity...")
    try:
        import socket
        socket.create_connection(("www.google.com", 443), timeout=5)
        print("   ✅ Can reach Google servers")
    except Exception as e:
        print(f"   ❌ Cannot reach Google servers: {e}")
        return False
    
    # Test 6: Test format conversion (OGG to WAV)
    print("\n6️⃣ Testing OGG to WAV conversion...")
    try:
        # Create a synthetic OGG file
        temp_ogg = "/tmp/test_audio.ogg"
        temp_wav = "/tmp/test_converted.wav"
        audio = AudioSegment.silent(duration=1000)
        audio.export(temp_ogg, format="ogg")
        
        # Try to load and convert
        audio = AudioSegment.from_file(temp_ogg)
        audio.export(temp_wav, format="wav")
        
        if os.path.exists(temp_wav):
            print(f"   ✅ OGG to WAV conversion working")
            os.remove(temp_ogg)
            os.remove(temp_wav)
        else:
            print("   ❌ Conversion failed")
            return False
    except Exception as e:
        print(f"   ❌ Format conversion failed: {e}")
        return False
    
    print("\n" + "="*60)
    print("✅ All diagnostic checks passed!")
    print("="*60)
    print("\n💡 If audio ingest is still failing, check:")
    print("   1. The Flask app logs for [INGEST] messages")
    print("   2. The uploaded audio file format and duration")
    print("   3. Network connectivity from the container to Google")
    print("   4. Google API rate limits or authentication issues")
    print("\n")
    return True

if __name__ == '__main__':
    success = test_audio_pipeline()
    sys.exit(0 if success else 1)
