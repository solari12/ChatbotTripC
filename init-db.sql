-- Initialize TripC.AI Chatbot Database with PgVector extension

-- Create vector database
CREATE DATABASE tripc_vectors;

-- Connect to vector database
\c tripc_vectors;

-- Enable PgVector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create embedding table for vector search
CREATE TABLE IF NOT EXISTS embedding (
    id SERIAL PRIMARY KEY,
    json_path TEXT NOT NULL,
    raw_content TEXT NOT NULL,
    embedding vector(1536), -- OpenAI text-embedding-3-small dimension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS embedding_vector_idx ON embedding USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create index for content search
CREATE INDEX IF NOT EXISTS embedding_content_idx ON embedding USING gin(to_tsvector('english', raw_content));

-- Create table for chat history (optional)
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    intent TEXT,
    platform TEXT,
    device TEXT,
    language TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for chat history
CREATE INDEX IF NOT EXISTS chat_history_session_idx ON chat_history(session_id);
CREATE INDEX IF NOT EXISTS chat_history_created_idx ON chat_history(created_at);

-- Create table for user bookings (optional)
CREATE TABLE IF NOT EXISTS user_bookings (
    id SERIAL PRIMARY KEY,
    booking_reference TEXT UNIQUE NOT NULL,
    user_name TEXT NOT NULL,
    user_email TEXT NOT NULL,
    user_phone TEXT,
    booking_type TEXT NOT NULL,
    booking_details JSONB,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for bookings
CREATE INDEX IF NOT EXISTS user_bookings_reference_idx ON user_bookings(booking_reference);
CREATE INDEX IF NOT EXISTS user_bookings_email_idx ON user_bookings(user_email);
CREATE INDEX IF NOT EXISTS user_bookings_status_idx ON user_bookings(status);

-- Grant permissions to tripc_user
GRANT ALL PRIVILEGES ON DATABASE tripc_vectors TO tripc_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tripc_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tripc_user;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for user_bookings
CREATE TRIGGER update_user_bookings_updated_at 
    BEFORE UPDATE ON user_bookings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
