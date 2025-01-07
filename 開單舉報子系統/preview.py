from flask import Flask, render_template, send_from_directory, request, redirect, url_for, session, flash
import mysql.connector
from fpdf import FPDF
import os
import bcrypt
import time
import threading
import shutil
from PIL import Image
import requests
from datetime import timedelta
from datetime import datetime

app = Flask(__name__)
app.secret_key = '1234'

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

def log_action(user_id, action, accident_id):
    conn = get_db_connection(db_config_accidents)
    cursor = conn.cursor()
    query = """
    INSERT INTO ticket_issue_logs (user_id, action, timestamp, accident_id)
    VALUES (%s, %s, %s, %s)
    """
    cursor.execute(query, (user_id, action, datetime.now(), accident_id))
    conn.commit()
    cursor.close()
    conn.close()

# 註冊功能
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        conn = get_db_connection(db_config_accidents)
        cursor = conn.cursor()
        
        # 檢查帳號是否已經存在
        cursor.execute("SELECT * FROM ticket_issuer WHERE username = %s", (username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            flash("帳號已存在，請選擇其他帳號", 'error')
        else:
            # 插入新用戶
            cursor.execute("INSERT INTO ticket_issuer (username, password) VALUES (%s, %s)", (username, hashed_password))
            conn.commit()
            flash("註冊成功，請登入", 'success')
            return redirect('/login')
        
        cursor.close()
        conn.close()
    
    return render_template('register.html')

# 用戶登入功能
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection(db_config_accidents)
        cursor = conn.cursor(dictionary=True)
        
        # 查詢用戶是否存在
        cursor.execute("SELECT * FROM ticket_issuer WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['user_id'] = user['user_id']  # 設置 session
            session['username'] = user['username']  # 設置 session
            return redirect('/preview_data')
        else:
            flash("帳號或密碼錯誤", 'error')
    return render_template('login.html')

# 登出功能
@app.route('/logout')
def logout():
    session.clear()
    flash('您已成功登出！', 'info')
    return redirect(url_for('login'))

# 記錄用戶操作的函數
def log_user_action(user_id, action, accident_id=None):
    conn = get_db_connection(db_config_accidents)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO ticket_issue_logs (user_id, action, accident_id) VALUES (%s, %s, %s)",
        (user_id, action, accident_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

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
    pdf = FPDF(orientation='P', unit='mm', format=(210, 250))
    pdf.add_page()

    # 插入背景圖片 (指定大小)
    background_image_path = 'static/traffic_ticket.jpg'
    if os.path.exists(background_image_path):
        pdf.image(background_image_path, x=0, y=0, w=210)  # 圖片的起始座標和寬度可調整

    # 設定中文字型
    pdf.add_font('TC', '', "text.ttf", uni=True)
    pdf.set_font('TC', '', 12)
    
    pay_deadline = accident['date_time'] + timedelta(days=45)

    # 定義文字座標
    text_data = [
        {"value": vehicle_details['owner_id'], "x": 125, "y": 48},
        {"value": vehicle_details['owner_name'], "x": 170, "y": 48},
        {"value": licence_plate, "x": 25, "y": 55},
        {"value": vehicle_details['address'], "x": 50, "y": 63},
        {"value": accident['location'], "x": 25, "y": 76},
        {"value": accident['date_time'].strftime('%Y'), "x": 25, "y": 70},
        {"value": accident['date_time'].strftime('%m'), "x": 45, "y": 70},
        {"value": accident['date_time'].strftime('%d'), "x": 58, "y": 70},
        {"value": accident['date_time'].strftime('%H'), "x": 73, "y": 70},
        {"value": accident['date_time'].strftime('%M'), "x": 87, "y": 70},
        {"value": pay_deadline.strftime('%Y'), "x": 37, "y": 82},
        {"value": pay_deadline.strftime('%m'), "x": 58, "y": 82},
        {"value": pay_deadline.strftime('%d'), "x": 80, "y": 82}
    ]

    # 插入文字到 PDF
    for data in text_data:
        pdf.set_xy(data["x"], data["y"])
        pdf.cell(0, 10, f"{data['value']}", ln=False)  # 僅顯示數值


    # 如果有現場圖片，則顯示
    if accident['image']:
        image_path = os.path.join("./static/License_plate", accident['image'])
        if os.path.exists(image_path):
            pdf.image(image_path, x=0, y=145, w=200)  # 現場照片座標和大小
        else:
            pdf.set_xy(0, 145)
            pdf.cell(0, 10, "現場照片: 圖片不存在", ln=False)
    
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
    if 'username' not in session:
        return redirect('/login')
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
    
    if 'user_id' in session:
        user_id=session["user_id"]
        log_action(user_id, "列印罰單", accident_id)
    
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
    
    if 'user_id' in session:
        user_id=session["user_id"]
        log_action(user_id, "錯誤送回", accident_id)
    return redirect(url_for('preview_data'))
    
# 主路由
@app.route('/preview_data')
def preview_data():
    search_query = request.args.get('query', '')  # 獲取查詢參數
    
    # 取得 accidents 資料表中 recognized 為 "2or3" 的事故資料
    recognized_accidents = get_recognized_accidents()
    
    # 每個事故的車牌存入results
    results = []
    for accident in recognized_accidents:
        vehicle_details = get_vehicle_details(accident['licence_plate'])
        
        #顯示輸入參數的對應內容
        if (search_query.lower() in str(accident['accident_id']).lower() or
            search_query.lower() in accident['licence_plate'].lower()):
            results.append({
                "accident_id": accident['accident_id'],
                "licence_plate": accident['licence_plate'],
                "details": vehicle_details
            })
    
    # 傳送到HTML
    if 'username' in session:
        username = session['username']
        return render_template('preview.html', username=username, results=results, query=search_query)
    return redirect('/login')


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
