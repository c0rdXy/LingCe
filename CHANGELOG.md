# Changelog

## V0.0.8

- 解决一些已知 BUG。
- Fix practice range persistence after returning to the main screen.
- Keep "continue last" and range selection from overwriting each other.
- Restore wrong-question review from saved history after re-entering practice mode.
- Add the official GitHub icon on the home screen with a Star prompt tooltip.
- Remove obsolete no-op/commented code left from earlier iterations.

## V0.0.7

- Stop tracking local runtime data and keep `data/user_data.json` ignored.
- Add `data/user_data.example.json` as the user data structure example.
- Add settings import, export, and reset-to-defaults actions.
- Auto-load the bundled sample question bank on first launch when no previous bank exists.
- Add `scripts/release_check.py` for version, staged runtime data, large file, mojibake, compile, and test checks.
- Update README with local data and release check notes.

## V0.0.6

- Add configurable system settings for app name, subtitle, theme, exam duration, pass score, question type counts, and scores.
- Improve exam review behavior, answer display, and question status grid highlighting.
- Add exam history clearing from the statistics panel.
- Keep runtime settings and exam history out of version control.

## V0.0.4

- Fix dark theme display issues across main, practice, and exam screens.
- Refine practice mode flow and exam navigation controls.

## V0.0.3

- Improve window centering and startup display behavior.
- Fix startup loading order and reduce window flicker.
