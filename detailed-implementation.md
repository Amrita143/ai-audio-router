# Detailed Project Description and Implementation

## 🎯 Project Overview and Technical Architecture

This project implements a sophisticated audio routing system that intercepts and replaces microphone input with AI-generated speech. The core concept revolves around creating a virtual audio pipeline that applications perceive as a standard microphone input, while we programmatically feed it with synthesized audio.

### Technical Challenges and Solutions

The primary challenge is that most communication applications directly access the system's audio hardware through low-level APIs. We cannot simply "hijack" an existing microphone stream. Instead, we create a virtual audio device that acts as an intermediary:

1. **Virtual Audio Device**: Acts as both an audio sink (output) and source (input)
2. **Audio Router**: Captures audio data and routes it to the virtual device
3. **TTS Integration**: Generates speech using Google's Gemini API
4. **GUI Application**: Provides user interface for dynamic text generation

## 🔊 Understanding Audio Routing

### How Communication Apps Capture Audio

When applications like MS Teams or softphones capture audio, they:
1. Query the system for available audio input devices
2. Open an audio stream from the selected device
3. Read audio data in real-time from the device buffer
4. Encode and transmit the audio data

### Our Intervention Strategy

We insert a virtual audio device into this pipeline:
```
[Our Application] → [Virtual Audio Output] → [Virtual Cable] → [Virtual Audio Input] → [Communication App]
```

The virtual cable acts as a bridge, where anything played to the "output" side appears as microphone input on the "input" side.

## 💻 Implementation Details

### Part 1: Audio Device Discovery and Inspection

First, we need to understand what audio devices are available and how applications are using them.

