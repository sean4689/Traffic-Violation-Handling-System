from flask import Flask, jsonify, Response
import geojson
import pymysql
import re
import json

app = Flask(__name__)

# 資料庫連接設定
def get_db_connection():
    return pymysql.connect(
        host="localhost",  # 資料庫主機
        user="root",       # 使用者名稱
        password="1234",   # 密碼
        database="accidents"  # 資料庫名稱
    )

@app.route('/api/accidents', methods=['GET'])
def get_accidents():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("""
            SELECT cam_id, speed_limit, current_speed, location, date_time, longitude, latitude 
            FROM Accidents
            WHERE recognized = 4
        """)
        rows = cursor.fetchall()
    except pymysql.MySQLError as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

    features = []
    for row in rows:
        location = row['location']
        match = re.match(r'^.*?([^縣市]+?區)(.*路.*?(\d+號|\d+巷)?)', location)
        if match:
            district = match.group(1)  # 提取區名稱
            road_section = match.group(2)  # 提取路段資訊
        else:
            district = ""
            road_section = location  # 若無匹配則返回原字串

        feature = geojson.Feature(
            geometry=geojson.Point((row['longitude'], row['latitude'])),
            properties={
                'cam_id': row['cam_id'],
                'speed_limit': row['speed_limit'],
                'current_speed': row['current_speed'],
                'district': district,
                'road_section': road_section,
                'date_time': row['date_time'].isoformat()
            }
        )
        features.append(feature)



    feature_collection = geojson.FeatureCollection(features)
    response = Response(
        response=json.dumps(feature_collection, ensure_ascii=False),
        mimetype='application/json'
    )
    return response

if __name__ == '__main__':
    app.run(debug=True, port=5003)