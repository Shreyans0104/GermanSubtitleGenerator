# German VLC Subtitle Assistant

A Windows desktop tool that transcribes German audio/video locally and writes a bilingual SubRip (`.srt`) file. German appears first, English underneath. VLC on Windows and VLC for Android can play the original media with the external subtitle file.

## Requirements

- Windows 10 or 11, 64-bit
- Python 3.11, 64-bit
- 16 GB RAM is a reasonable starting point for CPU `int8` inference
- Several GB free disk space for packages and model weights; `large-v3` uses substantially more disk and memory than `large-v3-turbo`
- Internet is needed only for initial dependency/model installation. Processing is local afterward.

## Quick start

1. Extract this folder somewhere writable, e.g. `C:\GermanVLCSubtitleAssistant`.
2. Install **Python 3.11 x64** from https://www.python.org/downloads/windows/. During installation, enable the Python launcher / PATH options.
3. While online, double-click `setup_online.bat`.
4. When it finishes, double-click `install_models.bat`. This downloads `large-v3-turbo` and the offline German→English Argos translation package. You can optionally download `large-v3` too.
5. Double-click `run_offline.bat`.
6. Select your German MP3/WAV/M4A/FLAC or MP4/MKV/AVI/MOV/WebM file.
7. Choose `large-v3-turbo` for the default balance, or `large-v3` for a potentially more accurate but slower model.
8. Click **Generate bilingual subtitles**. The `.srt` defaults to the same folder and base name as the media.

No separate FFmpeg installation is required by this implementation; faster-whisper uses PyAV for decoding. Some unusual or damaged media files may still fail to decode.

## Offline behavior

- Install Python dependencies and models while online.
- `install_models.bat` downloads model files; do not skip this step.
- `run_offline.bat` sets Hugging Face offline flags before the application starts.
- After a successful first test, disconnect from the internet and generate subtitles for another file to verify your offline setup.
- Keep the `.venv` directory and the model caches. Removing them may require reinstalling dependencies or models.

The Hugging Face model cache is usually under `%USERPROFILE%\.cache\huggingface\hub`. Argos model data is managed by Argos Translate in its local application data. Do not delete these caches if you want to retain offline operation.

## VLC on Windows

The app writes `YourVideo.srt` beside `YourVideo.mp4` by default. Open the video in VLC. If subtitles do not appear automatically, choose **Subtitle → Add Subtitle File…** and select the `.srt`.

## VLC on Android over USB

1. Connect the Android phone to the PC and choose **File transfer** on the phone.
2. Copy the media file and its matching `.srt` file into the same folder on the phone. Keep the base names identical, e.g. `Lektion.mp4` and `Lektion.srt`.
3. Open the media in VLC for Android. If it doesn't auto-load, open the subtitle menu and select the external subtitle file.
4. Ensure VLC's subtitle auto-load setting is enabled if you want it to find matching files automatically.

Example output:

```srt
1
00:00:01,200 --> 00:00:04,000
Guten Morgen! Wie geht es dir heute?
Good morning! How are you today?
```

## Accuracy notes

- The app explicitly transcribes German (`language="de"`); it does not translate the audio directly.
- `large-v3` may perform better than `large-v3-turbo` on some difficult recordings, but actual results depend on accent, noise, music, recording quality and vocabulary.
- Argos Translate is fully offline, but its translation quality is not equivalent to every cloud-based neural translation service. Check important vocabulary and idioms.
- Each speech segment is translated separately. This preserves timestamps but can lose context across long sentences.
- Very long speech segments may wrap to multiple lines; check playback and adjust the caption width if needed.
- CPU processing can be slower than real time, especially with `large-v3`. The program is designed to prioritize local operation and a straightforward setup.

## Tests

Run `test_project.bat`. The included unit tests check SRT timestamp formatting, line wrapping, UTF-8 output, and bilingual line order. They do not test model accuracy or real media decoding.

## Troubleshooting

- **Model missing/offline error:** reconnect to the internet and run `install_models.bat`.
- **Argos translation model missing:** run `install_models.bat` online again and watch for errors.
- **Out of memory / very slow:** close other programs and use `large-v3-turbo`. Do not start multiple transcriptions at once.
- **No speech detected:** check volume and whether the file actually contains speech; try another source file.
- **Subtitle timing looks off:** test the source in VLC and compare with the generated timestamps. The output uses Whisper segment timestamps.
- **Accents/umlauts appear wrong:** VLC should read UTF-8 SRT; try VLC's subtitle encoding setting if needed.

## Project files

- `app.py` — Tkinter desktop GUI
- `subtitle_engine.py` — local transcription, translation and SRT generation
- `install_models.py` — one-time model download / installation
- `requirements.txt` — pinned Python dependencies
- `tests/test_srt.py` — unit tests
- `setup_online.bat`, `install_models.bat`, `run_offline.bat`, `test_project.bat` — Windows launchers
