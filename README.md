# AirDock

AirDock is an advanced webcam-based gesture recognition tool that allows you to control your PC without touching your mouse or keyboard. Using the power of Mediapipe Hand Tracking and a beautiful modern dark-mode GUI (built with CustomTkinter and PyWinStyles), AirDock offers a seamless hands-free experience.

## Features

- **App Switcher (Alt+Tab)**: Swipe your hand left or right to switch between active applications. Hold your hand in place to keep the switcher open, and drop it to select.
- **Volume Control**: Swipe up/down or use continuous hold gestures to adjust the system volume (Left hand for Volume Down, Right hand for Volume Up).
- **Instant Screenshots**: Make a fist for 0.5 seconds to instantly capture your screen.
- **Beautiful Modern GUI**: Real-time webcam preview, diagnostics panel (track hand coordinates, fps, swipe deltas), and customizable settings all inside a sleek dark-themed interface with acrylic glass styling.
- **Customizable Sensitivities**: Easily tweak the gesture thresholds (swipe sensitivity, cooldowns, fist ratios) to match your environment directly from the settings panel.
- **System Tray Support**: Hide the application entirely and let it run in the background from your system tray.

## Getting Started

### Option 1: Standalone Executable (Windows)

You can run the standalone Windows executable without installing any dependencies:
1. Download `airdock.exe` from the Releases tab.
2. Run `airdock.exe` - on its first run, it will automatically download the necessary machine learning model (`hand_landmarker.task`) into the directory.
3. Your camera light will turn on, and you can start using gestures immediately!

### Option 2: Running from Source

If you prefer to run the script using Python:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/AirDock.git
   cd AirDock
   ```

2. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the script:**
   ```bash
   cd airdock
   python airdock.py
   ```

## Controls & Gestures

- **Right Swipe**: Next Application (Alt + Tab)
- **Left Swipe**: Previous Application (Alt + Shift + Tab)
- **Right Hand Swipe/Hold Up**: Increase System Volume
- **Left Hand Swipe/Hold Down**: Decrease System Volume
- **Fist**: Take a Screenshot

*Tip: For the best experience, stand 1-2 meters from the camera. When returning your hand to rest, move it towards the center of the frame or drop it quickly—the built-in cooldown cancels unintended return triggers.*

## Configuration

Settings such as camera index, gesture cooldowns, thresholds, and colors are automatically saved in `config.json`. You can modify these settings via the built-in Settings Panel inside the app.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
