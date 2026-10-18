-- CampusStay Payment mock. Import into campusstay_payment as cs_payment.
CREATE TABLE IF NOT EXISTS payments (
    id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
    booking_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
    amount_minor BIGINT NOT NULL CHECK (amount_minor > 0), currency CHAR(3) NOT NULL,
    simulation VARCHAR(16) NOT NULL CHECK (simulation IN ('success','decline','slow_success')),
    status VARCHAR(12) NOT NULL CHECK (status IN ('CHARGED','DECLINED','REFUNDED')),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS refunds (
    id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
    payment_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
    amount_minor BIGINT NOT NULL CHECK (amount_minor > 0),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    FOREIGN KEY (payment_id) REFERENCES payments(id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS idempotency_records (
    scope VARCHAR(80) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    idem_key VARCHAR(128) COLLATE utf8mb4_bin NOT NULL,
    fingerprint CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    http_status INT, response_body JSON,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (scope,idem_key)
) ENGINE=InnoDB;
