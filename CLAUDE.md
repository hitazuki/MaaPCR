# Codex Instructions for MaaPCR

This repo is a MaaFramework automation project for Princess Connect! Re:Dive.

## Read First

- Work inside `D:\VSCProject\MaaPCR`.
- Check `git status` before commits or large edits. Do not revert user changes unless explicitly asked.
- For Limingjie (`黎明界`) pipeline, map, or template work, read `docs/zh_cn/黎明界实现注意事项.md` first.
- Detailed project layout, Maa pipeline protocol notes, and longer validation snippets live in `docs/zh_cn/Agent项目参考.md`.

## Windows / Python / Encoding

- JSON files must stay UTF-8.
- Chinese node names in pipeline JSON are easy to corrupt through PowerShell pipes. Prefer `apply_patch` for small edits.
- If a script must reference Chinese strings or paths through PowerShell, use Unicode escapes such as `"\u9ece\u660e\u754c"` or `Path('D:/Documents/MuMu\\u5171\\u4eab\\u6587\\u4ef6\\u5939/...')`.
- `python` may not be on `PATH`. Use the bundled runtime when needed:
  `C:\Users\SMALL\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`
- Avoid embedding Chinese literals in piped inline Python that writes files; PowerShell can convert them to `???`.

## Pipeline Editing

- Pipeline files define automation state machines under `assets/resource/pipeline/`.
- Do not send click actions that trigger page transitions directly back to a broad global router unless the page is already stable.
- Avoid duplicate routes in the same node. A target appearing in both `next` and `on_error` can be reported as `Duplicate route`.
- Prefer template matching over OCR when the UI element is stable and visually distinctive.
- Use two-coordinate click targets such as `[x, y]` unless the feature specifically requires a four-value target.
- After pipeline edits, validate JSON, duplicate/missing routes, and `git diff --check`; see `docs/zh_cn/Agent项目参考.md` for commands.

## Image Templates

- Current PCR recognition resolution is `1280x720`; crop templates directly from 720p screenshots or frames without stretching.
- Avoid variable UI in templates: counters, stamina, currency, notification badges, changing bottom numbers, temporary labels, click flashes, loading overlays, and transition blur.
- Prefer compact templates with stable distinctive features.
- Keep highlighted/clickable and dim/non-clickable states as separate templates.
- For common buttons with general meaning, first search and compare templates under `assets/resource/image/jp/common/`. If no suitable common template exists, create the reusable button template in that `common` folder instead of a feature folder.

## Recognition Score Testing

- When a template misses, test the candidate template against the screenshot locally before changing thresholds or ROIs.
- Use the same 720p screenshot and a small ROI around the expected position; compare best score and best box.
- If `cv2` is unavailable, use the bundled Python runtime with `PIL`/`numpy` NCC matching. Keep these tests read-only unless you are deliberately generating a new cropped template.
- Record useful scores in the final answer, especially old score vs new score and the chosen ROI/threshold.

## Commit Conventions

- Format: `type(scope): 中文描述`
- Common types: `fix`, `feat`, `ci`, `refactor`
- Examples:
  - `fix(limingjie): 优化探险获得装备ocr判定词`
  - `feat(desktop): 添加桌面端窗口名匹配`
  - `ci(build): 优化ci流程，生成并拷贝ico文件`
