#!/usr/bin/env python3
"""
Test script for iterating on audiobook chunking prompts.

This script:
1. Splits book into 500-word segments at sentence boundaries
2. Sends segments to LLM with the prompt
3. Tracks continuity across segments
4. Evaluates chunk quality metrics
5. Saves results for comparison
"""

import json
import re
import requests
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class Chunk:
    """Represents a single chunk with all metadata."""
    chunk_id: int
    text: str
    speaker: str
    chunk_type: str  # 'D' for dialogue, 'N' for narration
    emotion: str

    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        Remove/sanitize characters that CosyVoice TTS cannot handle well.

        Keeps:
        - Audio tags: [laughter], [whisper], [gasp], etc. (CosyVoice supports these)
        - Sentence punctuation: .,!?;:-

        Removes:
        - Quotes: " " ' ' ` ` (dialogue already separated, not needed)
        - Actions/asterisks: *action*, _emphasis_ (not TTS-friendly)
        - Parentheses for actions: (shrugs), (sighs) (keep for whispers/thoughts)

        Args:
            text: Raw text from chunking

        Returns:
            Sanitized text safe for TTS
        """
        import re

        # Remove all types of quotes
        text = re.sub(r'[""''`]', '', text)

        # Remove asterisk actions (common in books: *smiles*, *laughs*)
        text = re.sub(r'\*[^*]+\*', '', text)

        # Remove underscore emphasis (common in books: _really_, _important_)
        text = re.sub(r'_[^_]+_', '', text)

        # Clean up extra whitespace from removals
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces -> single space
        text = text.strip()  # Remove leading/trailing space

        return text

    def to_dict(self) -> Dict:
        """Convert to legacy JSON format with sanitized text."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.sanitize_text(self.text),  # Sanitize before saving
            "speaker": self.speaker,
            "metadata": {
                "type": "dialogue" if self.chunk_type == "D" else "narration",
                "emotion": self.emotion,
            },
            "emotion_prompt": self.emotion,
            "type": "dialogue" if self.chunk_type == "D" else "narration",
        }


@dataclass
class SegmentResult:
    """Results from processing one segment."""
    segment_number: int
    mood_line: str
    chunks: List[Chunk]
    raw_output: str
    quality_metrics: Dict[str, any] = field(default_factory=dict)


