import easyocr
import cv2
from roboflow import Roboflow
from PIL import Image
import re

# 初始化 Roboflow 模型
rf = Roboflow(api_key="nKpTtySN7UaGOQaP2abf")
project = rf.workspace().project("vehicle-registration-plates-trudk")
model = project.version(2).model

def detect_license_plate(image_path, confidence=70, overlap=30):
    """
    偵測車牌位置並回傳邊界座標。
    """
    prediction = model.predict(image_path, confidence=confidence, overlap=overlap)
    
    if prediction is None or len(prediction.json().get('predictions', [])) == 0:
        return [], "沒有偵測到車牌"

    predictions = prediction.json()['predictions']
    
    if len(predictions) > 1:
        return [], "多車牌"

    # 取得圖片
    image = cv2.imread(image_path)
    if image is None:
        return [], "無法讀取圖片"

    pred = predictions[0]
    x, y, w, h = pred['x'], pred['y'], pred['width'], pred['height']
    x1, y1 = int(x - w / 2), int(y - h / 2)
    x2, y2 = int(x + w / 2), int(y + h / 2)
    return [(x1, y1, x2, y2)], None

def recognize_license_plate(image_path, cropped_plate_coordinates):
    """
    使用 EasyOCR 辨識車牌文字。
    """
    reader = easyocr.Reader(['en'])
    
    if not cropped_plate_coordinates:
        return None, None, "沒有偵測到車牌區域文字"

    x1, y1, x2, y2 = cropped_plate_coordinates[0]
    image = cv2.imread(image_path)
    cropped_plate = image[y1:y2, x1:x2]

    ocr_results = reader.readtext(cropped_plate)
    if not ocr_results:
        return None, None, "沒有偵測到車牌區域文字"
    
    text, confidence = ocr_results[0][1], ocr_results[0][2]
    return text, confidence, None

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
    cropped_plate_coordinates, error_code = detect_license_plate(image_path)

    if error_code is not None:
        return None, None, error_code

    if cropped_plate_coordinates:
        text, confidence, error_code = recognize_license_plate(image_path, cropped_plate_coordinates)
        
        if text is None or confidence < 0.75:
            return None, confidence, "車牌辨識度過低"
        
        filtered_text = filter_license_plate(text)
        if filtered_text:
            return filtered_text, confidence, None
        else:
            return None, confidence, "車牌辨識度過低"
    else:
        return None, None, error_code

#  範例使用：
# image_path = "AI/License_plate/final_3.jpg"
# license_plate, confidence, ai_error_code = get_License_plate_data(image_path)
# print(f"車牌號碼: {license_plate}, 準確率: {confidence}, 錯誤代碼: {ai_error_code}")

