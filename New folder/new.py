#
# Flask-Based Knowledge Graph Generator
#

import networkx as nx
import os
import json
from mistralai import Mistral
from getpass import getpass
from dotenv import load_dotenv
from flask import Flask, render_template, request, send_file
import matplotlib.pyplot as plt
import io
import base64

# Load API key from .env file
load_dotenv()
api_key = os.getenv("MISTRAL_API_KEY")

app = Flask(__name__)

def extract_triples_with_mistral(text, api_key):
    """
    Uses the Mistral AI API to extract subject-predicate-object triples from text.
    """
    try:
        client = Mistral(api_key=api_key)
    except Exception as e:
        print(f"Error configuring the Mistral client: {e}")
        return []

    system_prompt = """
    You are an expert knowledge extraction system designed to build precise knowledge graphs from text.
    
    Your task is to identify entities and relationships in the provided text and format them as a valid JSON object.
    The JSON object must have a single key "triples" which contains a list of JSON objects.
    Each inner object should represent a (subject, predicate, object) triple with the keys "subj", "pred", and "obj".
    
    GUIDELINES:
    1. Extract only factual, explicit relationships from the text
    2. Subjects and objects should be specific named entities (people, organizations, concepts, etc.)
    3. Predicates should be concise, descriptive relationship verbs
    4. Normalize entities (use consistent names for the same entity)
    5. Avoid overly generic relationships
    6. Focus on relationships that would be valuable in a knowledge graph
    7. If an entity is a pronoun, replace it with its referent if clear from context
    8. Return ONLY the JSON object and nothing else
    
    Example output format:
    {
      "triples": [
        {"subj": "Apple Inc.", "pred": "founded by", "obj": "Steve Jobs"},
        {"subj": "Steve Jobs", "pred": "born in", "obj": "San Francisco"}
      ]
    }
    """

    user_prompt = f"Extract knowledge graph triples from the following text:\n\n{text}"

    try:
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        content = response.choices[0].message.content
        data = json.loads(str(content))
        return data.get("triples", [])

    except json.JSONDecodeError:
        print("Error: The LLM did not return valid JSON. Please try again.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred during the API call: {e}")
        return []


