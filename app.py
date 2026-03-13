"""
Hospital RAG - Conflict Detection Q&A System
Streamlit UI for querying hospital performance documents with
automated contradiction detection and source provenance.
"""
import os
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Hospital RAG — Conflict Detection",
    page_icon="+",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------
# 3-D Neon Green Floating Plus Sign — runs via st.components.v1.html
# The iframe JS injects a fixed WebGL canvas into the parent Streamlit
# document so it covers the full viewport behind all UI content.
# ------------------------------------------------------------------
_THREEJS_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"/></head>
<body style="margin:0;padding:0;background:transparent;overflow:hidden;">
<script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
<script>
(function() {
  var W = window.parent, D = W.document;

  // Clean up previous canvas on Streamlit re-runs
  var prev = D.getElementById('med-plus-canvas');
  if (prev) { prev.remove(); }

  // Create fixed background canvas in the parent page
  var cv = D.createElement('canvas');
  cv.id = 'med-plus-canvas';
  Object.assign(cv.style, {
    position: 'fixed', top: '0', left: '0',
    width: '100vw', height: '100vh',
    zIndex: '0', pointerEvents: 'none', opacity: '0.42',
  });
  D.body.appendChild(cv);

  // Scene
  var renderer = new THREE.WebGLRenderer({ canvas: cv, alpha: true, antialias: true });
  renderer.setPixelRatio(W.devicePixelRatio || 1);
  renderer.setSize(W.innerWidth, W.innerHeight);

  var scene  = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(32, W.innerWidth / W.innerHeight, 0.1, 100);
  camera.position.set(2.5, 0, 14);

  // Neon green phong material
  var mat = new THREE.MeshPhongMaterial({
    color: 0x00ff88, emissive: 0x00ff88,
    emissiveIntensity: 1.4, shininess: 160, specular: 0xbbffdd,
  });

  // Medical plus sign (H + V boxes) — sized to be a subtle bg element
  var plus = new THREE.Group();
  plus.add(new THREE.Mesh(new THREE.BoxGeometry(2.8, 0.72, 0.4), mat));
  plus.add(new THREE.Mesh(new THREE.BoxGeometry(0.72, 2.8, 0.4), mat));
  plus.position.set(2.5, -0.3, 0);   // shifted right, slightly below center
  scene.add(plus);

  // Transparent glow shell
  var gMat = new THREE.MeshPhongMaterial({
    color: 0x00ff88, emissive: 0x00ff88, emissiveIntensity: 0.4,
    transparent: true, opacity: 0.09, shininess: 4,
  });
  var glow = new THREE.Group();
  glow.add(new THREE.Mesh(new THREE.BoxGeometry(3.1, 1.0, 0.6), gMat));
  glow.add(new THREE.Mesh(new THREE.BoxGeometry(1.0, 3.1, 0.6), gMat));
  glow.position.set(2.5, -0.3, 0);
  scene.add(glow);

  // Lights
  scene.add(new THREE.AmbientLight(0xffffff, 0.2));
  var ptL = new THREE.PointLight(0x00ff88, 3.5, 28);
  ptL.position.set(2.5, 0, 7);
  scene.add(ptL);
  var dir = new THREE.DirectionalLight(0xffffff, 0.55);
  dir.position.set(4, 5, 4);
  scene.add(dir);

  // Mouse interaction from parent window
  var mx = 0, my = 0;
  W.addEventListener('mousemove', function(e) {
    mx = (e.clientX / W.innerWidth  - 0.5) * 2;
    my = (e.clientY / W.innerHeight - 0.5) * 2;
  });

  // Resize
  W.addEventListener('resize', function() {
    camera.aspect = W.innerWidth / W.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(W.innerWidth, W.innerHeight);
  });

  // Animation loop
  var t = 0;
  (function loop() {
    requestAnimationFrame(loop);
    t += 0.011;

    var ry = t * 0.4 + mx * 0.32;
    var rx = Math.sin(t * 0.27) * 0.18 + my * -0.18;
    plus.rotation.y = ry;  plus.rotation.x = rx;
    glow.rotation.y = ry;  glow.rotation.x = rx;

    var fy = Math.sin(t * 0.68) * 0.28;
    plus.position.y = fy;
    glow.position.y = fy;

    gMat.opacity = 0.09 + Math.sin(t * 1.7) * 0.05;
    mat.emissiveIntensity = 1.2 + Math.sin(t * 2.1) * 0.3;

    renderer.render(scene, camera);
  })();
})();
</script>
</body></html>
"""

# Inject Three.js 3D neon background once per session
if "_threejs_injected" not in st.session_state:
    components.html(_THREEJS_HTML, height=0)
    st.session_state["_threejs_injected"] = True

# ------------------------------------------------------------------
# CSS — Clean black theme, green accents, UI on top of canvas
# ------------------------------------------------------------------
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  html, body, [data-testid="stAppViewContainer"], .stApp {
      background: #000000 !important;
      font-family: 'Inter', sans-serif;
  }
  [data-testid="stMain"] { background: transparent !important; }
  [data-testid="stMainBlockContainer"] { position: relative; z-index: 1; }

  [data-testid="stSidebar"] {
      background: rgba(4,4,4,0.94) !important;
      border-right: 1px solid #181818;
      position: relative; z-index: 2;
  }
  [data-testid="stSidebar"] * { color: #c8c8c8 !important; }
  [data-testid="stSidebar"] h3,
  [data-testid="stSidebar"] strong { color: #ffffff !important; }

  .header-row {
      padding: 2rem 0 1.6rem 0;
      border-bottom: 1px solid #1a1a1a;
      margin-bottom: 2rem;
  }
  .header-row h1 {
      color: #ffffff; font-size: 1.75rem; font-weight: 700;
      margin: 0; letter-spacing: -0.02em;
  }
  .header-row p { color: #555; font-size: 0.9rem; margin: 0.3rem 0 0 0; }

  .section-label {
      color: #777; font-size: 0.72rem; font-weight: 600;
      text-transform: uppercase; letter-spacing: 0.1em;
      margin: 1.6rem 0 0.6rem 0;
      border-left: 2px solid #00ff88; padding-left: 0.6rem;
  }
  .answer-box {
      background: rgba(8,8,8,0.88); border: 1px solid #1e1e1e;
      border-radius: 10px; padding: 1.4rem 1.6rem; margin: 0.6rem 0 1.2rem 0;
      color: #e0e0e0; line-height: 1.72; backdrop-filter: blur(6px);
  }
  .metric-card {
      background: rgba(8,8,8,0.88); border: 1px solid #1e1e1e;
      border-radius: 8px; padding: 1rem; text-align: center;
  }
  .metric-card .m-label { color: #444; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; }
  .metric-card .m-value { color: #00ff88; font-size: 1.7rem; font-weight: 700; margin-top: 0.2rem; }

  .conflict-alert {
      background: rgba(200,40,40,0.07); border: 1px solid rgba(200,40,40,0.32);
      border-radius: 8px; padding: 0.8rem 1.2rem;
      color: #e87070; font-weight: 500; margin-bottom: 0.8rem;
  }
  .conf-high   { color: #00ff88; font-weight: 600; }
  .conf-medium { color: #facc15; font-weight: 600; }
  .conf-low    { color: #f87171; font-weight: 600; }

  .stButton > button {
      background: transparent !important; color: #00ff88 !important;
      border: 1px solid #00ff88 !important; border-radius: 6px;
      font-weight: 600; font-size: 0.875rem;
      transition: all 0.2s ease;
  }
  .stButton > button:hover {
      background: rgba(0,255,136,0.08) !important;
      box-shadow: 0 0 14px rgba(0,255,136,0.35);
      transform: translateY(-1px);
  }
  .stTextInput > div > div > input {
      background: rgba(10,10,10,0.9) !important;
      border: 1px solid #252525 !important; border-radius: 6px !important;
      color: #e0e0e0 !important;
  }
  .stTextInput > div > div > input:focus {
      border-color: #00ff88 !important;
      box-shadow: 0 0 0 2px rgba(0,255,136,0.14) !important;
  }
  hr { border-color: #181818 !important; }
  [data-testid="stExpander"] {
      background: rgba(8,8,8,0.9) !important;
      border: 1px solid #1e1e1e !important; border-radius: 8px !important;
  }
  [data-testid="stExpander"] summary { color: #aaaaaa !important; }

  .welcome-block {
      text-align: center; padding: 4rem 2rem; color: #333;
  }
  .welcome-block h3 { color: #4a4a4a; font-size: 1.1rem; font-weight: 400; margin: 0 0 0.5rem 0; }
  .welcome-block p  { font-size: 0.85rem; color: #333; }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------
def render_header():
    st.markdown("""
    <div class="header-row">
        <h1>Hospital RAG &mdash; Conflict Detection</h1>
        <p>Query hospital performance documents with automated contradiction detection, source provenance and confidence calibration</p>
    </div>
    """, unsafe_allow_html=True)


# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.markdown("### Configuration")
        api_key = st.text_input(
            "Google Gemini API Key",
            type="password",
            value="AIzaSyCTaZjSJIzqev63uQC3Lg6343g28WW4Gy4",
            help="Required for LLM responses. Get one at https://aistudio.google.com/",
        )
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
            st.success("API Key set")

        st.markdown("---")
        st.markdown("### Documents")
        if "vector_store" in st.session_state and st.session_state.vector_store:
            try:
                count = st.session_state.vector_store._collection.count()
                st.markdown(f"""
                <div class="metric-card">
                    <div class="m-label">Indexed Chunks</div>
                    <div class="m-value">{count}</div>
                </div>""", unsafe_allow_html=True)
            except Exception:
                pass
            docs_dir = os.path.join(os.path.dirname(__file__), "sample_documents")
            if os.path.exists(docs_dir):
                files = sorted(os.listdir(docs_dir))
                st.markdown(f"**{len(files)} documents loaded:**")
                for f in files:
                    st.markdown(f"- {f}")

        st.markdown("---")
        st.markdown("### Demo Queries")
        demos = [
            "How has patient satisfaction changed over Q1?",
            "What is the state of surgical outcomes this quarter?",
            "Is staff morale improving or declining?",
            "What is the hospital's financial health in Q1?",
            "Are infection rates increasing or decreasing?",
        ]
        for q in demos:
            if st.button(q, key=f"demo_{q[:20]}", use_container_width=True):
                st.session_state.demo_query = q

        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
**RAG Robustness & Conflict Detection**

- Retrieves relevant hospital documents
- Detects contradictions using NLI models
- Provides confidence-calibrated answers
- Shows full source provenance

**Tech Stack:** ChromaDB · Gemini 2.5 Flash · DeBERTa-v3
        """)
    return api_key


