import streamlit as st
import logging

from rag_functions import (
    # Core RAG functions
    process_query_with_document,
    process_query,
    create_vector_db_from_document,
    # Constants
    MODEL_NAME,
    EMBEDDING_MODEL
)
from helpers_func import start_new_chat_session, get_chat_sessions, get_chat_messages, get_chat_metadata, delete_chat_session

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'process_logs' not in st.session_state:
    st.session_state.process_logs = []

if 'current_document' not in st.session_state:
    st.session_state.current_document = None

if 'vector_db' not in st.session_state:
    st.session_state.vector_db = None

if 'document_processed' not in st.session_state:
    st.session_state.document_processed = False

if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None

def main():
    # Page config
    st.set_page_config(
        page_title="RAG-Powered Document Assistant",
        page_icon="📄",
        layout="wide"
    )

    # Custom styling with radio button styling
    st.markdown(
        """
        <style>
        .custom-div {
            background-color: #E3E3E312; 
            padding: 9px; 
            border-radius: 6px;
            color: white; 
            margin-top: 6px;
        }
        .st-c5, st-am {
        background-color: #E3E3E312;
        margin: 4px;
        padding: 2px;
        border-radius: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # File uploader with better styling
    uploaded_file = st.file_uploader(
        "🔗 Upload a document (PDF, CSV, JSON, TXT)",
        type=['pdf', 'csv', 'json', 'txt'],
        key="pdf_upload",
    )
    
    user_input = st.chat_input(
        placeholder="Ask a question about your document...",
        key="query_input"
    )
    
    if not uploaded_file:
        st.text("⚠ Please upload a document!")

    # Process when both file and query are provided
    if user_input and uploaded_file:
        process_query_with_document(user_input, uploaded_file)
    elif user_input and st.session_state.get('vector_db') is not None:
        # Allow follow-up queries without re-uploading if a vector DB is active
        process_query(user_input, overall_start:=__import__('time').time())

    # Always render full conversation for active chat in main area
    active_msgs = []
    if st.session_state.get('chat_id') is not None:
        try:
            active_msgs = get_chat_messages(st.session_state.chat_id)
        except Exception:
            active_msgs = []
    elif st.session_state.get('chat_history'):
        active_msgs = st.session_state.chat_history

    if active_msgs:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Conversation")
        for msg in active_msgs:
            if msg.get('question'):
                st.chat_message("user").write(msg['question'])
            if msg.get('answer'):
                st.chat_message("assistant").write(msg['answer'])
        st.markdown('</div>', unsafe_allow_html=True)

    # Sidebar with chat history and system info
    with st.sidebar:
        st.header("RAG-Powered Document Assistant 🤖", divider="green")

        # New Chat button
        if st.button("New Chat ✚", use_container_width=False):
            new_id = start_new_chat_session()
            st.session_state.chat_id = new_id
            st.rerun()

        
        # Chat History (list with selection + snippet). Selecting opens full conversation in main area.
        col_h, col_d = st.columns(2)

        with col_h:
            st.subheader("Chat History")
        with col_d:
            if st.button("Delete", icon=":material/delete:"):
                try:
                    delete_chat_session(st.session_state.chat_id)
                    st.session_state.chat_id = None
                    st.session_state.chat_history = []
                    st.rerun()
                except Exception:
                    pass

        sessions = get_chat_sessions()
        if sessions:
            # Radio to select active chat with last-answer snippet
            def snippet(text):
                return (text or "").replace("\n", " ")[:50]
            labels = [f"Chat {s['id']}, {(s.get('document_display_name') or 'no-document')} — {snippet(s.get('last_answer'))}..." for s in sessions]
            ids = [s['id'] for s in sessions]
            current_id = st.session_state.get('chat_id')
            default_index = ids.index(current_id) if current_id in ids else 0
            selected_label = st.radio("Select a chat", labels, index=default_index, key="chat_select")
            selected_idx = labels.index(selected_label)
            selected_id = ids[selected_idx]
            if current_id != selected_id:
                st.session_state.chat_id = selected_id
                # Restore document and vector DB
                meta = get_chat_metadata(selected_id)
                if meta and meta.get('path'):
                    st.session_state.current_document = meta
                    try:
                        vdb = create_vector_db_from_document(meta['path'])
                        if vdb:
                            st.session_state.vector_db = vdb
                            st.session_state.document_processed = True
                    except Exception:
                        pass
                st.rerun()

        else:
            st.caption("There's no any chat history...")
         
        # using custom styled div
        st.markdown(
            f"""
            <div class="custom-div">
                <b>SYSTEM INFO</b><br>
                Model: <code>{MODEL_NAME}</code> <br>
                Embedding: <code>{EMBEDDING_MODEL}</code>
            </div>
            """,
            unsafe_allow_html=True
        )
        

if __name__ == "__main__":
    main()