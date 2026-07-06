# Agent 项目参考

本文档放置不需要每次新对话都完整加载的背景、长命令和协议摘要。高频规则保留在根目录 `AGENTS.md`。

## Project Overview

- Type: MaaFramework Automation Project for Princess Connect! Re:Dive (PCR)
- Purpose: Automated gameplay for PCR with support for multiple servers

## File Structure

```plaintext
assets/
├── interface.json           # UI and task definitions
├── resource/
│   ├── image/              # Image templates
│   │   ├── jp/            # Japanese server images
│   │   ├── role/          # Character images
│   │   ├── tw/            # Taiwan server images
│   │   └── Delicacy/      # Food/cooking images
│   └── pipeline/          # Task pipeline definitions
```

## Validation Commands

After changing Limingjie pipeline JSON:

```powershell
Get-ChildItem assets\resource\pipeline\limingjie*.json | ForEach-Object { & 'C:\Users\SMALL\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m json.tool $_.FullName | Out-Null }
git diff --check
```

For nontrivial route changes, also check duplicate nodes, duplicate routes, and missing route targets:

```powershell
@'
import json
import re
from pathlib import Path

data = {}
duplicate_nodes = []
for path in sorted(Path("assets/resource/pipeline").glob("limingjie*.json")):
    part = json.loads(path.read_text(encoding="utf-8"))
    for name, node in part.items():
        if name in data:
            duplicate_nodes.append((name, str(path)))
        data[name] = node

duplicate_routes = []
missing = []
for name, node in data.items():
    seen = []
    for field in ("next", "on_error"):
        value = node.get(field) if isinstance(node, dict) else None
        if isinstance(value, list):
            for route in value:
                if route in seen:
                    duplicate_routes.append((name, route))
                seen.append(route)

    for field in ("next", "on_error", "all_of", "any_of"):
        value = node.get(field) if isinstance(node, dict) else None
        if isinstance(value, list):
            for route in value:
                if isinstance(route, str):
                    target = re.sub(r"^(\[[^\]]+\])+", "", route)
                    if target not in data:
                        missing.append((name, field, route, target))

print("duplicate_nodes", duplicate_nodes)
print("duplicate_routes", duplicate_routes)
print("missing", missing)
'@ | & 'C:\Users\SMALL\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -
```

Check for corrupted Chinese keys after risky JSON edits:

```powershell
@'
import json
from pathlib import Path

data = {}
for path in Path("assets/resource/pipeline").glob("limingjie*.json"):
    data.update(json.loads(path.read_text(encoding="utf-8")))
print([key for key in data if "?" in key])
'@ | & 'C:\Users\SMALL\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -
```

## Template Score Testing

Use local matching to verify whether a template/ROI is actually viable before editing pipeline thresholds. Keep the script read-only for score checks.

PowerShell can corrupt Chinese paths in piped Python. Use Unicode escapes for paths such as `MuMu\u5171\u4eab\u6587\u4ef6\u5939`.

Minimal NCC tester using `PIL` and `numpy`:

```powershell
@'
from pathlib import Path
from PIL import Image
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

root = Path("D:/VSCProject/MaaPCR")
screen_path = "D:/Documents/MuMu\\u5171\\u4eab\\u6587\\u4ef6\\u5939/Screenshots/example.png"
template_path = root / "assets/resource/image/jp/limingjie/example.png"
roi = (0, 0, 1280, 720)

screen = Image.open(screen_path).convert("L")
template = Image.open(template_path).convert("L")
x, y, w, h = roi
src = np.asarray(screen.crop((x, y, x + w, y + h)))
tpl = np.asarray(template)

th, tw = tpl.shape
windows = sliding_window_view(src, (th, tw))
tpl0 = tpl.astype(np.float32) - tpl.mean()
tpl_norm = np.sqrt((tpl0 * tpl0).sum())
wins = windows.astype(np.float32)
centered = wins - wins.mean(axis=(-1, -2), keepdims=True)
denom = np.sqrt((centered * centered).sum(axis=(-1, -2))) * tpl_norm
numer = (centered * tpl0).sum(axis=(-1, -2))
scores = np.where(denom > 1e-6, numer / denom, 0)
best_y, best_x = np.unravel_index(np.argmax(scores), scores.shape)
print("score", float(scores[best_y, best_x]))
print("box", [x + int(best_x), y + int(best_y), tw, th])
'@ | & 'C:\Users\SMALL\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -
```

## Pipeline Protocol Reference

Documentation: <https://maafw.com/docs/3.1-PipelineProtocol>

## Pipeline v1 Format

Each node contains:

- `recognition`: Recognition algorithm type, such as `DirectHit`, `TemplateMatch`, `OCR`, `And`, `Or`, `Custom`
- `action`: Action type, such as `DoNothing`, `Click`, `Swipe`, `StopTask`, `Custom`
- `next`: List of next nodes to check sequentially
- Other fields: `timeout`, `rate_limit`, `pre_delay`, `post_delay`

## Pipeline v2 Format

Recognition and action fields can be wrapped in nested objects:

```jsonc
{
    "NodeA": {
        "recognition": {
            "type": "TemplateMatch",
            "param": {
                "template": "A.png",
                "roi": [100, 100, 10, 10]
            }
        },
        "action": {
            "type": "Click",
            "param": {
                "target": "XXX"
            }
        },
        "next": ["NodeB"],
        "pre_delay": 1000
    }
}
```

## Common Recognition Types

- `DirectHit`: Execute action without recognition
- `TemplateMatch`: Image template matching
- `FeatureMatch`: Feature-based matching with perspective/size invariance
- `ColorMatch`: Color matching
- `OCR`: Text recognition
- `NeuralNetworkClassify`: Fixed-position classification
- `NeuralNetworkDetect`: Object detection
- `And`: All sub-recognitions must match
- `Or`: First matching sub-recognition wins

## Common Action Types

- `Click`, `LongPress`
- `Swipe`, `MultiSwipe`, `Scroll`
- `ClickKey`, `LongPressKey`, `InputText`
- `StartApp`, `StopApp`, `StopTask`
- `Command`, `Shell`, `Screencap`
- `Custom`

## Key Fields

- `roi`: Recognition region `[x, y, w, h]`, default full screen
- `roi_offset`: Additional offset for `roi`
- `target`: Action target location, default `true` uses recognition box
- `target_offset`: Additional offset for target
- `timeout`: Next-list loop timeout in ms, default `20000`; `-1` means infinite
- `rate_limit`: Recognition rate limit in ms, default `1000`
- `next`: Sequential routes
- `on_error`: Routes to execute on timeout/action failure

## Node Attributes

Prefix format: `"[Attribute]NodeName"` or object form: `{"name": "NodeName", "attribute": true}`.

- `[JumpBack]`: Return to parent node after execution completes
- `[Anchor]Name`: Reference anchor point set by another node

## default_pipeline.json

Default parameters can be set globally or by recognition/action type:

```jsonc
{
    "Default": {
        "rate_limit": 1000,
        "timeout": 20000,
        "pre_delay": 200
    },
    "TemplateMatch": {
        "threshold": 0.7
    },
    "Click": {
        "target": true
    }
}
```

Priority: node params > type defaults > `Default` object defaults > framework defaults.
