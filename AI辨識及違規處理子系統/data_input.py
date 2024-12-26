import pymysql
import os
import License_plate_recognition  # 匯入您的車牌辨識模組

# 資料庫連接設定
db = pymysql.connect(
    host="localhost",  # 資料庫主機
    user="root",       # 使用者名稱
    password="1234",   # 密碼
    database="accidents"  # 資料庫名稱
)

# 資料插入函式（包含車牌辨識後的資料）
def insert_data_after_recognition(cam_id, speed_limit, current_speed, location, date_time, image_path, licence_plate):
    try:
        cursor = db.cursor()

        # 修改插入的 SQL 語句，將資料庫直接插入，包含車牌號碼
        sql = """
        INSERT INTO Accidents (cam_id, speed_limit, current_speed, location, date_time, image, recognized, licence_plate)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        # 使用參數化查詢來防止 SQL 注入
        cursor.execute(sql, (cam_id, speed_limit, current_speed, location, date_time, image_path, "2" if licence_plate else "1", licence_plate))
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
        cam_id = input("輸入攝影機編號（cam_id，例如 'CAM12345'）：")
        speed_limit = int(input("輸入速限（speed_limit，例如 60）："))
        current_speed = int(input("輸入目前速度（current_speed，例如 80）："))
        location = input("輸入事故地點（location，例如 '台北市中正區羅斯福路一段12號'）：")
        date_time = input("輸入日期時間（date_time，例如 '2024-12-22 15:30:00'）：")
        image_filename = input("輸入圖片檔案名稱（例如 '0001.jpg'）：")

        # 預設路徑設定
        image_path = f"License_plate/{image_filename}"

        if not os.path.exists(image_path):
            print(f"圖片檔案 {image_filename} 不存在，請檢查路徑！")
            return

        # 進行車牌辨識
        licence_plate, recognized_status = License_plate_recognition.get_License_plate_data(image_path)

        if recognized_status == "2":
            print(f"辨識成功: 車牌號碼是 {licence_plate}")
        else:
            print("車牌辨識失敗或不確定，需人工辨視。")
            licence_plate = None

        # 一次性插入資料庫（包含車牌號碼及辨識結果）
        insert_data_after_recognition(cam_id, speed_limit, current_speed, location, date_time, image_filename, licence_plate)

    except ValueError as e:
        print(f"輸入資料格式有誤：{e}")


# 主選單
def main():
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
