"""
Interactive Chatbot Interface for GraphRAG System
Run this script for a command-line chatbot experience
"""

from graphrag_mistral import GraphRAGSystem
import os

def main():
    print("=" * 60)
    print("GraphRAG Chatbot with Mistral API")
    print("=" * 60)
    
    # Get API key
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        api_key = input("Enter your Mistral API key: ").strip()
        if not api_key:
            print("Error: API key is required!")
            return
    
    # Initialize system
    print("\nInitializing GraphRAG system...")
    rag_system = GraphRAGSystem(mistral_api_key=api_key)
    
    # Get file path
    print("\n" + "-" * 60)
    file_path = input("Enter the path to your text file: ").strip()
    
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found!")
        return
    
    # Load file
    print(f"\nLoading and processing '{file_path}'...")
    try:
        rag_system.load_text_file(file_path)
        print("✓ File loaded successfully!")
    except Exception as e:
        print(f"Error loading file: {e}")
        return
    
    # Show stats
    stats = rag_system.get_graph_stats()
    print("\n" + "-" * 60)
    print("Knowledge Graph Statistics:")
    print(f"  • Documents/Chunks: {stats['documents']}")
    print(f"  • Entities (Nodes): {stats['nodes']}")
    print(f"  • Relationships (Edges): {stats['edges']}")
    print("-" * 60)
    
    # Chat loop
    print("\n🤖 Chatbot ready! Type your questions (or 'quit' to exit)")
    print("=" * 60)
    
    while True:
        question = input("\n💬 You: ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break
        
        if not question:
            continue
        
        print("\n🤔 Thinking...")
        try:
            answer = rag_system.ask_question(question, use_graph=True)
            print(f"\n🤖 Assistant: {answer}")
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()

