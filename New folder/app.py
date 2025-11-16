# # app.py
# import os
# import json
# import io
# from flask import Flask, render_template, request, redirect, url_for, send_file, flash, jsonify
# from dotenv import load_dotenv
# from mistralai import Mistral
# import networkx as nx

# load_dotenv()
# API_KEY_ENV = os.getenv("MISTRAL_API_KEY", "")

# app = Flask(__name__)
# app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")  # change for production


# def extract_triples_with_mistral(text, api_key):
#     """
#     Reuses your Mistral client logic to extract triples.
#     The function returns a list of dicts, each having 'subj','pred','obj'.
#     If you don't have a Mistral key available you can return a sample list
#     for testing.
#     """
#     if not api_key:
#         # If no key provided, return a fallback sample for quick local testing
#         return [
#             {"subj": "Alan Turing", "pred": "proposed", "obj": "Turing Test"},
#             {"subj": "Turing Test", "pred": "published in", "obj": "Computing Machinery and Intelligence"},
#             {"subj": "IBM", "pred": "created", "obj": "Watson"},
#             {"subj": "Watson", "pred": "defeated", "obj": "Ken Jennings"},
#             {"subj": "Geoffrey Hinton", "pred": "is a", "obj": "AI researcher"},
#             {"subj": "AI researcher", "pred": "works on", "obj": "deep learning"},
#         ]

#     try:
#         client = Mistral(api_key=api_key)
#     except Exception as e:
#         print("Mistral client init error:", e)
#         return []

#     system_prompt = """
# You are an expert knowledge extraction system designed to build precise knowledge graphs from text.
# Return a JSON object with a single key "triples" which maps to a list of { "subj":"", "pred":"", "obj":"" } objects.
# Return ONLY the JSON object.
#     """

#     user_prompt = f"Extract triples from the following text:\n\n{text}"

#     try:
#         response = client.chat.complete(
#             model="mistral-large-latest",
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": user_prompt}
#             ],
#             response_format={"type": "json_object"},
#             temperature=0.1,
#         )
#         content = response.choices[0].message.content
#         data = json.loads(str(content))
#         return data.get("triples", [])
#     except Exception as e:
#         print("Error calling Mistral:", e)
#         return []


# def triples_to_graph_json(triples):
#     """
#     Convert triples into a nodes/links JSON structure suitable for D3 force graph.
#     Nodes are unique by name; links include a 'label' property for predicate.
#     """
#     nodes_map = {}
#     links = []
#     for t in triples:
#         if not all(k in t for k in ("subj", "pred", "obj")):
#             continue
#         subj = str(t["subj"]).strip()
#         obj = str(t["obj"]).strip()
#         pred = str(t["pred"]).strip()
#         if subj == "" or obj == "":
#             continue
#         # Add nodes if not exists
#         for name in (subj, obj):
#             if name not in nodes_map:
#                 nodes_map[name] = {
#                     "id": name,
#                     "label": name,
#                     # a simple initial radius; will be scaled in front-end
#                     "size": 20
#                 }
#         links.append({"source": subj, "target": obj, "label": pred})

#     # adjust node sizes by degree (optional)
#     G = nx.DiGraph()
#     for n in nodes_map:
#         G.add_node(n)
#     for l in links:
#         G.add_edge(l["source"], l["target"])
#     degrees = dict(G.degree())
#     for n, deg in degrees.items():
#         # scale size: base 12 + degree*6
#         nodes_map[n]["size"] = 12 + deg * 6

#     graph = {"nodes": list(nodes_map.values()), "links": links}
#     return graph


# @app.route("/", methods=["GET", "POST"])
# def index():
#     if request.method == "POST":
#         text = request.form.get("text", "").strip()
#         api_key = request.form.get("api_key", "").strip()
#         use_key = api_key if api_key else API_KEY_ENV

#         if "file" in request.files and request.files["file"].filename != "":
#             uploaded = request.files["file"]
#             if uploaded.filename and uploaded.filename.endswith(".txt"):
#                 text = uploaded.read().decode("utf-8")
#             else:
#                 flash("Invalid file format. Please upload a .txt file.", "error")
#                 return redirect(url_for("index"))

#         if not text:
#             flash("Please provide text or upload a .txt file.", "error")
#             return redirect(url_for("index"))

#         triples = extract_triples_with_mistral(text, use_key)
#         if not triples:
#             flash("No relationships found or extraction failed.", "error")
#             return redirect(url_for("index"))

#         graph = triples_to_graph_json(triples)
#         # store graph JSON in session-like temporary file (or in-memory)
#         # to keep things simple: we render graph page passing graph json via template
#         return render_template("graph.html", graph_json=json.dumps(graph), text=text)

#     return render_template("index.html", api_key=API_KEY_ENV)


# @app.route("/api/graph", methods=["POST"])
# def api_graph():
#     """
#     Optional API endpoint that accepts JSON with triples and returns nodes/links JSON.
#     Useful if you want to build a JS-only front-end in future.
#     """
#     payload = request.get_json(force=True)
#     triples = payload.get("triples", [])
#     graph = triples_to_graph_json(triples)
#     return jsonify(graph)


# if __name__ == "__main__":
#     app.run(debug=True, port=5000)





# app.py
import os
import json
import re
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
from mistralai import Mistral
import networkx as nx
import spacy # <-- Import spaCy

