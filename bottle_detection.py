# bottle_detection.py
import os, urllib.request, cv2, numpy as np
from datetime import datetime
import base64

# ---------- 1. Model loading / caching ----------
YOLO_DIR = "yolo_files"
WEIGHTS = "yolov4.weights"
CFG      = "yolov4.cfg"
NAMES    = "coco.names"

_URLS = {
    WEIGHTS: "https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v3_optimal/yolov4.weights",
    CFG:     "https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4.cfg",
    NAMES:   "https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names",
}

yolo_net = None          # cv2.dnn_Net
yolo_classes = []
yolo_output_layers = []

def _download():
    os.makedirs(YOLO_DIR, exist_ok=True)
    for fname, url in _URLS.items():
        fpath = os.path.join(YOLO_DIR, fname)
        if not os.path.exists(fpath):
            urllib.request.urlretrieve(url, fpath)

def load_model():
    global yolo_net, yolo_classes, yolo_output_layers
    if yolo_net is not None:
        return
    _download()
    w, c, n = (os.path.join(YOLO_DIR, p) for p in (WEIGHTS, CFG, NAMES))
    yolo_net  = cv2.dnn.readNet(w, c)
    yolo_classes = [l.strip() for l in open(n)]
    ln = yolo_net.getLayerNames()
    yolo_output_layers = [ln[i - 1] for i in yolo_net.getUnconnectedOutLayers()]

# ---------- 2. Detection routine (trimmed) ----------
def detect(image_bytes):
    load_model()
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return [], 0
    H, W = img.shape[:2]
    blob = cv2.dnn.blobFromImage(img, 0.00392, (608, 608), swapRB=True)
    yolo_net.setInput(blob)
    outs = yolo_net.forward(yolo_output_layers)

    bottle_ids = [yolo_classes.index(x) for x in ("bottle",) if x in yolo_classes]
    detections = []
    for out in outs:
        for det in out:
            scores = det[5:]
            cid = int(np.argmax(scores))
            conf = float(scores[cid])
            if cid in bottle_ids and conf > 0.30:
                cx, cy, w, h = det[:4] * np.array([W, H, W, H])
                x, y = int(cx - w / 2), int(cy - h / 2)
                detections.append(
                    {"class": "bottle", "confidence": round(conf * 100, 1), "box": [x, y, int(w), int(h)]}
                )
    return detections, len(detections)
