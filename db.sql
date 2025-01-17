DROP DATABASE IF EXISTS sa;

DROP DATABASE IF EXISTS accidents;
CREATE DATABASE accidents;
USE accidents;

DROP TABLE IF EXISTS Accidents;
CREATE TABLE IF NOT EXISTS Accidents (
    accident_id INT AUTO_INCREMENT PRIMARY KEY,
    cam_id VARCHAR(15) NOT NULL,
    speed_limit INT,
    current_speed INT,
    licence_plate VARCHAR(15),
    location VARCHAR(100),
    date_time DATETIME,
    image VARCHAR(200),
    latitude FLOAT,
    longitude FLOAT,
    recognized VARCHAR(3),             -- 1(ai no), 2(ai yes), 3(human yes), 4(done), 5(unrecognizable)
    confidence FLOAT,
    ai_error_code VARCHAR(20),
    manual_comments VARCHAR(20)
) AUTO_INCREMENT=10000001;

CREATE TABLE preview_lifetime (
    accident_id INT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
CREATE EVENT delete_preview
ON SCHEDULE EVERY 10 second
DO
  DELETE FROM preview_lifetime
  WHERE created_at < NOW() - INTERVAL 3 minute;
SET GLOBAL event_scheduler = ON;

DROP TABLE IF EXISTS traffic_ticket;
CREATE TABLE IF NOT EXISTS traffic_ticket (
    traffic_ticket_id INT AUTO_INCREMENT PRIMARY KEY,
    accident_id INT,
    cam_id VARCHAR(15) NOT NULL,
    speed_limit INT,
    current_speed INT,
    licence_plate VARCHAR(15) NOT NULL,
    confidence FLOAT NOT NULL,
    location VARCHAR(100),
    date_time DATETIME,
    image VARCHAR(200),
    owner_id VARCHAR(10),
    owner_name VARCHAR(100),
    address VARCHAR(255)
)AUTO_INCREMENT=10000001;

CREATE TABLE IF NOT EXISTS Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,                    -- 用來關聯使用者
    action VARCHAR(255),             -- 例如 "辨識車牌" 或 "修改車牌"
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 操作時間
    accident_id INT,                -- 關聯的事故
    FOREIGN KEY (user_id) REFERENCES users(user_id),  -- 關聯使用者資料表
    FOREIGN KEY (accident_id) REFERENCES accidents(accident_id) -- 關聯事故資料表
);

CREATE TABLE IF NOT EXISTS ticket_issuer (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE ticket_issue_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,                    -- 用來關聯使用者
    action VARCHAR(255),             -- 例如 "辨識車牌" 或 "修改車牌"
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 操作時間
    accident_id INT,                -- 關聯的事故ticket_issue_logs
    FOREIGN KEY (user_id) REFERENCES ticket_issuer(user_id),  -- 關聯使用者資料表
    FOREIGN KEY (accident_id) REFERENCES accidents(accident_id) -- 關聯事故資料表
);

ALTER TABLE logs ADD COLUMN details TEXT;



DROP DATABASE IF EXISTS vehicle_registration;
CREATE DATABASE vehicle_registration;
USE vehicle_registration;

DROP TABLE IF EXISTS VehicleOwners;
CREATE TABLE IF NOT EXISTS VehicleOwners (
    licence_plate VARCHAR(15) PRIMARY KEY,
    owner_id VARCHAR(10),
    owner_name VARCHAR(100),
    address VARCHAR(255),
    state VARCHAR(255)
);

INSERT INTO VehicleOwners (licence_plate, owner_id, owner_name, address,state) VALUES
('AFF-0666','T478591587', '劉阿豪', '桃園市八德區永福路8號',"正常"),
#('ALN-7568','D478591587', '林美惠', '高雄市苓雅區三多一路200巷5號',"正常"),
('BGR-5851','F478591587', '劉土豪', '桃園市缺德路87號',"正常"),
('ABC-1234','S478591587', '陳怡君', '台中市西屯區台灣大道三段25號',"失竊車輛");