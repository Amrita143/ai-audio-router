import pyaudio
import wave
import numpy as np
import sys
import os
from scipy import signal

def resample_audio(audio_data, orig_rate, target_rate, channels):
    """Resample audio data to target sample rate"""
    if orig_rate == target_rate:
        return audio_data
    
    # Calculate resampling ratio
    ratio = target_rate / orig_rate
    
    # Calculate new length
    new_length = int(len(audio_data) * ratio)
    
    # Resample
    resampled = signal.resample(audio_data, new_length)
    
    return resampled.astype(audio_data.dtype)

def send_audio_to_teams(wav_file, device_index=18):
    """Send audio file to MS Teams through VB-Audio Virtual Cable with resampling"""
    
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
        
        # Target format for VB-Cable
        target_rate = 48000
        target_channels = 2
        
        # Get device info
        device_info = p.get_device_info_by_index(device_index)
        print(f"Sending audio to: {device_info['name']}")
        print(f"File: {wav_file}")
        print(f"Original format: {orig_rate}Hz, {orig_channels} channels")
        print(f"Target format: {target_rate}Hz, {target_channels} channels")
        
        # Read all audio data
        frames = wf.readframes(wf.getnframes())
        wf.close()
        
        # Convert to numpy array
        if sample_width == 2:
            dtype = np.int16
            max_val = 32767
        elif sample_width == 3:
            dtype = np.int32
            max_val = 8388607
        elif sample_width == 4:
            dtype = np.int32
            max_val = 2147483647
        else:
            dtype = np.int16
            max_val = 32767
        
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
            # For mono/stereo audio
            if target_channels == 2:
                # Process stereo
                left = audio_data[0::2]
                right = audio_data[1::2]
                left_resampled = resample_audio(left, orig_rate, target_rate, 1)
                right_resampled = resample_audio(right, orig_rate, target_rate, 1)
                audio_data = np.empty(len(left_resampled) * 2, dtype=dtype)
                audio_data[0::2] = left_resampled
                audio_data[1::2] = right_resampled
            else:
                audio_data = resample_audio(audio_data, orig_rate, target_rate, target_channels)
        
        # Open output stream
        stream = p.open(
            format=p.get_format_from_width(sample_width),
            channels=target_channels,
            rate=target_rate,
            output=True,
            output_device_index=device_index
        )
        
        # Play the audio
        print("Playing audio to MS Teams...")
        chunk_size = 4096
        
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i+chunk_size]
            stream.write(chunk.tobytes())
        
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
    # Default to download.wav if no argument provided
    wav_file = sys.argv[1] if len(sys.argv) > 1 else "download.wav"
    
    # Try different device indices for CABLE Input
    # Device 18 is CABLE Input at 48kHz with 2 channels
    send_audio_to_teams(wav_file, device_index=18)