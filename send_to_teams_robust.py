import pyaudio
import wave
import numpy as np
import sys
import os
import time
from scipy import signal

def send_audio_to_teams_robust(wav_file, device_index=18):
    """Send audio file to MS Teams through VB-Audio Virtual Cable with robust playback"""
    
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
        print(f"Original format: {orig_rate}Hz, {orig_channels} channels, {sample_width*8}-bit")
        print(f"Target format: {target_rate}Hz, {target_channels} channels")
        print(f"Duration: {total_frames/orig_rate:.2f} seconds")
        
        # Read all audio data at once
        print("Loading audio file...")
        all_frames = wf.readframes(total_frames)
        wf.close()
        
        # Convert to numpy array
        if sample_width == 1:
            dtype = np.uint8
            audio_data = np.frombuffer(all_frames, dtype=dtype).astype(np.float32)
            audio_data = (audio_data - 128) / 128.0  # Convert to -1 to 1 range
        elif sample_width == 2:
            dtype = np.int16
            audio_data = np.frombuffer(all_frames, dtype=dtype).astype(np.float32)
            audio_data = audio_data / 32768.0  # Convert to -1 to 1 range
        elif sample_width == 3:
            # Handle 24-bit audio
            audio_data = np.zeros(total_frames * orig_channels, dtype=np.float32)
            for i in range(0, len(all_frames), 3):
                if i + 2 < len(all_frames):
                    sample = int.from_bytes(all_frames[i:i+3], byteorder='little', signed=True)
                    audio_data[i//3] = sample / 8388608.0  # Convert to -1 to 1 range
        else:
            dtype = np.int32
            audio_data = np.frombuffer(all_frames, dtype=dtype).astype(np.float32)
            audio_data = audio_data / 2147483648.0  # Convert to -1 to 1 range
        
        # Handle channel conversion
        if orig_channels == 1 and target_channels == 2:
            # Mono to stereo: duplicate the channel
            print("Converting mono to stereo...")
            audio_data = np.repeat(audio_data, 2)
            orig_channels = 2
        elif orig_channels == 2 and target_channels == 1:
            # Stereo to mono: average the channels
            print("Converting stereo to mono...")
            audio_data = audio_data.reshape(-1, 2).mean(axis=1)
            orig_channels = 1
        
        # Resample if needed
        if orig_rate != target_rate:
            print(f"Resampling from {orig_rate}Hz to {target_rate}Hz...")
            new_length = int(len(audio_data) * target_rate / orig_rate / orig_channels)
            
            if orig_channels == 2:
                # Resample stereo
                left = audio_data[0::2]
                right = audio_data[1::2]
                left_resampled = signal.resample(left, new_length)
                right_resampled = signal.resample(right, new_length)
                audio_data = np.empty(new_length * 2, dtype=np.float32)
                audio_data[0::2] = left_resampled
                audio_data[1::2] = right_resampled
            else:
                audio_data = signal.resample(audio_data, new_length)
        
        # Convert back to int16 for playback
        audio_data = (audio_data * 32767).astype(np.int16)
        
        # CRITICAL: Use optimal buffer size for VB-Cable
        # According to the manual, VB-Cable works best with specific buffer sizes
        frames_per_buffer = 1024  # This is optimal for 48kHz according to VB-Cable docs
        
        print("Opening audio stream...")
        # Open stream with callback for more reliable playback
        stream_opened = False
        retry_count = 0
        
        while not stream_opened and retry_count < 3:
            try:
                stream = p.open(
                    format=pyaudio.paInt16,  # Always use 16-bit for compatibility
                    channels=target_channels,
                    rate=target_rate,
                    output=True,
                    output_device_index=device_index,
                    frames_per_buffer=frames_per_buffer,
                    stream_callback=None  # Use blocking mode for better control
                )
                stream_opened = True
            except Exception as e:
                retry_count += 1
                print(f"Failed to open stream (attempt {retry_count}): {e}")
                time.sleep(0.5)
        
        if not stream_opened:
            raise Exception("Failed to open audio stream after 3 attempts")
        
        # IMPORTANT: Pre-fill buffer with silence to establish connection
        print("Initializing audio stream...")
        silence = np.zeros(frames_per_buffer * target_channels, dtype=np.int16)
        for _ in range(10):  # Send 10 buffers of silence
            stream.write(silence.tobytes())
        
        # Small delay to ensure VB-Cable is ready
        time.sleep(0.2)
        
        # Play the audio
        print("Playing audio...")
        chunk_size = frames_per_buffer * target_channels
        total_chunks = len(audio_data) // chunk_size
        
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i+chunk_size]
            
            # IMPORTANT: Always send full buffers
            if len(chunk) < chunk_size:
                # Pad with silence
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode='constant')
            
            # Write the chunk
            stream.write(chunk.tobytes(), exception_on_underflow=False)
            
            # Progress indicator
            current_chunk = i // chunk_size
            if current_chunk % 10 == 0:  # Update every 10 chunks
                progress = min(100, (i / len(audio_data)) * 100)
                print(f"\rProgress: {progress:.1f}%", end='', flush=True)
        
        print("\nFinalizing playback...")
        
        # Send additional silence at the end to ensure all audio is heard
        for _ in range(20):  # Send 20 buffers of silence
            stream.write(silence.tobytes())
        
        # Wait for stream to finish
        time.sleep(1.0)
        
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
    send_audio_to_teams_robust(wav_file, device_index=18)