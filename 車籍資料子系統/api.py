from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)

# 資料庫設定
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',
    'database': 'vehicle_registration'
}

# 建立資料庫連線
def get_db_connection():
    connection = mysql.connector.connect(
        host=db_config['host'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database']
    )
    return connection

# 查詢車牌號對應的資料
@app.route('/get_vehicle_info', methods=['POST'])
def get_vehicle_info():
    data = request.get_json()  # 從請求中取得 JSON 資料
    licence_plate = data.get('licence_plate')  # 取得車牌號

    if not licence_plate:
        return jsonify({"error": "licence_plate is required"}), 400

    # 建立資料庫連線
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 查詢車牌資料
    cursor.execute("SELECT * FROM VehicleOwners WHERE licence_plate = %s", (licence_plate,))
    vehicle_info = cursor.fetchall()
    
    # 關閉連線
    cursor.close()
    conn.close()
    
    if not vehicle_info:
        return jsonify({"message": "No data found for this licence plate"}), 404

    # 回傳資料為陣列格式
    return jsonify(vehicle_info)

if __name__ == '__main__':
        app.run(debug=True,port=5001)
