# HUD Boxes

Draws coloured HUD-style boxes over objects in a video. You type a list of words such as `person, car, dog`, and the [Moondream 3.1](https://moondream.ai) vision model finds them in every frame.

Builds on [ComfyUI_VLM_nodes](https://github.com/gokayfem/ComfyUI_VLM_nodes) (required) and doesn't modify it.

## Nodes

### HUD Multi Detect (Moondream)
Runs Moondream detection once for each word and merges all boxes into one `VLM_DETECTIONS` output.

| Input | Notes |
|---|---|
| `model` | From **Moondream 3.1 Loader** (ComfyUI_VLM_nodes) |
| `image` | Video frames, e.g. from **Get Video Components** |
| `objects` | Words to look for, separated by commas or new lines. Each word is one pass over the video, so 3 words take about 3× as long. |
| `fps` | Connect the fps output of Get Video Components |
| `frame_stride` | 1 = every frame, 2 = every other frame (about twice as fast) |
| `parallel_requests`, `max_objects`, `unload_after` | Passed through to Moondream |

Outputs: `detections`, and `objects_found` (box count per word).

### HUD Render Boxes (palette)
Draws the detections onto the frames.

| Input | Notes |
|---|---|
| `palette` | `neon`, `military`, `cyberpunk`, `thermal`, `mono white`, `mono red`, `pastel`, or `custom` |
| `custom_palette` | Hex colours used when palette = custom, e.g. `#FF0000, #00FF00, #0000FF` |
| `color_by` | `word`: one colour per word, in the order you typed them. `each box`: cycles through the palette. |
| `style` | `corners` (HUD brackets), `box`, or `box + corners` |
| `line_width`, `corner_length` | Thickness, and bracket length as a fraction of the box side |
| `fill_opacity` | Tint inside boxes; 0 = outline only |
| `draw_labels`, `show_score`, `uppercase_labels`, `label_size` | Label options |
| `hold_between_frames` | Keeps boxes on frames skipped by `frame_stride`, so they don't flicker |

Works with any `VLM_DETECTIONS` input, not only HUD Multi Detect.

## Typical graph

```
Load Video → Get Video Components ─┬─ images ─→ HUD Multi Detect ─→ HUD Render Boxes → Create Video → Save Video
Moondream 3.1 Loader ──────────────┘   (fps, audio passed to Create Video)
```

Example: [workflows/hud_boxes_multi.json](../../workflows/hud_boxes_multi.json)

## Requirements

- ComfyUI_VLM_nodes with its isolated Moondream 3.1 runtime set up. See [Moondream setup notes](../../resources/moondream-setup.md).
- NVIDIA GPU with an Ampere architecture or newer (RTX 30xx and up).
- On the Moondream Loader you need to accept the [Moondream Model License 1.0](https://moondream.ai/licenses/model/1.0) (`license_accepted`).