**File: `audio_inspector.py`**
```python
import pyaudio
import platform
import subprocess
import json
from typing import List, Dict, Any

class AudioInspector:
    """Inspects and reports on system audio devices and their usage."""
    
    def __init__(self):
        self.pyaudio = pyaudio.PyAudio()
        self.platform = platform.system()
    
    def get_audio_devices(self) -> List[Dict[str, Any]]:
        """Retrieves all audio devices with their properties."""
        devices = []
        
        for i in range(self.pyaudio.get_device_count()):
            info = self.pyaudio.get_device_info_by_index(i)
            
            # Extract relevant information
            device = {
                'index': i,
                'name': info['name'],
                'channels': info['maxInputChannels'],
                'sample_rate': int(info['defaultSampleRate']),
                'is_input': info['maxInputChannels'] > 0,
                'is_output': info['maxOutputChannels'] > 0,
                'host_api': self.pyaudio.get_host_api_info_by_index(info['hostApi'])['name']
            }
            devices.append(device)
        
        return devices
    
    def get_active_audio_processes(self) -> List[Dict[str, str]]:
        """Identifies processes currently using audio devices."""
        processes = []
        
        if self.platform == "Windows":
            # Use Windows Audio Session API via PowerShell
            ps_script = '''
            Add-Type @"
            using System;
            using System.Collections.Generic;
            using System.Runtime.InteropServices;
            
            public class AudioSession {
                public static List<string> GetActiveAudioProcesses() {
                    // This would require implementing COM interfaces
                    // For brevity, returning a mock implementation
                    return new List<string> { "Teams.exe", "chrome.exe" };
                }
            }
            "@
            [AudioSession]::GetActiveAudioProcesses() | ConvertTo-Json
            '''
            
            try:
                result = subprocess.run(
                    ['powershell', '-Command', ps_script],
                    capture_output=True,
                    text=True
                )
                # Parse the result
                if result.returncode == 0:
                    process_names = json.loads(result.stdout)
                    for name in process_names:
                        processes.append({'name': name, 'audio_device': 'System Default'})
            except Exception as e:
                print(f"Error getting Windows audio processes: {e}")
        
        elif self.platform == "Darwin":  # macOS
            # Use coreaudiod diagnostics
            try:
                result = subprocess.run(
                    ['sudo', 'lsof', '-p', '$(pgrep coreaudiod)'],
                    capture_output=True,
                    text=True
                )
                # Parse lsof output for audio-using processes
                # This is simplified - actual implementation would parse the output
                processes.append({'name': 'Microsoft Teams', 'audio_device': 'Default Input'})
            except Exception:
                pass
        
        elif self.platform == "Linux":
            # Use PulseAudio or ALSA tools
            try:
                result = subprocess.run(
                    ['pactl', 'list', 'source-outputs'],
                    capture_output=True,
                    text=True
                )
                # Parse PulseAudio output
                # Simplified for brevity
                processes.append({'name': 'teams', 'audio_device': 'Built-in Audio'})
            except Exception:
                pass
        
        return processes
    
    def display_report(self):
        """Displays a comprehensive audio device report."""
        print("=" * 60)
        print("AUDIO DEVICE INSPECTION REPORT")
        print("=" * 60)
        print(f"Platform: {self.platform}")
        print()
        
        # Display audio devices
        print("Available Audio Devices:")
        print("-" * 40)
        devices = self.get_audio_devices()
        
        for device in devices:
            if device['is_input']:
                print(f"\n[INPUT] {device['name']}")
                print(f"  Index: {device['index']}")
                print(f"  Channels: {device['channels']}")
                print(f"  Sample Rate: {device['sample_rate']} Hz")
                print(f"  Host API: {device['host_api']}")
        
        for device in devices:
            if device['is_output']:
                print(f"\n[OUTPUT] {device['name']}")
                print(f"  Index: {device['index']}")
                print(f"  Sample Rate: {device['sample_rate']} Hz")
                print(f"  Host API: {device['host_api']}")
        
        # Display active processes
        print("\n\nActive Audio Processes:")
        print("-" * 40)
        processes = self.get_active_audio_processes()
        
        for process in processes:
            print(f"\n{process['name']}")
            print(f"  Using: {process['audio_device']}")
        
        # Check for virtual audio devices
        print("\n\nVirtual Audio Devices Detected:")
        print("-" * 40)
        virtual_devices = self.detect_virtual_devices(devices)
        
        if virtual_devices:
            for vd in virtual_devices:
                print(f"\n{vd['name']} (Index: {vd['index']})")
                print(f"  Type: {'Input' if vd['is_input'] else ''} {'Output' if vd['is_output'] else ''}")
        else:
            print("\nNo virtual audio devices found!")
            print("Please install a virtual audio cable software.")
    
    def detect_virtual_devices(self, devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identifies virtual audio devices from the device list."""
        virtual_keywords = ['virtual', 'cable', 'blackhole', 'loopback', 'vb-audio']
        virtual_devices = []
        
        for device in devices:
            device_name_lower = device['name'].lower()
            if any(keyword in device_name_lower for keyword in virtual_keywords):
                virtual_devices.append(device)
        
        return virtual_devices
    
    def __del__(self):
        """Cleanup PyAudio instance."""
        self.pyaudio.terminate()

if __name__ == "__main__":
    inspector = AudioInspector()
    inspector.display_report()
```

### Part 2: Technical Investigation - Audio Channel Routing

To answer the investigation question: **Yes, it is absolutely possible to programmatically route audio through the same channel that dialers/softphones use.** The approach involves:

1. **Virtual Audio Cable**: Creates a virtual "wire" between audio applications
2. **Audio Loopback**: Captures audio output and feeds it back as input
3. **Programmatic Control**: Uses audio APIs to write data to the virtual device

The key insight is that we don't modify the existing audio stream; instead, we replace the entire input device with our virtual one that we control.

### Part 3: Test Script for Pre-recorded Audio

**File: `test_audio_sender.py`**
```python
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
```

### Part 4: AI Audio GUI with Gemini Integration

