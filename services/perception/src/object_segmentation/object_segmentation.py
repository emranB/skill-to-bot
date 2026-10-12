# Purpose: Segment the object indicated by a rough selection hint.
import os
from pathlib import Path

import cv2
import numpy as np

_SEGMENTER = None
_SEGMENTER_READY = False


def _pixel_box(frame, roi: list[float]) -> tuple[int, int, int, int]:
    height, width = frame.shape[:2]
    x, y, box_width, box_height = (float(v) for v in roi)
    left = int(round(x * width))
    top = int(round(y * height))
    wide = max(2, int(round(box_width * width)))
    high = max(2, int(round(box_height * height)))
    left = min(max(0, left), width - 2)
    top = min(max(0, top), height - 2)
    wide = min(wide, width - left)
    high = min(high, height - top)
    return left, top, wide, high


def _largest_overlap(
    mask: np.ndarray, hint: tuple[int, int, int, int]
) -> np.ndarray | None:
    binary = mask.astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary)
    left, top, wide, high = hint
    best = None
    best_overlap = 0
    for index in range(1, count):
        component = labels == index
        overlap = int(component[top : top + high, left : left + wide].sum())
        if overlap > best_overlap and int(stats[index, cv2.CC_STAT_AREA]) >= 30:
            best = component
            best_overlap = overlap
    return best


def grabcut_mask(frame, roi: list[float], iterations: int) -> np.ndarray:
    """Snap a rough rectangle or click to the foreground object inside it."""
    height, width = frame.shape[:2]
    hint = _pixel_box(frame, roi)
    left, top, wide, high = hint
    search = hint
    mask = np.zeros((height, width), np.uint8)
    mode = cv2.GC_INIT_WITH_RECT
    # A click is a small hint. Search a wider window and keep the click as foreground.
    if wide < width * 0.08 or high < height * 0.08:
        center_x = left + wide / 2
        center_y = top + high / 2
        search_w = min(width - 2, max(wide * 3, int(width * 0.22)))
        search_h = min(height - 2, max(high * 3, int(height * 0.28)))
        search_x = int(min(max(0, center_x - search_w / 2), width - search_w))
        search_y = int(min(max(0, center_y - search_h / 2), height - search_h))
        search = (search_x, search_y, search_w, search_h)
        mask[:] = cv2.GC_BGD
        mask[search_y : search_y + search_h, search_x : search_x + search_w] = (
            cv2.GC_PR_BGD
        )
        mask[top : top + high, left : left + wide] = cv2.GC_FGD
        mode = cv2.GC_INIT_WITH_MASK
    background = np.zeros((1, 65), np.float64)
    foreground = np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(frame, mask, search, background, foreground, iterations, mode)
    except cv2.error:
        chosen = np.zeros((height, width), dtype=bool)
        chosen[top : top + high, left : left + wide] = True
        return chosen
    foreground_mask = (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)
    chosen = _largest_overlap(foreground_mask, hint)
    if chosen is None or int(chosen.sum()) < 30:
        chosen = np.zeros((height, width), dtype=bool)
        chosen[top : top + high, left : left + wide] = True
    return chosen


def _mask_box(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        raise ValueError("The selection hint does not contain a segmentable object.")
    left, top = int(xs.min()), int(ys.min())
    return left, top, int(xs.max() - left + 1), int(ys.max() - top + 1)


def _iou(mask: np.ndarray, hint: tuple[int, int, int, int]) -> float:
    left, top, wide, high = hint
    hint_mask = np.zeros(mask.shape, dtype=bool)
    hint_mask[top : top + high, left : left + wide] = True
    intersection = int(np.logical_and(mask, hint_mask).sum())
    union = int(np.logical_or(mask, hint_mask).sum())
    return intersection / union if union else 0.0


def choose_instance(instances: list[dict], hint: tuple[int, int, int, int]):
    """Keep a detected instance only when it agrees with the selection hint."""
    left, top, wide, high = hint
    hint_area = wide * high
    best = None
    best_score = 0.0
    for instance in instances:
        mask = instance["mask"]
        score = _iou(mask, hint)
        area = int(mask.sum())
        ys, xs = np.nonzero(mask)
        if len(xs) == 0 or area > hint_area * 3:
            continue
        center_inside = (
            top <= float(ys.mean()) <= top + high
            and left <= float(xs.mean()) <= left + wide
        )
        if score < 0.2 or not center_inside:
            continue
        if score > best_score:
            best = mask
            best_score = score
    return best


class YoloSegmenter:
    """Pretrained YOLOv8 segmentation. CUDA is used when the runtime provides it."""

    def __init__(self, model_path: str):
        import onnxruntime as ort

        available = ort.get_available_providers()
        providers = [
            name
            for name in ("CUDAExecutionProvider", "CPUExecutionProvider")
            if name in available
        ]
        self.session = ort.InferenceSession(
            model_path, providers=providers or available
        )
        self.input_name = self.session.get_inputs()[0].name

    def instances(self, frame) -> list[dict]:
        canvas, scale, pad_x, pad_y = _letterbox(frame, 640)
        blob = canvas[:, :, ::-1].astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))[None]
        outputs = self.session.run(None, {self.input_name: blob})
        prediction, prototype = _split_outputs(outputs)
        return _decode_instances(
            frame.shape[:2], prediction, prototype, scale, pad_x, pad_y
        )


