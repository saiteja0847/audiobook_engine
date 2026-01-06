"""
Audiobook Engine Web UI
========================

Flask web application for audiobook generation with:
- Project management
- TTS provider selection per chunk
- Audio effects controls
- Model comparison
- Real-time generation monitoring
"""

import sys
from pathlib import Path

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import json
import threading
import time
from typing import Optional, Dict, List

from engine.config import PROJECTS_DIR, FLASK_HOST, FLASK_PORT
from engine.models import Chunk, Project, VoiceSeed
from engine.providers.registry import ProviderRegistry
from engine.audio.effects import AVAILABLE_EFFECTS, get_effect
from scripts.generate_audiobook import AudiobookGenerator


# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Global state for generation tracking
generation_status: Dict[str, Dict] = {}


# ============================================================
# Provider and Effects APIs
# ============================================================

@app.route('/api/providers/tts', methods=['GET'])
def get_tts_providers():
    """Get all available TTS providers."""
    try:
        providers = ProviderRegistry.list_tts()
        return jsonify({
            'success': True,
            'providers': providers
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/effects', methods=['GET'])
def get_effects():
    """Get all available audio effects with parameters."""
    try:
        effects = []
        for effect_name, effect_class in AVAILABLE_EFFECTS.items():
            effect = effect_class()
            effects.append({
                'name': effect.name,
                'display_name': effect.display_name,
                'parameters': effect.get_parameters()
            })

        return jsonify({
            'success': True,
            'effects': effects
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# Project Management APIs
# ============================================================

@app.route('/api/projects', methods=['GET'])
def list_projects():
    """List all projects."""
    try:
        if not PROJECTS_DIR.exists():
            return jsonify({
                'success': True,
                'projects': []
            })

        projects = []
        for project_dir in PROJECTS_DIR.iterdir():
            if project_dir.is_dir():
                project_json = project_dir / "project.json"
                if project_json.exists():
                    with open(project_json) as f:
                        project_data = json.load(f)
                        projects.append(project_data)
                else:
                    # Create minimal project entry
                    projects.append({
                        'slug': project_dir.name,
                        'name': project_dir.name.replace('-', ' ').title()
                    })

        return jsonify({
            'success': True,
            'projects': projects
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/projects', methods=['POST'])
def create_project():
    """Create a new project."""
    try:
        data = request.json
        name = data.get('name')
        slug = data.get('slug')
        book_content = data.get('book_content')
        description = data.get('description', '')

        # Validation
        if not name or not slug:
            return jsonify({
                'success': False,
                'error': 'Project name and slug are required'
            }), 400

        if not book_content:
            return jsonify({
                'success': False,
                'error': 'Book content is required'
            }), 400

        # Check if project already exists
        project_dir = PROJECTS_DIR / slug
        if project_dir.exists():
            return jsonify({
                'success': False,
                'error': f'Project "{slug}" already exists'
            }), 409

        # Create project directory
        project_dir.mkdir(parents=True, exist_ok=True)

        # Save book content
        book_file = project_dir / "book.txt"
        with open(book_file, 'w', encoding='utf-8') as f:
            f.write(book_content)

        # Create project.json
        project_data = {
            'name': name,
            'slug': slug,
            'description': description,
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'book_file': 'book.txt'
        }

        project_json = project_dir / "project.json"
        with open(project_json, 'w') as f:
            json.dump(project_data, f, indent=2)

        # Create subdirectories
        (project_dir / "audio").mkdir(exist_ok=True)
        (project_dir / "seeds").mkdir(exist_ok=True)

        return jsonify({
            'success': True,
            'message': 'Project created successfully',
            'project': project_data
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/projects/<project_slug>', methods=['GET'])
def get_project(project_slug):
    """Get project details."""
    try:
        project_dir = PROJECTS_DIR / project_slug
        if not project_dir.exists():
            return jsonify({
                'success': False,
                'error': 'Project not found'
            }), 404

        # Load project metadata
        project_json = project_dir / "project.json"
        if project_json.exists():
            with open(project_json) as f:
                project_data = json.load(f)
        else:
            project_data = {
                'slug': project_slug,
                'name': project_slug.replace('-', ' ').title()
            }

        # Load chunks
        chunks_json = project_dir / "chunked_book.json"
        if chunks_json.exists():
            with open(chunks_json) as f:
                chunks_data = json.load(f)
        else:
            chunks_data = []

        # Load seeds
        seeds_dir = project_dir / "seeds"
        seeds = []
        if seeds_dir.exists():
            for seed_dir in seeds_dir.iterdir():
                if seed_dir.is_dir():
                    seed_json = seed_dir / "seed.json"
                    if seed_json.exists():
                        with open(seed_json) as f:
                            seeds.append(json.load(f))

        # Count generated audio
        audio_dir = project_dir / "audio"
        audio_count = 0
        if audio_dir.exists():
            audio_count = len(list(audio_dir.glob("chunk_*.wav")))

        return jsonify({
            'success': True,
            'project': project_data,
            'chunks': chunks_data,
            'seeds': seeds,
            'audio_count': audio_count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# Chunk Management APIs
# ============================================================

@app.route('/api/projects/<project_slug>/chunks/<int:chunk_id>', methods=['PUT'])
def update_chunk(project_slug, chunk_id):
    """Update a chunk's configuration (TTS settings, effects)."""
    try:
        project_dir = PROJECTS_DIR / project_slug
        chunks_json = project_dir / "chunked_book.json"

        if not chunks_json.exists():
            return jsonify({
                'success': False,
                'error': 'Chunks file not found'
            }), 404

        # Load chunks
        with open(chunks_json) as f:
            chunks = json.load(f)

        # Find and update chunk
        chunk_found = False
        for i, chunk in enumerate(chunks):
            if chunk.get('chunk_id') == chunk_id or chunk.get('id') == chunk_id:
                # Update with request data
                update_data = request.json
                chunks[i].update(update_data)
                chunk_found = True
                break

        if not chunk_found:
            return jsonify({
                'success': False,
                'error': 'Chunk not found'
            }), 404

        # Save chunks
        with open(chunks_json, 'w') as f:
            json.dump(chunks, f, indent=2)

        return jsonify({
            'success': True,
            'chunk': chunks[i]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/projects/<project_slug>/chunks/<int:chunk_id>/audio', methods=['GET'])
def get_chunk_audio(project_slug, chunk_id):
    """Get audio file for a chunk."""
    try:
        project_dir = PROJECTS_DIR / project_slug
        audio_path = project_dir / "audio" / f"chunk_{chunk_id}.wav"

        if not audio_path.exists():
            return jsonify({
                'success': False,
                'error': 'Audio file not found'
            }), 404

        return send_file(
            audio_path,
            mimetype='audio/wav',
            as_attachment=False
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/projects/<project_slug>/book.txt', methods=['GET'])
def get_book_content(project_slug):
    """Get book.txt content for a project."""
    try:
        project_dir = PROJECTS_DIR / project_slug
        book_path = project_dir / "book.txt"

        if not book_path.exists():
            return jsonify({
                'success': False,
                'error': 'Book file not found'
            }), 404

        return send_file(
            book_path,
            mimetype='text/plain',
            as_attachment=False
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/projects/<project_slug>/seeds/<speaker>/<filename>', methods=['GET'])
def get_seed_audio(project_slug, speaker, filename):
    """Get seed audio file for a speaker."""
    try:
        project_dir = PROJECTS_DIR / project_slug
        seed_audio_path = project_dir / "seeds" / speaker / filename

        if not seed_audio_path.exists():
            return jsonify({
                'success': False,
                'error': 'Seed audio file not found'
            }), 404

        return send_file(
            seed_audio_path,
            mimetype='audio/wav',
            as_attachment=False
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/projects/<project_slug>/audiobook/full.wav', methods=['GET'])
def get_full_audiobook(project_slug):
    """Get full combined audiobook file."""
    try:
        project_dir = PROJECTS_DIR / project_slug
        audiobook_path = project_dir / "full_audiobook.wav"

        if not audiobook_path.exists():
            return jsonify({
                'success': False,
                'error': 'Full audiobook not found'
            }), 404

        return send_file(
            audiobook_path,
            mimetype='audio/wav',
            as_attachment=False
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/projects/<project_slug>/audiobook/combine', methods=['POST'])
def combine_audiobook(project_slug):
    """Combine all available chunk audio files into full audiobook."""
    import torch
    import torchaudio

    try:
        project_dir = PROJECTS_DIR / project_slug
        audio_dir = project_dir / "audio"

        if not audio_dir.exists():
            return jsonify({
                'success': False,
                'error': 'Audio directory not found'
            }), 404

        # Get all chunk audio files sorted by chunk number
        chunk_files = sorted(audio_dir.glob("chunk_*.wav"), key=lambda x: int(x.stem.split('_')[1]))

        if not chunk_files:
            return jsonify({
                'success': False,
                'error': 'No audio chunks found'
            }), 404

        # Load and concatenate all audio with small pauses between chunks
        audio_segments = []
        pause_samples = int(0.5 * 22050)  # 0.5 second pause at 22.05kHz
        pause = torch.zeros(1, pause_samples)

        for i, chunk_file in enumerate(chunk_files):
            chunk_audio, sr = torchaudio.load(str(chunk_file))
            audio_segments.append(chunk_audio)

            # Add pause between chunks (not after the last one)
            if i < len(chunk_files) - 1:
                audio_segments.append(pause)

        # Concatenate
        full_audio = torch.cat(audio_segments, dim=1)

        # Save combined audiobook
        audiobook_path = project_dir / "full_audiobook.wav"
        torchaudio.save(str(audiobook_path), full_audio, 22050)

        total_duration = full_audio.shape[-1] / 22050
        file_size = audiobook_path.stat().st_size / (1024 * 1024)

        return jsonify({
            'success': True,
            'message': 'Audiobook combined successfully',
            'stats': {
                'total_chunks': len(chunk_files),
                'duration': round(total_duration, 1),
                'duration_minutes': round(total_duration / 60, 1),
                'file_size_mb': round(file_size, 1)
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# Generation APIs
# ============================================================

@app.route('/api/projects/<project_slug>/generate', methods=['POST'])
def generate_audio(project_slug):
    """
    Generate audio for project chunks.

    Request body:
    {
        "chunks": [1, 2, 3],  // Optional: specific chunks to generate
        "force": false,        // Optional: force regeneration
        "start": 1,           // Optional: start chunk
        "end": 10,            // Optional: end chunk
        "default_provider": "cosyvoice",  // Optional: default TTS provider
        "default_method": "zero-shot",     // Optional: default inference method
        "default_speed": 1.0               // Optional: default playback speed (0.5-2.0)
    }
    """
    try:
        data = request.json or {}
        force = data.get('force', False)
        start_chunk = data.get('start')
        end_chunk = data.get('end')
        specific_chunks = data.get('chunks')
        default_provider = data.get('default_provider')
        default_method = data.get('default_method')
        default_speed = data.get('default_speed', 1.0)

        # Check if generation already in progress
        if project_slug in generation_status:
            status = generation_status[project_slug]
            if status['status'] == 'in_progress':
                return jsonify({
                    'success': False,
                    'error': 'Generation already in progress'
                }), 409

        # Initialize generation status
        generation_status[project_slug] = {
            'status': 'in_progress',
            'current_chunk': None,
            'total_chunks': 0,
            'generated': 0,
            'failed': 0,
            'start_time': time.time(),
            'progress': 0
        }

        # Start generation in background thread
        thread = threading.Thread(
            target=_run_generation,
            args=(project_slug, force, start_chunk, end_chunk, specific_chunks, default_provider, default_method, default_speed)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Generation started'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/projects/<project_slug>/generate/status', methods=['GET'])
def get_generation_status(project_slug):
    """Get current generation status."""
    try:
        if project_slug not in generation_status:
            return jsonify({
                'success': True,
                'status': 'idle'
            })

        return jsonify({
            'success': True,
            **generation_status[project_slug]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _run_generation(
    project_slug: str,
    force: bool,
    start_chunk: Optional[int],
    end_chunk: Optional[int],
    specific_chunks: Optional[List[int]],
    default_provider: Optional[str] = None,
    default_method: Optional[str] = None,
    default_speed: float = 1.0
):
    """
    Background thread function for audio generation.
    Updates generation_status dictionary.
    """
    try:
        generator = AudiobookGenerator(project_slug, force=force)

        # Load project
        if not generator.load_project():
            generation_status[project_slug]['status'] = 'failed'
            generation_status[project_slug]['error'] = 'Failed to load project'
            return

        # Update status
        generation_status[project_slug]['total_chunks'] = len(generator.chunks)

        # Filter chunks
        chunks_to_generate = generator.chunks
        if specific_chunks:
            chunks_to_generate = [c for c in chunks_to_generate if c.id in specific_chunks]
        elif start_chunk or end_chunk:
            start_idx = (start_chunk - 1) if start_chunk else 0
            end_idx = end_chunk if end_chunk else len(generator.chunks)
            chunks_to_generate = generator.chunks[start_idx:end_idx]

        # Generate chunks
        for i, chunk in enumerate(chunks_to_generate):
            generation_status[project_slug]['current_chunk'] = chunk.id
            generation_status[project_slug]['progress'] = int((i / len(chunks_to_generate)) * 100)

            success = generator.generate_chunk(
                chunk,
                default_provider=default_provider,
                default_method=default_method,
                default_speed=default_speed
            )

            if success:
                generation_status[project_slug]['generated'] += 1
            else:
                generation_status[project_slug]['failed'] += 1

        # Complete
        generation_status[project_slug]['status'] = 'completed'
        generation_status[project_slug]['progress'] = 100
        generation_status[project_slug]['end_time'] = time.time()

    except Exception as e:
        generation_status[project_slug]['status'] = 'failed'
        generation_status[project_slug]['error'] = str(e)


# ============================================================
# Main Routes
# ============================================================

@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/project/<project_slug>')
def project_page(project_slug):
    """Project detail page."""
    return render_template('project.html', project_slug=project_slug)


# ============================================================
# Initialize and Run
# ============================================================

@app.route('/api/shutdown', methods=['POST'])
def shutdown_server():
    """Shutdown the Flask server."""
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        # If not running with werkzeug dev server, use os._exit
        import os
        import threading
        def shutdown():
            import time
            time.sleep(0.5)  # Give time to send response
            os._exit(0)
        threading.Thread(target=shutdown).start()
        return jsonify({'message': 'Server shutting down...'}), 200
    func()
    return jsonify({'message': 'Server shutting down...'}), 200


def initialize_providers():
    """Initialize TTS providers."""
    print("\n" + "="*60)
    print("Initializing Audiobook Engine")
    print("="*60)

    # Register CosyVoice 2 provider
    try:
        from engine.providers.tts.cosyvoice import CosyVoiceProvider
        ProviderRegistry.register_tts(CosyVoiceProvider)
    except ImportError as e:
        print(f"⚠ Warning: Could not load CosyVoice 2 provider: {e}")
    except Exception as e:
        print(f"⚠ Warning: Error registering CosyVoice 2 provider: {e}")

    # Register CosyVoice 3 provider
    try:
        from engine.providers.tts.cosyvoice3 import CosyVoice3Provider
        ProviderRegistry.register_tts(CosyVoice3Provider)
    except ImportError as e:
        print(f"⚠ Warning: Could not load CosyVoice 3 provider: {e}")
    except Exception as e:
        print(f"⚠ Warning: Error registering CosyVoice 3 provider: {e}")

    # Register Dia2 provider (EXPERIMENTAL - NOT RECOMMENDED)
    # Dia2 is designed for dialogue continuation, not voice cloning
    # Voice cloning quality is poor compared to CosyVoice
    # Only register if explicitly enabled
    DIA2_ENABLED = False  # Set to True to enable Dia2 (not recommended)

    if DIA2_ENABLED:
        try:
            from engine.providers.tts.dia2 import Dia2Provider
            ProviderRegistry.register_tts(Dia2Provider)
            print("⚠ WARNING: Dia2 enabled - voice cloning quality will be poor!")
        except ImportError as e:
            print(f"⚠ Warning: Could not load Dia2 provider: {e}")
        except Exception as e:
            print(f"⚠ Warning: Error registering Dia2 provider: {e}")

    # List registered providers
    providers = ProviderRegistry.list_tts()
    print(f"\n✓ Registered {len(providers)} TTS provider(s):")
    for p in providers:
        print(f"  - {p['display_name']} ({p['name']})")
        print(f"    Methods: {', '.join(p['methods'])}")

    print("\n" + "="*60)
    print(f"Web UI ready at http://{FLASK_HOST}:{FLASK_PORT}")
    print("="*60 + "\n")


if __name__ == '__main__':
    initialize_providers()
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=True,
        threaded=True
    )
