"""HUD Boxes: multi-word Moondream detection and palette-controlled box rendering.

Builds on ComfyUI_VLM_nodes (must be installed). Nothing in that pack is modified.
"""

import sys

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

PALETTES = {
    "neon": "#00FFC8, #FF2D95, #FFE600, #00A2FF, #B026FF, #FF6B00",
    "military": "#7CFF4F, #C8FF00, #3DDC84, #E0E0E0, #FFB000",
    "cyberpunk": "#FCEE0A, #00F0FF, #FF003C, #8A2BE2, #39FF14",
    "thermal": "#FFFFFF, #FFD000, #FF7A00, #FF0040, #A000FF",
    "mono white": "#FFFFFF",
    "mono red": "#FF2A2A",
    "pastel": "#A0E7E5, #FFAEBC, #FBE7C6, #B4F8C8, #CDB4DB",
}


def _vlm_module(suffix):
    for name, module in list(sys.modules.items()):
        if name.endswith("ComfyUI_VLM_nodes.nodes." + suffix) or name == "ComfyUI_VLM_nodes.nodes." + suffix:
            return module
    raise RuntimeError("HUD Boxes needs ComfyUI_VLM_nodes to be installed and loaded.")


def _parse_words(text):
    words = []
    for part in text.replace("\n", ",").split(","):
        word = part.strip()
        if word and word not in words:
            words.append(word)
    if not words:
        raise ValueError("Enter at least one word to look for, e.g. person, car, dog")
    return words


def _parse_hex(value):
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    if len(value) != 6:
        raise ValueError(f"Bad colour '{value}': use #RRGGBB, e.g. #00FFC8")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _parse_palette(preset, custom):
    text = custom if preset == "custom" else PALETTES[preset]
    colors = [_parse_hex(c) for c in text.replace("\n", ",").split(",") if c.strip()]
    if not colors:
        raise ValueError("Palette is empty: enter hex colours like #00FFC8, #FF2D95")
    return colors


def _font(size):
    for name in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "LiberationSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


class HUDMultiDetect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MOONDREAM31_MODEL",),
                "image": ("IMAGE",),
                "objects": ("STRING", {
                    "multiline": True,
                    "default": "person, car",
                    "tooltip": "Words to look for, separated by commas or new lines. Each word is one detection pass.",
                }),
                "fps": ("FLOAT", {"default": 30.0, "min": 0.001, "max": 1000.0, "step": 0.001}),
                "frame_stride": ("INT", {"default": 2, "min": 1, "max": 100000,
                                         "tooltip": "1 analyses every frame; 2 every other frame (faster)."}),
                "parallel_requests": ("INT", {"default": 4, "min": 1, "max": 32}),
                "max_objects": ("INT", {"default": 100, "min": 1, "max": 1000,
                                        "tooltip": "Max boxes per word per frame."}),
                "unload_after": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("VLM_DETECTIONS", "STRING")
    RETURN_NAMES = ("detections", "objects_found")
    FUNCTION = "detect"
    CATEGORY = "HUD Boxes"
    DESCRIPTION = "Runs Moondream detect once per word and merges all boxes into one detections output."

    def detect(self, model, image, objects, fps, frame_stride, parallel_requests, max_objects, unload_after):
        md = _vlm_module("moondream31")
        vt = _vlm_module("vision_types")
        words = _parse_words(objects)
        detector = md.Moondream31Detect()

        sequences = []
        for i, word in enumerate(words):
            last = i == len(words) - 1
            seq = detector.detect(model, image, word, fps, frame_stride, parallel_requests,
                                  max_objects, unload_after and last)[0]
            sequences.append(seq)

        merged = {}
        for seq in sequences:
            for frame in seq.frames:
                entry = merged.setdefault(frame.frame_index, [frame.timestamp, []])
                entry[1].extend(frame.detections)

        first = sequences[0]
        frames = tuple(
            vt.FrameDetections(
                frame_index=index,
                timestamp=merged[index][0],
                width=first.width,
                height=first.height,
                detections=tuple(merged[index][1]),
            )
            for index in sorted(merged)
        )
        sequence = vt.DetectionSequence(
            width=first.width,
            height=first.height,
            frames=frames,
            frame_count=max(s.frame_count for s in sequences),
            fps=first.fps,
            source=first.source,
            metadata={"hud_objects": words},
        )
        counts = {w: 0 for w in words}
        for det in sequence.all_detections():
            if det.label in counts:
                counts[det.label] += 1
        summary = "\n".join(f"{w}: {n} boxes" for w, n in counts.items())
        return (sequence, summary)


