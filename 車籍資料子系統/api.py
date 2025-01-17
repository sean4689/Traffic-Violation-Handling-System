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
    try:
        connection = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        return connection
    except mysql.connector.Error as err:
        return {"error": f"Database connection failed: {err}"}

# 查詢車牌號對應的資料
@app.route('/get_vehicle_info', methods=['POST'])
def get_vehicle_info():
    try:
        data = request.get_json()  # 從請求中取得 JSON 資料
        if not data or 'licence_plate' not in data:
            return jsonify({"error": "Invalid request. 'licence_plate' is required"}), 400

        licence_plate = data.get('licence_plate')  # 取得車牌號

        # 建立資料庫連線
        conn = get_db_connection()
        if isinstance(conn, dict) and "error" in conn:
            return jsonify(conn), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # 查詢車牌資料
        query = """
        SELECT 
            licence_plate,
            owner_id,
            owner_name,
            address,
            state
        FROM 
            VehicleOwners
        WHERE 
            licence_plate = %s
        """
        cursor.execute(query, (licence_plate,))
        vehicle_info = cursor.fetchall()
        
        # 關閉連線
        cursor.close()
        conn.close()
        
        if not vehicle_info:
            return jsonify({"message": "No data found for this licence plate"}), 404

        # 回傳資料為 JSON 陣列格式
        return jsonify(vehicle_info)
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5555)
