# Contributing to scribeforge

Thanks for your interest! scribeforge is a small, focused tool and contributions
are very welcome — especially around the parts that make it different.

## Where help is most valuable

The loop-repair detector (`scribeforge/asr.py`) is the heart of the project.
Real-world failure samples and tighter heuristics are the highest-value
contributions. See the roadmap in the [README](README.md#roadmap) for the
bigger items (`faster-whisper` backend, VAD pre-pass, timestamps, per-talk
exports).

## Development setup

```bash
git clone https://github.com/KirillRem777/scribeforge
cd scribeforge
python -m pip install -e .
pip install pytest
pytest -q
```

The loop-detector tests need no whisper binary or model — they exercise the
pure heuristics on plain text, so the suite runs anywhere.

## Pull requests

- Keep PRs focused; one logical change per PR.
- Add or update a test when you touch detection logic in `asr.py`.
- Run `pytest -q` before pushing — CI runs the same suite on Python 3.9–3.12.
- Match the existing style: small functions, clear names, comments only where
  the *why* isn't obvious from the code.

## Reporting a loop sample

Found a file where whisper loops and scribeforge missed it (or false-positived)?
Open an issue with: the language, the audio length, and the raw `.txt` whisper
produced (or a snippet showing the repeat). Those samples directly improve the
detector.

## License

By contributing you agree your contributions are licensed under the project's
[MIT License](LICENSE).