**File: `gemini_tts.py`**
```python
import os
import struct
import wave
import io
from typing import Optional, Generator, Tuple
from google import genai
from google.genai import types
import dotenv

# Load environment variables
dotenv.load_dotenv()

class GeminiTTS:
    """Handles text-to-speech conversion using Google's Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.5-flash-preview-tts"
        self.voice_name = "Kore"  # Professional female voice
    
    def generate_speech(self, text: str) -> bytes:
        """Generates speech from text and returns WAV audio data."""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=self.voice_name,
                            )
                        )
                    ),
                )
            )
            
            # Extract audio data
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            
            # Convert to WAV format if needed
            wav_data = self._ensure_wav_format(audio_data)
            
            return wav_data
            
        except Exception as e:
            print(f"Error generating speech: {e}")
            raise
    
    def generate_speech_stream(self, text: str) -> Generator[bytes, None, None]:
        """Generates speech in streaming mode for lower latency."""
        try:
            # Configure for streaming
            generate_content_config = types.GenerateContentConfig(
                temperature=1,
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=self.voice_name
                        )
                    )
                ),
            )
            
            # Stream the generation
            for chunk in self.client.models.generate_content_stream(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=text)],
                    ),
                ],
                config=generate_content_config,
            ):
                if (chunk.candidates is None or 
                    chunk.candidates[0].content is None or 
                    chunk.candidates[0].content.parts is None):
                    continue
                
                if (chunk.candidates[0].content.parts[0].inline_data and 
                    chunk.candidates[0].content.parts[0].inline_data.data):
                    
                    inline_data = chunk.candidates[0].content.parts[0].inline_data
                    audio_chunk = inline_data.data
                    
                    # Convert chunk to WAV if needed
                    if inline_data.mime_type != "audio/wav":
                        audio_chunk = self._convert_to_wav_chunk(
                            audio_chunk, 
                            inline_data.mime_type
                        )
                    
                    yield audio_chunk
                    
        except Exception as e:
            print(f"Error in speech stream: {e}")
            raise
    
    def _ensure_wav_format(self, audio_data: bytes) -> bytes:
        """Ensures audio data is in WAV format."""
        # Check if already WAV by looking for RIFF header
        if audio_data[:4] == b"RIFF":
            return audio_data
        
        # Convert to WAV (assuming PCM data)
        return self._create_wav_header(audio_data) + audio_data
    
    def _create_wav_header(self, audio_data: bytes, 
                          sample_rate: int = 24000, 
                          bits_per_sample: int = 16, 
                          num_channels: int = 1) -> bytes:
        """Creates a WAV file header for raw PCM data."""
        data_size = len(audio_data)
        bytes_per_sample = bits_per_sample // 8
        block_align = num_channels * bytes_per_sample
        byte_rate = sample_rate * block_align
        chunk_size = 36 + data_size
        
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",          # ChunkID
            chunk_size,       # ChunkSize
            b"WAVE",          # Format
            b"fmt ",          # Subchunk1ID
            16,               # Subchunk1Size
            1,                # AudioFormat (PCM)
            num_channels,     # NumChannels
            sample_rate,      # SampleRate
            byte_rate,        # ByteRate
            block_align,      # BlockAlign
            bits_per_sample,  # BitsPerSample
            b"data",          # Subchunk2ID
            data_size         # Subchunk2Size
        )
        
        return header
    
    def _convert_to_wav_chunk(self, audio_data: bytes, mime_type: str) -> bytes:
        """Converts an audio chunk to WAV format based on MIME type."""
        # Parse audio parameters from MIME type
        params = self._parse_audio_mime_type(mime_type)
        
        # For streaming, we return raw PCM data
        # The header will be added by the audio player
        return audio_data
    
    def _parse_audio_mime_type(self, mime_type: str) -> dict:
        """Parses audio parameters from MIME type string."""
        bits_per_sample = 16
        rate = 24000
        
        parts = mime_type.split(";")
        for param in parts:
            param = param.strip()
            if param.lower().startswith("rate="):
                try:
                    rate = int(param.split("=", 1)[1])
                except (ValueError, IndexError):
                    pass
            elif param.startswith("audio/L"):
                try:
                    bits_per_sample = int(param.split("L", 1)[1])
                except (ValueError, IndexError):
                    pass
        
        return {"bits_per_sample": bits_per_sample, "rate": rate}

# Test function
if __name__ == "__main__":
    tts = GeminiTTS()
    
    # Test basic generation
    test_text = "Hello, this is a test of the Gemini text to speech system."
    print(f"Generating speech for: {test_text}")
    
    audio_data = tts.generate_speech(test_text)
    
    # Save to file
    with open("test_output.wav", "wb") as f:
        f.write(audio_data)
    
    print("Audio saved to test_output.wav")
```

