# auto_label.py
import logging
import os

import cv2

from logic.yolo_inference import (
    ModelNotFoundError,
    contour_to_yolo_seg,
    draw_detection_overlay,
    find_model_path,
    run_yolo_inference,
)

logger = logging.getLogger(__name__)

# Optional override: HCI_MODEL_PATH=/path/to/best.pt
_ENV_MODEL = os.environ.get("HCI_MODEL_PATH", "").strip()


def generate_labels(img_path, detector=None):
    """
    Run YOLO inference and return (label_lines, img, labelled) for _autolabel_worker.

    detector is accepted for API compatibility but not used (heuristic stub ignored).
    """
    img = cv2.imread(img_path)
    if img is None:
        labelled = {"_skip_reason": "image unreadable"}
        logger.error("generate_labels: cannot read %s", img_path)
        return [], None, labelled

    model_path = _ENV_MODEL or find_model_path()
    if not model_path:
        raise ModelNotFoundError(
            "No YOLO weights found. Expected D:\\HCI_interor\\best_gdrive.pt "
            "or gdrive_dataset/runs/**/best.pt"
        )

    try:
        labelled, label_lines, used = run_yolo_inference(img, model_path=model_path)
    except ModelNotFoundError:
        raise
    except Exception as exc:
        logger.exception("generate_labels inference failed for %s", img_path)
        labelled = {"_skip_reason": f"inference error: {exc}"}
        return [], img, labelled

    if not label_lines:
        labelled["_skip_reason"] = (
            f"zero detections (model={os.path.basename(used)})"
        )
        logger.warning(
            "generate_labels: zero Wall/Door/Window detections for %s using %s",
            img_path,
            used,
        )
    else:
        logger.info(
            "generate_labels: %s polygons from %s using %s",
            len(label_lines),
            img_path,
            used,
        )

    return label_lines, img, labelled


def draw_labelled_image(img, labelled, marked_path):
    """Save coloured polygon overlay preview."""
    if img is None:
        return
    vis = draw_detection_overlay(img, labelled)
    cv2.imwrite(marked_path, vis)
