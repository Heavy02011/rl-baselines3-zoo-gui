# RL Racing GUI (rl-baselines3-zoo)

Standalone GUI extracted from the [`gui/` folder](https://github.com/Heavy02011/rl-racing-2022-v2_race16/tree/main/gui) of the RL Racing project. It is built on top of [RL Baselines3 Zoo](https://github.com/DLR-RM/rl-baselines3-zoo) (`rl_zoo3`) for training and enjoying agents on the racing environment.

![Sample GUI](assets/gui-sample.png)

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

## Installation (uv)
1) Clone this repository:
```bash
git clone https://github.com/Heavy02011/rl-baselines3-zoo-gui.git
cd rl-baselines3-zoo-gui
```
2) Install [uv](https://github.com/astral-sh/uv) if you don't have it yet:
```bash
pip install --user uv
```
3) Create and activate a virtual environment with uv:
```bash
uv venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
```
4) Install Python dependencies with uv:
```bash
uv pip install -r requirements.txt
```
5) (Optional) Pull racing assets/models from the original project if you need the tracks or pre-trained policies. Copy the full `gui/` contents from the upstream repo so that the scripts and assets (e.g., `gui.py` or `app.py`, `maps/`, `models/`, configs) sit in this folder:
```bash
git clone https://github.com/Heavy02011/rl-racing-2022-v2_race16.git
cp -r rl-racing-2022-v2_race16/gui/* .
```

## Usage
- Launch the GUI entrypoint that ships with the copied `gui/` files:
  - `python gui.py` (main script used in the upstream GUI), or
  - `streamlit run app.py` (if you prefer the Streamlit version).
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
