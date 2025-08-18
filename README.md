## RAG App with Ollama (Streamlit)

![App Screenshot](https://iili.io/FpFiAns.md.png)

Build a fast, local-first Retrieval-Augmented Generation (RAG) assistant over your own documents using Streamlit, LangChain, ChromaDB, and Ollama. Upload PDFs, CSVs, JSON, or TXT files and ask natural questions; the app retrieves the most relevant chunks and answers using a local LLM.

### Key Features
- **Local-first**: Runs entirely on your machine with Ollama models
- **Multi-format ingestion**: PDF, CSV, JSON, TXT
- **Fast retrieval**: ChromaDB vector store with tuned chunking and similarity search
- **Interactive UI**: Streamlit chat interface with history and session switching
- **Persistence**: Chat history in SQLite, vectors in Chroma, uploaded docs stored on disk
- **Observability**: Inline timings, doc count, and a detailed process log expander

### Tech Stack
- Streamlit UI
- Ollama for LLM and embeddings
- LangChain (chains, retrievers, loaders)
- ChromaDB vector store
- SQLite for chat session persistence

---

## Quickstart

### 1) Requirements
- Python 3.10+
- Ollama installed and running (ensure the background service/daemon is active)

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
ollama pull codegemma:latest
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

### Architecture
```mermaid
flowchart LR
  U[User] -->|asks| S[Streamlit UI]
  S -->|uploads| L[Loaders: PDF/CSV/JSON/TXT]
  L --> SPLIT[Chunking]
  SPLIT --> EMB[Embeddings (Ollama nomic-embed-text)]
  EMB --> V[ChromaDB]
  S -->|retrieves top-k| V
  V -->|context| RAG[Prompt + Chain]
  RAG --> LLM[Chat Model (Ollama codegemma)]
  LLM -->|answer| S
```

---

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

## Configuration & Customization

### Models
Change defaults in `rag_functions.py`:
```21:25:rag_functions.py
# Constants for AI Models and Chroma DB
MODEL_NAME = "codegemma:latest" 
EMBEDDING_MODEL = "nomic-embed-text"
PERSIST_DIRECTORY = "./chroma_db"
```

- To use a different chat model (e.g., `llama3:8b`), set `MODEL_NAME` accordingly and run `ollama pull llama3:8b`.
- To use a different embedding model, update `EMBEDDING_MODEL` and pull it via `ollama` as well.

### Chunking and Retrieval
Adjust chunking in `split_documents` and retrieval depth in `create_fast_retriever` inside `rag_functions.py`:
- `chunk_size` (default 1800) and `chunk_overlap` (default 400)
- `k` in similarity search (default 5)

### GPU/CPU
The app initializes Ollama integrations with `num_gpu=1` by default. On CPU-only machines, set it to `0` in `rag_functions.py` for both `OllamaEmbeddings` and `ChatOllama`.

### Data Locations
- Uploaded files: `processed_docs/`
- Vector store: `chroma_db/`
- Chat history: `chat_data.sqlite3`

---

## Using the App
1. Start Ollama (ensure the service is running).
2. Pull models (once): `ollama pull codegemma:latest` and `ollama pull nomic-embed-text`.
3. `streamlit run streamlit_app.py`
4. Upload a document in the UI.
5. Ask questions. You can start new chats, switch between sessions, and delete sessions via the sidebar.

### Supported Formats
- PDF, CSV, JSON, TXT

---

## Troubleshooting
- "Model preload failed" or connection errors: ensure Ollama is installed, running, and the models are pulled.
- Document load issues (especially PDFs): some environments require additional system packages for `unstructured` loaders. Try upgrading `unstructured` or installing related OS dependencies.
- Slow first response: the first call warms up the model; subsequent calls are faster.
- CPU-only systems: set `num_gpu=0` in the Ollama integrations if you do not have a compatible GPU.
- Clearing state: delete `chroma_db/`, `chat_data.sqlite3`, or files under `processed_docs/` to reset data.

---

## Security & Privacy
- All processing happens locally if your Ollama server runs on the same machine.
- Uploaded documents are stored in `processed_docs/` and are not uploaded to any external service by this app.

---

## Roadmap Ideas
- Multi-document indexing and corpus management
- Adjustable prompt templates and system instructions in the UI
- Advanced retrieval strategies (MMR, Rerankers)
- Export chat transcripts

---

## Contributing
Contributions are welcome! Please open an issue or PR with a clear description of the change.

---

## License
Add your preferred license here (e.g., MIT, Apache-2.0). If you choose MIT, include a `LICENSE` file at the repo root.

---

## Acknowledgments
- Streamlit, LangChain, ChromaDB, and Ollama communities for great tooling.

---

## References
- App screenshot used in this README: `https://iili.io/FpFiAns.md.png`


