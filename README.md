# RL Racing GUI (rl-baselines3-zoo)

Standalone GUI extracted from the [`gui/` folder](https://github.com/Heavy02011/rl-racing-2022-v2_race16/tree/main/gui) of the RL Racing project. It is built on top of [RL Baselines3 Zoo](https://github.com/DLR-RM/rl-baselines3-zoo) (`rl_zoo3`) for training and enjoying agents on the racing environment.

## Prerequisites
- Python **3.10+**
- System packages (recommended for Box2D and video support):
  - `ffmpeg`
  - `swig`
  - `cmake`
- (Optional) NVIDIA CUDA/cuDNN if you want GPU acceleration for PyTorch.

On Debian/Ubuntu you can install the system tools with:
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg swig cmake
```

## Installation
1) Clone this repository:
```bash
git clone https://github.com/Heavy02011/rl-baselines3-zoo-gui.git
cd rl-baselines3-zoo-gui
```
2) Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
```
3) Install Python dependencies:
```bash
pip install -r requirements.txt
```
4) (Optional) Pull racing assets/models from the original project if you need the tracks or pre-trained policies:
```bash
git clone https://github.com/Heavy02011/rl-racing-2022-v2_race16.git
# copy the needed folders (e.g., maps/models) from rl-racing-2022-v2_race16/gui/ into this repo
```

## Usage
- Launch the GUI entrypoint from this folder (for example):
  - `python gui.py` (if the GUI is a Python script), or
  - `streamlit run app.py` (if the GUI is Streamlit-based).
- To enjoy a trained RL agent with `rl_zoo3` and show the environment window:
```bash
python -m rl_zoo3.enjoy --algo ppo --env CarRacing-v2 --env-kwargs render_mode=human -f logs/
```
Replace `algo`, `env`, and the log folder with your own configuration or the assets copied from the RL Racing project.

## Troubleshooting
- Box2D installation issues: ensure `swig` and `cmake` are installed before `pip install -r requirements.txt`.
- No render window: set `render_mode=human` in `--env-kwargs` (or the equivalent config) so the environment opens a GUI window.

## License
This repository is released under the MIT License. See [LICENSE](LICENSE) for details.
