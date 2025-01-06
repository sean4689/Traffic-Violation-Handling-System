from flask import Flask, render_template, send_from_directory, request, redirect, url_for
import mysql.connector
from fpdf import FPDF
import os
import time
import threading
import shutil
from PIL import Image
import requests

app = Flask(__name__)

# 設定 PDF 存儲資料夾
folder_path = 'preview'
if not os.path.exists(folder_path):
    os.makedirs(folder_path)

# 資料庫設定
db_config_accidents = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',
    'database': 'accidents'
}

db_config_vehicle_registration = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',
    'database': 'vehicle_registration'
}

# 建立資料庫連線
def get_db_connection(db_config):
    connection = mysql.connector.connect(
        host=db_config['host'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database']
    )
    return connection

# 查詢 accidents 資料表中 recognized 是 "2or3" 的 accident_id
def get_recognized_accidents():
    conn = get_db_connection(db_config_accidents)
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT accident_id, licence_plate FROM Accidents WHERE recognized IN (2, 3);")
    accidents = cursor.fetchall()
    
    
    cursor.close()
    conn.close()
    return accidents

# 查詢 vehicle_registration 資料庫中的車輛詳細資訊
def get_vehicle_details(licence_plate):
    conn = get_db_connection(db_config_vehicle_registration)
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM VehicleOwners WHERE licence_plate = %s", (licence_plate,))
    details = cursor.fetchall()
    print(details)
    
    cursor.close()
    conn.close()
    return details


from fpdf import FPDF

#產生PDF
@app.route('/generate_ticket_pdf/<accident_id>')
def generate_ticket_pdf(accident_id):
    # 連接事故資料庫
    conn_accidents = get_db_connection(db_config_accidents)
    cursor_accidents = conn_accidents.cursor(dictionary=True)
    
    # 查詢事故資料
    cursor_accidents.execute("SELECT * FROM Accidents WHERE accident_id = %s", (accident_id,))
    accident = cursor_accidents.fetchone()
    
    if not accident:
        cursor_accidents.close()
        conn_accidents.close()
        return "事故資料未找到"

    # 取得車牌號碼
    licence_plate = accident['licence_plate']

    # 連接車主資料庫並查詢車主資料
    conn_vehicle = get_db_connection(db_config_vehicle_registration)
    cursor_vehicle = conn_vehicle.cursor(dictionary=True)
    cursor_vehicle.execute("SELECT * FROM VehicleOwners WHERE licence_plate = %s", (licence_plate,))
    vehicle_details = cursor_vehicle.fetchone()
    
    if not vehicle_details:
        cursor_vehicle.close()
        conn_vehicle.close()
        return "車主資料未找到"
    
    cursor_accidents.close()
    cursor_vehicle.close()
    conn_accidents.close()
    conn_vehicle.close()

    # 開始生成 PDF
    pdf = FPDF(orientation='P', unit='mm', format=(210, 220))
    pdf.add_page()

    # 設定中文字型
    pdf.add_font('TC', '', "text.ttf", uni=True)
    pdf.set_font('TC', '', 12)

    # 設定背景顏色
    pdf.set_fill_color(255, 182, 193)  # 粉紅色
    pdf.rect(0, 0, 210, 220, 'F')  # 填充背景

    # 罰單標題
    pdf.cell(200, 10, txt="交通罰單", ln=True, align='C')
    pdf.ln(10)
    
    # 內容區塊
    pdf.set_text_color(0, 0, 0)
    pdf.cell(60, 10, '違規編號', border=1, align='C', fill=False)
    pdf.cell(130, 10, str(accident_id), border=1, align='C', fill=False)
    pdf.ln()
    pdf.cell(60, 10, '車牌號碼', border=1, align='C', fill=False)
    pdf.cell(130, 10, licence_plate, border=1, align='C', fill=False)
    pdf.ln()
    pdf.cell(60, 10, '車主姓名', border=1, align='C', fill=False)
    pdf.cell(130, 10, vehicle_details['owner_name'], border=1, align='C', fill=False)
    pdf.ln()
    pdf.cell(60, 10, '車主身分證號', border=1, align='C', fill=False)
    pdf.cell(130, 10, vehicle_details['owner_id'], border=1, align='C', fill=False)
    pdf.ln()
    pdf.cell(60, 10, '車主地址', border=1, align='C', fill=False)
    pdf.cell(130, 10, vehicle_details['address'], border=1, align='C', fill=False)
    pdf.ln()
    pdf.cell(60, 10, '違規地點', border=1, align='C', fill=False)
    pdf.cell(130, 10, accident['location'], border=1, align='C', fill=False)
    pdf.ln()
    pdf.cell(60, 10, '違規日期', border=1, align='C', fill=False)
    pdf.cell(130, 10, accident['date_time'].strftime('%Y-%m-%d'), border=1, align='C', fill=False)
    pdf.ln()
    pdf.cell(60, 10, '違規時間', border=1, align='C', fill=False)
    pdf.cell(130, 10, accident['date_time'].strftime('%H:%M:%S'), border=1, align='C', fill=False)
    pdf.ln()

    # 如果有現場圖片，則顯示
    if accident['image']:
        image_path = os.path.join("./static/License_plate", accident['image'])
        if os.path.exists(image_path):
            pdf.cell(60, 10, '現場照片', border=1, align='C', fill=False)
            pdf.image(image_path, x=80, y=pdf.get_y(), w=50)  # 放置圖片，大小可根據需求調整
        else:
            pdf.cell(60, 10, '現場照片', border=1, align='C', fill=False)
            pdf.cell(130, 10, '圖片不存在', border=1, align='C', fill=False)
    
    # 建立 lifetime 資料
    add_recognized_accidents_to_table(accident_id)
    
    # 儲存 PDF
    output_path = f"preview/{accident_id}.pdf"
    if os.path.exists(output_path):
        pdf.output(output_path)
        return "1"  # 檔案已存在，回傳 1
    pdf.output(output_path)
    return "0"  # 檔案不存在，回傳 0




# 將已的事故資料加入 preview_lifetime 資料表，並刷新 created_at
def add_recognized_accidents_to_table(accident_id):
    conn = get_db_connection(db_config_accidents)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO preview_lifetime (accident_id) 
            VALUES (%s) 
            ON DUPLICATE KEY UPDATE created_at = CURRENT_TIMESTAMP
            """,
            (accident_id,)
        )
        conn.commit()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        conn.close()



# 下載 PDF 檔案（給HTML用）
@app.route('/download_ticket/<accident_id>')
def download_ticket(accident_id):
    ticket_path = os.path.join(folder_path, f"{accident_id}.pdf")
    return send_from_directory(folder_path, f"{accident_id}.pdf")



# 罰單預覽頁面
@app.route('/ticket_preview/<accident_id>')
def ticket_preview(accident_id):
    # 連接資料庫
    conn = get_db_connection(db_config_accidents)
    cursor = conn.cursor(dictionary=True)
    
    # 查詢事故資料
    cursor.execute("SELECT * FROM Accidents WHERE accident_id = %s", (accident_id,))
    accident = cursor.fetchone()

    # 查詢車主資料
    vehicle_details = get_vehicle_details(accident['licence_plate'])

    cursor.close()
    conn.close()
    
    # 生成 PDF 罰單
    ticket_path = generate_ticket_pdf(accident_id)
    
    # 傳遞事故和車主資料到模板
    return render_template('ticket_preview.html', ticket_path=ticket_path, accident_id=accident_id, accident=accident, vehicle_details=vehicle_details[0])




def send_ticket(accident_id):
    # 檔案來源資料夾
    source_folder = 'preview'
    
    # 檔案目標資料夾
    target_folder = 'traffic_tickets'
    
    # 檔案名稱
    source_file = os.path.join(source_folder, f'{accident_id}.pdf')
    target_file = os.path.join(target_folder, f'{accident_id}.pdf')
    
    # 確保目標資料夾存在
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    
    # 檢查來源檔案是否存在
    if os.path.exists(source_file):
        try:
            # 複製檔案
            shutil.copy(source_file, target_file)
            print(f"檔案 {accident_id}.pdf 已成功從 {source_folder} 複製到 {target_folder}.")
        except Exception as e:
            print(f"複製檔案時發生錯誤: {e}")
    else:
        print(f"檔案 {accident_id}.pdf 不存在於 {source_folder}.")
        

    conn = get_db_connection(db_config_accidents)
    cursor = conn.cursor()
    
    cursor.execute("SELECT location FROM Accidents WHERE accident_id = %s;", (accident_id,))
    location = cursor.fetchone()
    coordinates=get_coordinates(location, access_token)
    longitude = coordinates[0]
    latitude = coordinates[1]
    cursor.execute("UPDATE Accidents SET longitude = %s WHERE accident_id = %s", (longitude, accident_id))
    cursor.execute("UPDATE Accidents SET latitude = %s WHERE accident_id = %s", (latitude, accident_id))
    cursor.execute("UPDATE Accidents SET recognized=5 WHERE accident_id = %s", (accident_id,))
    conn.commit()
    
    cursor.close()
    conn.close()


# 列印罰單
@app.route('/print_ticket/<accident_id>', methods=['POST'])
def print_ticket(accident_id):

    #複製預覽PDF
    send_ticket(accident_id)
    
    # 返回首頁
    return redirect(url_for('preview_data'))

# 將錯誤罰單回傳給人工識別
@app.route('/ticket_wrong/<accident_id>', methods=['POST'])
def ticket_wrong(accident_id):
    conn = get_db_connection(db_config_accidents)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Accidents SET recognized = 1 WHERE accident_id = %s", (accident_id,))
        conn.commit()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('preview_data'))
    
# 主路由
@app.route('/preview_data')
def preview_data():
    # 取得 accidents 資料表中 recognized 為 "2or3" 的事故資料
    recognized_accidents = get_recognized_accidents()
    
    # 將每個事故的 licence_plate 對應的詳細資料存入 results
    results = []
    for accident in recognized_accidents:
        vehicle_details = get_vehicle_details(accident['licence_plate'])
        
        results.append({
            "accident_id": accident['accident_id'],
            "licence_plate": accident['licence_plate'],
            "details": vehicle_details
        })
    
    # 將資料傳遞到 HTML 模板
    return render_template('preview.html', results=results)


# 資料表名稱與欄位
table_name = "preview_lifetime"
unique_column = "accident_id"

def delete_preview():
    # 建立資料庫連線
    connection = get_db_connection(db_config_accidents)
    cursor = connection.cursor()

    try:
        # 獲取資料夾中的所有 PDF 檔案名稱
        pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]

        for pdf_file in pdf_files:
            # 去掉檔案的副檔名，獲取唯一碼
            unique_code = os.path.splitext(pdf_file)[0]
            
            # 檢查資料庫中是否存在該唯一碼
            query = f"SELECT COUNT(*) FROM {table_name} WHERE {unique_column} = %s"
            cursor.execute(query, (unique_code,))
            result = cursor.fetchone()

            # 如果資料庫中沒有該唯一碼，刪除該檔案
            if result[0] == 0:
                file_path = os.path.join(folder_path, pdf_file)
                os.remove(file_path)
                print(f"已刪除檔案: {file_path}")

    except mysql.connector.Error as err:
        print(f"資料庫錯誤: {err}")
    except Exception as e:
        print(f"執行錯誤: {e}")
    finally:
        # 關閉資料庫連線
        cursor.close()
        connection.close()

def run_delete_preview():
    while True:
        delete_preview()
        time.sleep(10)  # 每10秒執行一次清理

# 在一個獨立的線程中運行定時清理程式
preview_delete_thread = threading.Thread(target=run_delete_preview, daemon=True)
preview_delete_thread.start()

access_token="pk.eyJ1Ijoic2VhbjEwMTEiLCJhIjoiY200bGVlNGNxMDB1ZjJqcThxZ3FpZW96aiJ9.AYZsVeMfUy0hFDw1yHhKYA"
def get_coordinates(address, access_token):
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address}.json"
    params = {
        'access_token': access_token,
        'limit': 1
    }
    response = requests.get(url, params=params)
    data = response.json()

    if 'features' in data and len(data['features']) > 0:
        coordinates = data['features'][0]['geometry']['coordinates']
        return coordinates
    else:
        return None
        

if __name__ == '__main__':
    app.run(debug=True,port=5001)
