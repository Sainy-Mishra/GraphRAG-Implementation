"""
GraphRAG System using Mistral API
Handles text file upload, knowledge graph construction, and Q&A chatbot
"""

import os
import re
import json
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import networkx as nx
from mistralai import Mistral
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import spacy
from sentence_transformers import SentenceTransformer

class GraphRAGSystem:
    def __init__(self, mistral_api_key: str, model: str = "mistral-large-latest"):
        """
        Initialize the GraphRAG System
        
        Args:
            mistral_api_key: Your Mistral API key
            model: Mistral model to use (default: mistral-large-latest)
        """
        self.mistral_client = Mistral(api_key="wC6qujfIk7MlyJyagePGqu7YdNxmBFHr")
        self.model = model
        
        # Initialize NLP models
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Warning: spaCy model 'en_core_web_sm' not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        # Initialize sentence transformer for embeddings
        print("Loading sentence transformer model...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Knowledge graph
        self.graph = nx.Graph()
        
        # Document storage
        self.documents = []  # List of text chunks
        self.document_embeddings = None  # Embeddings for chunks
        self.entity_to_chunks = defaultdict(list)  # Map entities to document chunks
        
        # Entity information
        self.entities = {}  # entity_name -> entity_info
        self.relationships = []  # List of (entity1, relationship, entity2)
        
    def load_text_file(self, file_path: str, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Load and process a text file
        
        Args:
            file_path: Path to the text file
            chunk_size: Size of each text chunk
            chunk_overlap: Overlap between chunks
        """
        print(f"Loading text file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Split into chunks
        self.documents = self._chunk_text(text, chunk_size, chunk_overlap)
        print(f"Created {len(self.documents)} text chunks")
        
        # Process documents to extract entities and build graph
        self._process_documents()
        
        # Generate embeddings for all chunks
        print("Generating embeddings for document chunks...")
        self.document_embeddings = self.embedder.encode(self.documents, show_progress_bar=True)
        
        print(f"GraphRAG system initialized with {len(self.documents)} chunks")
        print(f"Knowledge graph contains {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
    
    def _chunk_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), chunk_size - chunk_overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks
    
    def _process_documents(self):
        """Process documents to extract entities and relationships"""
        print("Extracting entities and relationships...")
        
        if self.nlp is None:
            # Fallback: simple entity extraction using Mistral
            self._extract_entities_with_mistral()
        else:
            # Use spaCy for entity extraction
            self._extract_entities_with_spacy()
        
        # Build knowledge graph
        self._build_knowledge_graph()
    
    def _extract_entities_with_spacy(self):
        """Extract entities using spaCy"""
        for idx, doc_text in enumerate(self.documents):
            spacy_doc = self.nlp(doc_text)
            
            # Extract named entities
            for ent in spacy_doc.ents:
                entity_name = ent.text.strip()
                entity_type = ent.label_
                
                if len(entity_name) > 1:  # Filter out single characters
                    if entity_name not in self.entities:
                        self.entities[entity_name] = {
                            'type': entity_type,
                            'mentions': []
                        }
                    
                    self.entities[entity_name]['mentions'].append({
                        'chunk_idx': idx,
                        'text': doc_text[:200]  # Store snippet
                    })
                    
                    self.entity_to_chunks[entity_name].append(idx)
            
            # Extract relationships (simplified: co-occurrence in same sentence)
            for sent in spacy_doc.sents:
                sent_entities = [ent.text for ent in sent.ents if len(ent.text) > 1]
                for i, ent1 in enumerate(sent_entities):
                    for ent2 in sent_entities[i+1:]:
                        if ent1 != ent2:
                            self.relationships.append((ent1, 'related_to', ent2))
    
    def _extract_entities_with_mistral(self):
        """Extract entities using Mistral API (fallback when spaCy not available)"""
        print("Using Mistral API for entity extraction...")
        
        # Process in batches to avoid too many API calls
        batch_size = 5
        for i in range(0, len(self.documents), batch_size):
            batch = self.documents[i:i+batch_size]
            batch_text = "\n\n".join([f"Chunk {j}: {chunk}" for j, chunk in enumerate(batch)])
            
            prompt = f"""Extract all important entities (people, places, organizations, concepts) from the following text chunks.
Return a JSON list of entities with their types. Format:
[{{"entity": "EntityName", "type": "PERSON|ORG|LOC|CONCEPT"}}]

Text:
{batch_text[:2000]}

JSON:"""
            
            try:
                response = self.mistral_client.chat.complete(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                result = response.choices[0].message.content.strip()
                # Try to extract JSON from response
                json_match = re.search(r'\[.*\]', result, re.DOTALL)
                if json_match:
                    entities_data = json.loads(json_match.group())
                    for entity_data in entities_data:
                        entity_name = entity_data.get('entity', '').strip()
                        entity_type = entity_data.get('type', 'CONCEPT')
                        if entity_name:
                            if entity_name not in self.entities:
                                self.entities[entity_name] = {
                                    'type': entity_type,
                                    'mentions': []
                                }
                            # Track the batch range for this entity (entity found in chunks i to i+len(batch))
                            for chunk_idx in range(i, min(i + len(batch), len(self.documents))):
                                if chunk_idx not in self.entity_to_chunks[entity_name]:
                                    self.entity_to_chunks[entity_name].append(chunk_idx)
                                    self.entities[entity_name]['mentions'].append({
                                        'chunk_idx': chunk_idx,
                                        'text': self.documents[chunk_idx][:200]
                                    })
            except Exception as e:
                print(f"Error extracting entities from batch {i}: {e}")
                continue
    
    def _build_knowledge_graph(self):
        """Build knowledge graph from entities and relationships"""
        # Add entities as nodes
        for entity_name, entity_info in self.entities.items():
            self.graph.add_node(entity_name, **entity_info)
        
        # Add relationships as edges
        relationship_counts = defaultdict(int)
        for ent1, rel, ent2 in self.relationships:
            if ent1 in self.entities and ent2 in self.entities:
                key = tuple(sorted([ent1, ent2]))
                relationship_counts[key] += 1
                self.graph.add_edge(ent1, ent2, weight=relationship_counts[key])
        
        print(f"Built knowledge graph with {self.graph.number_of_nodes()} entities")
    
    def _retrieve_relevant_chunks(self, query: str, top_k: int = 5) -> List[Tuple[int, float, str]]:
        """Retrieve most relevant document chunks using semantic similarity"""
        query_embedding = self.embedder.encode([query])
        
        # Calculate cosine similarity
        similarities = cosine_similarity(query_embedding, self.document_embeddings)[0]
        
        # Get top-k chunks
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append((idx, float(similarities[idx]), self.documents[idx]))
        
        return results
    
    def _get_graph_context(self, query: str) -> str:
        """Get relevant context from knowledge graph"""
        # Find entities in query
        query_lower = query.lower()
        relevant_entities = []
        
        for entity_name in self.entities.keys():
            if entity_name.lower() in query_lower:
                relevant_entities.append(entity_name)
        
        # Get neighbors of relevant entities
        context_parts = []
        for entity in relevant_entities[:5]:  # Limit to top 5 entities
            if entity in self.graph:
                neighbors = list(self.graph.neighbors(entity))[:5]
                context_parts.append(f"Entity '{entity}' is connected to: {', '.join(neighbors)}")
        
        return "\n".join(context_parts)
    
    def ask_question(self, question: str, use_graph: bool = True) -> str:
        """
        Ask a question and get an answer using GraphRAG
        
        Args:
            question: The question to ask
            use_graph: Whether to use graph context (default: True)
        
        Returns:
            Answer string
        """
        print(f"\nProcessing question: {question}")
        
        # Retrieve relevant document chunks
        relevant_chunks = self._retrieve_relevant_chunks(question, top_k=5)
        
        # Build context from retrieved chunks
        context = "\n\n".join([
            f"[Document Chunk {idx+1} (relevance: {score:.2f})]:\n{chunk[:500]}"
            for idx, score, chunk in relevant_chunks
        ])
        
        # Get graph context if enabled
        graph_context = ""
        if use_graph:
            graph_context = self._get_graph_context(question)
            if graph_context:
                graph_context = f"\n\n[Knowledge Graph Context]:\n{graph_context}"
        
        # Build prompt for Mistral
        system_prompt = """You are a helpful assistant that answers questions based on the provided context from documents and knowledge graph.
Use the context information to provide accurate, detailed answers. If the context doesn't contain enough information, say so."""
        
        user_prompt = f"""Based on the following context, please answer the question.

{context}{graph_context}

Question: {question}

Answer:"""
        
        try:
            response = self.mistral_client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            
            answer = response.choices[0].message.content.strip()
            return answer
        
        except Exception as e:
            return f"Error generating answer: {str(e)}"
    
    def get_graph_stats(self) -> Dict:
        """Get statistics about the knowledge graph"""
        return {
            'nodes': self.graph.number_of_nodes(),
            'edges': self.graph.number_of_edges(),
            'documents': len(self.documents),
            'entities': len(self.entities),
            'relationships': len(self.relationships)
        }
    
    def visualize_graph(self, top_n: int = 20):
        """Visualize the knowledge graph (requires matplotlib and networkx)"""
        try:
            import matplotlib.pyplot as plt
            
            # Get top N most connected nodes
            degree_centrality = nx.degree_centrality(self.graph)
            top_nodes = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:top_n]
            top_node_names = [node for node, _ in top_nodes]
            
            # Create subgraph
            subgraph = self.graph.subgraph(top_node_names)
            
            # Draw graph
            plt.figure(figsize=(12, 8))
            pos = nx.spring_layout(subgraph, k=1, iterations=50)
            nx.draw(subgraph, pos, with_labels=True, node_color='lightblue', 
                   node_size=1000, font_size=8, font_weight='bold', edge_color='gray')
            plt.title(f"Knowledge Graph (Top {top_n} nodes)")
            plt.tight_layout()
            plt.show()
        except ImportError:
            print("matplotlib not available. Install with: pip install matplotlib")
        except Exception as e:
            print(f"Error visualizing graph: {e}")

