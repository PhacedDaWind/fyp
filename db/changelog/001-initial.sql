--liquibase formatted sql
--changeset help:001
CREATE TABLE users (id VARCHAR(36) PRIMARY KEY, email VARCHAR(150) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL, role VARCHAR(16) NOT NULL);
CREATE TABLE sessions (token VARCHAR(64) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, expires BIGINT NOT NULL, FOREIGN KEY (user_id) REFERENCES users(id));
CREATE TABLE vehicles (id VARCHAR(36) PRIMARY KEY, plate VARCHAR(12) NOT NULL UNIQUE, owner VARCHAR(100) NOT NULL, category VARCHAR(16) NOT NULL, ownerId VARCHAR(50) NOT NULL, model VARCHAR(100) NOT NULL, validFrom VARCHAR(10) NOT NULL, validTo VARCHAR(10) NOT NULL, notes VARCHAR(500) NOT NULL, blocked BOOLEAN NOT NULL);
CREATE TABLE activity (id VARCHAR(36) PRIMARY KEY, message VARCHAR(500) NOT NULL, at VARCHAR(40) NOT NULL, actor VARCHAR(150) NOT NULL);
CREATE TABLE attempts (id VARCHAR(36) PRIMARY KEY, plate VARCHAR(12) NOT NULL, direction VARCHAR(8) NOT NULL, decision VARCHAR(16) NOT NULL, reason VARCHAR(150) NOT NULL, created BIGINT NOT NULL, approved_by VARCHAR(150), confirmed BOOLEAN NOT NULL DEFAULT FALSE, visit_id VARCHAR(36), duration_seconds BIGINT);
CREATE TABLE visits (id VARCHAR(36) PRIMARY KEY, plate VARCHAR(12) NOT NULL, kind VARCHAR(16) NOT NULL, entry_at VARCHAR(40), exit_at VARCHAR(40), duration_seconds BIGINT, status VARCHAR(16) NOT NULL, guard VARCHAR(150), entry_attempt VARCHAR(36) UNIQUE, exit_attempt VARCHAR(36) UNIQUE, open_plate VARCHAR(12) UNIQUE);
CREATE INDEX visits_plate ON visits(plate);
CREATE INDEX activity_time ON activity(at);
--rollback DROP TABLE visits;
--rollback DROP TABLE attempts;
--rollback DROP TABLE activity;
--rollback DROP TABLE vehicles;
--rollback DROP TABLE sessions;
--rollback DROP TABLE users;