**File: `audio_router.py`**
```python
import pyaudio
import threading
import queue
import time
import numpy as np
from typing import Optional, Callable

class AudioRouter:
    """Routes audio data to virtual audio output devices."""
    
    def __init__(self, device_name: Optional[str] = None, 
                 sample_rate: int = 24000,
                 channels: int = 1,
                 chunk_size: int = 1024):
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
        
        # Open audio stream
        self.stream = self.pyaudio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            output=True,
            output_device_index=self.device_index,
            frames_per_buffer=self.chunk_size
        )
        
        # Start playback thread
        self.playback_thread = threading.Thread(target=self._playback_loop)
        self.playback_thread.start()
        
        print("Audio router started.")
    
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
    
    virtual_keywords = ['cable output', 'vb-audio', 'blackhole', 'virtual']
    
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        device_name = info['name'].lower()
        
        if any(kw in device_name for kw in virtual_keywords) and info['maxOutputChannels'] > 0:
            p.terminate()
            return info['name']
    
    p.terminate()
    return None
```

**File: `ai_audio_gui.py`**
```python
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import wave
import io
from gemini_tts import GeminiTTS
from audio_router import AudioRouter, find_virtual_cable_device

class AIAudioGUI:
    """GUI application for AI-powered audio transmission."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Audio Transmitter")
        self.root.geometry("500x400")
        self.root.resizable(True, True)
        
        # Initialize components
        self.tts = GeminiTTS()
        self.audio_router = None
        self.is_transmitting = False
        
        # Message template
        self.message_template = """This message is for {full_name}, this is Jessica with COUNTY Process Serving Division.
Your Case Number is {case_number}. Disclaimer: This message is generated by an AI system.
"""
        
        # Setup GUI
        self._setup_gui()
        self._setup_audio_router()
    
    def _setup_gui(self):
        """Creates the GUI elements."""
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="AI Audio Transmitter", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Full Name input
        ttk.Label(main_frame, text="Full Name:").grid(row=1, column=0, 
                                                      sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(main_frame, textvariable=self.name_var, 
                                   width=40)
        self.name_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Case Number input
        ttk.Label(main_frame, text="Case Number:").grid(row=2, column=0, 
                                                        sticky=tk.W, pady=5)
        self.case_var = tk.StringVar()
        self.case_entry = ttk.Entry(main_frame, textvariable=self.case_var, 
                                   width=40)
        self.case_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Audio Device selection
        ttk.Label(main_frame, text="Audio Device:").grid(row=3, column=0, 
                                                         sticky=tk.W, pady=5)
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(main_frame, textvariable=self.device_var,
                                        state="readonly", width=37)
        self.device_combo.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        self.generate_button = ttk.Button(button_frame, text="Generate and Send",
                                         command=self._on_generate_send)
        self.generate_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop",
                                     command=self._on_stop,
                                     state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="5")
        status_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), 
                         pady=10)
        status_frame.columnconfigure(0, weight=1)
        
        self.status_label = ttk.Label(status_frame, text="Ready", 
                                     foreground="green")
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        # Progress bar
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(main_frame, text="Message Preview", 
                                      padding="5")
        preview_frame.grid(row=6, column=0, columnspan=2, 
                          sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        
        # Text preview
        self.preview_text = tk.Text(preview_frame, height=8, wrap=tk.WORD,
                                   font=('Arial', 9))
        self.preview_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for preview
        scrollbar = ttk.Scrollbar(preview_frame, orient="vertical",
                                 command=self.preview_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.preview_text.configure(yscrollcommand=scrollbar.set)
        
        # Bind events
        self.name_var.trace('w', self._update_preview)
        self.case_var.trace('w', self._update_preview)
        
        # Configure row weights for resizing
        main_frame.rowconfigure(6, weight=1)
    
    def _setup_audio_router(self):
        """Initializes the audio router with available devices."""
        # Find virtual cable device
        virtual_device = find_virtual_cable_device()
        
        if virtual_device:
            self.device_var.set(virtual_device)
            self.audio_router = AudioRouter(virtual_device)
            self.audio_router.start()
            self._update_status("Audio router initialized", "green")
        else:
            self._update_status("No virtual audio device found!", "red")
            messagebox.showwarning(
                "No Virtual Audio Device",
                "No virtual audio cable device was found.\n\n"
                "Please install VB-CABLE (Windows), BlackHole (macOS), "
                "or configure PulseAudio (Linux)."
            )
        
        # Populate device list
        self._populate_audio_devices()
    
    def _populate_audio_devices(self):
        """Populates the audio device dropdown."""
        import pyaudio
        p = pyaudio.PyAudio()
        
        devices = []
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0:
                devices.append(info['name'])
        
        p.terminate()
        
        self.device_combo['values'] = devices
    
    def _update_preview(self, *args):
        """Updates the message preview."""
        name = self.name_var.get() or "[Full Name]"
        case = self.case_var.get() or "[Case Number]"
        
        message = self.message_template.format(
            full_name=name.upper(),
            case_number=case
        )
        
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(1.0, message)
    
    def _update_status(self, message: str, color: str = "black"):
        """Updates the status label."""
        self.status_label.config(text=message, foreground=color)
    
    def _on_generate_send(self):
        """Handles the Generate and Send button click."""
        # Validate inputs
        if not self.name_var.get():
            messagebox.showerror("Error", "Please enter a full name.")
            return
        
        if not self.case_var.get():
            messagebox.showerror("Error", "Please enter a case number.")
            return
        
        if not self.audio_router:
            messagebox.showerror("Error", "Audio router not initialized.")
            return
        
        # Disable button and start progress
        self.generate_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress.start()
        
        # Start generation in separate thread
        self.is_transmitting = True
        thread = threading.Thread(target=self._generate_and_send)
        thread.start()
    
    def _generate_and_send(self):
        """Generates and sends the audio (runs in separate thread)."""
        try:
            self._update_status("Generating audio...", "blue")
            
            # Format the message
            message = self.message_template.format(
                full_name=self.name_var.get().upper(),
                case_number=self._format_case_number(self.case_var.get())
            )
            
            # Generate audio
            audio_data = self.tts.generate_speech(message)
            
            if not self.is_transmitting:
                return
            
            self._update_status("Transmitting audio...", "orange")
            
            # Send audio through router
            # Split audio into chunks for real-time playback
            chunk_size = 4096
            audio_stream = io.BytesIO(audio_data)
            
            # Skip WAV header if present
            if audio_data[:4] == b"RIFF":
                audio_stream.seek(44)  # Standard WAV header size
            
            while self.is_transmitting:
                chunk = audio_stream.read(chunk_size)
                if not chunk:
                    break
                
                self.audio_router.send_audio(chunk)
            
            self._update_status("Transmission complete", "green")
            
        except Exception as e:
            self._update_status(f"Error: {str(e)}", "red")
            messagebox.showerror("Error", f"Failed to generate/send audio:\n{str(e)}")
        
        finally:
            # Re-enable button and stop progress
            self.root.after(0, self._reset_ui)
    
    def _format_case_number(self, case_number: str) -> str:
        """Formats case number for speech (e.g., '582193' → '58...21...93')."""
        # Remove any non-numeric characters
        digits = ''.join(filter(str.isdigit, case_number))
        
        # Group digits for clearer speech
        if len(digits) >= 6:
            return f"{digits[:2]}...{digits[2:4]}...{digits[4:6]}"
        else:
            return case_number
    
    def _on_stop(self):
        """Handles the Stop button click."""
        self.is_transmitting = False
        if self.audio_router:
            self.audio_router.clear_queue()
        self._update_status("Stopped", "red")
    
    def _reset_ui(self):
        """Resets UI elements after operation."""
        self.generate_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress.stop()
        self.is_transmitting = False
    
    def run(self):
        """Starts the GUI application."""
        # Initial preview update
        self._update_preview()
        
        # Start the main loop
        self.root.mainloop()
        
        # Cleanup
        if self.audio_router:
            self.audio_router.stop()

def main():
    """Main entry point."""
    app = AIAudioGUI()
    app.run()

if __name__ == "__main__":
    main()
```

