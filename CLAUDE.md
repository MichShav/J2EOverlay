# CLAUDE.md — J2EOverlay

## What this project is

A PyQt5 desktop app that captures the screen, OCRs Japanese text (Tesseract),
translates it offline (FuguMT / OPUS-MT via Hugging Face Transformers + PyTorch),
and draws English translations in a transparent click-through overlay on top of
the original text. Target users: people playing Japanese games. Targets
Windows 7+ and Linux (X11/Wayland). Python 3.7+.

## Architecture & threading model (CRITICAL — read before editing)

Two threads:

1. **Qt main thread** (`main.py`): UI only — system tray, overlay rendering,
   region selector dialog, timers, hotkey signal handlers.
2. **Worker thread** (`src/pipeline.py` → `TranslationWorker`): ALL heavy work —
   screen capture (mss), OCR, model loading, translation.

Communication is signals-only:

- Main → worker: `CaptureTrigger.fire(region)` → queued onto `worker.process()`.
- Worker → main: `results_ready(list)`, `no_change()`, `error(str)`, `initialized(str)`.

Invariants that MUST hold:

- **Never call Qt widget methods from the worker thread or from pynput
  callbacks.** pynput's `GlobalHotKeys` callbacks run on the listener thread;
  they only emit signals on `HotkeyBridge` (see `main.py`).
- **Never construct `ScreenCapture`/`OCREngine`/`Translator` on the main
  thread.** They're created lazily inside `TranslationWorker._ensure_initialized()`
  on the worker thread. mss instances have thread affinity; model loading takes
  seconds and would freeze the UI.
- **The `_busy` flag in `J2EOverlayApp` is the only job queue.** While a job is
  in flight, new capture requests (auto-capture ticks, hotkey spam) are dropped,
  not queued. Do not add a queue of pending captures — stale frames are useless.
- **Coordinate spaces:** Qt geometry (overlay boxes, region selector) is in
  LOGICAL points; mss capture and OCR boxes are in PHYSICAL pixels. The
  conversion happens in exactly one place — `TranslationWorker.process()`,
  using `device_pixel_ratio` captured at startup. Additionally, `OCREngine`
  upscales images internally before OCR and divides box coordinates back down
  before returning, so its callers always see original-capture pixel space.

## Module map

- `main.py` — app wiring: tray, hotkeys (`pynput.GlobalHotKeys`, config format
  `<ctrl>+<shift>+t`), worker thread setup, `--debug` flag, generated tray icon.
- `src/pipeline.py` — `TranslationWorker`: frame-diff skip (MD5 of 64x36
  grayscale thumbnail), LRU translation cache (`OrderedDict`, max 5000),
  batched translation, `is_valid_translation` filtering, DPI conversion.
- `src/ocr_engine.py` — Tesseract wrapper. Preprocessing: upscale (LANCZOS,
  config `ocr.upscale`, default 2) → grayscale → invert if mean < 128.
  Merges Tesseract word fragments into lines by `(block_num, par_num,
  line_num)` and joins WITHOUT spaces (correct for Japanese). Applies
  `ocr.confidence_threshold`. `is_japanese_text` requires length ≥ 2 and
  ≥ 30% Japanese chars (filters OCR noise).
- `src/translator.py` — offline-first model loading order: custom path →
  fugumt (local cache) → opus-mt (local cache) → fugumt (network, last
  resort, with a message pointing at `download_models.py`). Optional fp16
  on CUDA (`translation.fp16`, off by default — Marian models can emit
  NaNs in half precision), `inference_mode`, `num_beams=4`,
  `no_repeat_ngram_size=3`, truncation at 512, warm-up inference at init.
  `translate()` routes through `translate_batch()` — keep one code path.
- `src/overlay.py` — `TranslationOverlay` (paint-event rendering;
  `set_translations()` replaces all boxes in one repaint) and
  `RegionSelector` (**must remain a `QDialog`** — `main.py` calls `exec_()`).
- `src/screen_capture.py` — mss wrapper. **The region attribute is named
  `_region` deliberately**: a previous bug named it `capture_region`, which
  shadowed the `capture_region()` method on instances and made every region
  capture crash with `TypeError: 'NoneType' object is not callable`. Never
  add an instance attribute named after a method here.
- `src/config.py` — JSON config with dot-notation `get()`. Defaults must stay
  in sync with `config.json` (they drifted once: default service said
  "google" while config.json said "sugoi").
