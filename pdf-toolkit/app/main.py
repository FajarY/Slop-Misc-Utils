"""PDF Toolkit: an offline desktop app for everyday PDF and image chores."""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

import webview
from webview.dom import DOMEventHandler

import ops

APP_NAME = "PDF Toolkit"
APP_VERSION = "1.0.0"

PDF_TYPES = ("PDF files (*.pdf)",)
IMAGE_TYPES = ("Images (*.jpg;*.jpeg;*.png;*.webp;*.bmp;*.tif;*.tiff)",)
TOOL_FILE_TYPES = {
    "compress-pdf": PDF_TYPES,
    "merge-pdf": PDF_TYPES,
    "pdf-to-images": PDF_TYPES,
    "compress-images": IMAGE_TYPES,
    "images-to-pdf": IMAGE_TYPES,
}


def resource_dir() -> Path:
    # PyInstaller unpacks bundled data into sys._MEIPASS.
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def system_uses_dark_theme() -> bool:
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        return False


def safe_file_name(name: str, fallback: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", (name or "").strip()).strip(" .")
    if name.lower().endswith(".pdf"):
        name = name[:-4]
    return name or fallback


class Api:
    """Methods exposed to JavaScript as window.pywebview.api.*

    pywebview runs each call on its own thread and hands JS a promise.
    """

    def __init__(self) -> None:
        self._window: webview.Window | None = None
        self._cancel = threading.Event()
        self._job_lock = threading.Lock()

    def attach(self, window: webview.Window) -> None:
        self._window = window

    # -- file selection ----------------------------------------------------- #

    def pick_files(self, tool: str) -> list[dict]:
        paths = self._window.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=True,
            file_types=TOOL_FILE_TYPES.get(tool, PDF_TYPES) + ("All files (*.*)",),
        )
        return self.describe(list(paths or []))

    def pick_folder(self) -> str | None:
        result = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        return result[0] if result else None

    def describe(self, paths: list[str]) -> list[dict]:
        files = []
        for p in ops.expand_paths(paths):
            kind = ops.file_kind(p)
            if kind:
                files.append({
                    "path": p,
                    "name": os.path.basename(p),
                    "size": os.path.getsize(p),
                    "kind": kind,
                })
        return files

    def thumbnail(self, path: str) -> dict:
        data, pages = ops.thumbnail_png(path)
        uri = "data:image/png;base64," + base64.b64encode(data).decode() if data else None
        return {"thumb": uri, "pages": pages}

    # -- running jobs ------------------------------------------------------- #

    def cancel(self) -> None:
        self._cancel.set()

    def run(self, tool: str, paths: list[str], options: dict) -> dict:
        if not self._job_lock.acquire(blocking=False):
            return {"error": "Another job is already running", "results": []}
        self._cancel.clear()
        results: list[dict] = []
        try:
            self._run(tool, paths, options or {}, results)
        except ops.OperationCancelled:
            return {"cancelled": True, "results": results}
        except Exception as exc:  # surfaced to the UI as a message
            return {"error": str(exc), "results": results}
        finally:
            self._job_lock.release()
        return {"results": results}

    def _run(self, tool: str, paths: list[str], opt: dict, results: list[dict]) -> None:
        out_dir = opt.get("outputDir") or None

        if tool in ("merge-pdf", "images-to-pdf"):
            default = "merged" if tool == "merge-pdf" else "images"
            folder = Path(out_dir or Path(paths[0]).parent)
            out = ops.unique_path(folder / (safe_file_name(opt.get("fileName"), default) + ".pdf"))
            if tool == "merge-pdf":
                results.append(ops.merge_pdfs(paths, str(out), self._progress, self._cancel.is_set))
            else:
                results.append(ops.images_to_pdf(
                    paths, str(out),
                    page_size=opt.get("pageSize", "fit"),
                    orientation=opt.get("orientation", "auto"),
                    margin=float(opt.get("margin", 0)),
                    progress=self._progress,
                    cancelled=self._cancel.is_set,
                ))
            self._progress(1, "Done")
            return

        total = len(paths)
        for i, path in enumerate(paths):
            if self._cancel.is_set():
                raise ops.OperationCancelled()
            name = os.path.basename(path)
            self._progress(i / total, f"{name} ({i + 1} of {total})")

            def sub_progress(fraction: float, message: str, i=i, name=name) -> None:
                self._progress((i + fraction) / total, f"{name}: {message}")

            try:
                if tool == "compress-pdf":
                    r = ops.compress_pdf(path, out_dir, opt.get("level", "recommended"),
                                         bool(opt.get("grayscale")))
                elif tool == "compress-images":
                    r = ops.compress_image(path, out_dir, int(opt.get("quality", 75)),
                                           int(opt.get("maxDim", 0)), opt.get("format", "keep"))
                elif tool == "pdf-to-images":
                    r = ops.pdf_to_images(path, out_dir, opt.get("format", "png"),
                                          int(opt.get("dpi", 150)), opt.get("pages", ""),
                                          sub_progress, self._cancel.is_set)
                else:
                    raise ValueError(f"Unknown tool {tool}")
            except ops.OperationCancelled:
                raise
            except Exception as exc:
                r = {"source": path, "output": None, "ok": False, "error": str(exc)}
            results.append(r)
        self._progress(1, "Done")

    def _progress(self, fraction: float, message: str) -> None:
        payload = json.dumps({"fraction": max(0.0, min(1.0, fraction)), "message": message})
        try:
            self._window.evaluate_js(f"window.app && window.app.onProgress({payload})")
        except Exception:
            pass

    # -- results ------------------------------------------------------------ #

    def reveal(self, path: str) -> None:
        """Open Explorer with the file selected (or the folder opened)."""
        p = Path(path)
        if p.is_dir():
            os.startfile(p)
        elif p.exists():
            subprocess.Popen(["explorer", "/select,", str(p)])

    def open_path(self, path: str) -> None:
        if Path(path).exists():
            os.startfile(path)

    def app_info(self) -> dict:
        return {"name": APP_NAME, "version": APP_VERSION}