def _letterbox(frame, size: int):
    height, width = frame.shape[:2]
    scale = min(size / height, size / width)
    resized = cv2.resize(frame, (int(round(width * scale)), int(round(height * scale))))
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    pad_y = (size - resized.shape[0]) // 2
    pad_x = (size - resized.shape[1]) // 2
    canvas[pad_y : pad_y + resized.shape[0], pad_x : pad_x + resized.shape[1]] = resized
    return canvas, scale, pad_x, pad_y


def _split_outputs(outputs):
    prediction = None
    prototype = None
    for output in outputs:
        if output.ndim == 3:
            prediction = output
        elif output.ndim == 4:
            prototype = output[0]
    if prediction is None or prototype is None:
        raise ValueError("Segmentation model returned an unexpected output shape.")
    if prediction.shape[1] < prediction.shape[2]:
        prediction = prediction[0].T
    else:
        prediction = prediction[0]
    return prediction, prototype


def _decode_instances(shape, prediction, prototype, scale, pad_x, pad_y) -> list[dict]:
    height, width = shape
    class_scores = prediction[:, 4:84]
    confidence = class_scores.max(axis=1)
    keep = confidence >= 0.25
    if not np.any(keep):
        return []
    boxes = prediction[keep, :4]
    coefficients = prediction[keep, 84:]
    confidence = confidence[keep]
    proto_h, proto_w = prototype.shape[1:]
    masks = coefficients @ prototype.reshape(prototype.shape[0], -1)
    masks = 1.0 / (1.0 + np.exp(-masks))
    masks = masks.reshape(-1, proto_h, proto_w)
    boxes_xyxy = []
    for cx, cy, box_width, box_height in boxes:
        x1 = (cx - box_width / 2 - pad_x) / scale
        y1 = (cy - box_height / 2 - pad_y) / scale
        x2 = (cx + box_width / 2 - pad_x) / scale
        y2 = (cy + box_height / 2 - pad_y) / scale
        boxes_xyxy.append((x1, y1, x2, y2))
    indices = cv2.dnn.NMSBoxes(
        [(x1, y1, x2 - x1, y2 - y1) for x1, y1, x2, y2 in boxes_xyxy],
        confidence.tolist(),
        0.25,
        0.7,
    )
    if len(indices) == 0:
        return []
    instances = []
    for index in np.array(indices).reshape(-1):
        full = cv2.resize(masks[index], (640, 640))
        cropped_h = int(round(height * scale))
        cropped_w = int(round(width * scale))
        cropped = full[pad_y : pad_y + cropped_h, pad_x : pad_x + cropped_w]
        resized = cv2.resize(cropped, (width, height)) > 0.5
        x1, y1, x2, y2 = boxes_xyxy[index]
        clipped = np.zeros_like(resized)
        xa, ya = max(0, int(x1)), max(0, int(y1))
        xb, yb = min(width, int(x2)), min(height, int(y2))
        if xb <= xa or yb <= ya:
            continue
        clipped[ya:yb, xa:xb] = resized[ya:yb, xa:xb]
        if int(clipped.sum()) < 30:
            continue
        instances.append({"mask": clipped, "confidence": float(confidence[index])})
    return instances


def load_segmenter():
    """Load the pretrained segmenter once when its model file is present."""
    global _SEGMENTER, _SEGMENTER_READY
    if _SEGMENTER_READY:
        return _SEGMENTER
    _SEGMENTER_READY = True
    path = Path(os.environ.get("SEGMENTATION_MODEL", "/app/models/yolov8n-seg.onnx"))
    if path.is_file():
        try:
            _SEGMENTER = YoloSegmenter(str(path))
        except (ImportError, OSError, ValueError):
            _SEGMENTER = None
    return _SEGMENTER


def segment_selection(frame, roi: list[float], config: dict, segmenter=None):
    """Return the object mask and tight pixel box for a rough hint."""
    hint = _pixel_box(frame, roi)
    mask = None
    if segmenter is not None:
        try:
            mask = choose_instance(segmenter.instances(frame), hint)
        except (cv2.error, ValueError, RuntimeError):
            mask = None
    if mask is None:
        mask = grabcut_mask(frame, roi, int(config["segment_iterations"]))
    return mask, _mask_box(mask)
