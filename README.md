<div align="center">
  <br>
  <h1>🌬️ AirDock</h1>
  
  **Advanced Webcam-Based Gesture Recognition Tool**
  <br><br>
  
  [![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
  [![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
  [![Platform](https://img.shields.io/badge/Platform-Windows-0078d7?style=for-the-badge&logo=windows&logoColor=white)]()
  
  <p><i>Control your PC effortlessly without touching your mouse or keyboard, powered by Mediapipe AI.</i></p>
</div>

---

## ✨ Features

- 🔀 **App Switcher (Alt+Tab)**: Swipe your hand left or right to switch between active applications. Hold your hand in place to keep the switcher open, and drop it to select.
- 🔊 **Volume Control**: Swipe up/down or use continuous hold gestures to adjust the system volume (Left hand for Volume Down, Right hand for Volume Up).
- 📸 **Instant Screenshots**: Make a fist for **0.5 seconds** to instantly capture your screen.
- 🎨 **Beautiful Modern GUI**: Real-time webcam preview, diagnostics panel (track hand coordinates, fps, swipe deltas), and customizable settings all inside a sleek dark-themed interface with acrylic glass styling.
- ⚙️ **Customizable Sensitivities**: Easily tweak the gesture thresholds (swipe sensitivity, cooldowns, fist ratios) to match your environment directly from the settings panel.
- 👻 **System Tray Support**: Hide the application entirely and let it run smoothly in the background.

---

## 🚀 Getting Started

### 📦 Option 1: Standalone Executable (Windows)
*The easiest way to get started, no installations required!*

1. Download `airdock.exe` from the [Releases](#) tab.
2. Run `airdock.exe`. On its first run, it will automatically download the necessary machine learning model (`hand_landmarker.task`).
3. Your camera light will turn on—you're ready to start using gestures immediately!

### 🐍 Option 2: Running from Source
*For developers and Python enthusiasts.*

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rithulraveendran/AirDock.git
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

---

## ✋ Controls & Gestures Map

| Gesture | Action Triggered |
| :--- | :--- |
| **Right Swipe** 👉 | Next Application *(Alt + Tab)* |
| **Left Swipe** 👈 | Previous Application *(Alt + Shift + Tab)* |
| **Right Hand Swipe/Hold Up** 📈 | Increase System Volume |
| **Left Hand Swipe/Hold Down** 📉 | Decrease System Volume |
| **Fist** ✊ | Take a Screenshot |

> **💡 Pro-Tip:** For the best experience, stand **1-2 meters** from the camera. When returning your hand to rest, move it towards the center of the frame or drop it quickly—the built-in cooldown cancels unintended return triggers!

---

## 🛠️ Configuration
Settings such as **camera index**, **gesture cooldowns**, **thresholds**, and **colors** are automatically saved in `config.json`. You can modify these settings via the beautifully designed built-in Settings Panel inside the app.

---

## 📜 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

<div align="center">
  <br>
  <i>Built with ❤️ using CustomTkinter and Mediapipe</i>
</div>