- `download_models.py` — one-time model download script (~400MB fugumt,
  ~300MB opus-mt fallback).

## Historical bugs — do not reintroduce

1. `ScreenCapture` attribute/method shadowing (see above).
2. `RegionSelector` as plain `QWidget` → `exec_()` AttributeError.
3. Hotkey listener that was an empty stub (`on_press` → `pass`).
4. Pipeline running synchronously on the Qt main thread.
5. Per-word translation of Japanese fragments (must merge lines first).
6. Config `confidence_threshold` accepted but never applied.
7. `translate()` missing `truncation=True` (batch path had it, single didn't).
8. Tray icon with no icon set → invisible on Windows; icon is generated at
   runtime in `make_tray_icon()`.
9. `TranslationOverlay` attribute named `font` shadowed `QWidget.font()`;
   it is now `overlay_font`. Same rule as `ScreenCapture`: never name an
   instance attribute after a Qt method.

## Running & debugging

```bash
pip install -r requirements.txt   # PyQt5, Pillow, pytesseract, mss, pynput, torch, transformers
python download_models.py        # one-time, needs internet
python main.py                   # or: python main.py --debug
```

External dependency: Tesseract ≥ 4.0 with `jpn` traineddata must be installed
on the system (`tesseract-ocr-jpn` on Debian/Ubuntu; UB-Mannheim installer on
Windows). `OCREngine._setup_tesseract` probes common Windows paths;
`ocr.tesseract_path` in config.json overrides.

Logging uses the `logging` module (logger names: `j2eoverlay`, module
loggers). Use `--debug` for verbose output. Do not add `print()` calls.

## Test status

There are NO automated tests in the repo yet. The current code was verified by:

- `py_compile` on all modules.
- Ad-hoc unit checks (stubbed pytesseract) of: line merging, noise filtering,
  upscale coordinate scale-back, dark-image inversion, `is_japanese_text`,
  config keys. These checks are not committed.

**Not yet verified on real hardware** (good first tasks):

- Overlay box alignment on a high-DPI / scaled Windows display.
- Multi-monitor behavior (overlay covers primary screen only; mss monitor
  index handling is simplistic; a monitor-selection config key would need
  to be reintroduced alongside overlay/DPI changes).
- `--psm 11` vs `--psm 6` quality for full-screen capture.
- GlobalHotKeys on Wayland (pynput global hooks often don't work there —
  tray menu is the fallback).
- **Whether mss captures the overlay window itself.** If it does (likely
  on X11; on Windows, GDI BitBlt normally skips layered windows), auto-
  capture enters a feedback loop: the overlay covers the Japanese text,
  the next OCR pass finds nothing, the overlay clears, the text is
  re-detected, the overlay redraws — visible blinking every tick. The fix
  would be hide-overlay → short delay → capture → show, coordinated from
  the main thread. Do not implement it blind; verify the problem exists
  on the target platform first.
- End-to-end run with real Tesseract + models.

A proper pytest suite for `ocr_engine` (with a stubbed `pytesseract`) and
`pipeline` (with stubbed components) would be valuable; the merging and
coordinate logic is pure and easily testable.

## Config reference (config.json)

- `hotkey.*` — pynput GlobalHotKeys format, e.g. `<ctrl>+<shift>+t`.
- `ocr.language` (`jpn`, or `jpn+jpn_vert` for vertical text),
  `ocr.psm` (6 = region, 11 = full screen), `ocr.confidence_threshold` (0–100),
  `ocr.upscale` (int ≥ 1), `ocr.tesseract_path`.
- `translation.model_path` — custom local model dir;
  `translation.fp16` — half precision on CUDA (off by default, NaN risk).
- `overlay.*` — colors/font/opacity, read once at startup.
- `capture.scan_interval` — auto-capture period in ms.

## Conventions

- Python stdlib `logging`, type hints on public methods, docstrings on classes
  and non-trivial methods.
- Keep `src/config.py` defaults and `config.json` in sync when adding keys.
- New heavy operations go in the worker; new UI goes in the main thread.
- Keep `requirements.txt` minimal; torch/transformers are already the heavy part.

## Roadmap candidates (from README)

manga-ocr backend (much better than Tesseract for stylized game fonts; keep
Tesseract for box detection or make backend configurable), DeepL/Azure
services, custom glossary, translation history, multi-monitor support,
macOS support, packaging (`pyproject.toml` + entry point — the
`sys.path.insert` in `main.py` is a hack worth removing).
