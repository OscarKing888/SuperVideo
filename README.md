# SuperVideo

Reusable Python module and CLI for extracting selected video frames into JPG files.

## Features

- Default frame extraction: `5`, `10`, `30`
- Recursive directory scanning
- Default scan extension: `mp4`
- Optional scan across common video formats
- Sibling `.cfg` override for frame list, output path, and resize policy
- `ffmpeg` backend with extensible extractor interface
- CLI entrypoint plus `bat` / `sh` wrapper scripts

## Layout

- `src/supervideo_frame_extractor/`: reusable package
- `scripts/extract_frames.bat`: Windows wrapper
- `scripts/extract_frames.sh`: POSIX wrapper
- `tests/`: basic automated coverage

## Quick Start

Run against a single file:

```bash
PYTHONPATH=src python -m supervideo_frame_extractor video/test.mp4
```

Run against a directory and write outputs under `output/`:

```bash
PYTHONPATH=src python -m supervideo_frame_extractor video --output-root output
```

Scan common video formats instead of only `mp4`:

```bash
PYTHONPATH=src python -m supervideo_frame_extractor video --all-common-video-formats
```

Apply a global long-edge limit:

```bash
PYTHONPATH=src python -m supervideo_frame_extractor video/test.mp4 --max-long-side 1280
```

Apply a global shrink divisor:

```bash
PYTHONPATH=src python -m supervideo_frame_extractor video/test.mp4 --scale-divisor 2
```

## CFG Format

If `video/test.mp4` exists, the tool will look for `video/test.cfg`.

The file supports either plain key/value pairs or an `[extract]` section:

```ini
[extract]
frames = 5, 10, 30, 60
output_dir = extracted_frames
scale_divisor = 2
```

Supported keys:

- `frames`: comma or space separated 1-based frame numbers
- `output_dir`: absolute path, or relative to the video file directory
- `scale_divisor`: shrink by divisor, for example `2`
- `max_long_side`: cap the output long edge in pixels

If a cfg file specifies `frames`, `scale_divisor`, `max_long_side`, or `output_dir`, those values override the CLI/global defaults for that video.

## Wrapper Scripts

Windows:

```powershell
scripts\extract_frames.bat video --output-root output
```

POSIX:

```bash
sh scripts/extract_frames.sh video --output-root output
```

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```
