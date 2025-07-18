from flask import Blueprint, request, jsonify
import cv2
import numpy as np
import base64
import os
import urllib.request
from datetime import datetime

# Create blueprint
bottle_detection_bp = Blueprint('bottle_detection', __name__)

# Global variables for YOLO model
yolo_net = None
yolo_classes = None
yolo_output_layers = None

def download_yolo_files():
    """Download YOLO model files if they don't exist"""
    yolo_dir = 'yolo_files'
    if not os.path.exists(yolo_dir):
        os.makedirs(yolo_dir)
    
    files_to_download = {
        'yolov4.weights': 'https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v3_optimal/yolov4.weights',
        'yolov4.cfg': 'https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4.cfg',
        'coco.names': 'https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names'
    }
    
    for filename, url in files_to_download.items():
        filepath = os.path.join(yolo_dir, filename)
        if not os.path.exists(filepath):
            print(f"Downloading {filename}...")
            try:
                urllib.request.urlretrieve(url, filepath)
                print(f"✅ Downloaded {filename}")
            except Exception as e:
                print(f"❌ Failed to download {filename}: {e}")
                return False
    
    return True

def load_yolo_model():
    """Load YOLO model for object detection"""
    global yolo_net, yolo_classes, yolo_output_layers
    
    try:
        yolo_dir = 'yolo_files'
        
        weights_path = os.path.join(yolo_dir, 'yolov4.weights')
        config_path = os.path.join(yolo_dir, 'yolov4.cfg')
        classes_path = os.path.join(yolo_dir, 'coco.names')
        
        if not all(os.path.exists(path) for path in [weights_path, config_path, classes_path]):
            print("YOLO files not found. Downloading...")
            if not download_yolo_files():
                return False
        
        yolo_net = cv2.dnn.readNet(weights_path, config_path)
        
        with open(classes_path, 'r') as f:
            yolo_classes = [line.strip() for line in f.readlines()]
        
        layer_names = yolo_net.getLayerNames()
        yolo_output_layers = [layer_names[i - 1] for i in yolo_net.getUnconnectedOutLayers()]
        
        print("✅ YOLO model loaded successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error loading YOLO model: {e}")
        return False

def detect_bottles_yolo(image_data):
    """Detect bottles in image using YOLO"""
    global yolo_net, yolo_classes, yolo_output_layers
    
    if yolo_net is None:
        return [], 0, 0.0
    
    try:
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return [], 0, 0.0
        
        height, width, channels = img.shape
        
        # YOLO detection
        blob = cv2.dnn.blobFromImage(img, 0.00392, (608, 608), (0, 0, 0), True, crop=False)
        yolo_net.setInput(blob)
        outputs = yolo_net.forward(yolo_output_layers)
        
        boxes = []
        confidences = []
        class_ids = []
        detections = []
        
        # Look for bottle-related classes
        bottle_classes = ['bottle', 'cup', 'wine glass']
        bottle_class_ids = [yolo_classes.index(cls) for cls in bottle_classes if cls in yolo_classes]
        
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = int(np.argmax(scores))
                confidence = float(scores[class_id])
                
                if class_id in bottle_class_ids and confidence > 0.15:  # Lower threshold for better detection
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    
                    if w > 15 and h > 15 and x >= 0 and y >= 0:
                        boxes.append([x, y, w, h])
                        confidences.append(confidence)
                        class_ids.append(class_id)
                        
                        detections.append({
                            'class': yolo_classes[class_id],
                            'confidence': round(confidence * 100, 1),
                            'box': [x, y, w, h]
                        })
        
        # Apply NMS
        final_detections = []
        if len(boxes) > 0:
            indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.15, 0.4)
            if len(indexes) > 0:
                for i in indexes.flatten():
                    final_detections.append(detections[i])
        
        # Calculate average confidence
        if final_detections:
            confidences = [float(d['confidence']) for d in final_detections]
            avg_confidence = round(sum(confidences) / len(confidences), 1)
        else:
            avg_confidence = 0.0
        
        return final_detections, len(final_detections), float(avg_confidence)
        
    except Exception as e:
        print(f"Error in bottle detection: {e}")
        return [], 0, 0.0

def create_detection_visualization(image_data, detections):
    """Create visualization with bounding boxes"""
    try:
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return None
        
        vis_img = img.copy()
        
        # Draw bounding boxes
        for i, detection in enumerate(detections):
            x, y, w, h = detection['box']
            confidence = detection['confidence']
            
            # Green color for bottles
            color = (0, 255, 0)
            
            # Draw rectangle
            cv2.rectangle(vis_img, (x, y), (x + w, y + h), color, 3)
            
            # Draw label
            label = f"{i+1}: {confidence:.1f}%"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            cv2.rectangle(vis_img, (x, y - label_size[1] - 10), (x + label_size[0] + 5, y), color, -1)
            cv2.putText(vis_img, label, (x + 3, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Add count at top
        if detections:
            count_text = f"Detected: {len(detections)} bottles"
            cv2.putText(vis_img, count_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Convert to base64
        _, buffer = cv2.imencode('.jpg', vis_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return img_base64
        
    except Exception as e:
        print(f"Error creating visualization: {e}")
        return None

@bottle_detection_bp.route('/detect-bottles', methods=['POST'])
def detect_bottles():
    """Detect bottles in uploaded image"""
    global yolo_net
    
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        # Check file size (max 10MB)
        file_size = len(file.read())
        file.seek(0)
        if file_size > 10 * 1024 * 1024:
            return jsonify({'error': 'File too large. Maximum size is 10MB.'}), 400
        
        image_data = file.read()
        
        # Initialize YOLO if not loaded
        if yolo_net is None:
            print("Loading YOLO model...")
            if not load_yolo_model():
                return jsonify({'error': 'Failed to load YOLO model'}), 500
        
        # Detect bottles
        detections, bottle_count, avg_confidence = detect_bottles_yolo(image_data)
        
        # Create visualization
        visualization = create_detection_visualization(image_data, detections)
        
        response_data = {
            'success': True,
            'bottle_count': bottle_count,
            'avg_confidence': avg_confidence,
            'detections': detections,
            'timestamp': datetime.now().isoformat()
        }
        
        if visualization:
            response_data['visualization'] = visualization
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in bottle detection: {e}")
        return jsonify({'error': f'Detection failed: {str(e)}'}), 500

@bottle_detection_bp.route('/model-status', methods=['GET'])
def model_status():
    """Check if YOLO model is ready"""
    global yolo_net
    return jsonify({
        'ready': yolo_net is not None,
        'message': 'YOLO model ready' if yolo_net is not None else 'YOLO model not loaded'
    })