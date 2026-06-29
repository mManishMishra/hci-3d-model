# auto_label.py
import cv2

def generate_labels(img_path, detector):
    img = cv2.imread(img_path)
    # Placeholder: Returns an empty list of labels
    labelled = detector.detect(img) if detector else {}
    return [], img, labelled

def draw_labelled_image(img, labelled, marked_path):
    cv2.imwrite(marked_path, img)

def contour_to_yolo_seg(cnt, img_w, img_h, cid):
    if cnt is None or len(cnt) < 3: 
        return ""
    flat = cnt.flatten()
    coords = []
    for i in range(0, len(flat), 2):
        # Normalize coordinates between 0 and 1 for YOLO
        coords.append(f"{flat[i]/img_w:.6f} {flat[i+1]/img_h:.6f}")
    return f"{cid} " + " ".join(coords)