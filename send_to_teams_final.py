import pyaudio
import wave
import numpy as np
import sys
import os
import time
from scipy import signal

def send_audio_to_teams_final(wav_file, device_index=18):
    """Send audio file to MS Teams with anti-gating measures"""
    
    if not os.path.exists(wav_file):
        print(f"Error: {wav_file} not found!")
        return
    
    p = pyaudio.PyAudio()
    
    try:
        # Open the wave file
        wf = wave.open(wav_file, 'rb')
        
        # Get file properties
        orig_rate = wf.getframerate()
        orig_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        total_frames = wf.getnframes()
        duration = total_frames / orig_rate
        
        # Target format for VB-Cable
        target_rate = 48000
        target_channels = 2
        
        # Get device info
        device_info = p.get_device_info_by_index(device_index)
        print(f"Sending audio to: {device_info['name']}")
        print(f"File: {wav_file}")
        print(f"Duration: {duration:.2f} seconds")
        
        # Read all audio data
        print("Loading and processing audio...")
        all_frames = wf.readframes(total_frames)
        wf.close()
        
        # Convert to float32 for processing
        if sample_width == 2:
            audio_data = np.frombuffer(all_frames, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            # Handle other bit depths
            audio_data = np.frombuffer(all_frames, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Convert mono to stereo if needed
        if orig_channels == 1:
            audio_data = np.repeat(audio_data, 2)
            orig_channels = 2
        
        # Resample to 48kHz if needed
        if orig_rate != target_rate:
            print(f"Resampling from {orig_rate}Hz to {target_rate}Hz...")
            new_length = int(len(audio_data) * target_rate / orig_rate / orig_channels)
            
            left = audio_data[0::2]
            right = audio_data[1::2]
            left_resampled = signal.resample(left, new_length)
            right_resampled = signal.resample(right, new_length)
            
            audio_data = np.empty(new_length * 2, dtype=np.float32)
            audio_data[0::2] = left_resampled
            audio_data[1::2] = right_resampled
            
            duration = new_length / target_rate
        
        # IMPORTANT: Add a very low frequency pilot tone to prevent Teams from gating
        print("Adding anti-gating carrier signal...")
        t = np.linspace(0, duration, len(audio_data) // 2)
        
        # Create a 50Hz pilot tone at very low amplitude (barely audible)
        pilot_tone = np.sin(2 * np.pi * 50 * t) * 0.005  # Very quiet
        
        # Add pilot tone to both channels
        audio_data[0::2] += pilot_tone
        audio_data[1::2] += pilot_tone
        
        # Also boost the overall level slightly
        audio_data *= 1.2
        
        # Clip to prevent distortion
        audio_data = np.clip(audio_data, -1.0, 1.0)
        
        # Convert back to int16
        audio_data = (audio_data * 32767).astype(np.int16)
        
        # Open stream with optimal settings
        print("Opening audio stream...")
        stream = p.open(
            format=pyaudio.paInt16,
            channels=target_channels,
            rate=target_rate,
            output=True,
            output_device_index=device_index,
            frames_per_buffer=1024
        )
        
        # Pre-roll: Send a tone burst to "wake up" Teams
        print("Sending wake-up signal...")
        wake_duration = 0.5
        wake_samples = int(target_rate * wake_duration)
        t_wake = np.linspace(0, wake_duration, wake_samples)
        
        # Create a sweep from 200Hz to 800Hz
        wake_freq = 200 + 600 * t_wake / wake_duration
        wake_signal = np.sin(2 * np.pi * wake_freq * t_wake) * 0.1
        
        # Fade in/out
        fade_len = int(0.05 * target_rate)
        wake_signal[:fade_len] *= np.linspace(0, 1, fade_len)
        wake_signal[-fade_len:] *= np.linspace(1, 0, fade_len)
        
        # Make stereo and convert to int16
        wake_stereo = np.zeros(wake_samples * 2, dtype=np.int16)
        wake_stereo[0::2] = (wake_signal * 32767).astype(np.int16)
        wake_stereo[1::2] = (wake_signal * 32767).astype(np.int16)
        
        # Play wake-up signal
        stream.write(wake_stereo.tobytes())
        
        # Short pause
        time.sleep(0.2)
        
        # Play the main audio
        print("Playing main audio...")
        chunk_size = 1024 * target_channels
        total_chunks = len(audio_data) // chunk_size
        
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i+chunk_size]
            
            if len(chunk) < chunk_size:
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode='constant')
            
            stream.write(chunk.tobytes())
            
            # Progress
            if (i // chunk_size) % 50 == 0:
                progress = min(100, (i / len(audio_data)) * 100)
                print(f"\rProgress: {progress:.1f}%", end='', flush=True)
        
        print("\nFinalizing...")
        
        # Send trailing tone to ensure all audio is heard
        trail_duration = 1.0
        trail_samples = int(target_rate * trail_duration)
        trail_tone = np.sin(2 * np.pi * 50 * np.linspace(0, trail_duration, trail_samples)) * 0.01
        trail_stereo = np.zeros(trail_samples * 2, dtype=np.int16)
        trail_stereo[0::2] = (trail_tone * 32767).astype(np.int16)
        trail_stereo[1::2] = (trail_tone * 32767).astype(np.int16)
        
        stream.write(trail_stereo.tobytes())
        
        # Cleanup
        stream.stop_stream()
        stream.close()
        print("Playback completed!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        p.terminate()

if __name__ == "__main__":
    wav_file = sys.argv[1] if len(sys.argv) > 1 else "download.wav"
    
    print("=== MS Teams Audio Sender ===")
    print("\nIMPORTANT: Make sure in MS Teams:")
    print("1. Microphone is set to 'CABLE Output (VB-Audio Virtual Cable)'")
    print("2. Noise suppression is set to 'Low' or 'Off'")
    print("3. You're not muted in the Teams call")
    print("\nStarting in 3 seconds...\n")
    
    time.sleep(3)
    
    send_audio_to_teams_final(wav_file, device_index=18)