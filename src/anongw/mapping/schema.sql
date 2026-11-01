-- Схема хранилища соответствий (docs/architecture.md §6).
-- Изоляция: составной ключ (user_id, context_id, marker).
-- Консистентность повторов: уникальность normalized_value внутри контекста
-- (NULL не конфликтует — записи без нормализации пока не связаны).
CREATE TABLE IF NOT EXISTS mappings (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          TEXT    NOT NULL,
    context_id       TEXT    NOT NULL,
    marker           TEXT    NOT NULL,
    entity_type      TEXT    NOT NULL,
    original_value   TEXT    NOT NULL,
    normalized_value TEXT,
    created_at       TEXT    NOT NULL,
    expires_at       TEXT    NOT NULL,
    UNIQUE (user_id, context_id, marker),
    UNIQUE (user_id, context_id, normalized_value)
);

CREATE INDEX IF NOT EXISTS idx_mappings_expiry ON mappings (expires_at);
CREATE INDEX IF NOT EXISTS idx_mappings_lookup ON mappings (user_id, normalized_value);
