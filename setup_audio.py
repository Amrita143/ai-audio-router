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