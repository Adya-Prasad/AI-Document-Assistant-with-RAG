import logging
from datetime import datetime
import streamlit as st
import os
from pathlib import Path
import sqlite3

UPLOAD_DIRECTORY = "./processed_docs"
DB_PATH = "./chat_data.sqlite3"

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

def _init_db():
    """Initialize SQLite DB for chat sessions and messages."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    document_path TEXT,
                    document_unique_name TEXT,
                    document_display_name TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    question TEXT,
                    answer TEXT,
                    response_time REAL,
                    document TEXT,
                    FOREIGN KEY(chat_id) REFERENCES chat_sessions(id)
                )
                """
            )
            conn.commit()
            # Add missing columns in case table existed from older version
            cur.execute("PRAGMA table_info(chat_sessions)")
            existing_cols = {row[1] for row in cur.fetchall()}
            if "document_path" not in existing_cols:
                cur.execute("ALTER TABLE chat_sessions ADD COLUMN document_path TEXT")
            if "document_unique_name" not in existing_cols:
                cur.execute("ALTER TABLE chat_sessions ADD COLUMN document_unique_name TEXT")
            if "document_display_name" not in existing_cols:
                cur.execute("ALTER TABLE chat_sessions ADD COLUMN document_display_name TEXT")
            conn.commit()
    except Exception as e:
        logging.error(f"Failed to initialize DB: {e}")

_init_db()

def add_log(message, log_type="INFO"):
    """Add a log entry with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {log_type}: {message}"
    st.session_state.process_logs.append(log_entry)
    logging.info(message)

def clear_logs():
    """Clear all process logs"""
    st.session_state.process_logs = []

def add_to_chat_history(question, answer, response_time, doc_name):
    """Add question and answer to chat history"""
    chat_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "answer": answer,
        "response_time": response_time,
        "document": doc_name
    }
    st.session_state.chat_history.append(chat_entry)

    # Persist to DB under current chat session
    try:
        # Ensure a chat session exists
        if 'chat_id' not in st.session_state or st.session_state.get('chat_id') is None:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO chat_sessions(created_at) VALUES (?)",
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),)
                )
                st.session_state.chat_id = cur.lastrowid
                conn.commit()

        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO chat_messages(chat_id, timestamp, question, answer, response_time, document)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    st.session_state.chat_id,
                    chat_entry["timestamp"],
                    chat_entry["question"],
                    chat_entry["answer"],
                    chat_entry["response_time"],
                    chat_entry["document"],
                ),
            )
            # Update current chat session with document metadata for switching later
            try:
                if st.session_state.get('current_document'):
                    cur.execute(
                        """
                        UPDATE chat_sessions
                        SET document_path = ?, document_unique_name = ?, document_display_name = ?
                        WHERE id = ?
                        """,
                        (
                            st.session_state.current_document.get('path'),
                            st.session_state.current_document.get('unique_name'),
                            st.session_state.current_document.get('name'),
                            st.session_state.chat_id,
                        ),
                    )
            except Exception as e:
                logging.error(f"Failed to update chat session doc metadata: {e}")
            conn.commit()
    except Exception as e:
        logging.error(f"Failed to persist chat message: {e}")

def start_new_chat_session():
    """Start a new chat within the same session (keeps current document/vector DB). Returns new chat_id."""
    new_chat_id = None
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO chat_sessions(created_at) VALUES (?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),)
            )
            new_chat_id = cur.lastrowid
            st.session_state.chat_id = new_chat_id
            conn.commit()
    except Exception as e:
        logging.error(f"Failed to create new chat session: {e}")

    # Reset in-memory chat-related state but keep document/vector_db
    st.session_state.chat_history = []
    st.session_state.process_logs = []
    st.session_state.last_response = None
    # Clear input box if present
    try:
        st.session_state["query_input"] = ""
    except Exception:
        pass

    return new_chat_id

def get_chat_sessions():
    """Return list of chat sessions sorted by newest first."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT s.id,
                       s.document_display_name,
                       (
                         SELECT m.answer
                         FROM chat_messages m
                         WHERE m.chat_id = s.id
                         ORDER BY m.id DESC
                         LIMIT 1
                       ) AS last_answer
                FROM chat_sessions s
                ORDER BY s.id DESC
                """
            )
            rows = cur.fetchall()
            sessions = [
                {
                    "id": r[0],
                    "document_display_name": r[1],
                    "last_answer": r[2],
                }
                for r in rows
            ]
            return sessions
    except Exception as e:
        logging.error(f"Failed to fetch chat sessions: {e}")
        return []

def get_chat_messages(chat_id):
    """Return messages for a chat session (oldest first)."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT timestamp, question, answer, response_time, document
                FROM chat_messages
                WHERE chat_id = ?
                ORDER BY id ASC
                """,
                (chat_id,),
            )
            rows = cur.fetchall()
            messages = [
                {
                    "timestamp": r[0],
                    "question": r[1],
                    "answer": r[2],
                    "response_time": r[3],
                    "document": r[4],
                }
                for r in rows
            ]
            return messages
    except Exception as e:
        logging.error(f"Failed to fetch chat messages: {e}")
        return []

def get_chat_metadata(chat_id):
    """Return stored document metadata for a chat session."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT document_path, document_unique_name, document_display_name FROM chat_sessions WHERE id = ?",
                (chat_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "path": row[0],
                "unique_name": row[1],
                "name": row[2],
            }
    except Exception as e:
        logging.error(f"Failed to fetch chat metadata: {e}")
        return None

def delete_chat_session(chat_id: int) -> None:
    """Delete a chat session and all of its messages."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM chat_messages WHERE chat_id = ?", (chat_id,))
            cur.execute("DELETE FROM chat_sessions WHERE id = ?", (chat_id,))
            conn.commit()
    except Exception as e:
        logging.error(f"Failed to delete chat session {chat_id}: {e}")

def save_uploaded_file(uploaded_file):
    """Save uploaded file to temporary directory"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d")
        file_extension = Path(uploaded_file.name).suffix
        original_name = Path(uploaded_file.name).stem

        # check if a file with the same original name exists (need to update it!)
        if os.path.exists(UPLOAD_DIRECTORY):
            existing_files = os.listdir(UPLOAD_DIRECTORY)
            for current_file in existing_files:
                if current_file.startswith(f"{original_name}_"):
                    existing_path = os.path.join(UPLOAD_DIRECTORY, current_file).replace(os.sep, '/')
                    add_log(f"SAME Document found in memory: {current_file}")
                    return existing_path, current_file
        # Create unique filename and path in memory
        unique_filename = f"{original_name}_{timestamp}{file_extension}"
        file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename).replace(os.sep, '/')

        # create directory if it don't exist
        os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
        # save the file
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        add_log(f"This file: {unique_filename}, got the FIRST time")
        add_log(f"File saved successfully: {unique_filename}")
        return file_path, unique_filename
    except Exception as e:
        add_log(f"Error saving file: {str(e)}", "ERROR")
        return None, None