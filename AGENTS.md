# Codex Instructions for MaaPracticeBoilerplate

This file contains instructions for Codex when working on this project.

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

## Coding Conventions

### File Encoding

- All JSON files should use UTF-8 encoding

## Commit Conventions

- Format: `type: 中文描述` (Conventional Commits with Chinese descriptions)
- Types: `fix`, `feat`, `ci`, `refactor`
- Scope optional: `type(scope): 中文描述`
- Examples:
  - `fix: 优化探险获得装备ocr判定词`
  - `feat: 添加桌面端窗口名匹配`
  - `ci: 优化ci流程，生成并拷贝ico文件`

## Notes

- This is an open-source project; check git status before committing changes
- Pipeline files define automated task sequences
- Interface.json defines user interface and task options

---

# Pipeline Protocol Reference

Documentation: <https://maafw.com/docs/3.1-PipelineProtocol>

## Pipeline v1 Format

Each node contains:

- `recognition`: Recognition algorithm type (DirectHit, TemplateMatch, FeatureMatch, ColorMatch, OCR, NeuralNetworkClassify, NeuralNetworkDetect, And, Or, Custom)
- `action`: Action type (DoNothing, Click, LongPress, Swipe, MultiSwipe, Scroll, ClickKey, LongPressKey, InputText, StartApp, StopApp, StopTask, Command, Shell, Screencap, Custom)
- `next`: List of next nodes to check (sequential matching)
- Other fields: timeout, rate_limit, pre_delay, post_delay, etc.

## Pipeline v2 Format

Recognition and action fields wrapped in nested objects:

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

- **DirectHit**: Execute action without recognition
- **TemplateMatch**: Image template matching ("find image")
- **FeatureMatch**: Feature-based image matching with perspective/size invariance
- **ColorMatch**: Color matching ("find color")
- **OCR**: Text recognition
- **NeuralNetworkClassify**: Deep learning classification for fixed positions
- **NeuralNetworkDetect**: Deep learning object detection
- **And**: Logical AND - all sub-recognitions must match (v5.3+)
- **Or**: Logical OR - first match wins (v5.3+)

## Common Action Types

- **Click**: Click at target location
- **LongPress**: Long press
- **Swipe**: Linear swipe
- **MultiSwipe**: Multi-finger swipe
- **Scroll**: Mouse wheel scroll (v5.1+)
- **ClickKey**: Press key once
- **LongPressKey**: Long press key
- **InputText**: Input text
- **StartApp**: Start application
- **StopApp**: Stop application
- **StopTask**: Stop current task chain
- **Command**: Execute command
- **Shell**: Execute ADB shell command (v5.3+)
- **Screencap**: Save screenshot (v5.8+)

## Key Fields

- `roi`: Recognition region [x, y, w, h], default [0,0,0,0] (full screen)
- `roi_offset`: Additional offset for roi
- `target`: Action target location (default = true = use recognition box)
- `target_offset`: Additional offset for target
- `timeout`: Next list loop timeout in ms, default 20000 (20s), -1 = infinite (v5.5+)
- `rate_limit`: Recognition rate limit in ms, default 1000
- `next`: List of next nodes (checked sequentially)
- `on_error`: Nodes to execute on timeout/action failure

## Node Attributes (v5.1+)

Prefix format: `"[Attribute]NodeName"` or object: `{"name": "NodeName", "attribute": true}`

- `[JumpBack]`: Return to parent node after execution completes
- `[Anchor]Name`: Reference anchor point set by another node

## default_pipeline.json (v5.3+)

Set default parameters for all nodes or specific recognition/action types:

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

Priority: node params > type defaults > Default object defaults > framework defaults
