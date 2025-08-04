import pyaudio
import wave
import threading
import time
import numpy as np
from typing import Optional

class AudioSender:
    """Sends audio files through a specified audio output device."""
    
    def __init__(self, device_name: Optional[str] = None):
        self.pyaudio = pyaudio.PyAudio()
        self.device_index = self._find_device(device_name) if device_name else None
        self.is_playing = False
        self.playback_thread = None
    
    def _find_device(self, device_name: str) -> Optional[int]:
        """Finds the device index by name."""
        for i in range(self.pyaudio.get_device_count()):
            info = self.pyaudio.get_device_info_by_index(i)
            if device_name.lower() in info['name'].lower():
                return i
        return None
    
    def play_audio_file(self, filename: str, device_index: Optional[int] = None):
        """Plays an audio file through the specified device."""
        if device_index is None:
            device_index = self.device_index
        
        try:
            # Open the wave file
            wf = wave.open(filename, 'rb')
            
            # Open output stream
            stream = self.pyaudio.open(
                format=self.pyaudio.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True,
                output_device_index=device_index
            )
            
            # Read and play audio data
            chunk_size = 1024
            data = wf.readframes(chunk_size)
            
            self.is_playing = True
            print(f"Playing {filename}...")
            
            while data and self.is_playing:
                stream.write(data)
                data = wf.readframes(chunk_size)
            
            # Cleanup
            stream.stop_stream()
            stream.close()
            wf.close()
            
            print("Playback completed.")
            
        except Exception as e:
            print(f"Error playing audio: {e}")
    
    def play_async(self, filename: str):
        """Plays audio file asynchronously."""
        self.playback_thread = threading.Thread(
            target=self.play_audio_file,
            args=(filename,)
        )
        self.playback_thread.start()
    
    def stop(self):
        """Stops the current playback."""
        self.is_playing = False
        if self.playback_thread:
            self.playback_thread.join()
    
    def list_output_devices(self):
        """Lists all available output devices."""
        print("\nAvailable Output Devices:")
        print("-" * 40)
        
        for i in range(self.pyaudio.get_device_count()):
            info = self.pyaudio.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0:
                print(f"{i}: {info['name']} ({info['maxOutputChannels']} channels)")
        
        # Highlight virtual devices
        print("\nRecommended Virtual Devices:")
        virtual_keywords = ['cable', 'virtual', 'blackhole']
        
        for i in range(self.pyaudio.get_device_count()):
            info = self.pyaudio.get_device_info_by_index(i)
            if any(kw in info['name'].lower() for kw in virtual_keywords):
                print(f"  → {i}: {info['name']}")
    
    def __del__(self):
        """Cleanup PyAudio instance."""
        self.pyaudio.terminate()

def main():
    """Main function to test audio sending."""
    print("Audio Sender Test Script")
    print("=" * 50)
    
    sender = AudioSender()
    
    # List available devices
    sender.list_output_devices()
    
    # Select device
    print("\nSelect output device index (or press Enter for default): ", end='')
    device_input = input().strip()
    
    if device_input:
        try:
            device_index = int(device_input)
            sender.device_index = device_index
        except ValueError:
            print("Invalid device index. Using default.")
    
    # Wait for user command
    print("\nReady to send audio.")
    print("Commands:")
    print("  'Start' - Begin sending test.mp3")
    print("  'Stop'  - Stop current playback")
    print("  'Exit'  - Quit the program")
    print()
    
    while True:
        command = input("Enter command: ").strip().lower()
        
        if command == 'start':
            sender.play_async('test.mp3')
        elif command == 'stop':
            sender.stop()
        elif command == 'exit':
            sender.stop()
            break
        else:
            print("Unknown command. Try 'Start', 'Stop', or 'Exit'.")
    
    print("\nGoodbye!")

if __name__ == "__main__":
    main()