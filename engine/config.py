"""
Engine Configuration
====================

Configuration for audiobook engine components.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
PROJECTS_DIR = BASE_DIR / "projects"
EXTERNAL_MODELS_DIR = BASE_DIR.parent  # Parent of audiobook_engine

# Audio settings
AUDIO_SAMPLE_RATE = 22050
AUDIO_CHANNELS = 1
MIN_VALID_AUDIO_DURATION = 0.5  # seconds

# API Keys (optional - for chunking/seed providers)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# External TTS Model Paths
COSYVOICE_PATH = EXTERNAL_MODELS_DIR / "CosyVoice"
DIA2_PATH = EXTERNAL_MODELS_DIR / "dia2"
CHATTERBOX_PATH = EXTERNAL_MODELS_DIR / "Chatterbox"  # Future

# Web UI settings
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5002"))  # Different port from old app
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
MAX_UPLOAD_SIZE_MB = 50

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