# ------------------------------------------------------------------
# Pipeline
# ------------------------------------------------------------------
def initialize_pipeline():
    st.session_state.setdefault("vector_store", None)
    st.session_state.setdefault("chain", None)

    if st.session_state.vector_store is None:
        from config import CHROMA_PERSIST_DIR
        chroma_path = Path(CHROMA_PERSIST_DIR)
        if chroma_path.exists() and any(chroma_path.iterdir()):
            with st.spinner("Loading indexed documents (may download embedding model on first run)..."):
                from ingestion import load_vector_store
                st.session_state.vector_store = load_vector_store()
                st.toast("Vector store loaded.")
        else:
            with st.spinner("Ingesting documents — downloading embedding model on first run, please wait..."):
                from ingestion import ingest_documents
                st.session_state.vector_store = ingest_documents()
                if st.session_state.vector_store:
                    st.toast("Documents ingested successfully.")
                else:
                    st.error("Failed to ingest documents. Check the sample_documents folder.")
                    return False
    return True


# ------------------------------------------------------------------
# Render helpers
# ------------------------------------------------------------------
def render_confidence(confidence: dict):
    level = confidence["level"]
    css  = {"High": "conf-high", "Medium": "conf-medium", "Low": "conf-low"}.get(level, "conf-medium")
    st.markdown(
        f'<div style="margin:.8rem 0;"><span class="{css}">Confidence: {level} ({confidence["score"]:.0f}%)</span></div>',
        unsafe_allow_html=True,
    )
    if confidence.get("factors"):
        with st.expander("Confidence factors"):
            for f in confidence["factors"]:
                st.markdown(f"- {f}")