def create_knowledge_graph(triples):
    """
    Creates a knowledge graph visualization and returns it as a base64 encoded image.
    """
    if not triples:
        return None

    G = nx.DiGraph()

    for t in triples:
        if not all(k in t for k in ['subj', 'pred', 'obj']):
            continue
        subj, pred, obj = str(t['subj']), str(t['pred']), str(t['obj'])
        G.add_node(subj)
        G.add_node(obj)
        G.add_edge(subj, obj, label=pred)

    # Create figure
    plt.figure(figsize=(14, 10))
    
    # Use spring layout
    pos = nx.spring_layout(G, k=1, iterations=50)
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_size=2000, node_color='lightblue', 
                          alpha=0.9, linewidths=2, edgecolors='darkblue')
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, edge_color='gray', 
                          arrows=True, arrowsize=20, width=2)
    
    # Draw labels
    nx.draw_networkx_labels(G, pos, font_size=10, font_family='sans-serif')
    
    # Draw edge labels
    edge_labels = {(u, v): d['label'] for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
    
    plt.title("Knowledge Graph", fontsize=16)
    plt.axis('off')
    plt.tight_layout()
    
    # Save the graph to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    
    # Encode the image to base64
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close()
    
    return image_base64


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Check if text was submitted
        text = request.form.get('text', '')
        api_key_input = request.form.get('api_key', '')
        
        # Use provided API key or the one from environment
        use_api_key = api_key_input if api_key_input else api_key
        
        if not use_api_key:
            return render_template('index.html', 
                                 error="Please provide a Mistral AI API key")
        
        if not text:
            return render_template('index.html', 
                                 error="Please provide some text to analyze")
        
        # Extract triples
        triples = extract_triples_with_mistral(text, use_api_key)
        
        if not triples:
            return render_template('index.html', 
                                 error="No relationships found in the text")
        
        # Create knowledge graph visualization
        graph_image = create_knowledge_graph(triples)
        
        return render_template('index.html', 
                             triples=triples,
                             graph_image=graph_image,
                             text=text,
                             api_key=use_api_key)
    
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return render_template('index.html', error="No file uploaded")
    
    file = request.files['file']
    api_key_input = request.form.get('api_key', '')
    
    # Use provided API key or the one from environment
    use_api_key = api_key_input if api_key_input else api_key
    
    if not use_api_key:
        return render_template('index.html', 
                             error="Please provide a Mistral AI API key")
    
    if file.filename == '':
        return render_template('index.html', error="No file selected")
    
    if file and file.filename and file.filename.endswith('.txt'):
        text = file.read().decode('utf-8')
        
        # Extract triples
        triples = extract_triples_with_mistral(text, use_api_key)
        
        if not triples:
            return render_template('index.html', 
                                 error="No relationships found in the text")
        
        # Create knowledge graph visualization
        graph_image = create_knowledge_graph(triples)
        
        return render_template('index.html', 
                             triples=triples,
                             graph_image=graph_image,
                             text=text,
                             api_key=use_api_key)
    
    return render_template('index.html', error="Invalid file format. Please upload a .txt file")


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Create the HTML template
    template_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Knowledge Graph Generator</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1 {
            text-align: center;
            color: #333;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"], textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        textarea {
            height: 150px;
            resize: vertical;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
        .error {
            color: red;
            padding: 10px;
            background-color: #ffe6e6;
            border-radius: 4px;
            margin-bottom: 15px;
        }
        .success {
            color: green;
            padding: 10px;
            background-color: #e6ffe6;
            border-radius: 4px;
            margin-bottom: 15px;
        }
        .results {
            margin-top: 20px;
        }
        .graph-container {
            text-align: center;
            margin: 20px 0;
        }
        .graph-image {
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .triples-list {
            margin-top: 20px;
        }
        .triple-item {
            padding: 10px;
            border-bottom: 1px solid #eee;
        }
        .tabs {
            display: flex;
            margin-bottom: 15px;
        }
        .tab {
            padding: 10px 15px;
            background-color: #f1f1f1;
            border: 1px solid #ddd;
            cursor: pointer;
        }
        .tab.active {
            background-color: #fff;
            border-bottom: none;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Knowledge Graph Generator</h1>
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        
        <div class="tabs">
            <div class="tab active" onclick="switchTab('text-tab')">Enter Text</div>
            <div class="tab" onclick="switchTab('file-tab')">Upload File</div>
        </div>
        
        <form method="POST" action="/" id="text-tab" class="tab-content active">
            <div class="form-group">
                <label for="api_key">Mistral AI API Key:</label>
                <input type="text" id="api_key" name="api_key" value="{{ api_key if api_key else '' }}" placeholder="Enter your Mistral AI API key">
            </div>
            
            <div class="form-group">
                <label for="text">Text to Analyze:</label>
                <textarea id="text" name="text" placeholder="Paste your text here...">{{ text if text else '' }}</textarea>
            </div>
            
            <button type="submit">Generate Knowledge Graph</button>
        </form>
        
        <form method="POST" action="/upload" enctype="multipart/form-data" id="file-tab" class="tab-content">
            <div class="form-group">
                <label for="api_key_file">Mistral AI API Key:</label>
                <input type="text" id="api_key_file" name="api_key" value="{{ api_key if api_key else '' }}" placeholder="Enter your Mistral AI API key">
            </div>
            
            <div class="form-group">
                <label for="file">Upload Text File (.txt):</label>
                <input type="file" id="file" name="file" accept=".txt">
            </div>
            
            <button type="submit">Generate Knowledge Graph</button>
        </form>
        
        {% if triples %}
        <div class="results">
            <h2>Results</h2>
            <p>Found {{ triples|length }} relationships:</p>
            
            <div class="graph-container">
                <img src="data:image/png;base64,{{ graph_image }}" alt="Knowledge Graph" class="graph-image">
            </div>
            
            <div class="triples-list">
                <h3>Extracted Relationships:</h3>
                {% for triple in triples %}
                <div class="triple-item">
                    <strong>{{ triple.subj }}</strong> &rarr; {{ triple.pred }} &rarr; <strong>{{ triple.obj }}</strong>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
    </div>
    
    <script>
        function switchTab(tabId) {
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab content
            document.getElementById(tabId).classList.add('active');
            
            // Update tab styles
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            event.currentTarget.classList.add('active');
        }
    </script>
</body>
</html>"""
    
    # Write the template to file with UTF-8 encoding
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(template_html)
    
    print("Starting Flask server...")
    print("Open your browser and go to http://localhost:5000")
    app.run(debug=True)