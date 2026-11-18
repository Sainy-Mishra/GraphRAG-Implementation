# app.py  -  Knowledge Graph Generator (Flask + D3)
# Engines: spaCy (local), Basic (local), LLM (free Groq API by default)
import os
import json
import re
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
from openai import OpenAI
import networkx as nx
import spacy

# Load the spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Spacy model not found. Please run 'python -m spacy download en_core_web_sm'")
    nlp = None

load_dotenv()
API_KEY_ENV = os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY") or ""
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

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
        if token.pos_ == "VERB":
            subj = None
            obj = None
            for child in token.children:
                if "subj" in child.dep_:
                    subj = child.text
                if "obj" in child.dep_:
                    obj = child.text

            if subj and obj:
                triples.append({
                    "subj": subj.strip().title(),
                    "pred": token.lemma_,
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
    return [triple for s in sentences if s.strip() and (triple := simple_nlp_extractor(s))]


def _call_llm(client, messages):
    """Call the LLM, asking for JSON. Falls back if JSON mode or the model name is not accepted."""
    model = LLM_MODEL
    use_json = True
    last_error = None
    for _ in range(3):
        try:
            kwargs = dict(model=model, messages=messages, temperature=0.1)
            if use_json:
                kwargs["response_format"] = {"type": "json_object"}
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            last_error = e
            msg = str(e).lower()
            if "model" in msg and any(s in msg for s in ("not found", "decommission", "does not exist", "no longer supported")):
                skip = ("whisper", "guard", "tts", "embed", "playai", "orpheus")
                options = [m.id for m in client.models.list().data
                           if m.id != model and not any(s in m.id.lower() for s in skip)]
                if not options:
                    raise
                model = options[0]
                print(f"Model unavailable; switching to '{model}'")
            elif use_json:
                use_json = False  # retry without JSON mode
            else:
                raise
    raise last_error


def extract_triples_with_llm(text, api_key):
    """Uses a free LLM API (Groq by default) to extract triples. Returns (triples, error_message)."""
    if not api_key:
        return [], "No API key found. Paste your Groq key in the box or put GROQ_API_KEY in the .env file."
    try:
        client = OpenAI(api_key=api_key, base_url=LLM_BASE_URL)
        system_prompt = (
            "You are an expert knowledge extraction system. Extract precise subject-predicate-object triples. "
            "Return ONLY a JSON object with a single key 'triples' which maps to a list of objects, "
            "each with 'subj', 'pred', and 'obj' keys."
        )
        user_prompt = f"Extract triples from the following text and answer in JSON:\n\n{text[:12000]}"
        content = _call_llm(client, [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        match = re.search(r'\{.*\}', content, re.DOTALL)
        data = json.loads(match.group() if match else content)
        return data.get("triples", []), None
    except Exception as e:
        print("Error calling LLM:", e)
        return [], f"LLM request failed: {e}"


# --- Graph Conversion & Routes ---

def triples_to_graph_json(triples):
    """Converts a list of triples to a D3.js-compatible graph JSON."""
    nodes_map = {}
    links = []
    for t in triples:
        subj, pred, obj = str(t.get("subj")).strip(), str(t.get("pred")).strip(), str(t.get("obj")).strip()
        if not all((subj, pred, obj)):
            continue
        for name in (subj, obj):
            if name not in nodes_map:
                nodes_map[name] = {"id": name, "label": name, "size": 20}
        links.append({"source": subj, "target": obj, "label": pred})
    if not nodes_map:
        return {"nodes": [], "links": []}
    G = nx.DiGraph([(l["source"], l["target"]) for l in links])
    degrees = dict(G.degree())
    for n, deg in degrees.items():
        nodes_map[n]["size"] = 12 + deg * 4
    return {"nodes": list(nodes_map.values()), "links": links}


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        text = request.form.get("text", "").strip()
        engine = request.form.get("engine", "spacy")

        if "file" in request.files and request.files["file"].filename != "":
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
        if engine in ("llm", "mistral"):
            api_key = request.form.get("api_key", "").strip() or API_KEY_ENV
            triples, error = extract_triples_with_llm(text, api_key)
            if error:
                flash(error, "error")
                return redirect(url_for("index"))
        elif engine == "spacy":
            triples = extract_triples_spacy(text)
        else:
            triples = extract_triples_basic(text)

        if not triples:
            flash("No relationships could be extracted with the selected engine.", "error")
            return redirect(url_for("index"))

        graph = triples_to_graph_json(triples)
        return render_template("graph.html", graph_json=json.dumps(graph))

    return render_template("index.html", api_key=API_KEY_ENV)


if __name__ == "__main__":
    app.run(debug=True, port=5000)