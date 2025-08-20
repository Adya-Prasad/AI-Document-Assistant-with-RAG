import os
import logging
import time
import hashlib
import streamlit as st
import ollama
from langchain_community.document_loaders import UnstructuredPDFLoader, CSVLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from helpers_func import (
    add_log,
    clear_logs,
    add_to_chat_history,
    save_uploaded_file,
)

# Constants for AI Models and Chroma DB
MODEL_NAME = "codegemma:latest" 
EMBEDDING_MODEL = "nomic-embed-text"
PERSIST_DIRECTORY = "./chroma_db"


def get_file_hash(file_content):
    """Generate hash for uploaded file to detect changes"""
    return hashlib.md5(file_content).hexdigest()

def ingest_docs(doc_path):
    """Load documents for supported file types: PDF, CSV, JSON, TXT"""
    add_log(f"Attempting to load file from: {doc_path}")
    if not os.path.exists(doc_path):
        add_log(f"File not found at path: {doc_path}", "ERROR")
        st.error("File not found")
        return None

    _, ext = os.path.splitext(doc_path)
    ext = ext.lower()

    try:
        if ext == ".pdf":
            add_log("PDF file detected, loading document...")
            loader = UnstructuredPDFLoader(file_path=doc_path)
            docs = loader.load()
            add_log(f"PDF loaded successfully. Found {len(docs)} document(s)")
            return docs
        if ext == ".csv":
            add_log("CSV file detected, loading rows as documents...")
            loader = CSVLoader(file_path=doc_path, encoding="utf-8")
            docs = loader.load()
            add_log(f"CSV loaded successfully. Found {len(docs)} rows")
            return docs
        if ext in (".json", ".txt"):
            add_log(f"{ext.upper()} file detected, loading as text document...")
            loader = TextLoader(doc_path, encoding="utf-8")
            docs = loader.load()
            add_log(f"File loaded successfully. Found {len(docs)} document(s)")
            return docs

        # Fallback: treat as text
        add_log("Unknown extension, loading as plain text")
        loader = TextLoader(doc_path, encoding="utf-8")
        docs = loader.load()
        add_log(f"File loaded successfully. Found {len(docs)} document(s)")
        return docs
    except Exception as e:
        add_log(f"Error loading file: {str(e)}", "ERROR")
        st.error(f"Error loading file: {str(e)}")
        return None

def split_documents(documents):
    """Split documents into smaller chunks with better parameters for detailed content"""
    add_log("Starting document splitting process...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1800,  
        chunk_overlap=400, 
        separators=["\n\n", "\n", ". ", " ", ""], 
        length_function=len,
    )
    chunks = text_splitter.split_documents(documents)
    add_log(f"Documents split into {len(chunks)} chunks with improved parameters")
    return chunks

def create_vector_db_from_document(doc_path):
    """Create vector database from uploaded document"""
    add_log("Creating vector database from uploaded document...")
    
    add_log(f"Ensuring embedding model is available: {EMBEDDING_MODEL}")
    try:
        ollama.pull(EMBEDDING_MODEL)
        add_log("Embedding model ready")
    except Exception as e:
        add_log(f"Error pulling embedding model: {str(e)}", "ERROR")
        return None

    embedding = OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        num_gpu=1
    )

    data = ingest_docs(doc_path)
    if data is None:
        return None
    
    chunks = split_documents(data)

    add_log("Creating vector database from document chunks...")
    try:
        # doc_name = Path(doc_path).stem
        collection_name = f"doc_{get_file_hash(open(doc_path, 'rb').read())[:8]}"
        
        vector_db = Chroma.from_documents(
            documents=chunks,
            embedding=embedding,
            collection_name=collection_name,
        )
        add_log("Vector database created successfully")
        return vector_db
    except Exception as e:
        add_log(f"Error creating vector database: {str(e)}", "ERROR")
        return None

def create_fast_retriever(vector_db):
    """Create a retriever that gets more relevant chunks for detailed responses"""
    add_log("Creating enhanced similarity retriever")
    retriever = vector_db.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 5} 
    )
    add_log("Enhanced retriever created (k = 5 similarity search)")
    return retriever

def create_chain(llm):
    """Create the RAG chain"""
    add_log("Building RAG chain")
    template = """You are a knowledgeable assistant helping users understand documents and extract asked information from the document. Based on attached document, please provide a comprehensive and correct answer to the user's question.

Instructions:
- Use the context to provide as much relevant detail as possible
- highlight the main answer of user question
- Provide thorough answers that satisfy the user's information needs and intention
- Primarily pay attention to data, data tables, data rows , json and other data info and present it in correct format
- If you don't know something based on the context, clearly state what you don't know

Context from the document:
{context}
User Question: {question}
"""

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    add_log("RAG chain created successfully")
    return chain

@st.cache_resource
def preload_model():
    """Preload the model for faster response"""
    add_log(f"Preloading model: {MODEL_NAME}")
    try:
        llm = ChatOllama(
            model=MODEL_NAME,
            num_gpu=1,
            temperature=0.1,
            num_thread=4
        )
        add_log("Warming up the model with test query...")
        llm.invoke("Hello")
        add_log("Model preloaded and warmed up successfully")
        return llm
    except Exception as e:
        add_log(f"Model preload failed: {str(e)}", "ERROR")
        st.error(f"Model preload failed: {str(e)}")
        return None

def format_docs(docs):
    """Format documents for context"""
    return "\n\n".join(doc.page_content for doc in docs)

