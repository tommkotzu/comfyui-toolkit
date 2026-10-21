# comfyui-toolkit

My own ComfyUI custom nodes, example workflows, and a collection of resources and links.

## Install

Clone into your ComfyUI `custom_nodes` folder and restart ComfyUI:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/tommkotzu/comfyui-toolkit.git
```

Every node pack inside `nodes/` is loaded automatically. If one pack fails to import, the others still load. The error appears in the ComfyUI console.

## Node packs

| Pack | What it does | Category in ComfyUI |
|---|---|---|
| [hud_boxes](nodes/hud_boxes/) | Multi-word Moondream object detection and HUD-style box overlays with your own colour palettes | `HUD Boxes` |

## Workflows

Drag a `.json` from [`workflows/`](workflows/) onto the ComfyUI canvas.

| Workflow | Needs |
|---|---|
| [hud_boxes_multi.json](workflows/hud_boxes_multi.json) | hud_boxes, [ComfyUI_VLM_nodes](https://github.com/gokayfem/ComfyUI_VLM_nodes), optional [TimeSlice-Nodes](https://github.com/systms-ai/TimeSlice-Nodes) |

## Resources

Links, other node packs and setup notes: [resources/](resources/README.md).

## Repo layout

```
__init__.py        loads every pack in nodes/
nodes/<pack>/      one folder per node pack, each with its own README
workflows/         example workflows
resources/         links, notes, troubleshooting
```

To add a new pack, create `nodes/<name>/__init__.py` that exports `NODE_CLASS_MAPPINGS` (and optionally `NODE_DISPLAY_NAME_MAPPINGS`).


External Links and recources

seamless transitions
https://huggingface.co/systms/SYSTMS-FLW-IC-LORA-LTX-2.3
