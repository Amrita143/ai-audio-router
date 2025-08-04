import os
import struct
import wave
import io
import numpy as np
from typing import Optional, Generator, Tuple
from google import genai
from google.genai import types
import dotenv
import tempfile
from dotenv import load_dotenv
import pyaudio

# Load environment variables
try:
    load_dotenv()
except Exception as e:
    # Ignore .env loading errors
    pass

class GeminiTTS:
    """Handles text-to-speech conversion using Google's Gemini API with VB-Cable compatibility."""
    
    def __init__(self, api_key: Optional[str] = None, 
                 target_sample_rate: int = 48000, 
                 target_channels: int = 2,
                 target_bit_depth: int = 24):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.5-flash-preview-tts"
        self.voice_name = "Kore"  # Professional female voice
        
        # VB-Cable target format
        self.target_sample_rate = target_sample_rate  # 48000 Hz
        self.target_channels = target_channels        # 2 channels (stereo)
        self.target_bit_depth = target_bit_depth      # 24-bit
    
    def generate_speech(self, text: str) -> bytes:
        """Generates speech from text and returns VB-Cable compatible WAV audio data."""
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
            
            # Convert to VB-Cable compatible format
            vb_cable_audio = self._convert_to_vb_cable_format(audio_data)
            
            return vb_cable_audio
            
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
    
    def _convert_to_vb_cable_format(self, audio_data: bytes) -> bytes:
        """Converts Gemini audio output to VB-Cable compatible format using numpy."""
        try:
            # Ensure audio data has WAV header
            if audio_data[:4] != b"RIFF":
                audio_data = self._create_wav_header(audio_data) + audio_data
            
            # Create temporary input file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_input:
                temp_input.write(audio_data)
                temp_input.flush()
                
                # Read the WAV file
                with wave.open(temp_input.name, 'rb') as wf:
                    frames = wf.readframes(wf.getnframes())
                    sample_rate = wf.getframerate()
                    channels = wf.getnchannels()
                    sample_width = wf.getsampwidth()
                
                print(f"Original Gemini audio: {sample_rate}Hz, {channels} channels, {sample_width*8}-bit")
                
                # Convert audio data to numpy array
                if sample_width == 1:
                    dtype = np.uint8
                elif sample_width == 2:
                    dtype = np.int16
                else:
                    dtype = np.int32
                
                audio_array = np.frombuffer(frames, dtype=dtype)
                
                # Handle multi-channel to mono conversion if needed
                if channels > 1:
                    audio_array = audio_array.reshape(-1, channels)
                    audio_array = np.mean(audio_array, axis=1)
                
                # Resample to target sample rate if needed
                if sample_rate != self.target_sample_rate:
                    try:
                        from scipy import signal
                        num_samples = int(len(audio_array) * self.target_sample_rate / sample_rate)
                        audio_array = signal.resample(audio_array, num_samples)
                    except ImportError:
                        print("WARNING: scipy not installed. Audio resampling may not work properly.")
                        print("Install with: pip install scipy")
                        # Simple linear interpolation fallback
                        indices = np.linspace(0, len(audio_array) - 1, 
                                            int(len(audio_array) * self.target_sample_rate / sample_rate))
                        audio_array = np.interp(indices, np.arange(len(audio_array)), audio_array)
                
                # Convert to stereo (duplicate mono to both channels)
                if self.target_channels == 2:
                    audio_array = np.column_stack((audio_array, audio_array))
                
                # Normalize and convert to 24-bit
                if np.max(np.abs(audio_array)) > 0:
                    audio_array = (audio_array * (2**23 - 1) / np.max(np.abs(audio_array))).astype(np.int32)
                else:
                    audio_array = audio_array.astype(np.int32)
                
                # Create output WAV file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_output:
                    with wave.open(temp_output.name, 'wb') as wf:
                        wf.setnchannels(self.target_channels)
                        wf.setsampwidth(3)  # 24-bit
                        wf.setframerate(self.target_sample_rate)
                        
                        # Convert to 24-bit packed format
                        if self.target_channels == 2:
                            audio_24bit = bytearray()
                            for sample_pair in audio_array:
                                for sample in sample_pair:
                                    sample_bytes = struct.pack('<i', int(sample))[:3]
                                    audio_24bit.extend(sample_bytes)
                        else:
                            audio_24bit = bytearray()
                            for sample in audio_array:
                                sample_bytes = struct.pack('<i', int(sample))[:3]
                                audio_24bit.extend(sample_bytes)
                        
                        wf.writeframes(bytes(audio_24bit))
                    
                    # Read the converted data
                    with open(temp_output.name, 'rb') as f:
                        converted_data = f.read()
                
                # Clean up temporary files
                try:
                    os.unlink(temp_input.name)
                except:
                    pass
                try:
                    os.unlink(temp_output.name)
                except:
                    pass
                
                print(f"Converted to VB-Cable format: {self.target_sample_rate}Hz, {self.target_channels} channels, {self.target_bit_depth}-bit")
                
                return converted_data
                
        except Exception as e:
            print(f"Error converting to VB-Cable format: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to original format conversion
            if audio_data[:4] != b"RIFF":
                return self._create_wav_header(audio_data) + audio_data
            return audio_data
    
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
    
    def generate_message_audio(self, full_name: str, case_number: str, output_file: str = None) -> str:
        """Generate the specific message audio for the project requirements."""
        message_template = f"""This message is for {full_name}, this is Jessica with COUNTY Process Serving Division.
Your Case Number is {case_number}. Disclaimer: This message is generated by an AI system."""
        
        print(f"Generating AI audio message for {full_name}, Case: {case_number}")
        
        # Generate the speech
        audio_data = self.generate_speech(message_template)
        
        # Save to file
        if output_file is None:
            output_file = f"message_{full_name.replace(' ', '_')}_{case_number}.wav"
        
        with open(output_file, "wb") as f:
            f.write(audio_data)
        
        print(f"VB-Cable compatible audio saved to: {output_file}")
        print(f"Format: {self.target_sample_rate}Hz, {self.target_channels} channels, {self.target_bit_depth}-bit")
        
        return output_file

# Test function
if __name__ == "__main__":
    # Check for required dependencies
    try:
        import numpy as np
        from scipy import signal
    except ImportError as e:
        print("WARNING: Required dependencies missing:")
        print("Install with: pip install numpy scipy")
        print(f"Missing: {e}")
        exit(1)
    
    tts = GeminiTTS(api_key = "AIzaSyA2BTRMlCWbNjS1KmZ7upyQ4xY08Otu8mY")
    
    # Test VB-Cable compatible generation
    test_text = "Hello, this is a test of the VB-Cable compatible Gemini text to speech system."
    print(f"Generating VB-Cable compatible speech for: {test_text}")
    
    audio_data = tts.generate_speech(test_text)
    
    # Save to file
    with open("test_output_vb_cable.wav", "wb") as f:
        f.write(audio_data)
    
    print("VB-Cable compatible audio saved to test_output_vb_cable.wav")
    
    # Test message generation
    print("\nTesting message generation...")
    message_file = tts.generate_message_audio("John Doe", "12345")
    print(f"Message audio file created: {message_file}")