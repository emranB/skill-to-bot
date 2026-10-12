# Purpose: Segment the object indicated by a rough selection hint.
import logging
import os
from pathlib import Path

import cv2
import numpy as np

_SEGMENTER = None
_SEGMENTER_READY = False
logger = logging.getLogger("perception.segmentation")


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


def _largest_overlap(mask: np.ndarray, hint: tuple[int, int, int, int]) -> np.ndarray | None:
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
        mask[search_y : search_y + search_h, search_x : search_x + search_w] = cv2.GC_PR_BGD
        mask[top : top + high, left : left + wide] = cv2.GC_FGD
        mode = cv2.GC_INIT_WITH_MASK
    background = np.zeros((1, 65), np.float64)
    foreground = np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(frame, mask, search, background, foreground, iterations, mode)
    except cv2.error as error:
        raise ValueError(
            "The selection hint could not be segmented. Select a clearer object."
        ) from error
    foreground_mask = (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)
    chosen = _largest_overlap(foreground_mask, hint)
    if chosen is None or int(chosen.sum()) < 30:
        raise ValueError("The selection hint does not contain a segmentable foreground object.")
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


def choose_instance(instances: list[dict], hint: tuple[int, int, int, int], accept=None):
    """Keep a detected instance only when it agrees with the selection hint."""
    left, top, wide, high = hint
    hint_area = wide * high
    best = None
    best_score = 0.0
    for instance in instances:
        mask = instance["mask"]
        agreement = accept(mask) if accept is not None else 1.0
        area = int(mask.sum())
        ys, xs = np.nonzero(mask)
        click = wide <= mask.shape[1] * 0.08 and high <= mask.shape[0] * 0.08
        if len(xs) == 0 or (area > hint_area * 3 and not click):
            continue
        if not agreement:
            continue
        center_inside = (
            top <= float(ys.mean()) <= top + high and left <= float(xs.mean()) <= left + wide
        )
        overlap = int(mask[top : top + high, left : left + wide].sum())
        coverage = overlap / area
        click_hit = overlap / hint_area >= 0.6
        if not (center_inside and coverage >= 0.6 or click and click_hit):
            continue
        score = coverage + _iou(mask, hint)
        if accept is not None:
            score *= float(instance.get("confidence", 1.0)) * agreement
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
            name for name in ("CUDAExecutionProvider", "CPUExecutionProvider") if name in available
        ]
        self.session = ort.InferenceSession(model_path, providers=providers or available)
        self.input_name = self.session.get_inputs()[0].name

    def instances(self, frame) -> list[dict]:
        canvas, scale, pad_x, pad_y = _letterbox(frame, 640)
        blob = canvas[:, :, ::-1].astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))[None]
        outputs = self.session.run(None, {self.input_name: blob})
        prediction, prototype = _split_outputs(outputs)
        return _decode_instances(frame.shape[:2], prediction, prototype, scale, pad_x, pad_y)

    def selected_instances(self, frame, roi: list[float], accept=None) -> list[dict]:
        """Retry a focused crop when full-frame inference misses the hinted object."""
        instances = self.instances(frame)
        hint = _pixel_box(frame, roi)
        chosen = choose_instance(instances, hint, accept)
        if chosen is not None and accept is not None:
            return instances
        if chosen is not None and _iou(chosen, hint) >= 0.35:
            return instances
        height, width = frame.shape[:2]
        x, y, wide, high = hint
        center_x, center_y = x + wide / 2, y + high / 2
        wide = max(wide, width * 0.12)
        high = max(high, height * 0.2)
        for context in (0.6, 1.1):
            x0 = max(0, int(center_x - wide * context))
            y0 = max(0, int(center_y - high * context))
            x1 = min(width, int(center_x + wide * context))
            y1 = min(height, int(center_y + high * context))
            for instance in self.instances(frame[y0:y1, x0:x1]):
                cropped = instance["mask"]
                if (
                    x0 > 0
                    and cropped[:, 0].any()
                    or x1 < width
                    and cropped[:, -1].any()
                    or y0 > 0
                    and cropped[0].any()
                    or y1 < height
                    and cropped[-1].any()
                ):
                    continue
                mask = np.zeros((height, width), dtype=bool)
                mask[y0:y1, x0:x1] = cropped
                instances.append({**instance, "mask": mask})
            chosen = choose_instance(instances, hint, accept)
            if chosen is not None and _iou(chosen, hint) >= 0.35:
                break
        return instances


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
    classes = class_scores[keep].argmax(axis=1)
    proto_h, proto_w = prototype.shape[1:]
    masks = coefficients @ prototype.reshape(prototype.shape[0], -1)
    masks = np.clip(masks, -80, 80)
    masks = 1.0 / (1.0 + np.exp(-masks))
    masks = masks.reshape(-1, proto_h, proto_w)
    boxes_xyxy = []
    for cx, cy, box_width, box_height in boxes:
        x1 = (cx - box_width / 2 - pad_x) / scale
        y1 = (cy - box_height / 2 - pad_y) / scale
        x2 = (cx + box_width / 2 - pad_x) / scale
        y2 = (cy + box_height / 2 - pad_y) / scale
        boxes_xyxy.append((x1, y1, x2, y2))
    indices = []
    for category in np.unique(classes):
        group = np.flatnonzero(classes == category)
        kept = cv2.dnn.NMSBoxes(
            [
                (
                    boxes_xyxy[i][0],
                    boxes_xyxy[i][1],
                    boxes_xyxy[i][2] - boxes_xyxy[i][0],
                    boxes_xyxy[i][3] - boxes_xyxy[i][1],
                )
                for i in group
            ],
            confidence[group].tolist(),
            0.25,
            0.7,
        )
        indices.extend(group[np.asarray(kept, dtype=int).reshape(-1)].tolist())
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
            logger.exception("Segmentation model could not be loaded; fallback is active.")
            _SEGMENTER = None
    return _SEGMENTER


def select_object(frame, roi: list[float], config: dict, segmenter=None, accept=None):
    """Return acquired geometry and provenance, independent of model structures."""
    hint = _pixel_box(frame, roi)
    mask = None
    if segmenter is not None:
        try:
            search = getattr(segmenter, "selected_instances", None)
            instances = search(frame, roi, accept) if search else segmenter.instances(frame)
            mask = choose_instance(instances, hint, accept)
        except (cv2.error, ValueError, RuntimeError):
            logger.exception("Segmentation inference failed.")
            mask = None
    source = "yolo" if mask is not None else "grabcut"
    if mask is None:
        if accept is not None:
            raise ValueError("No compatible object mask was detected.")
        mask = grabcut_mask(frame, roi, int(config["segment_iterations"]))
    return {"mask": mask, "box": _mask_box(mask), "source": source}


def segment_selection(frame, roi: list[float], config: dict, segmenter=None):
    """Preserve the existing mask/box interface for selection callers."""
    selected = select_object(frame, roi, config, segmenter)
    return selected["mask"], selected["box"]
