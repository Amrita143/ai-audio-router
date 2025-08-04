# AI Audio Router for Communication Systems

This project enables routing AI-generated audio (using Google's Gemini Text-to-Speech) through your system's audio input channels, allowing the synthesized speech to be transmitted through applications like MS Teams, dialers, or other calling systems.

## 🎯 Project Overview

The system creates a virtual audio pipeline that:
- Captures and routes pre-recorded or AI-generated audio through virtual microphone inputs
- Integrates with Google's Gemini TTS for dynamic speech synthesis
- Provides a GUI for real-time text-to-speech generation with variable substitution
- Streams audio with minimal latency to communication applications

## 📋 Prerequisites

### System Requirements
- Python 3.8 or higher
- pip (Python package manager)
- Virtual Audio Cable software (platform-specific, see below)

### Platform-Specific Virtual Audio Setup

#### Windows
1. Download and install [VB-CABLE Virtual Audio Device](https://vb-audio.com/Cable/)
2. After installation, restart your computer
3. You'll see "CABLE Input" as a recording device and "CABLE Output" as a playback device

#### macOS
1. Download and install [BlackHole](https://existential.audio/blackhole/)
2. Choose the 2ch version for this project
3. After installation, "BlackHole 2ch" will appear in your audio devices

#### Linux
1. PulseAudio is typically pre-installed on most distributions
2. If not, install it:
   ```bash
   sudo apt-get install pulseaudio pulseaudio-utils
   ```

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd ai-audio-router
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the project root:
```
GEMINI_API_KEY=AIzaSyA2BTRMlCWbNjS1KmZ7upyQ4xY08Otu8mY
```

### 5. Configure Virtual Audio Device
Run the setup script to configure your virtual audio device:
```bash
python setup_audio.py
```

### 6. Configure Your Communication Application
1. Open MS Teams (or your communication app)
2. Go to Settings → Devices
3. Set your microphone to:
   - Windows: "CABLE Output (VB-Audio Virtual Cable)"
   - macOS: "BlackHole 2ch"
   - Linux: "Virtual_Microphone" (created by our setup)

## 🎮 Usage

### Step 1: List Available Audio Devices
```bash
python audio_inspector.py
```
This will show all available audio devices and which applications are using them.

### Step 2: Test with Pre-recorded Audio
```bash
python test_audio_sender.py
```
Type "Start" when prompted to send the test.mp3 file through the virtual audio channel.

### Step 3: Run the AI Audio GUI
```bash
python ai_audio_gui.py
```
This launches the GUI where you can:
1. Enter the recipient's full name
2. Enter the case number
3. Click "Generate and Send" to synthesize and transmit the audio

## 📁 Project Structure

```
ai-audio-router/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── .env                        # Environment variables (create this)
├── setup_audio.py              # Virtual audio device setup
├── audio_inspector.py          # List and inspect audio devices
├── test_audio_sender.py        # Test script for pre-recorded audio
├── ai_audio_gui.py            # Main GUI application
├── audio_router.py            # Core audio routing logic
├── gemini_tts.py              # Google Gemini TTS integration
├── test.mp3                   # Test audio file (add your own)
└── Detailed_Project_Description_and_Implementation.md
```

## 🔧 Troubleshooting

### Audio Not Transmitting
1. Ensure the virtual audio device is properly installed
2. Check that your communication app is using the correct input device
3. Run `audio_inspector.py` to verify device configuration

### No Audio Devices Found
- Windows: Reinstall VB-CABLE and restart
- macOS: Check Security & Privacy settings for microphone access
- Linux: Restart PulseAudio: `pulseaudio -k && pulseaudio --start`

### Gemini API Errors
- Verify your API key is correct in the `.env` file
- Check your internet connection
- Ensure you haven't exceeded API rate limits

## 🛡️ Security Notes

- The provided API key should be replaced with your own for production use
- Never commit API keys to version control
- Consider implementing API key encryption for production deployments

## 📞 Support

For issues or questions:
1. Check the Detailed_Project_Description_and_Implementation.md for in-depth technical details
2. Review the troubleshooting section above
3. Check application logs in the `logs/` directory

## 📄 License

This project is for educational and testing purposes. 