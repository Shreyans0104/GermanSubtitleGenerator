"""Run while online once to pre-download the Whisper and Argos models."""
from __future__ import annotations
import os
import sys
from pathlib import Path

def main():
    print("This setup downloads model files. It may require several GB of disk space.")
    print("Whisper model: large-v3-turbo (recommended default)")
    from faster_whisper import WhisperModel
    # Instantiating the model downloads it into the Hugging Face cache.
    WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")
    print("Downloaded large-v3-turbo.")
    answer = input("Also download the larger large-v3 model for higher accuracy? [y/N]: ").strip().lower()
    if answer == "y":
        WhisperModel("large-v3", device="cpu", compute_type="int8")
        print("Downloaded large-v3.")

    import argostranslate.package
    import argostranslate.translate
    langs = argostranslate.translate.get_installed_languages()
    have_pair = any(
        l.code == "de" and any(t.to_lang.code == "en" for t in l.translations)
        for l in langs
    )
    if not have_pair:
        print("Refreshing Argos package index…")
        argostranslate.package.update_package_index()
        packages = argostranslate.package.get_available_packages()
        package = next(
            (p for p in packages if p.from_code == "de" and p.to_code == "en"),
            None
        )
        if package is None:
            raise RuntimeError("No German→English package found in the Argos package index.")
        print("Downloading and installing German→English translation package…")
        argostranslate.package.install_from_path(package.download())
    print("German→English translation model is installed.")
    print("\nModel setup complete. You can now run run_offline.bat without internet.")
    print("For stricter offline mode, disconnect Wi-Fi after confirming a successful test.")

if __name__ == "__main__":
    main()
