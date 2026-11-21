from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from subtitle_engine import transcribe_file, SUPPORTED_MEDIA

APP_TITLE = "German VLC Subtitle Assistant"
MODE_BILINGUAL = "German + English"
MODE_GERMAN = "German only"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("860x680")
        self.minsize(760, 600)

        self.messages = queue.Queue()
        self.worker = None
        self.cancel_event = threading.Event()
        self.output_path = None
        self._auto_output = ""

        self.file_var = ctk.StringVar()
        self.out_var = ctk.StringVar()
        self.model_var = ctk.StringVar(value="large-v3-turbo")
        self.mode_var = ctk.StringVar(value=MODE_BILINGUAL)

        self._build_ui()
        self.after(150, self._poll_messages)

    # ------------------------------------------------------------------ UI
    def _card(self, parent):
        return ctk.CTkFrame(parent, corner_radius=12)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=APP_TITLE,
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text="German-only or bilingual German + English subtitles, generated locally.",
            text_color=("gray35", "gray65"),
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.theme_switch = ctk.CTkSwitch(
            header, text="Dark mode", command=self._toggle_theme
        )
        self.theme_switch.select()
        self.theme_switch.grid(row=0, column=1, rowspan=2, sticky="e")

        # Files card
        files = self._card(self)
        files.grid(row=1, column=0, sticky="ew", padx=24, pady=8)
        files.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(files, text="Media file", width=90, anchor="w").grid(
            row=0, column=0, padx=(16, 8), pady=(16, 8), sticky="w"
        )
        ctk.CTkEntry(
            files,
            textvariable=self.file_var,
            placeholder_text="Select an audio or video file...",
        ).grid(row=0, column=1, sticky="ew", pady=(16, 8))
        ctk.CTkButton(
            files, text="Choose media...", width=130, command=self._choose_file
        ).grid(row=0, column=2, padx=16, pady=(16, 8))

        ctk.CTkLabel(files, text="Output SRT", width=90, anchor="w").grid(
            row=1, column=0, padx=(16, 8), pady=(8, 16), sticky="w"
        )
        ctk.CTkEntry(
            files,
            textvariable=self.out_var,
            placeholder_text="Where to save the subtitle file...",
        ).grid(row=1, column=1, sticky="ew", pady=(8, 16))
        ctk.CTkButton(
            files,
            text="Save as...",
            width=130,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self._choose_output,
        ).grid(row=1, column=2, padx=16, pady=(8, 16))

        # Options card
        opts = self._card(self)
        opts.grid(row=2, column=0, sticky="ew", padx=24, pady=8)
        opts.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(opts, text="Model").grid(
            row=0, column=0, padx=(16, 8), pady=16, sticky="w"
        )
        ctk.CTkOptionMenu(
            opts,
            variable=self.model_var,
            values=["large-v3-turbo", "large-v3"],
            width=160,
        ).grid(row=0, column=1, padx=(0, 24), pady=16)

        ctk.CTkLabel(opts, text="Subtitles").grid(
            row=0, column=2, padx=(0, 8), pady=16, sticky="w"
        )
        ctk.CTkSegmentedButton(
            opts,
            values=[MODE_BILINGUAL, MODE_GERMAN],
            variable=self.mode_var,
            command=self._on_mode_change,
        ).grid(row=0, column=3, padx=(0, 16), pady=16, sticky="w")

        ctk.CTkLabel(
            opts,
            text="Processing: CPU int8 (recommended for 16 GB RAM)",
            text_color=("gray35", "gray65"),
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, columnspan=4, padx=16, pady=(0, 14), sticky="w")

        # Actions
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=24, pady=8)

        self.start_button = ctk.CTkButton(
            actions,
            text="Generate subtitles",
            height=40,
            width=190,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start,
        )
        self.start_button.pack(side="left")

        self.cancel_button = ctk.CTkButton(
            actions,
            text="Cancel",
            height=40,
            width=100,
            fg_color="gray40",
            hover_color="gray30",
            state="disabled",
            command=self._cancel,
        )
        self.cancel_button.pack(side="left", padx=8)

        self.open_button = ctk.CTkButton(
            actions,
            text="Open output folder",
            height=40,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            state="disabled",
            command=self._open_output,
        )
        self.open_button.pack(side="left")

        # Status + progress
        status = ctk.CTkFrame(self, fg_color="transparent")
        status.grid(row=4, column=0, sticky="ew", padx=24, pady=(8, 0))
        status.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(status, text="Ready", anchor="w")
        self.status_label.grid(row=0, column=0, sticky="w")

        self.progress = ctk.CTkProgressBar(status, mode="determinate")
        self.progress.set(0)
        self.progress.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        # Log
        self.log = ctk.CTkTextbox(
            self,
            wrap="word",
            state="disabled",
            font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=12,
        )
        self.log.grid(row=5, column=0, sticky="nsew", padx=24, pady=(12, 24))
        self.log.tag_config("ok", foreground="#2fa572")
        self.log.tag_config("err", foreground="#e5534b")

        self._log("Ready. Install dependencies and AI models before generating subtitles.")

    # ------------------------------------------------------------- helpers
    def _log(self, text, tag=None):
        self.log.configure(state="normal")
        if tag:
            self.log.insert("end", text + "\n", tag)
        else:
            self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _toggle_theme(self):
        ctk.set_appearance_mode("dark" if self.theme_switch.get() else "light")

    def _suffix(self):
        return "_DE.srt" if self.mode_var.get() == MODE_GERMAN else "_DE_EN.srt"

    def _default_output(self, media):
        p = Path(media)
        return str(p.with_name(p.stem + self._suffix()))

    def _set_running(self, running):
        if running:
            self.start_button.configure(state="disabled")
            self.cancel_button.configure(state="normal")
            self.open_button.configure(state="disabled")
            self.progress.configure(mode="indeterminate")
            self.progress.start()
            self.status_label.configure(text="Working... this can take a while")
        else:
            self.start_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
            self.progress.stop()
            self.progress.configure(mode="determinate")

    # ------------------------------------------------------------ handlers
    def _on_mode_change(self, _value):
        media = self.file_var.get().strip()
        current = self.out_var.get().strip()
        if media and current in ("", self._auto_output):
            new = self._default_output(media)
            self.out_var.set(new)
            self._auto_output = new

    def _choose_file(self):
        extensions = " ".join("*" + ext for ext in sorted(SUPPORTED_MEDIA))
        path = filedialog.askopenfilename(
            title="Select German audio or video",
            filetypes=[("Audio and video", extensions), ("All files", "*.*")],
        )
        if path:
            self.file_var.set(path)
            new = self._default_output(path)
            self.out_var.set(new)
            self._auto_output = new

    def _choose_output(self):
        media = self.file_var.get().strip()
        initial = (Path(media).stem + self._suffix()) if media else "captions" + self._suffix()
        path = filedialog.asksaveasfilename(
            title="Save subtitles",
            defaultextension=".srt",
            initialfile=initial,
            filetypes=[("SubRip subtitles", "*.srt")],
        )
        if path:
            self.out_var.set(path)
            self._auto_output = ""

    def _start(self):
        media = self.file_var.get().strip()
        if not media or not Path(media).is_file():
            messagebox.showerror(
                "Choose a file", "Select an existing audio or video file first."
            )
            return

        if self.worker and self.worker.is_alive():
            return

        output = self.out_var.get().strip()
        if not output:
            messagebox.showerror(
                "Choose an output", "Please specify where to save the subtitle file."
            )
            return

        if Path(output).resolve() == Path(media).resolve():
            messagebox.showerror(
                "Invalid output", "The subtitle output cannot overwrite the media file."
            )
            return

        mode_label = self.mode_var.get()
        subtitle_mode = "german_only" if mode_label == MODE_GERMAN else "bilingual"
        model = self.model_var.get()

        self.cancel_event.clear()
        self._set_running(True)

        self._log(f"Media: {media}")
        self._log(f"Model: {model}")
        self._log(f"Subtitle language: {mode_label}")
        self._log("Starting local processing...")

        self.worker = threading.Thread(
            target=self._run_job,
            args=(media, output, model, subtitle_mode),
            daemon=True,
        )
        self.worker.start()

    def _cancel(self):
        self.cancel_event.set()
        self.cancel_button.configure(state="disabled")
        self.status_label.configure(text="Cancelling...")
        self._log("Cancel requested...")

    def _run_job(self, media, output, model, subtitle_mode):
        try:
            result = transcribe_file(
                media_path=media,
                output_path=output,
                model_name=model,
                compute_type="int8",
                subtitle_mode=subtitle_mode,
                progress=lambda msg: self.messages.put(("log", msg)),
                cancel_check=self.cancel_event.is_set,
            )
            self.messages.put(("done", str(result)))
        except Exception as exc:
            self.messages.put(("error", str(exc)))

    def _poll_messages(self):
        try:
            while True:
                kind, value = self.messages.get_nowait()

                if kind == "log":
                    self._log(value)

                elif kind == "done":
                    self.output_path = value
                    self.out_var.set(value)
                    self._auto_output = ""
                    self._log("SUCCESS: " + value, "ok")
                    self._set_running(False)
                    self.progress.set(1)
                    self.status_label.configure(text="Done")
                    self.open_button.configure(state="normal")

                elif kind == "error":
                    self._log("ERROR: " + value, "err")
                    self._set_running(False)
                    self.progress.set(0)
                    self.status_label.configure(text="Failed")
                    messagebox.showerror("Subtitle generation failed", value)

        except queue.Empty:
            pass

        self.after(150, self._poll_messages)

    def _open_output(self):
        path = self.output_path or self.out_var.get().strip()
        if path and Path(path).exists():
            folder = str(Path(path).parent)
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        else:
            messagebox.showinfo("Output folder", "Generate subtitles first.")


if __name__ == "__main__":
    App().mainloop()