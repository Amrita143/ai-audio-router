import pyaudio
import wave
import numpy as np
import time

def diagnose_teams_audio(wav_file="download.wav"):
    """Diagnose why audio cuts off in MS Teams"""
    
    print("=== MS Teams Audio Diagnostic ===\n")
    
    # Step 1: Check file
    try:
        wf = wave.open(wav_file, 'rb')
        duration = wf.getnframes() / wf.getframerate()
        print(f"Audio file: {wav_file}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Format: {wf.getframerate()}Hz, {wf.getnchannels()} channels, {wf.getsampwidth()*8}-bit")
        
        # Read first second of audio
        first_second_frames = int(wf.getframerate() * 1.0)
        first_second_data = wf.readframes(first_second_frames)
        wf.close()
        
        # Check if audio starts with silence
        audio_array = np.frombuffer(first_second_data, dtype=np.int16)
        max_amplitude = np.max(np.abs(audio_array))
        print(f"First second max amplitude: {max_amplitude} (out of 32767)")
        
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    print("\n=== Testing different playback methods ===\n")
    
    p = pyaudio.PyAudio()
    
    # Find the CABLE Input device
    cable_device = None
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['name'] == "CABLE Input (VB-Audio Virtual Cable)" and info['defaultSampleRate'] == 48000:
            cable_device = i
            break
    
    if cable_device is None:
        print("ERROR: Could not find CABLE Input device at 48kHz")
        p.terminate()
        return
    
    print(f"Using device {cable_device}: CABLE Input (VB-Audio Virtual Cable)\n")
    
    # Test 1: Simple beep test
    print("Test 1: Playing 1-second beep...")
    sample_rate = 48000
    duration = 1.0
    frequency = 440
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    beep = (np.sin(2 * np.pi * frequency * t) * 0.3 * 32767).astype(np.int16)
    # Make stereo
    stereo_beep = np.zeros(len(beep) * 2, dtype=np.int16)
    stereo_beep[0::2] = beep
    stereo_beep[1::2] = beep
    
    try:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=2,
            rate=sample_rate,
            output=True,
            output_device_index=cable_device,
            frames_per_buffer=2048
        )
        
        # Send some silence first
        silence = np.zeros(2048 * 2, dtype=np.int16)
        for _ in range(5):
            stream.write(silence.tobytes())
        
        # Play beep
        stream.write(stereo_beep.tobytes())
        
        # Send silence after
        for _ in range(5):
            stream.write(silence.tobytes())
        
        stream.stop_stream()
        stream.close()
        print("Beep test completed - did you hear it in Teams?\n")
        
    except Exception as e:
        print(f"Beep test failed: {e}\n")
    
    time.sleep(2)
    
    # Test 2: Play with different buffer configurations
    print("Test 2: Testing different buffer sizes...")
    
    # Generate a spoken test pattern
    test_duration = 5.0
    t = np.linspace(0, test_duration, int(sample_rate * test_duration))
    
    # Create a pattern: beep-silence-beep-silence...
    test_pattern = np.zeros_like(t)
    for i in range(5):
        start = int(i * sample_rate)
        end = int((i + 0.5) * sample_rate)
        if end < len(test_pattern):
            test_pattern[start:end] = np.sin(2 * np.pi * (440 + i * 100) * t[start:end]) * 0.3
    
    test_audio = (test_pattern * 32767).astype(np.int16)
    # Make stereo
    stereo_test = np.zeros(len(test_audio) * 2, dtype=np.int16)
    stereo_test[0::2] = test_audio
    stereo_test[1::2] = test_audio
    
    for buffer_size in [512, 1024, 2048, 4096]:
        print(f"\nTesting buffer size: {buffer_size}")
        
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=2,
                rate=sample_rate,
                output=True,
                output_device_index=cable_device,
                frames_per_buffer=buffer_size
            )
            
            # Pre-fill with silence
            silence = np.zeros(buffer_size * 2, dtype=np.int16)
            for _ in range(10):
                stream.write(silence.tobytes())
            
            # Play test pattern
            chunk_size = buffer_size * 2
            for i in range(0, len(stereo_test), chunk_size):
                chunk = stereo_test[i:i+chunk_size]
                if len(chunk) < chunk_size:
                    chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode='constant')
                stream.write(chunk.tobytes())
            
            # Post-fill with silence
            for _ in range(10):
                stream.write(silence.tobytes())
            
            stream.stop_stream()
            stream.close()
            print(f"Buffer size {buffer_size} - completed")
            
        except Exception as e:
            print(f"Buffer size {buffer_size} - failed: {e}")
        
        time.sleep(1)
    
    p.terminate()
    
    print("\n=== Diagnostic Summary ===")
    print("1. If you heard the initial beep, VB-Cable connection is working")
    print("2. If you heard all 5 beeps in the pattern, audio streaming is stable")
    print("3. If audio cuts off, it may be due to:")
    print("   - MS Teams audio processing/gating")
    print("   - VB-Cable buffer underruns")
    print("   - Sample rate mismatch")
    print("\nRecommendations:")
    print("- Ensure MS Teams microphone is set to 'CABLE Output (VB-Audio Virtual Cable)'")
    print("- Check MS Teams audio settings for noise suppression/gating")
    print("- Try disabling 'Noise suppression' in Teams settings")

if __name__ == "__main__":
    diagnose_teams_audio()