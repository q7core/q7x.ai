-- Q7C-731: additive isolated schema. Apply once using the Supabase migration tool.
-- Intentionally fail on existing names rather than silently adopting other objects.
CREATE SCHEMA ai_chat;
REVOKE ALL ON SCHEMA ai_chat FROM PUBLIC, anon, authenticated, service_role;

CREATE ROLE ai_chat_api NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE ai_chat_api SET search_path = ai_chat, pg_catalog;
ALTER ROLE ai_chat_api SET statement_timeout = '10s';
ALTER ROLE ai_chat_api SET idle_in_transaction_session_timeout = '15s';

CREATE TABLE ai_chat.message_counter (
  singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
  last_id bigint NOT NULL CHECK (last_id >= 0)
);
INSERT INTO ai_chat.message_counter VALUES (true, 0);

CREATE TABLE ai_chat.messages (
  id bigint PRIMARY KEY CHECK (id > 0),
  sender text NOT NULL CHECK (length(btrim(sender)) > 0 AND octet_length(sender) <= 128),
  channel text NOT NULL DEFAULT 'general' CHECK (length(btrim(channel)) > 0 AND octet_length(channel) <= 128),
  text text NOT NULL CHECK (length(btrim(text)) > 0 AND octet_length(text) <= 16384),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  idempotency_key text CHECK (idempotency_key ~ '^[A-Za-z0-9._:-]{1,128}$'),
  UNIQUE (sender, channel, idempotency_key)
);
CREATE INDEX messages_channel_id ON ai_chat.messages (channel, id);
ALTER TABLE ai_chat.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_chat.message_counter ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON ALL TABLES IN SCHEMA ai_chat FROM PUBLIC, anon, authenticated, service_role;
GRANT USAGE ON SCHEMA ai_chat TO ai_chat_api;
GRANT SELECT ON ai_chat.messages TO ai_chat_api;
CREATE POLICY api_read ON ai_chat.messages FOR SELECT TO ai_chat_api USING (true);

CREATE FUNCTION ai_chat.append_message(p_sender text, p_channel text, p_text text, p_key text DEFAULT NULL)
RETURNS ai_chat.messages
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, ai_chat
AS $$
DECLARE
  result ai_chat.messages;
  new_id bigint;
BEGIN
  -- A sequence or timestamp can publish higher IDs before lower IDs commit.
  -- Every app write MUST use this function: this row lock survives to COMMIT.
  PERFORM 1 FROM ai_chat.message_counter WHERE singleton FOR UPDATE;
  IF p_key IS NOT NULL THEN
    SELECT * INTO result FROM ai_chat.messages
      WHERE sender = p_sender AND channel = p_channel AND idempotency_key = p_key;
    IF FOUND THEN
      IF result.text IS DISTINCT FROM p_text THEN
        RAISE EXCEPTION 'idempotency conflict' USING ERRCODE = '23505';
      END IF;
      RETURN result;
    END IF;
  END IF;
  UPDATE ai_chat.message_counter SET last_id = last_id + 1 WHERE singleton RETURNING last_id INTO new_id;
  INSERT INTO ai_chat.messages (id, sender, channel, text, idempotency_key)
    VALUES (new_id, p_sender, p_channel, p_text, p_key) RETURNING * INTO result;
  RETURN result;
END;
$$;
REVOKE ALL ON FUNCTION ai_chat.append_message(text,text,text,text) FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION ai_chat.append_message(text,text,text,text) TO ai_chat_api;
COMMENT ON TABLE ai_chat.messages IS 'Q7C-731 shared agent messages. Append only through append_message; IDs follow committed write order.';
NOTIFY pgrst, 'reload schema';
NOTIFY pgrst, 'reload config';
