from flask import Flask, render_template, request, redirect, session, flash, jsonify, url_for
import mysql.connector
import bcrypt
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 用於 session 或 flash 消息

# 資料庫連線設定
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',
    'database': 'accidents'
}

def log_action(user_id, action, accident_id, details=None):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    query = """
    INSERT INTO logs (user_id, action, timestamp, accident_id, details)
    VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(query, (user_id, action, datetime.now(), accident_id, details))
    conn.commit()
    cursor.close()
    conn.close()


@app.route('/')
def index():
    # 顯示登入的帳號名稱
    if 'username' in session:
        username = session['username']
        return render_template('manual_recognize_page.html', username=username)
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # 檢查帳號是否已經存在
        cursor.execute("SELECT * FROM Users WHERE username = %s", (username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            flash("帳號已存在，請選擇其他帳號", 'error')
        else:
            # 插入新用戶
            cursor.execute("INSERT INTO Users (username, password) VALUES (%s, %s)", (username, hashed_password))
            conn.commit()
            flash("註冊成功，請登入", 'success')
            return redirect('/login')
        
        cursor.close()
        conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        # 查找該用戶
        cursor.execute("SELECT * FROM Users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['username'] = user['username']  # 設置 session
            return redirect('/')
        else:
            flash("帳號或密碼錯誤", 'error')
        
        cursor.close()
        conn.close()
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)  # 清除 session 中的 user_id
    session.pop('username', None)  # 清除 session 中的 username
    flash("您已成功登出", "info")  # 顯示登出提示訊息
    return redirect(url_for('login'))  # 登出後重定向回登入頁面

@app.route('/accidents/<status>')
def get_accidents(status):
    if 'username' not in session:
        return redirect('/login')

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    # 根據選擇的狀態查詢資料，返回事故的辨識狀態
    if status == '1':
        query = "SELECT accident_id, location, date_time, recognized FROM Accidents WHERE recognized = '1'"
    elif status == '3':
        query = "SELECT accident_id, location, date_time, recognized FROM Accidents WHERE recognized IN (2, 3)"
    elif status == '5':
        query = "SELECT accident_id, location, date_time, recognized FROM Accidents WHERE recognized = '5'"

    cursor.execute(query)
    accidents = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(accidents=accidents)

@app.route('/recognize/<int:accident_id>', methods=['GET', 'POST'])
def recognize(accident_id):
    if 'username' not in session:
        return redirect('/login')

    try:
        with mysql.connector.connect(**db_config) as conn:
            with conn.cursor(dictionary=True) as cursor:
                query = "SELECT * FROM Accidents WHERE accident_id = %s"
                cursor.execute(query, (accident_id,))
                accident = cursor.fetchone()

                if not accident:
                    flash("找不到事故資料！", "danger")
                    return redirect('/')

                if request.method == 'POST':
                    new_licence_plate = request.form.get('licence_plate')

                    if not new_licence_plate:
                        flash("請提供車牌號碼！", "danger")
                        return redirect(f'/recognize/{accident_id}')

                    # 調用車牌查詢 API
                    api_url = 'http://localhost:5555/get_vehicle_info'
                    response = requests.post(api_url, json={"licence_plate": new_licence_plate})

                    username = session['username']
                    cursor.execute("SELECT user_id FROM Users WHERE username = %s", (username,))
                    user = cursor.fetchone()
                    user_id = user['user_id'] if user else None

                    if response.status_code == 404:
                        flash("未記錄的車牌！", "danger")
                        
                        # 記錄辨識失敗操作
                        if user_id:
                            log_action(user_id, "辨識失敗", accident_id, f"車牌: {new_licence_plate} 未記錄")
                        
                        # 更新事故標記為「無法辨識」
                        update_query = """
                            UPDATE Accidents
                            SET recognized = 5, manual_comments = %s
                            WHERE accident_id = %s
                        """
                        cursor.execute(update_query, (f"無法辨識車牌: {new_licence_plate}", accident_id))
                        conn.commit()

                        return redirect(f'/recognize/{accident_id}')

                    if response.status_code != 200:
                        flash(f"車牌查詢失敗：{response.json().get('error', '未知錯誤')}", "danger")

                        # 記錄辨識失敗操作
                        if user_id:
                            log_action(user_id, "辨識失敗", accident_id, f"查詢失敗: {new_licence_plate}")

                        return redirect(f'/recognize/{accident_id}')

                    # 成功更新事故資料
                    update_query = """
                        UPDATE Accidents
                        SET licence_plate = %s, recognized = '3'
                        WHERE accident_id = %s
                    """
                    cursor.execute(update_query, (new_licence_plate, accident_id))
                    conn.commit()

                    if user_id:
                        log_action(user_id, "人工辨識完成", accident_id, f"車牌修改為: {new_licence_plate}")
                    
                    flash("事故資料更新成功！", "success")
                    return redirect('/')

        return render_template('recognize_page.html', accident=accident)

    except mysql.connector.Error as e:
        flash(f"資料庫錯誤：{e}", "danger")
        return redirect('/')
    except Exception as e:
        flash(f"發生錯誤：{e}", "danger")
        return redirect('/')

@app.route('/logs')
def view_logs():
    if 'username' not in session:
        return redirect('/login')
    
    try:
        with mysql.connector.connect(**db_config) as conn:
            with conn.cursor(dictionary=True) as cursor:
                query = """
                SELECT L.*, U.username, A.location, A.date_time 
                FROM Logs L
                JOIN Users U ON L.user_id = U.user_id
                LEFT JOIN Accidents A ON L.accident_id = A.accident_id
                ORDER BY L.timestamp DESC
                """
                cursor.execute(query)
                logs = cursor.fetchall()

        return render_template('logs_page.html', logs=logs)
    
    except mysql.connector.Error as e:
        flash(f"資料庫錯誤：{e}", "danger")
        return redirect('/')

@app.route('/unrecognizable/<int:accident_id>', methods=['POST'])
def mark_unrecognizable(accident_id):
    if 'username' not in session:
        return redirect('/login')

    manual_comment = request.form.get('manual_comments', 0)  # 預設為 0 防止空值

    try:
        with mysql.connector.connect(**db_config) as conn:
            with conn.cursor() as cursor:
                update_query = """
                UPDATE Accidents
                SET recognized = 5, manual_comments = %s
                WHERE accident_id = %s
                """
                cursor.execute(update_query, (manual_comment, accident_id))
                conn.commit()
                
                flash("事故已標記為無法辨識", "info")

                # 記錄操作日志
                username = session['username']
                cursor.execute("SELECT user_id FROM Users WHERE username = %s", (username,))
                user = cursor.fetchone()
                user_id = user[0] if user else None
                
                if user_id:
                    log_action(user_id, f"標記事故 {accident_id} 為無法辨識 (原因: {manual_comment})", accident_id)
                
    except mysql.connector.Error as e:
        flash(f"資料庫錯誤: {e}", "danger")
    
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