# Load the spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Spacy model not found. Please run 'python -m spacy download en_core_web_sm'")
    nlp = None

load_dotenv()
API_KEY_ENV = os.getenv("MISTRAL_API_KEY", "")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

# --- Extractor Functions ---

def extract_triples_spacy(text):
    """Extracts triples using spaCy's dependency parsing."""
    if not nlp:
        return []
    
    triples = []
    doc = nlp(text)

    for token in doc:
        # Look for a verb
        if token.pos_ == "VERB":
            subj = None
            obj = None
            # Find subject and object connected to this verb
            for child in token.children:
                if "subj" in child.dep_:
                    subj = child.text
                if "obj" in child.dep_:
                    obj = child.text
            
            if subj and obj:
                # Capitalize for consistency
                triples.append({
                    "subj": subj.strip().title(),
                    "pred": token.lemma_, # Use the base form of the verb
                    "obj": obj.strip().title()
                })
    return triples


def simple_nlp_extractor(sentence):
    """A basic NLP function to find subject, predicate, object triples."""
    common_verbs = [
        'is', 'are', 'was', 'were', 'has', 'have', 'had', 'likes', 'owns',
        'belongs to', 'jumps over', 'sat on', 'lives in', 'chase', 'made of',
        'love', 'eat', 'drink', 'wear', 'see', 'proposed', 'created', 'defeated',
        'published in', 'works on'
    ]
    sentence = re.sub(r'[.,!?]', '', sentence).lower()
    for verb in common_verbs:
        pattern = r'\b' + re.escape(verb) + r'\b'
        parts = re.split(pattern, sentence, maxsplit=1)
        if len(parts) == 2:
            subj, obj = parts[0].strip(), parts[1].strip()
            if subj and obj:
                clean_subj = re.sub(r'^(the|a|an)\s+', '', subj).strip()
                clean_obj = re.sub(r'^(the|a|an)\s+', '', obj).strip()
                return {'subj': clean_subj.title(), 'pred': verb, 'obj': clean_obj.title()}
    return None

def extract_triples_basic(text):
    """Extracts triples using the basic NLP sentence-by-sentence method."""
    sentences = re.split(r'[.!?]+', text)
    triples = [triple for s in sentences if s.strip() and (triple := simple_nlp_extractor(s))]
    return triples

def extract_triples_with_mistral(text, api_key):
    """Uses Mistral AI to extract triples for higher accuracy."""
    if not api_key:
        return [
            {"subj": "Alan Turing", "pred": "proposed", "obj": "Turing Test"},
            {"subj": "Turing Test", "pred": "published in", "obj": "Computing Machinery and Intelligence"},
        ]
    try:
        client = Mistral(api_key=api_key)
        system_prompt = "You are an expert knowledge extraction system. Extract precise subject-predicate-object triples. Return ONLY a JSON object with a single key 'triples' which maps to a list of objects, each with 'subj', 'pred', and 'obj' keys."
        user_prompt = f"Extract triples from the following text:\n\n{text}"
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        return json.loads(str(response.choices[0].message.content)).get("triples", [])
    except Exception as e:
        print("Error calling Mistral:", e)
        return []

# --- Graph Conversion & Routes ---

def triples_to_graph_json(triples):
    """Converts a list of triples to a D3.js-compatible graph JSON."""
    nodes_map = {}
    links = []
    for t in triples:
        subj, pred, obj = str(t.get("subj")).strip(), str(t.get("pred")).strip(), str(t.get("obj")).strip()
        if not all((subj, pred, obj)): continue
        for name in (subj, obj):
            if name not in nodes_map: nodes_map[name] = {"id": name, "label": name, "size": 20}
        links.append({"source": subj, "target": obj, "label": pred})
    if not nodes_map: return {"nodes": [], "links": []}
    G = nx.DiGraph([(l["source"], l["target"]) for l in links])
    degrees = dict(G.degree())
    for n, deg in degrees.items(): nodes_map[n]["size"] = 12 + deg * 4
    return {"nodes": list(nodes_map.values()), "links": links}

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        text = request.form.get("text", "").strip()
        engine = request.form.get("engine", "spacy")
        
        # File handling
        if "file" in request.files and request.files["file"].filename != "":
            # File handling logic placeholder
            uploaded = request.files["file"]
            if uploaded.filename and uploaded.filename.endswith(".txt"):
                text = uploaded.read().decode("utf-8")
            else:
                flash("Invalid file format. Please upload a .txt file.", "error")
                return redirect(url_for("index"))
        
        if not text:
            flash("Please provide text or upload a file.", "error")
            return redirect(url_for("index"))

        triples = []
        if engine == 'mistral':
            api_key = request.form.get("api_key", "").strip()
            use_key = api_key if api_key else API_KEY_ENV
            triples = extract_triples_with_mistral(text, use_key)
        elif engine == 'spacy':
            triples = extract_triples_spacy(text)
        else: # 'basic' engine
            triples = extract_triples_basic(text)

        if not triples:
            flash("No relationships could be extracted with the selected engine.", "error")
            return redirect(url_for("index"))

        graph = triples_to_graph_json(triples)
        return render_template("graph.html", graph_json=json.dumps(graph))

    return render_template("index.html", api_key=API_KEY_ENV)

if __name__ == "__main__":
    app.run(debug=True, port=5000)