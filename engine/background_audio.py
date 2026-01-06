"""
Background audio generation service using Stable Audio in isolated environment.
Calls Stable Audio via subprocess in separate conda environment.
"""

import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BackgroundAudioGenerator:
    """
    Manages background audio generation using Stable Audio in separate conda environment.
    """

    def __init__(
        self,
        conda_env: str = "audiobook-stable",
        script_path: Optional[Path] = None
    ):
        """
        Initialize background audio generator.

        Args:
            conda_env: Name of conda environment with Stable Audio installed
            script_path: Path to generate_background_audio.py script
        """
        self.conda_env = conda_env

        if script_path is None:
            # Default to scripts directory
            script_path = Path(__file__).parent.parent / "scripts" / "generate_background_audio.py"

        self.script_path = Path(script_path)

        if not self.script_path.exists():
            raise FileNotFoundError(f"Background audio script not found: {self.script_path}")

    def generate(
        self,
        prompt: str,
        output_path: Path,
        duration: float = 10.0,
        steps: int = 100,
        cfg_scale: float = 7.0,
        device: str = "mps"
    ) -> Dict[str, Any]:
        """
        Generate background audio using Stable Audio in separate conda environment.

        Args:
            prompt: Text description of the sound (e.g., "gentle rain ambience")
            output_path: Path to save the generated .wav file
            duration: Duration in seconds
            steps: Number of diffusion steps (higher = better quality, slower)
            cfg_scale: Classifier-free guidance scale
            device: Device to use ("mps" for Mac M4, "cuda", "cpu")

        Returns:
            Dict with generation results:
            {
                "success": bool,
                "output_path": str,
                "duration": float,
                "prompt": str,
                "error": str (if failed)
            }
        """
        logger.info(f"Generating background audio: '{prompt}' ({duration}s)")

        # Build command to run in conda environment
        cmd = [
            "conda", "run",
            "-n", self.conda_env,
            "--no-capture-output",  # Show output in real-time
            "python", str(self.script_path),
            "--prompt", prompt,
            "--output", str(output_path),
            "--duration", str(duration),
            "--steps", str(steps),
            "--cfg-scale", str(cfg_scale),
            "--device", device
        ]

        try:
            # Run subprocess
            logger.debug(f"Running command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300  # 5 minute timeout
            )

            # Log output
            if result.stdout:
                logger.info(f"Stable Audio output:\n{result.stdout}")
            if result.stderr:
                logger.warning(f"Stable Audio stderr:\n{result.stderr}")

            # Check if output file was created
            if not output_path.exists():
                raise RuntimeError(f"Output file not created: {output_path}")

            return {
                "success": True,
                "output_path": str(output_path),
                "duration": duration,
                "prompt": prompt,
                "steps": steps,
                "cfg_scale": cfg_scale
            }

        except subprocess.CalledProcessError as e:
            error_msg = f"Stable Audio generation failed: {e.stderr}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "stdout": e.stdout,
                "stderr": e.stderr
            }

        except subprocess.TimeoutExpired:
            error_msg = f"Stable Audio generation timed out after 5 minutes"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }

