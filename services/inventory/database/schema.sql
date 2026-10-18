-- CampusStay Inventory. Import into campusstay_inventory as cs_inventory.
CREATE TABLE IF NOT EXISTS room_types (
    id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    price_minor BIGINT NOT NULL CHECK (price_minor > 0), currency CHAR(3) NOT NULL
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS room_stock (
    room_type_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    stay_date DATE NOT NULL,
    capacity INT NOT NULL CHECK (capacity > 0),
    available INT NOT NULL CHECK (available >= 0 AND available <= capacity),
    PRIMARY KEY (room_type_id, stay_date),
    FOREIGN KEY (room_type_id) REFERENCES room_types(id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS holds (
    id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
    booking_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
    room_type_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    stay_date DATE NOT NULL,
    status VARCHAR(12) NOT NULL CHECK (status IN ('HELD','CONFIRMED','RELEASED')),
    amount_minor BIGINT NOT NULL CHECK (amount_minor > 0), currency CHAR(3) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    FOREIGN KEY (room_type_id,stay_date) REFERENCES room_stock(room_type_id,stay_date)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS idempotency_records (
    scope VARCHAR(80) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    idem_key VARCHAR(128) COLLATE utf8mb4_bin NOT NULL,
    fingerprint CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    http_status INT, response_body JSON,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (scope,idem_key)
) ENGINE=InnoDB;
