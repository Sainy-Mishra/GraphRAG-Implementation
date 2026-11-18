"""
Interactive Chatbot Interface for GraphRAG System
Run this script for a command-line chatbot experience.
Uses a free LLM API (Groq by default). Get a free key at https://console.groq.com/keys
"""

from graphrag_mistral import GraphRAGSystem
import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # lets you keep GROQ_API_KEY in a .env file
except ImportError:
    pass


def main():
    print("=" * 60)
    print("GraphRAG Chatbot (free Groq LLM)")
    print("=" * 60)

    # Get API key
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        api_key = input("Enter your Groq API key (starts with gsk_): ").strip()
        if not api_key:
            print("Error: API key is required!")
            return

    # Initialize system
    print("\nInitializing GraphRAG system...")
    rag_system = GraphRAGSystem(api_key=api_key)

    # Get file path
    print("\n" + "-" * 60)
    file_path = input("Enter the path to your text file: ").strip().strip('"')

    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found!")
        return

    # Load file
    print(f"\nLoading and processing '{file_path}'...")
    try:
        rag_system.load_text_file(file_path)
        print("File loaded successfully!")
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    # Show stats
    stats = rag_system.get_graph_stats()
    print("\n" + "-" * 60)
    print("Knowledge Graph Statistics:")
    print(f"  - Documents/Chunks: {stats['documents']}")
    print(f"  - Entities (Nodes): {stats['nodes']}")
    print(f"  - Relationships (Edges): {stats['edges']}")
    print("-" * 60)

    # Chat loop
    print("\nChatbot ready! Type your questions (or 'quit' to exit)")
    print("=" * 60)

    while True:
        question = input("\nYou: ").strip()

        if question.lower() in ['quit', 'exit', 'q']:
            print("\nGoodbye!")
            break

        if not question:
            continue

        print("\nThinking...")
        try:
            answer = rag_system.ask_question(question, use_graph=True)
            print(f"\nAssistant: {answer}")
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()