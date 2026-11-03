from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
FACE_DATASET_DIR = DATA_DIR / "faces"
MODELS_DIR = PROJECT_ROOT / "models"
STREAMLIT_CONFIG_PATH = PROJECT_ROOT / ".streamlit" / "config.toml"


def ensure_runtime_directories() -> None:
    for path in (FACE_DATASET_DIR, MODELS_DIR):
        path.mkdir(parents=True, exist_ok=True)
