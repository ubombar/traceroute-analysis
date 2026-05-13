BEGIN TRANSACTION;

-- Rename columns
ALTER TABLE fies RENAME COLUMN pdid TO probing_directive_id;
ALTER TABLE fies RENAME COLUMN seq TO sequence_number;
ALTER TABLE fies RENAME COLUMN ip TO ip_version;
ALTER TABLE fies RENAME COLUMN dest_addr TO destination_address;
ALTER TABLE fies RENAME COLUMN near_ttl TO near_probe_ttl;
ALTER TABLE fies RENAME COLUMN near_reply TO near_reply_address;
ALTER TABLE fies RENAME COLUMN near_sent TO near_sent_timestamp;
ALTER TABLE fies RENAME COLUMN near_received TO near_received_timestamp;
ALTER TABLE fies RENAME COLUMN far_ttl TO far_probe_ttl;
ALTER TABLE fies RENAME COLUMN far_reply TO far_reply_address;
ALTER TABLE fies RENAME COLUMN far_sent TO far_sent_timestamp;
ALTER TABLE fies RENAME COLUMN far_received TO far_received_timestamp;
ALTER TABLE fies RENAME COLUMN created TO production_timestamp;

-- Add source_address
ALTER TABLE fies ADD COLUMN source_address TEXT;

-- Recreate table with correct constraints
CREATE TABLE fies_new (
    agent_id                TEXT        NOT NULL,
    probing_directive_id    INTEGER     NOT NULL,
    sequence_number         INTEGER     NOT NULL,
    ip_version              INTEGER     NOT NULL,
    protocol                INTEGER     NOT NULL,
    source_address          TEXT        NOT NULL,
    destination_address     TEXT        NOT NULL,
    near_probe_ttl          INTEGER,
    near_reply_address      TEXT,
    near_sent_timestamp     TEXT,
    near_received_timestamp TEXT,
    far_probe_ttl           INTEGER,
    far_reply_address       TEXT,
    far_sent_timestamp      TEXT,
    far_received_timestamp  TEXT,
    production_timestamp    TEXT        NOT NULL
);

INSERT INTO fies_new SELECT
    agent_id,
    probing_directive_id,
    sequence_number,
    ip_version,
    protocol,
    '',
    destination_address,
    near_probe_ttl,
    near_reply_address,
    near_sent_timestamp,
    near_received_timestamp,
    far_probe_ttl,
    far_reply_address,
    far_sent_timestamp,
    far_received_timestamp,
    production_timestamp
FROM fies;

DROP TABLE fies;
ALTER TABLE fies_new RENAME TO fies;

COMMIT;