def display_chat_history():
    """Display chat history in a nice format"""
    if st.session_state.chat_history:
        st.subheader("Chat History")
        
        for i, chat in enumerate(reversed(st.session_state.chat_history)):
            with st.expander(f"Q: {chat['question'][:50]}... ({chat['timestamp']})", expanded=(i==0)):
                st.markdown(f"**Response:** {chat['answer'][:80]}")
                st.markdown(f"_Document:_ {chat['document']}")

def display_process_logs():
    """Display process logs in a dropdown"""
    if st.session_state.process_logs:
        with st.expander("Process Logs", expanded=False):
            if st.button("Clear Logs"):
                clear_logs()
                st.rerun()
            
            log_text = "\n".join(st.session_state.process_logs)
            st.code(log_text, language="text")

def process_query_with_document(user_input, uploaded_file):
    """Process both document and query together"""
    # Check if we need to process this document (avoid reprocessing same file)
    file_hash = get_file_hash(uploaded_file.getbuffer())
    current_doc_hash = st.session_state.get('current_doc_hash', None)
    
    # Only process document if it's new or changed
    if file_hash != current_doc_hash:
        clear_logs()
        add_log(f"Processing new document: {uploaded_file.name}")
        
        with st.spinner("Processing document and generating response..."):
            try:
                overall_start = time.time()
                
                # Save uploaded file
                file_path, unique_filename = save_uploaded_file(uploaded_file)
                
                if not file_path:
                    st.error("Failed to save uploaded file")
                    return
                
                st.session_state.current_document = {
                    'name': uploaded_file.name,
                    'path': file_path,
                    'unique_name': unique_filename
                }
                st.session_state.current_doc_hash = file_hash
                
                # Create vector database from document
                vector_db = create_vector_db_from_document(file_path)
                
                if not vector_db:
                    st.error("Failed to process the document")
                    return
                
                st.session_state.vector_db = vector_db
                st.session_state.document_processed = True
                
                # Continue with query processing...
                process_query(user_input, overall_start)
                
            except Exception as e:
                error_msg = f"An error occurred: {str(e)}"
                add_log(error_msg, "ERROR")
                st.error(error_msg)
                logging.error(f"Error details: {e}")
    else:
        # Document already processed, just handle the query
        if st.session_state.vector_db:
            process_query(user_input, time.time())

def process_query(user_input, overall_start):
    """Process query with existing vector database"""
    try:
        # Load model
        add_log("Retrieving preloaded model...")
        llm = preload_model()
        
        if llm is None:
            st.error("Failed to load the language model")
            return

        # Create retriever and get relevant documents
        add_log("Setting up document retriever...")
        retriever = create_fast_retriever(st.session_state.vector_db)

        add_log("Searching for relevant document chunks...")
        relevant_docs = retriever.get_relevant_documents(user_input)
        add_log(f"Found {len(relevant_docs)} relevant document chunks")
        context = format_docs(relevant_docs)
        
        # Create chain and generate response
        add_log("Creating processing chain...")
        rag_chain = create_chain(llm)

        add_log("Generating response...")
        response_start = time.time()
        response = rag_chain.invoke({"context": context, "question": user_input})
        response_end = time.time()
        overall_end = time.time()

        response_time = response_end - response_start
        total_time = overall_end - overall_start

        add_log(f"Response generated successfully in {response_time:.2f}s")
        add_log(f"Total process time: {total_time:.2f}s")

        # Display metrics
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown(f"**Response Time:** `{response_time:.2f}s`")
        with col_b:
            st.markdown(f"**Total Time:** `{total_time:.2f}s`")
        with col_c:
            st.markdown(f"**Docs Found:** `{len(relevant_docs)}`")

        # Store last response; main area renders full conversation now
        st.session_state.last_response = response

        # Show process logs expander right after output and before retrieved context
        display_process_logs()

        # Show retrieved context with better formatting
        with st.expander("Retrieved Context", expanded=False):
            for i, doc in enumerate(relevant_docs):
                st.markdown(f"**Chunk {i+1}:**")
                
                # Clean and format the content better
                content = doc.page_content.strip()
                
                # Filter out obvious page numbers, table of contents, or meaningless content
                lines = content.split('\n')
                cleaned_lines = []
                
                for line in lines:
                    line = line.strip()
                    # Skip lines that are just numbers, single characters, or very short
                    if len(line) > 10 and not line.isdigit() and not (len(line) < 5 and line.replace(' ', '').isdigit()):
                        cleaned_lines.append(line)
                
                cleaned_content = '\n'.join(cleaned_lines)
                
                # Show more content but limit for readability
                if len(cleaned_content) > 800:
                    display_content = cleaned_content[:800] + "..."
                else:
                    display_content = cleaned_content
                
                # Display in a more readable format
                if display_content.strip():
                    st.text_area(
                        f"Content from Chunk {i+1}:",
                        display_content,
                        height=150,
                        key=f"chunk_{i}",
                        disabled=True
                    )
                else:
                    st.warning(f"Chunk {i+1} contains mostly formatting data (page numbers, table of contents, etc.)")
                
                st.markdown("---")
        
        # Add to chat history
        add_to_chat_history(
            user_input, 
            response, 
            response_time, 
            st.session_state.current_document['name'] if st.session_state.current_document else "Unknown"
        )
        
    except Exception as e:
        error_msg = f"An error occurred during query processing: {str(e)}"
        add_log(error_msg, "ERROR")
        st.error(error_msg)
        logging.error(f"Error details: {e}")