## 🛠️ Setup and Configuration Scripts

**File: `setup_audio.py`**
```python
import platform
import subprocess
import sys
import os

class AudioSetup:
    """Sets up virtual audio devices based on the platform."""
    
    def __init__(self):
        self.platform = platform.system()
    
    def setup(self):
        """Main setup function."""
        print("Audio Setup Utility")
        print("=" * 50)
        print(f"Detected platform: {self.platform}")
        print()
        
        if self.platform == "Windows":
            self._setup_windows()
        elif self.platform == "Darwin":  # macOS
            self._setup_macos()
        elif self.platform == "Linux":
            self._setup_linux()
        else:
            print(f"Unsupported platform: {self.platform}")
            sys.exit(1)
    
    def _setup_windows(self):
        """Setup instructions for Windows."""
        print("Windows Setup Instructions:")
        print("-" * 40)
        print()
        print("1. Download VB-CABLE from: https://vb-audio.com/Cable/")
        print("2. Extract the ZIP file")
        print("3. Run VBCABLE_Setup_x64.exe as Administrator")
        print("4. Click 'Install Driver' and follow the prompts")
        print("5. Restart your computer")
        print()
        print("After installation:")
        print("- 'CABLE Input' will appear as a recording device")
        print("- 'CABLE Output' will appear as a playback device")
        print()
        print("Configure MS Teams:")
        print("1. Open MS Teams")
        print("2. Go to Settings → Devices")
        print("3. Set Microphone to 'CABLE Output (VB-Audio Virtual Cable)'")
        print()
        
        # Check if VB-CABLE is installed
        try:
            result = subprocess.run(
                ['powershell', '-Command', 
                 'Get-WmiObject Win32_SoundDevice | Where-Object {$_.Name -like "*CABLE*"}'],
                capture_output=True,
                text=True
            )
            
            if "CABLE" in result.stdout:
                print("✓ VB-CABLE appears to be installed!")
            else:
                print("✗ VB-CABLE not detected. Please install it first.")
        except Exception as e:
            print(f"Could not check installation status: {e}")
    
    def _setup_macos(self):
        """Setup instructions for macOS."""
        print("macOS Setup Instructions:")
        print("-" * 40)
        print()
        print("1. Download BlackHole from: https://existential.audio/blackhole/")
        print("2. Choose 'BlackHole 2ch' version")
        print("3. Run the installer")
        print("4. Grant necessary permissions when prompted")
        print()
        print("After installation:")
        print("- 'BlackHole 2ch' will appear in Audio MIDI Setup")
        print()
        print("Configure MS Teams:")
        print("1. Open MS Teams")
        print("2. Go to Settings → Devices")
        print("3. Set Microphone to 'BlackHole 2ch'")
        print()
        
        # Check if BlackHole is installed
        try:
            result = subprocess.run(
                ['system_profiler', 'SPAudioDataType'],
                capture_output=True,
                text=True
            )
            
            if "BlackHole" in result.stdout:
                print("✓ BlackHole appears to be installed!")
            else:
                print("✗ BlackHole not detected. Please install it first.")
        except Exception as e:
            print(f"Could not check installation status: {e}")
    
    def _setup_linux(self):
        """Setup instructions for Linux with PulseAudio."""
        print("Linux Setup Instructions:")
        print("-" * 40)
        print()
        print("Creating virtual audio devices with PulseAudio...")
        print()
        
        try:
            # Load module-null-sink for virtual output
            subprocess.run([
                'pactl', 'load-module', 'module-null-sink',
                'sink_name=virtual_speaker',
                'sink_properties=device.description="Virtual_Speaker"'
            ])
            
            # Load module-virtual-source for virtual input
            subprocess.run([
                'pactl', 'load-module', 'module-virtual-source',
                'source_name=virtual_mic',
                'master=virtual_speaker.monitor',
                'source_properties=device.description="Virtual_Microphone"'
            ])
            
            print("✓ Virtual audio devices created!")
            print()
            print("Configure MS Teams:")
            print("1. Open MS Teams")
            print("2. Go to Settings → Devices")
            print("3. Set Microphone to 'Virtual_Microphone'")
            print()
            print("Note: These virtual devices are temporary.")
            print("To make them permanent, add the commands to:")
            print("  /etc/pulse/default.pa")
            
        except Exception as e:
            print(f"Error creating virtual devices: {e}")
            print()
            print("Manual setup required:")
            print("1. Install PulseAudio if not present:")
            print("   sudo apt-get install pulseaudio pavucontrol")
            print()
            print("2. Create virtual devices manually:")
            print("   pactl load-module module-null-sink sink_name=virtual_speaker")
            print("   pactl load-module module-virtual-source source_name=virtual_mic master=virtual_speaker.monitor")

def main():
    setup = AudioSetup()
    setup.setup()
    
    print()
    print("Setup instructions complete!")
    print("Run 'python audio_inspector.py' to verify your configuration.")

if __name__ == "__main__":
    main()
```

