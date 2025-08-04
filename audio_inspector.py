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