class ChunkingTester:
    """Test and iterate on chunking prompts."""

    # V5 prompt - improved with explicit quote removal, self-check repair, and "I" mapping
    CHUNKING_PROMPT = """You are an audiobook narration preprocessor.

You MUST follow the HARD CONSTRAINTS and produce ONLY TOON output.

========================
TASK
========================
1) Read the entire passage and identify:
   - primary scene mood (one emotion)
   - up to 3 mood shifts (optional)
2) Normalize the text (line breaks / hyphen wraps) before chunking.
3) Chunk into sentence-level units.
4) ALWAYS separate dialogue from narration into distinct chunks.
5) Assign speaker, type, and emotion for each chunk.
6) Track character references via the Character Registry (canonical names only).

========================
CHARACTER REGISTRY (CANONICAL SPEAKERS ONLY)
========================
You MUST use ONLY these canonical speaker names:

VIOLET
MIRA
MOM
FITZGIBBONS
UNNAMED_RIDER
MALE_CANDIDATE
RHIANNON
DYLAN
RIDER_PARAPET
XADEN
UNKNOWN
NARRATOR

Aliases map to canonical:
- VIOLET: Violet, Sis, Candidate Sorrengail, Candidate, General Sorrengail's youngest, Daughter of a scribe, Daughter of a rider
- MIRA: Mira, Lieutenant Sorrengail, Lieutenant
- MOM: Mom, Mother, General, Commanding General of Basgiath, General Sorrengail
- FITZGIBBONS: Captain, Captain Fitzgibbons
- UNNAMED_RIDER: The rider next to Captain Fitzgibbons, Marked rider
- MALE_CANDIDATE: Snickering asshole, The jerk behind me, Guy behind me
- RHIANNON: Rhiannon, Woman ahead of me
- DYLAN: Blond guy
- RIDER_PARAPET: Rider with ripped sleeves, One with ripped-off sleeves
- XADEN: Riorson, Xaden Riorson, Fen Riorson's son, The third rider, Wingleader

========================
EMOTIONS (USE ONLY THESE - NO OTHERS)
========================
Allowed emotions ONLY:
[neutral, somber, contemplative, tense, angry, joyful, fearful, tender, bitter]

CRITICAL:
- You MUST ONLY output one of these emotions.
- If you feel tempted to use a non-listed emotion, map to closest allowed:
  contempt/scorn/sarcasm/disgust → bitter
  sadness/dread/grief → somber
  anxiety/worry/nervous → tense (controlled) or fearful (panic/pleading)
  calm/peaceful → neutral or contemplative
  surprise/shock → tense or fearful

========================
TEXT NORMALIZATION (DO THIS FIRST)
========================
Before chunking:
1) Treat ALL line breaks as spaces unless there is an empty line (paragraph break).
2) Fix hyphen-wrapped words:
   Example: "thirty-\\npound" -> "thirty-pound"
3) Preserve punctuation and sentence boundaries.

========================
DIALOGUE EXTRACTION (CRITICAL)
========================
Definitions:
- Dialogue = text inside quotation marks: " " or " "
- Narration = everything else (including first-person actions/thoughts like "I scoff.", "I snort.", "My stomach turns.")

HARD RULES:
1) ANY quoted span MUST become its own chunk:
   - type = D
   - speaker = a canonical character name (NOT NARRATOR)
   - REMOVE all quote characters from the text field
2) If a sentence contains both dialogue and narration, split into multiple chunks.
3) DO NOT include dialogue tags inside dialogue chunks.
   Example:
   WRONG: Then undo it, Mira seethes.
   CORRECT:
   - Then undo it,|MIRA|D|angry
   - Mira seethes.|NARRATOR|N|angry
4) After processing, there MUST be ZERO quote characters anywhere in output.

========================
SPEAKER RULES
========================
1) Narration chunks:
   - speaker MUST be NARRATOR
   - type MUST be N
   - Never assign VIOLET/MIRA/etc to narration even if it is first-person ("I ...").
2) Dialogue chunks:
   - Determine speaker by nearby dialogue tags:
     "Mira snaps" -> MIRA
     "Mom says" -> MOM
     "Violet says / I say" -> VIOLET (in this book, first-person narrator is VIOLET)
   - Use paragraph continuity (new paragraph often indicates speaker change).
   - Use response patterns (Q&A).
   - If truly unknown, use UNKNOWN.
3) Alias mentions in narration do NOT make them the speaker.

========================
EMOTION RULES (CONSISTENT + SMALL-MODEL FRIENDLY)
========================
1) Pick a primary_mood for the segment (one allowed emotion).
2) Emotion inertia: keep the same emotion as the previous chunk unless a strong cue appears.
3) Default narration to the current scene mood unless strong cue.
4) Verb cues (strong cues):
   - shouts/snaps/seethes/thunders/yells -> angry
   - pleads/begs/voice cracks -> fearful
   - gasps/stomach turns/lungs burning/near fall -> tense (or fearful if panic)
   - softens/brace shoulders/gentle greeting -> tender
   - scoffs/snorts/grumbles/self-deprecation -> bitter
5) Pleas about death/safety ("You're sending her to die!") -> fearful (not joyful).
6) "I'm fine!" in embarrassment/defensiveness -> fearful or bitter (not joyful).
7) Plain exposition/descriptions -> neutral or contemplative.

========================
CHUNKING RULES
========================
- Chunk at sentence boundaries.
- Keep chunks short and natural (avoid merging multiple sentences unless necessary).
- Do NOT split a sentence into fragments unless punctuation clearly implies it.

========================
INCREMENTAL CHUNK NUMBERING (CRITICAL)
========================
- Start numbering at PREVIOUS_CHUNK_ID + 1
- If PREVIOUS_CHUNK_ID is None, start at 1
- Numbers must be consecutive with no gaps

========================
OUTPUT FORMAT (TOON ONLY)
========================
Return TOON format only. No explanation. No markdown.

Line 1: MOOD|<primary_mood>|<shift1;shift2;shift3 or none>
Remaining lines: <chunk_id>|<text>|<speaker>|<type>|<emotion>

========================
FINAL SELF-CHECK + REPAIR (MUST APPLY SILENTLY)
========================
Before output, ensure ALL of these are true; if not, FIX them:
1) MOOD line exists and has exactly 3 fields, starting with "MOOD|".
2) Every chunk line has exactly 5 pipe-separated fields.
3) speaker is ONLY from the canonical speaker list (never "I", never quoted speaker strings).
   - If speaker == I, map it to VIOLET when it is dialogue.
4) If type == D, speaker MUST NOT be NARRATOR.
5) If type == N, speaker MUST be NARRATOR.
6) No quote characters remain anywhere in output text fields.
7) emotion is ONLY from the allowed list (no exceptions).
8) If a chunk contains both dialogue and narration, split it and label narration as NARRATOR|N.
9) IDs are consecutive and start at the correct value.

========================
SEGMENT CONTINUITY
========================
PREVIOUS_CHUNK_ID: {previous_chunk_id}
PREVIOUS_SEGMENT_MOOD: {previous_mood}
PREVIOUS_SEGMENT_ENDING: {last_2_3_sentences}

========================
TEXT TO PROCESS
========================
{text_to_process}"""

    def __init__(self, api_url: str = "http://localhost:8000/v1/chat/completions",
                 model: str = "qwen3-4b-instruct-2507-4bit"):
        """
        Initialize the tester.

        Args:
            api_url: The OpenAI-compatible API endpoint
            model: Model name to use
        """
        self.api_url = api_url
        self.model = model
        self.segments: List[str] = []
        self.results: List[SegmentResult] = []

    def split_into_segments(self, text: str, words_per_segment: int = 500) -> List[str]:
        """
        Split text into segments at sentence boundaries.

        Args:
            text: Full book text
            words_per_segment: Target words per segment

        Returns:
            List of text segments
        """
        # Split into sentences (rough approximation)
        # This preserves paragraph structure
        paragraphs = text.split('\n\n')
        sentences = []
        for para in paragraphs:
            # Split on sentence boundaries but keep the delimiter
            para_sentences = re.split(r'(?<=[.!?])\s+', para.strip())
            sentences.extend([s for s in para_sentences if s])

        # Group sentences into segments of ~500 words
        segments = []
        current_segment = []
        current_word_count = 0

        for sentence in sentences:
            sentence_words = len(sentence.split())
            if current_word_count + sentence_words > words_per_segment and current_segment:
                # Start new segment
                segments.append(' '.join(current_segment))
                current_segment = [sentence]
                current_word_count = sentence_words
            else:
                current_segment.append(sentence)
                current_word_count += sentence_words

        # Don't forget the last segment
        if current_segment:
            segments.append(' '.join(current_segment))

        return segments

    def call_llm(self, prompt: str) -> str:
        """
        Call the local LLM API.

        Args:
            prompt: The full prompt to send

        Returns:
            Raw response text
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,  # Increased from 0.3 for more emotion variation
            "max_tokens": 4096  # Increased for longer passages
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except Exception as e:
            print(f"❌ API Error: {e}")
            return ""

    def parse_toon_output(self, raw_output: str) -> Tuple[str, List[Chunk]]:
        """
        Parse TOON format output from LLM.

        Args:
            raw_output: Raw text from LLM

        Returns:
            Tuple of (mood_line, list of Chunks)
        """
        lines = raw_output.strip().split('\n')

        # Filter out empty lines and markdown artifacts
        lines = [l for l in lines if l.strip() and not l.strip().startswith('```')]

        if not lines:
            return "", []

        # First line is mood
        mood_line = lines[0].strip()

        # Remaining lines are chunks
        chunks = []
        for line in lines[1:]:
            parts = line.strip().split('|')
            if len(parts) >= 5:
                try:
                    chunk_id = int(parts[0].strip())
                    text = parts[1].strip()
                    speaker = parts[2].strip().upper()
                    chunk_type = parts[3].strip().upper()
                    emotion = parts[4].strip()

                    chunks.append(Chunk(
                        chunk_id=chunk_id,
                        text=text,
                        speaker=speaker,
                        chunk_type=chunk_type,
                        emotion=emotion
                    ))
                except (ValueError, IndexError) as e:
                    print(f"⚠️  Failed to parse line: {line} - {e}")
                    continue

        return mood_line, chunks

    def calculate_quality_metrics(self, chunks: List[Chunk]) -> Dict[str, any]:
        """
        Calculate quality metrics for a set of chunks.

        Args:
            chunks: List of chunks

        Returns:
            Dictionary of metrics
        """
        if not chunks:
            return {}

        valid_emotions = {'neutral', 'somber', 'contemplative', 'tense',
                         'angry', 'joyful', 'fearful', 'tender', 'bitter'}

        total_chunks = len(chunks)
        dialogue_chunks = sum(1 for c in chunks if c.chunk_type == 'D')
        narration_chunks = sum(1 for c in chunks if c.chunk_type == 'N')

        # Check for emotion validity
        invalid_emotions = [c.emotion for c in chunks if c.emotion.lower() not in valid_emotions]

        # Check for quote contamination (dialogue with quotes still in text)
        quotes_in_dialogue = [c for c in chunks if c.chunk_type == 'D' and '"' in c.text]

        # Check for unknown speakers in dialogue
        unknown_speakers = sum(1 for c in chunks if c.chunk_type == 'D' and c.speaker == 'UNKNOWN')

        # Check for special characters that will be sanitized
        chunks_with_quotes = sum(1 for c in chunks if any(q in c.text for q in ['"', '"', "'", "'", "`"]))
        chunks_with_asterisks = sum(1 for c in chunks if '*' in c.text)
        chunks_with_underscores = sum(1 for c in chunks if '_' in c.text)

        # Average chunk length (words)
        avg_length = sum(len(c.text.split()) for c in chunks) / total_chunks if total_chunks > 0 else 0

        return {
            "total_chunks": total_chunks,
            "dialogue_chunks": dialogue_chunks,
            "narration_chunks": narration_chunks,
            "dialogue_ratio": dialogue_chunks / total_chunks if total_chunks > 0 else 0,
            "invalid_emotions": len(invalid_emotions),
            "invalid_emotion_list": list(set(invalid_emotions)),
            "quotes_remaining": len(quotes_in_dialogue),
            "unknown_speakers": unknown_speakers,
            "chunks_sanitized_quotes": chunks_with_quotes,
            "chunks_sanitized_asterisks": chunks_with_asterisks,
            "chunks_sanitized_underscores": chunks_with_underscores,
            "avg_word_count": round(avg_length, 1),
        }

    def process_segment(self, segment_text: str, segment_number: int,
                       previous_chunk_id: Optional[int] = None,
                       previous_mood: str = "None",
                       last_sentences: str = "None") -> SegmentResult:
        """
        Process a single segment through the LLM.

        Args:
            segment_text: The text segment to process
            segment_number: Which segment this is (for tracking)
            previous_chunk_id: Last chunk ID from previous segment
            previous_mood: Previous segment's mood
            last_sentences: Last 2-3 sentences from previous segment

        Returns:
            SegmentResult with chunks and metrics
        """
        # Build the prompt with continuity
        prompt = self.CHUNKING_PROMPT.format(
            text_to_process=segment_text,
            previous_chunk_id=previous_chunk_id if previous_chunk_id is not None else "None",
            previous_mood=previous_mood,
            last_2_3_sentences=last_sentences
        )

        print(f"\n{'='*60}")
        print(f"Processing Segment {segment_number}")
        print(f"{'='*60}")
        print(f"Words: {len(segment_text.split())}")
        print(f"Previous chunk ID: {previous_chunk_id}")
        print(f"Previous mood: {previous_mood}")

        # Call LLM
        raw_output = self.call_llm(prompt)

        if not raw_output:
            print("❌ No output from LLM")
            return SegmentResult(
                segment_number=segment_number,
                mood_line="",
                chunks=[],
                raw_output="",
                quality_metrics={"error": "No LLM output"}
            )

        # Parse output
        mood_line, chunks = self.parse_toon_output(raw_output)

        print(f"\n✅ Parsed {len(chunks)} chunks")
        print(f"Mood: {mood_line}")
        if chunks:
            print(f"First chunk_id: {chunks[0].chunk_id} (expected: {previous_chunk_id + 1 if previous_chunk_id else 1})")
            print(f"Last chunk_id: {chunks[-1].chunk_id}")

        # Calculate metrics
        metrics = self.calculate_quality_metrics(chunks)
        print(f"\nMetrics:")
        for key, value in metrics.items():
            if key != "invalid_emotion_list":
                print(f"  {key}: {value}")

        return SegmentResult(
            segment_number=segment_number,
            mood_line=mood_line,
            chunks=chunks,
            raw_output=raw_output,
            quality_metrics=metrics
        )

    def process_book(self, book_path: Path, max_segments: int = None) -> List[SegmentResult]:
        """
        Process entire book through the pipeline.

        Args:
            book_path: Path to book.txt
            max_segments: Limit number of segments for testing (None = all)

        Returns:
            List of SegmentResults
        """
        print(f"Loading book from {book_path}")
        text = book_path.read_text()

        # Split into segments
        self.segments = self.split_into_segments(text)
        print(f"Split into {len(self.segments)} segments")

        if max_segments:
            self.segments = self.segments[:max_segments]
            print(f"Limiting to first {max_segments} segments for testing")

        # Process each segment
        all_chunks = []
        previous_chunk_id = None
        previous_mood = "None"
        last_sentences = "None"

        for i, segment in enumerate(self.segments, 1):
            result = self.process_segment(
                segment,
                i,
                previous_chunk_id,
                previous_mood,
                last_sentences
            )
            self.results.append(result)

            # Update continuity for next segment
            if result.chunks:
                previous_chunk_id = result.chunks[-1].chunk_id
                previous_mood = result.mood_line

                # Get last 2-3 sentences from this segment's text
                sentences = re.split(r'(?<=[.!?])\s+', segment.strip())
                last_sentences = ' '.join(sentences[-3:]) if len(sentences) > 3 else segment

            all_chunks.extend(result.chunks)

        print(f"\n{'='*60}")
        print(f"Processing complete!")
        print(f"Total chunks generated: {len(all_chunks)}")
        print(f"{'='*60}")

        return self.results

    def save_results(self, output_path: Path):
        """
        Save results to JSON for inspection.

        Args:
            output_path: Where to save the JSON
        """
        # Convert to legacy format
        legacy_chunks = []
        for result in self.results:
            for chunk in result.chunks:
                legacy_chunks.append(chunk.to_dict())

        output_data = {
            "metadata": {
                "total_chunks": len(legacy_chunks),
                "segments_processed": len(self.results),
            },
            "chunks": legacy_chunks
        }

        output_path.write_text(json.dumps(output_data, indent=2))
        print(f"\n✅ Results saved to {output_path}")

    def save_raw_toon(self, output_path: Path):
        """
        Save raw TOON output from LLM for debugging.

        Args:
            output_path: Where to save the TOON file
        """
        toon_lines = []
        for result in self.results:
            toon_lines.append(f"# Segment {result.segment_number}")
            toon_lines.append(f"{result.mood_line}")
            for chunk in result.chunks:
                toon_lines.append(f"{chunk.chunk_id}|{chunk.text}|{chunk.speaker}|{chunk.chunk_type}|{chunk.emotion}")
            toon_lines.append("")  # Blank line between segments

        output_path.write_text('\n'.join(toon_lines))
        print(f"✅ Raw TOON output saved to {output_path}")

    def print_summary(self):
        """Print summary statistics."""
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")

        for result in self.results:
            print(f"\nSegment {result.segment_number}:")
            print(f"  Mood: {result.mood_line}")
            if result.quality_metrics:
                for key, value in result.quality_metrics.items():
                    if key != "invalid_emotion_list":
                        print(f"  {key}: {value}")


def main():
    """Run the chunking test."""
    import argparse

    parser = argparse.ArgumentParser(description="Test audiobook chunking prompts")
    parser.add_argument("--book", type=str,
                       default="/Users/saiteja/Downloads/My-Projects/Claude-Code/Audiobook-Attempt-3/audiobook_engine/projects/fourth-wing/book.txt",
                       help="Path to book.txt")
    parser.add_argument("--output", type=str,
                       default="/Users/saiteja/Downloads/My-Projects/Claude-Code/Audiobook-Attempt-3/audiobook_engine/projects/fourth-wing/chunked_book_test.json",
                       help="Output JSON path")
    parser.add_argument("--segments", type=int, default=None,
                       help="Max segments to process (for testing)")
    parser.add_argument("--api-url", type=str,
                       default="http://localhost:8000/v1/chat/completions",
                       help="LLM API URL")
    parser.add_argument("--model", type=str,
                       default="qwen3-4b-instruct-2507-4bit",
                       help="Model name")

    args = parser.parse_args()

    tester = ChunkingTester(api_url=args.api_url, model=args.model)

    # Process the book
    results = tester.process_book(Path(args.book), max_segments=args.segments)

    # Save results
    tester.save_results(Path(args.output))

    # Also save raw TOON for debugging
    toon_path = Path(args.output).with_suffix('.toon.txt')
    tester.save_raw_toon(toon_path)

    # Print summary
    tester.print_summary()


if __name__ == "__main__":
    main()