def render_conflicts(conflict_result: dict):
    if not conflict_result["has_conflicts"]:
        st.success("No conflicting evidence detected among retrieved documents.")
        return
    st.markdown(f'<div class="conflict-alert">{conflict_result["conflict_count"]} Conflict(s) Detected</div>',
                unsafe_allow_html=True)
    for i, c in enumerate(conflict_result["conflicts"], 1):
        with st.expander(
            f"Conflict #{i} | Score: {c['contradiction_score']:.2f} | "
            f"{c['doc_a']['source']} vs {c['doc_b']['source']}",
            expanded=(i <= 2),
        ):
            col1, col2 = st.columns(2)
            for col, side in [(col1, "doc_a"), (col2, "doc_b")]:
                with col:
                    st.markdown(f"**{c[side]['source']}**")
                    st.markdown(f"*Dept: {c[side]['department']}*")
                    st.markdown(f"*Similarity: {c[side]['similarity_score']:.2f}*")
                    st.info(c[side]["snippet"][:300])
            st.markdown("**NLI Score Breakdown:**")
            c1, c2, c3 = st.columns(3)
            c1.metric("Contradiction", f"{c['contradiction_score']:.2f}")
            c2.metric("Entailment",    f"{c.get('entailment_score', 0):.2f}")
            c3.metric("Neutral",       f"{c.get('neutral_score', 0):.2f}")


