-- CampusStay Reservation. Cross-service IDs have no foreign keys to peer databases.
CREATE TABLE IF NOT EXISTS bookings (
    id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
    room_type_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    stay_date DATE NOT NULL, request_body JSON NOT NULL,
    status VARCHAR(24) NOT NULL CHECK (status IN ('PENDING','RESERVED','PAYMENT_PENDING','PAYMENT_UNCERTAIN','PAID','CONFIRMED','COMPENSATING','CANCELLED')),
    amount_minor BIGINT CHECK (amount_minor > 0), currency CHAR(3),
    payment_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin,
    notification_status VARCHAR(12) NOT NULL DEFAULT 'PENDING' CHECK (notification_status IN ('PENDING','SENT')),
    failure_status INT, failure_body JSON, correlation_id VARCHAR(128) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX idx_bookings_recovery (status,updated_at)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS booking_steps (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    booking_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    from_state VARCHAR(24), to_state VARCHAR(24) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    FOREIGN KEY (booking_id) REFERENCES bookings(id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS idempotency_records (
    scope VARCHAR(80) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    idem_key VARCHAR(128) COLLATE utf8mb4_bin NOT NULL,
    fingerprint CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    booking_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
    http_status INT, response_body JSON,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (scope,idem_key), FOREIGN KEY (booking_id) REFERENCES bookings(id)
) ENGINE=InnoDB;
