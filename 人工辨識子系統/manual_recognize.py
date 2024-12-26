from flask import Flask, render_template, request, redirect, session, flash, jsonify, url_for
import mysql.connector
import bcrypt
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 用於 session 或 flash 消息

# 資料庫連線設定
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',
    'database': 'accidents'
}

def log_action(user_id, action, accident_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    query = """
    INSERT INTO logs (user_id, action, timestamp, accident_id)
    VALUES (%s, %s, %s, %s)
    """
    cursor.execute(query, (user_id, action, datetime.now(), accident_id))
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

    # 根據選擇的狀態查詢資料
    if status == '1':
        query = "SELECT * FROM Accidents WHERE recognized = '1'"
    elif status == '3':
        query = "SELECT * FROM Accidents WHERE recognized IN (2, 3)"

    cursor.execute(query)
    accidents = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(accidents=accidents)

@app.route('/recognize/<int:accident_id>', methods=['GET', 'POST'])
def recognize(accident_id):
    if 'username' not in session:
        return redirect('/login')

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    # 查詢事故資料
    query = "SELECT * FROM Accidents WHERE accident_id = %s"
    cursor.execute(query, (accident_id,))
    accident = cursor.fetchone()

    if request.method == 'POST':
        new_licence_plate = request.form.get('licence_plate')
        
        # 更新車牌資料
        update_query = """
            UPDATE Accidents
            SET licence_plate = %s, recognized = '3'
            WHERE accident_id = %s
        """
        cursor.execute(update_query, (new_licence_plate, accident_id))
        conn.commit()

        # 取得用戶 ID
        username = session['username']
        cursor.execute("SELECT user_id FROM Users WHERE username = %s", (username,))
        user = cursor.fetchone()
        user_id = user['user_id'] if user else None

        if user_id:
            # 記錄操作日志
            log_action(user_id, "辨識車牌", accident_id)

        # 顯示成功訊息
        flash("車牌已更新！", "success")
        return redirect('/')

    cursor.close()
    conn.close()

    return render_template('recognize_page.html', accident=accident)


@app.route('/logs')
def logs():
    if 'username' not in session:
        return redirect('/login')

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    # 查詢所有日志紀錄
    cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC")
    log_entries = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('logs_page.html', logs=log_entries)




if __name__ == '__main__':
    app.run(debug=True,port=5000)
