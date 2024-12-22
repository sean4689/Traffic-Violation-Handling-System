import easyocr
import cv2
from roboflow import Roboflow
from PIL import Image
import matplotlib.pyplot as plt
import re

# 初始化 Roboflow 模型
rf = Roboflow(api_key="nKpTtySN7UaGOQaP2abf")
project = rf.workspace().project("license-plate-recognition-rxg4e")
model = project.version(4).model

def detect_license_plate(image_path, confidence=40, overlap=30):
    """
    偵測車牌位置並回傳邊界座標。
    """
    prediction = model.predict(image_path, confidence=confidence, overlap=overlap)
    
    if prediction is None or len(prediction.json().get('predictions', [])) == 0:
        print("需人工辨視: 沒有偵測到車牌。")
        return []

    predictions = prediction.json()['predictions']
    
    if len(predictions) > 1:
        print("需人工辨視: 偵測到多個車牌。")
        return []
    
    pred = predictions[0]
    x, y, w, h = pred['x'], pred['y'], pred['width'], pred['height']
    x1, y1 = int(x - w / 2), int(y - h / 2)
    x2, y2 = int(x + w / 2), int(y + h / 2)
    return [(x1, y1, x2, y2)]

def recognize_license_plate(image_path, cropped_plate_coordinates):
    """
    使用 EasyOCR 辨識車牌文字。
    """
    reader = easyocr.Reader(['en'])
    
    if not cropped_plate_coordinates:
        return None, None

    x1, y1, x2, y2 = cropped_plate_coordinates[0]
    image = cv2.imread(image_path)
    cropped_plate = image[y1:y2, x1:x2]

    # pil_image = Image.fromarray(cv2.cvtColor(cropped_plate, cv2.COLOR_BGR2RGB))
    # plt.imshow(pil_image)
    # plt.axis('off')
    # plt.show()

    ocr_results = reader.readtext(cropped_plate)
    if not ocr_results:
        print("需人工辨視: 沒有辨識到車牌區域的文字。")
        return None, None
    
    text, confidence = ocr_results[0][1], ocr_results[0][2]
    return text, confidence

def filter_license_plate(text):
    """
    根據台灣車牌規則過濾並格式化車牌號碼。
    """
    text = re.sub(r'[^A-Za-z0-9]', '', text).upper()

    match = re.match(r'^([A-HJ-NP-Z]{3})([012356789]{4})$', text)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return None

def get_License_plate_data(image_path):
    """
    偵測並識別車牌，並回傳結果。
    """
    cropped_plate_coordinates = detect_license_plate(image_path)

    if cropped_plate_coordinates:
        text, confidence = recognize_license_plate(image_path, cropped_plate_coordinates)
        
        if text is None or confidence < 0.85:
            print("準確率: "+str(confidence))
            return None, "1"
        
        filtered_text = filter_license_plate(text)
        if filtered_text:
            print("準確率: "+str(confidence))
            return filtered_text, "2"
        else:
            return None, "1"
    else:
        return None, "1"

#  範例使用：
# image_path = "License_plate/Processed/mobile01-08ee84cb765e9b3a10be5c8152fa7676.jpg"
# license_plate, recognized = get_License_plate_data(image_path)
# print(f"車牌號碼: {license_plate}, 是否成功識別: {recognized}")