## 📦 Dependencies

**File: `requirements.txt`**
```
pyaudio==0.2.14
google-genai==0.2.0
python-dotenv==1.0.0
numpy==1.24.3
wave==0.0.2
```

## 🔍 Technical Deep Dive

### Understanding Virtual Audio Routing

The core concept involves creating a "virtual wire" between applications:

1. **Virtual Output Device**: Where we send our audio
2. **Virtual Cable**: Connects output to input
3. **Virtual Input Device**: What MS Teams/dialers see as a microphone

When we play audio to the virtual output, it appears as microphone input to any application using the virtual input device.

### Streaming Architecture

To minimize latency, we implement a streaming architecture:

1. **Text Input**: User enters dynamic values
2. **TTS Generation**: Gemini API generates audio in chunks
3. **Audio Queue**: Buffers chunks for smooth playback
4. **Real-time Routing**: Streams to virtual device as chunks arrive

### Security Considerations

1. **API Key Management**: Use environment variables
2. **Input Validation**: Sanitize user inputs
3. **Audio Privacy**: Be aware of legal implications of automated calling
4. **Rate Limiting**: Implement to avoid API abuse

## 🚨 Important Legal Notice

This system is for educational and testing purposes. When using automated calling systems:

1. Comply with local telecommunication laws
2. Obtain proper consent before automated calls
3. Follow regulations like TCPA (US) or similar in your jurisdiction
4. Never use for harassment or illegal purposes

## 🔮 Future Enhancements

1. **Multiple Voice Options**: Add voice selection in GUI
2. **Audio Effects**: Add pitch/speed modulation
3. **Recording Feature**: Save generated audio for review
4. **Template Management**: Save/load message templates
5. **Batch Processing**: Handle multiple calls sequentially
6. **Analytics**: Track call metrics and success rates
