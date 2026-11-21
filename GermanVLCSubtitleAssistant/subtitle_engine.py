from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Callable, Iterable


def set_offline_mode() -> None:
    """Prevent model downloads during transcription."""
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


SUPPORTED_MEDIA = {
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus",
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".mpeg", ".mpg",
}


def timestamp(seconds: float) -> str:
    """Convert seconds to the SRT timestamp format."""
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)

    return (
        f"{hours:02d}:{minutes:02d}:"
        f"{secs:02d},{milliseconds:03d}"
    )


def wrap_caption(text: str, max_chars: int = 44) -> str:
    """Wrap caption text without splitting words."""
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return ""

    words = text.split()
    lines = []
    current = ""

    for word in words:
        if not current:
            current = word
        elif len(current) + len(word) + 1 <= max_chars:
            current += " " + word
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)

    return "\n".join(lines)


def write_srt(
    entries: Iterable[dict],
    output_path: str | Path,
    subtitle_mode: str = "bilingual",
) -> None:
    """
    Write German-only or bilingual SubRip subtitles.

    German-only mode writes just the German transcript.
    Bilingual mode writes German first and English underneath.
    """
    if subtitle_mode not in {"german_only", "bilingual"}:
        raise ValueError(
            "subtitle_mode must be 'german_only' or 'bilingual'."
        )

    output_path = Path(output_path)
    blocks = []

    for index, item in enumerate(entries, 1):
        start = max(0.0, float(item["start"]))
        end = max(float(item["end"]), start + 0.15)

        german = wrap_caption(str(item.get("german", "")))

        if subtitle_mode == "bilingual":
            english = wrap_caption(str(item.get("english", "")))
            caption_text = "\n".join(
                part for part in (german, english) if part
            )
        else:
            caption_text = german

        if caption_text:
            blocks.append(
                f"{index}\n"
                f"{timestamp(start)} --> {timestamp(end)}\n"
                f"{caption_text}"
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        "\n\n".join(blocks) + ("\n" if blocks else ""),
        encoding="utf-8-sig",
    )


def get_translation_function():
    """Load the installed offline German-to-English translator."""
    try:
        import argostranslate.translate as argos_translate

        languages = argos_translate.get_installed_languages()

        german = next(
            (language for language in languages if language.code == "de"),
            None,
        )
        english = next(
            (language for language in languages if language.code == "en"),
            None,
        )

        if german is None or english is None:
            raise RuntimeError(
                "German-to-English translation model is missing. "
                "Run install_models.py while connected to the internet."
            )

        translation = german.get_translation(english)
        return translation.translate

    except ImportError as exc:
        raise RuntimeError(
            "Argos Translate is not installed. "
            "Install the dependencies before running the application."
        ) from exc


def transcribe_file(
    media_path: str | Path,
    output_path: str | Path | None = None,
    model_name: str = "large-v3-turbo",
    compute_type: str = "int8",
    progress: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
    subtitle_mode: str = "bilingual",
) -> Path:
    """
    Transcribe German speech and generate an SRT subtitle file.

    subtitle_mode:
        'german_only' - German captions without translation.
        'bilingual'   - German captions with English underneath.
    """
    if subtitle_mode not in {"german_only", "bilingual"}:
        raise ValueError(
            "Choose 'german_only' or 'bilingual' for subtitle_mode."
        )

    set_offline_mode()

    media_path = Path(media_path).expanduser().resolve()

    if not media_path.is_file():
        raise FileNotFoundError(f"Media file not found: {media_path}")

    if media_path.suffix.lower() not in SUPPORTED_MEDIA:
        raise ValueError(
            f"Unsupported media extension: {media_path.suffix}"
        )

    output = (
        Path(output_path)
        if output_path
        else media_path.with_suffix(".srt")
    )
    output = output.expanduser().resolve()

    if output == media_path:
        raise ValueError(
            "The subtitle output cannot overwrite the media file."
        )

    def report(message: str) -> None:
        if progress:
            progress(message)

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "faster-whisper is missing. Install the project dependencies first."
        ) from exc

    # Only load Argos Translate when English translation is requested.
    translator = None

    if subtitle_mode == "bilingual":
        translator = get_translation_function()

    report(
        f"Loading Whisper model '{model_name}' "
        f"on CPU ({compute_type})..."
    )

    try:
        model = WhisperModel(
            model_name,
            device="cpu",
            compute_type=compute_type,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Could not load model '{model_name}'. "
            "Check that the model is installed and sufficient memory is available."
        ) from exc

    report("Transcribing German speech...")

    segments, info = model.transcribe(
        str(media_path),
        language="de",
        task="transcribe",
        beam_size=5 if model_name == "large-v3" else 3,
        vad_filter=True,
        condition_on_previous_text=True,
        word_timestamps=False,
    )

    entries = []
    started = time.time()

    # faster-whisper returns a lazy segment generator.
    # Iterating over it performs the actual transcription.
    for index, segment in enumerate(segments, 1):
        if cancel_check and cancel_check():
            raise InterruptedError("Subtitle generation cancelled.")

        german = re.sub(r"\s+", " ", segment.text).strip()

        if not german:
            continue

        english = ""

        if translator is not None:
            report(f"Translating caption {index}...")

            try:
                english = translator(german).strip()
            except Exception as exc:
                english = (
                    "[Translation failed - check the installed "
                    "German-to-English model]"
                )
                report(f"Translation warning on caption {index}: {exc}")

        entries.append(
            {
                "start": float(segment.start),
                "end": float(segment.end),
                "german": german,
                "english": english,
            }
        )

        if index % 10 == 0:
            report(f"Processed {index} captions...")

    if not entries:
        raise RuntimeError(
            "No speech was detected. Check the audio and try a clearer recording."
        )

    write_srt(
        entries,
        output,
        subtitle_mode=subtitle_mode,
    )

    elapsed_minutes = (time.time() - started) / 60

    mode_description = (
        "German-only"
        if subtitle_mode == "german_only"
        else "German + English"
    )

    report(
        f"Done: {len(entries)} {mode_description} captions saved to "
        f"{output} (detected language: {info.language}; "
        f"{elapsed_minutes:.1f} minutes elapsed)."
    )

    return output