def _enable_file_drop(window: webview.Window) -> None:
    """Native file drops: the browser side can't see full paths, Python can."""

    def on_drop(event: dict) -> None:
        files = (event.get("dataTransfer") or {}).get("files") or []
        paths = [f.get("pywebviewFullPath") for f in files if f.get("pywebviewFullPath")]
        if paths:
            window.evaluate_js(f"window.app && window.app.addPaths({json.dumps(paths)})")

    def ignore(_event: dict) -> None:
        pass

    doc_events = window.dom.document.events
    doc_events.dragenter += DOMEventHandler(ignore, True, False)
    doc_events.dragover += DOMEventHandler(ignore, True, False, debounce=500)
    doc_events.drop += DOMEventHandler(on_drop, True, False)


def _use_dark_title_bar(window: webview.Window) -> None:
    try:
        import ctypes

        hwnd = window.native.Handle.ToInt32()
        on = ctypes.c_int(1)
        # DWMWA_USE_IMMERSIVE_DARK_MODE (20 on Windows 10 20H1+ and 11)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(on), ctypes.sizeof(on))
    except Exception:
        pass


def main() -> None:
    dark = system_uses_dark_theme()
    api = Api()
    window = webview.create_window(
        APP_NAME,
        url=str(resource_dir() / "ui" / "index.html"),
        js_api=api,
        width=1180,
        height=780,
        min_size=(920, 620),
        background_color="#16171b" if dark else "#f6f7f9",
    )
    api.attach(window)

    def on_start(win: webview.Window) -> None:
        if dark:
            _use_dark_title_bar(win)
        _enable_file_drop(win)

    webview.start(on_start, window, debug=bool(os.environ.get("PDF_TOOLKIT_DEBUG")))


if __name__ == "__main__":
    main()
