import pymysql
import os
import License_plate_recognition  # 匯入您的車牌辨識模組
from datetime import datetime  # 匯入 datetime 模組
import requests

# 資料庫連接設定
db = pymysql.connect(
    host="localhost",  # 資料庫主機
    user="root",       # 使用者名稱
    password="1234",   # 密碼
    database="accidents"  # 資料庫名稱
)

# 資料插入函式（包含車牌辨識後的資料）
def insert_data_after_recognition(cam_id, speed_limit, current_speed, location, date_time, image_filename, licence_plate, confidence, ai_error_code):
    try:
        cursor = db.cursor()

        # 修改插入的 SQL 語句，將資料庫直接插入，包含車牌號碼、信心度及辨識結果
        sql = """
        INSERT INTO Accidents (cam_id, speed_limit, current_speed, location, date_time, image, recognized, licence_plate, confidence, ai_error_code)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # 使用參數化查詢來防止 SQL 注入
        cursor.execute(sql, (cam_id, speed_limit, current_speed, location, date_time, image_filename, "1" if ai_error_code else "2", licence_plate, confidence, ai_error_code))
        db.commit()
        print("資料插入成功！")

    except Exception as e:
        db.rollback()
        print(f"資料插入失敗: {e}")

    finally:
        cursor.close()


# 用戶輸入初始資料並處理車牌辨識
def get_user_initial_input():
    try:
        # 提示用戶輸入所有資料，以空格拆分
        user_input = input("依次輸入以下資訊，使用,分隔：\n攝影機編號(cam_id，例如 'CAM12345')、速限(speed_limit，例如 60)、目前速度(current_speed，例如 80)、事故地點(location，例如 '台北市中正區羅斯福路一段12號')、日期時間(date_time，例如 '2024/1/10 12:00 AM')：\n")

        # 使用 split 方法拆分輸入的字串
        inputs = user_input.split(",", 5)

        # 將拆分的內容賦值給對應變數
        cam_id = inputs[3]
        speed_limit = int(inputs[4])
        current_speed = int(inputs[5])
        location = inputs[1]
        date_str = inputs[2]
        image_filename = inputs[0]+".jpg"

        # 轉換日期時間格式
        date_time = datetime.strptime(date_str, "%Y/%m/%d %I:%M %p")

        # 預設路徑設定
        image_path = "License_plate/" + image_filename

        # 進行車牌辨識
        licence_plate, confidence, ai_error_code = License_plate_recognition.get_License_plate_data(image_path)

        if ai_error_code:
            print(f"車牌辨識失敗或不確定，需人工辨視錯誤代碼: {ai_error_code}。")
            licence_plate = None
        else:
            print(f"辨識成功: 車牌號碼是 {licence_plate}, 準確率: {confidence * 100:.0f}%")
            
            # API URL
            api_url = "http://127.0.0.1:5555/get_vehicle_info"

            try:
                # 發送 POST 請求
                response = requests.post(api_url, json={"licence_plate": licence_plate})
                
                # 確認回應狀態碼
                if response.status_code == 200:
                    # 解析回傳資料
                    vehicle_info = response.json()
                    
                    if vehicle_info:
                        # 提取第一筆資料的 state 欄位
                        state = vehicle_info[0]['state']
                        if not state == "正常":
                            ai_error_code = state
                    else:
                        print("回傳資料為空！")
                elif response.status_code == 404:
                    ai_error_code = "查無車籍資料"
                else:
                    print(f"發生錯誤 (狀態碼: {response.status_code})")
            except requests.exceptions.RequestException as e:
                print(f"API 請求失敗：{str(e)}")



        # 一次性插入資料庫（包含車牌號碼、信心度及辨識結果）
        insert_data_after_recognition(cam_id, speed_limit, current_speed, location, date_time, image_filename, licence_plate, confidence, ai_error_code)

    except ValueError as e:
        print(f"輸入資料格式有誤：{e}")


# 主選單
def main():
    os.chdir(os.path.dirname(__file__))  # 設定工作目錄為目前檔案所
    os.getcwd()
    print("新的工作目录:", os.getcwd())
    while True:
        print("\n1. 輸入初始資料")
        print("2. 離開")
        choice = input("請選擇操作：")
        if choice == "1":
            get_user_initial_input()
        elif choice == "2":
            print("結束程式。")
            break
        else:
            print("無效選項，請重新選擇。")

# 執行主程式
main()

# 關閉資料庫連線
db.close()