class HUDRenderBoxes:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "detections": ("VLM_DETECTIONS",),
                "palette": (list(PALETTES) + ["custom"], {"default": "neon",
                            "tooltip": "Colour set. Each word gets the next colour in order."}),
                "custom_palette": ("STRING", {"multiline": False, "default": "#00FFC8, #FF2D95, #FFE600",
                                   "tooltip": "Used when palette = custom. Hex colours, comma separated, in word order."}),
                "color_by": (["word", "each box"], {"default": "word"}),
                "style": (["box", "corners", "box + corners"], {"default": "corners"}),
                "line_width": ("INT", {"default": 3, "min": 1, "max": 32}),
                "corner_length": ("FLOAT", {"default": 0.25, "min": 0.05, "max": 0.5, "step": 0.05,
                                  "tooltip": "Corner bracket length as a fraction of the box side."}),
                "fill_opacity": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.05,
                                 "tooltip": "Tinted fill inside boxes. 0 = outline only."}),
                "draw_labels": ("BOOLEAN", {"default": True}),
                "show_score": ("BOOLEAN", {"default": False}),
                "uppercase_labels": ("BOOLEAN", {"default": True}),
                "label_size": ("INT", {"default": 16, "min": 6, "max": 96}),
                "hold_between_frames": ("BOOLEAN", {"default": True,
                                        "tooltip": "With frame_stride > 1, keep boxes on skipped frames so they don't flicker."}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("overlay",)
    FUNCTION = "render"
    CATEGORY = "HUD Boxes"
    DESCRIPTION = "Draws detection boxes with your own colour palette and HUD-style corners."

    def render(self, image, detections, palette, custom_palette, color_by, style, line_width,
               corner_length, fill_opacity, draw_labels, show_score, uppercase_labels, label_size,
               hold_between_frames):
        colors = _parse_palette(palette, custom_palette)
        images = image if image.ndim == 4 else image.unsqueeze(0)
        if images.shape[2] != detections.width or images.shape[1] != detections.height:
            raise ValueError("Image size doesn't match the detections; feed the same frames into both.")

        order = list(detections.metadata.get("hud_objects", ())) if detections.metadata else []
        for det in detections.all_detections():
            label = det.label or det.text or "object"
            if label not in order:
                order.append(label)

        lookup = {f.frame_index: f for f in detections.frames}
        if len(images) != detections.frame_count and len(images) == len(detections.frames):
            lookup = {i: f for i, f in enumerate(detections.frames)}
        font = _font(label_size)

        out = []
        held = ()
        for index in range(images.shape[0]):
            frame = lookup.get(index)
            if frame is not None:
                held = frame.detections
            dets = frame.detections if frame is not None else (held if hold_between_frames else ())
            pixels = (images[index, ..., :3].detach().cpu().float().clamp(0, 1).numpy() * 255).astype(np.uint8)
            visual = Image.fromarray(pixels, "RGB")
            if not dets:
                out.append(images[index, ..., :3].cpu().float())
                continue

            if fill_opacity > 0:
                layer = Image.new("RGBA", visual.size, (0, 0, 0, 0))
                ldraw = ImageDraw.Draw(layer)
                for n, det in enumerate(dets):
                    color = self._color(det, n, order, colors, color_by)
                    ldraw.rectangle([round(v) for v in det.bbox_xyxy], fill=color + (round(255 * fill_opacity),))
                visual = Image.alpha_composite(visual.convert("RGBA"), layer).convert("RGB")

            draw = ImageDraw.Draw(visual)
            for n, det in enumerate(dets):
                color = self._color(det, n, order, colors, color_by)
                x1, y1, x2, y2 = (round(v) for v in det.bbox_xyxy)
                x2, y2 = max(x1, x2 - 1), max(y1, y2 - 1)
                if style in ("box", "box + corners"):
                    w = line_width if style == "box" else max(1, line_width // 2)
                    draw.rectangle((x1, y1, x2, y2), outline=color, width=w)
                if style in ("corners", "box + corners"):
                    cw = max(2, round((x2 - x1) * corner_length))
                    ch = max(2, round((y2 - y1) * corner_length))
                    for cx, cy, dx, dy in ((x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)):
                        draw.line([(cx, cy), (cx + dx * cw, cy)], fill=color, width=line_width)
                        draw.line([(cx, cy), (cx, cy + dy * ch)], fill=color, width=line_width)
                if draw_labels:
                    text = det.label or det.text or "object"
                    if uppercase_labels:
                        text = text.upper()
                    if show_score and det.score is not None:
                        text += f" {det.score:.0%}"
                    tb = draw.textbbox((0, 0), text, font=font)
                    tw, th = tb[2] - tb[0], tb[3] - tb[1]
                    tx = min(max(0, x1), max(0, visual.width - tw - 6))
                    ty = y1 - th - 8
                    if ty < 0:
                        ty = min(visual.height - th - 6, y1 + line_width + 2)
                    draw.rectangle((tx, ty, tx + tw + 6, ty + th + 6), fill=color)
                    luminance = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
                    draw.text((tx + 3 - tb[0], ty + 3 - tb[1]), text, font=font,
                              fill=(0, 0, 0) if luminance > 140 else (255, 255, 255))
            out.append(torch.from_numpy(np.asarray(visual, dtype=np.float32) / 255.0))
        return (torch.stack(out),)

    @staticmethod
    def _color(det, n, order, colors, color_by):
        if color_by == "each box":
            return colors[n % len(colors)]
        label = det.label or det.text or "object"
        return colors[order.index(label) % len(colors)]


NODE_CLASS_MAPPINGS = {
    "HUDMultiDetect": HUDMultiDetect,
    "HUDRenderBoxes": HUDRenderBoxes,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "HUDMultiDetect": "HUD Multi Detect (Moondream)",
    "HUDRenderBoxes": "HUD Render Boxes (palette)",
}
