# 🚀 GraphRAG-Based Chatbot  
*A Knowledge-Graph Powered Retrieval-Augmented Generation System*

---

## 📖 Overview

This project implements a **GraphRAG (Graph-based Retrieval-Augmented Generation)** chatbot capable of answering complex, multi-hop queries using a combination of:

- **Knowledge Graphs**
- **Semantic Search**
- **LLM-powered response generation (Mistral API)**

By converting unstructured text into structured entity-relationship graphs, the system provides **contextually rich, accurate, and explainable** responses.

---

## 📂 Project Structure

├── graphrag_mistral.py # Core GraphRAG logic <br>
├── interactive_chatbot.py # Command-line chatbot interface <br>
├── documents/ # Folder containing text files <br>
├── README.md # Documentation <br>


---

## ✨ Features

- 🔗 **Knowledge Graph Construction** from raw text  
- 🧠 **Entity & Relationship Extraction** (spaCy + fallback LLM)  
- 🔍 **Semantic Vector Search** using embeddings  
- 🕸️ **Graph-Aware Query Expansion**  
- 🤖 **RAG Answering with Mistral API**  
- 🧵 Handles **multi-hop reasoning**  
- 🔒 Reduces hallucinations with graph grounding  
- 💬 Interactive CLI for testing queries  

---

## 🧱 Architecture

### **1. Text Loader & Chunker**  
Splits documents into overlapping, meaningful chunks.

### **2. Entity & Relationship Extraction**  
- Uses spaCy for NER  
- Falls back to Mistral for better coverage  

### **3. Vector Embedding Generator**  
Generates embeddings for text chunks for semantic search.

### **4. Knowledge Graph Builder**  
Creates a graph of entities → relationships using NetworkX.

### **5. Query Engine**  
- Retrieves relevant chunks  
- Traverses the knowledge graph  
- Prepares final prompt  

### **6. LLM Response Generator**  
Uses Mistral API to generate grounded answers.

---

## 🛠️ Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/Sainy-Mishra/GraphRAG-Implementation.git
cd GraphRAG-Implementation
```

## 💻 Requirements
spacy==3.7.2 <br>
sentence-transformers==2.6.0 <br>
networkx==3.2.1 <br>
mistralai==0.1.8 <br>
numpy==1.26.4 <br>
scikit-learn==1.4.0 <br>
tqdm==4.66.1<br>
python-dotenv==1.0.1 <br>