def render_sources(sources: list):
    if not sources:
        return
    st.markdown('<div class="section-label">Source Provenance</div>', unsafe_allow_html=True)
    for src in sources:
        with st.expander(
            f"{src['source']} | {src['department']} | "
            f"Similarity: {src['max_similarity']:.2f} | Chunks: {src['chunks_retrieved']}",
            expanded=False,
        ):
            st.markdown(f"- **Doc ID:** {src['doc_id']}")
            st.markdown(f"- **Type:** {src['doc_type']}")
            st.markdown(f"- **Highest Similarity:** {src['max_similarity']:.4f}")
            for j, snip in enumerate(src["snippets"], 1):
                st.markdown(f"*Snippet {j}:*")
                st.text(snip[:300])


def render_answer(result: dict):
    st.markdown('<div class="section-label">Answer</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="answer-box">{result["answer"]}</div>', unsafe_allow_html=True)
    render_confidence(result["confidence"])
    st.markdown("---")
    st.markdown('<div class="section-label">Conflict Analysis</div>', unsafe_allow_html=True)
    render_conflicts(result["conflicts"])
    st.markdown("---")
    render_sources(result["sources"])
    with st.expander("All Retrieved Chunks (Raw)", expanded=False):
        for i, chunk in enumerate(result.get("retrieved_chunks", []), 1):
            st.markdown(f"**Chunk #{i}** — {chunk['source']} (Score: {chunk['similarity_score']:.4f})")
            st.text(chunk["content"][:500])
            st.markdown("---")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    render_header()
    api_key = render_sidebar()

    if not initialize_pipeline():
        return

    # Build/rebuild the chain when api_key is present and chain is missing or uses an old model
    from config import LLM_MODEL
    if api_key and (
        st.session_state.get("chain") is None
        or st.session_state.get("chain_model") != LLM_MODEL
    ):
        from rag_pipeline import build_chain
        try:
            st.session_state.chain = build_chain(api_key)
            st.session_state.chain_model = LLM_MODEL
        except Exception as e:
            st.error(f"Failed to build LLM chain: {e}")
            return

    st.markdown('<div class="section-label">Ask a Question</div>', unsafe_allow_html=True)

    # Populate input from demo query if one was clicked
    if "demo_query" in st.session_state:
        st.session_state["query_input"] = st.session_state.pop("demo_query")

    # Use a keyed widget so Streamlit preserves the value across re-runs
    query = st.text_input(
        "Question",
        key="query_input",
        placeholder="e.g. How has patient satisfaction changed over Q1?",
        label_visibility="collapsed",
    )

    col1, col2, _ = st.columns([1, 1, 4])
    with col1:
        submit = st.button("Analyze", type="primary", use_container_width=True)
    with col2:
        if st.button("Clear", use_container_width=True):
            st.session_state.pop("last_result", None)
            st.session_state["query_input"] = ""
            st.rerun()

    if submit:
        current_query = st.session_state.get("query_input", "").strip()
        if not current_query:
            st.warning("Please enter a question first.")
        elif not api_key:
            st.warning("Please enter your Google Gemini API Key in the sidebar.")
        else:
            # Rebuild chain if needed (e.g. key was just entered)
            if st.session_state.get("chain") is None:
                from rag_pipeline import build_chain
                try:
                    st.session_state.chain = build_chain(api_key)
                except Exception as e:
                    st.error(f"Failed to build LLM chain: {e}")
                    return

            with st.spinner("Retrieving documents and detecting conflicts..."):
                try:
                    from rag_pipeline import query_with_conflict_detection
                    result = query_with_conflict_detection(
                        chain=st.session_state.chain,
                        vector_store=st.session_state.vector_store,
                        question=current_query,
                    )
                    st.session_state.last_result = result
                except Exception as e:
                    st.error(f"Error during analysis: {e}")
                    return

    if "last_result" in st.session_state:
        render_answer(st.session_state.last_result)
    else:
        st.markdown("""
        <div class="welcome-block">
            <h3>Ready to analyze hospital documents</h3>
            <p>Enter a question above or select a demo query from the sidebar.</p>
            <p style="margin-top:1rem;font-size:0.78rem;color:#2a2a2a;">
                Hospital documents indexed &middot; Conflict detection powered by NLI
                &middot; Source provenance tracking &middot; Confidence calibration
            </p>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
