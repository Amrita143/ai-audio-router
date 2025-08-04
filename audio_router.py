import pyaudio
import threading
import queue
import time
import numpy as np
from typing import Optional, Callable

class AudioRouter:
    """Routes audio data to virtual audio output devices."""
    
    def __init__(self, device_name: Optional[str] = None, 
                 sample_rate: int = 48000,  # VB-Cable compatible
                 channels: int = 2,          # VB-Cable stereo
                 chunk_size: int = 2048):    # Larger chunks for 48kHz
        self.pyaudio = pyaudio.PyAudio()
        self.device_index = self._find_device(device_name) if device_name else None
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.audio_queue = queue.Queue()
        self.is_running = False
        self.stream = None
        self.playback_thread = None
    
    def _find_device(self, device_name: str) -> Optional[int]:
        """Finds output device by name."""
        for i in range(self.pyaudio.get_device_count()):
            info = self.pyaudio.get_device_info_by_index(i)
            if device_name.lower() in info['name'].lower() and info['maxOutputChannels'] > 0:
                print(f"Found audio device: {info['name']} (Index: {i})")
                return i
        
        print(f"Warning: Device '{device_name}' not found. Using default.")
        return None
    
    def start(self):
        """Starts the audio routing thread."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Open audio stream with VB-Cable compatible format
        # Note: PyAudio doesn't have direct 24-bit support, we'll use 32-bit float
        # which VB-Cable can handle and provides good quality
        self.stream = self.pyaudio.open(
            format=pyaudio.paFloat32,  # Better compatibility than paInt24
            channels=self.channels,
            rate=self.sample_rate,
            output=True,
            output_device_index=self.device_index,
            frames_per_buffer=self.chunk_size
        )
        
        # Start playback thread
        self.playback_thread = threading.Thread(target=self._playback_loop)
        self.playback_thread.start()
        
        print(f"Audio router started: {self.sample_rate}Hz, {self.channels} channels")
    
    def stop(self):
        """Stops the audio routing thread."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Signal thread to stop
        self.audio_queue.put(None)
        
        # Wait for thread to finish
        if self.playback_thread:
            self.playback_thread.join()
        
        # Close stream
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        print("Audio router stopped.")
    
    def _playback_loop(self):
        """Main playback loop that processes audio queue."""
        while self.is_running:
            try:
                # Get audio data from queue (timeout prevents hanging)
                audio_data = self.audio_queue.get(timeout=0.1)
                
                if audio_data is None:  # Stop signal
                    break
                
                # Write to audio stream
                self.stream.write(audio_data)
                
            except queue.Empty:
                # No audio data available, continue
                continue
            except Exception as e:
                print(f"Playback error: {e}")
    
    def send_audio(self, audio_data: bytes):
        """Sends audio data to the output device."""
        if not self.is_running:
            print("Warning: Audio router not started.")
            return
        
        # Add to queue for playback
        self.audio_queue.put(audio_data)
    
    def send_audio_stream(self, audio_generator):
        """Sends audio from a generator/stream."""
        for chunk in audio_generator:
            if not self.is_running:
                break
            self.send_audio(chunk)
    
    def clear_queue(self):
        """Clears any pending audio in the queue."""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
    
    def get_latency(self) -> float:
        """Returns the current audio latency in seconds."""
        if self.stream:
            return self.stream.get_output_latency()
        return 0.0
    
    def __del__(self):
        """Cleanup resources."""
        self.stop()
        self.pyaudio.terminate()

# Utility function for finding virtual cable device
def find_virtual_cable_device() -> Optional[str]:
    """Automatically finds virtual audio cable device name."""
    p = pyaudio.PyAudio()
    
    virtual_keywords = ['cable input', 'cable output', 'vb-audio', 'blackhole', 'virtual']
    
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        device_name = info['name'].lower()
        
        if any(kw in device_name for kw in virtual_keywords) and info['maxOutputChannels'] > 0:
            print(f"Found virtual cable: {info['name']} (Index: {i})")
            p.terminate()
            return info['name']
    
    p.terminate()
    return None