import pyaudio
import wave
import numpy as np
import sys
import os
import time
from scipy import signal

def send_audio_to_teams_optimized(wav_file, device_index=18):
    """Send audio file to MS Teams through VB-Audio Virtual Cable with optimized buffering"""
    
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
        
        # Target format for VB-Cable
        target_rate = 48000
        target_channels = 2
        
        # Get device info
        device_info = p.get_device_info_by_index(device_index)
        print(f"Sending audio to: {device_info['name']}")
        print(f"File: {wav_file}")
        print(f"Original format: {orig_rate}Hz, {orig_channels} channels")
        print(f"Target format: {target_rate}Hz, {target_channels} channels")
        print(f"Duration: {total_frames/orig_rate:.2f} seconds")
        
        # Read all audio data
        frames = wf.readframes(total_frames)
        wf.close()
        
        # Convert to numpy array
        if sample_width == 2:
            dtype = np.int16
        elif sample_width == 3:
            # For 24-bit, read as 32-bit and mask
            dtype = np.int32
        elif sample_width == 4:
            dtype = np.int32
        else:
            dtype = np.int16
        
        audio_data = np.frombuffer(frames, dtype=dtype)
        
        # Handle channel conversion
        if orig_channels == 1 and target_channels == 2:
            # Mono to stereo: duplicate the channel
            audio_data = np.repeat(audio_data, 2)
        elif orig_channels == 2 and target_channels == 1:
            # Stereo to mono: average the channels
            audio_data = audio_data.reshape(-1, 2).mean(axis=1).astype(dtype)
        
        # Resample if needed
        if orig_rate != target_rate:
            print(f"Resampling from {orig_rate}Hz to {target_rate}Hz...")
            if target_channels == 2:
                # Process stereo
                left = audio_data[0::2]
                right = audio_data[1::2]
                left_resampled = signal.resample(left, int(len(left) * target_rate / orig_rate))
                right_resampled = signal.resample(right, int(len(right) * target_rate / orig_rate))
                audio_data = np.empty(len(left_resampled) * 2, dtype=dtype)
                audio_data[0::2] = left_resampled.astype(dtype)
                audio_data[1::2] = right_resampled.astype(dtype)
            else:
                audio_data = signal.resample(audio_data, int(len(audio_data) * target_rate / orig_rate))
                audio_data = audio_data.astype(dtype)
        
        # IMPORTANT: Use larger buffer size for VB-Cable (as per manual recommendations)
        # VB-Cable works best with buffer sizes that are multiples of 512 or 1024
        frames_per_buffer = 2048  # Increased buffer size
        
        # Open output stream with larger buffer
        stream = p.open(
            format=p.get_format_from_width(sample_width),
            channels=target_channels,
            rate=target_rate,
            output=True,
            output_device_index=device_index,
            frames_per_buffer=frames_per_buffer
        )
        
        # Add small initial delay to ensure Teams is ready
        print("Starting playback...")
        time.sleep(0.1)
        
        # Play the audio with proper buffering
        total_samples = len(audio_data)
        samples_played = 0
        
        # Process in larger chunks to prevent underruns
        chunk_size = frames_per_buffer * target_channels
        
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i+chunk_size]
            
            # Pad the last chunk if necessary
            if len(chunk) < chunk_size:
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode='constant')
            
            stream.write(chunk.tobytes())
            
            # Show progress
            samples_played += len(chunk)
            progress = min(100, (samples_played / total_samples) * 100)
            print(f"\rProgress: {progress:.1f}%", end='', flush=True)
        
        print("\n")
        
        # Ensure all audio is played before closing
        time.sleep(0.5)  # Additional buffer time
        
        # Cleanup
        stream.stop_stream()
        stream.close()
        print("Playback completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        p.terminate()

if __name__ == "__main__":
    # Default to download.wav if no argument provided
    wav_file = sys.argv[1] if len(sys.argv) > 1 else "download.wav"
    
    # Use device 18: CABLE Input (VB-Audio Virtual Cable) at 48kHz
    send_audio_to_teams_optimized(wav_file, device_index=18)