# RAG AI Document Assistant

![App Screenshot](https://iili.io/FpFiAns.md.png)

A fast, local-first Retrieval-Augmented Generation (RAG) assistant over your documents using Streamlit, LangChain, ChromaDB, and Ollama. Upload PDFs, CSVs, JSON, or TXT files and ask any minute questions; the app retrieves the most relevant chunks and answers using a local LLM.

### Key Features
- **Local-first**: Runs entirely on your machine with Ollama models
- **Multi-format ingestion**: PDF, CSV, JSON, TXT
- **Fast retrieval**: ChromaDB vector store with tuned chunking and similarity search
- **Interactive UI**: Streamlit chat interface with history and session switching
- **Persistence**: Chat history in SQLite, vectors in Chroma, uploaded docs stored on disk
- **Observability**: Inline timings, doc count, and a detailed process log expander

### Tech Stack
- Streamlit
- Ollama for LLM and embeddings
- LangChain (chains, retrievers, loaders)
- ChromaDB vector store
- SQLite for chat session persistence

---

## Quickstart

### 1) Requirements
> Ollama installed and running (ensure the background service/daemon is active)

### 2) Clone and install
```bash
git clone <this-repo-url>
cd RAG-app-with-ollama
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3) Pull required models in Ollama
```bash
ollama pull codegemma:latest # you can use any
ollama pull nomic-embed-text
```

If you prefer different models, see Customization below.

### 4) Run the app
```bash
streamlit run streamlit_app.py
```

Open the provided local URL in your browser, upload a document, and start chatting.

---

## How It Works
1. You upload a document (PDF/CSV/JSON/TXT). The app saves it under `processed_docs/` and computes a short file hash.
2. The document is loaded via suitable LangChain document loaders.
3. The content is split into tuned chunks (size ≈ 1800, overlap ≈ 400) for better recall.
4. Chunks are embedded with `nomic-embed-text` and stored in a ChromaDB collection.
5. Your question is used to retrieve the top-k similar chunks (k=5) from Chroma.
6. A prompt with the retrieved context is sent to the chat model (`codegemma:latest` by default) to generate the answer.
7. The UI shows timing metrics, retrieved context (under an expander), and maintains chat history per session.


## Project Structure
```text
RAG-app-with-ollama/
├─ streamlit_app.py           # Streamlit UI and sidebar chat management
├─ rag_functions.py           # RAG pipeline: load, split, embed, retrieve, chain
├─ helpers_func.py            # Uploads, logging, SQLite sessions/messages
├─ requirements.txt           # Python dependencies
├─ chat_data.sqlite3          # SQLite DB (created at runtime)
├─ processed_docs/            # Uploaded documents (saved here)
└─ chroma_db/                 # ChromaDB artifacts (created at runtime)
```

---

## Contributing
Contributions are welcome! Please open an issue or PR with a clear description of the change.

---

> Developed by Adya Prasad
