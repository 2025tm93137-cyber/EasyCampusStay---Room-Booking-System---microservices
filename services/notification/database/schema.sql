-- CampusStay Notification mock. No real email or SMS is sent.
CREATE TABLE IF NOT EXISTS notifications (
    id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
    booking_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
    recipient VARCHAR(254) NOT NULL,
    status VARCHAR(12) NOT NULL CHECK (status IN ('SENT','FAILED')),
    attempts INT NOT NULL CHECK (attempts > 0),
    simulation VARCHAR(12) NOT NULL CHECK (simulation IN ('success','fail_once')),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS idempotency_records (
    scope VARCHAR(80) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    idem_key VARCHAR(128) COLLATE utf8mb4_bin NOT NULL,
    fingerprint CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    http_status INT, response_body JSON,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (scope,idem_key)
) ENGINE=InnoDB;
