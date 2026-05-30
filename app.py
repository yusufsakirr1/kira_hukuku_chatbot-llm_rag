import streamlit as st
import re
import html as html_lib
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from groq import Groq

# ── Sayfa Ayarları ─────────────────────────────────────────────
st.set_page_config(
    page_title="kira_hukuku — Türk Kira Hukuku Asistanı",
    page_icon="⚖",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Konfigürasyon ──────────────────────────────────────────────
QDRANT_URL       = st.secrets["QDRANT_URL"]
QDRANT_API_KEY   = st.secrets["QDRANT_API_KEY"]
GROQ_API_KEY     = st.secrets["GROQ_API_KEY"]
KANUN_KOLEKSIYON = "kira_hukuku"
KARAR_KOLEKSIYON = "kira_yargitay"
TOP_KANUN        = 3
TOP_KARAR        = 4

# ╔══════════════════════════════════════════════════════════════╗
# ║  TASARIM: CSS INJECTION                                       ║
# ╚══════════════════════════════════════════════════════════════╝
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=JetBrains+Mono:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&display=swap" rel="stylesheet">

<style>
  /* ═══════════════════════════════════════════════════════════
     DESIGN TOKENS
     ═══════════════════════════════════════════════════════════ */
  :root {
    /* Surfaces */
    --bg              : #0f0e0c;
    --bg-elevated     : #1a1815;
    --surface         : #252220;
    --surface-cream   : #f5f0e8;
    --surface-cream-2 : #ebe5d7;

    /* Lines */
    --line            : #2d2925;
    --line-strong     : #3d3833;

    /* Text */
    --text            : #f5f0e8;
    --text-muted      : #a39e93;
    --text-dim        : #6e6961;
    --text-dark       : #1a1815;
    --text-body-dark  : #2a2620;

    /* Accents */
    --coral           : #d97757;
    --coral-light     : #e89478;
    --coral-deep      : #c96442;
    --gold            : #d4a574;
    --gold-deep       : #a8814f;

    /* Gradients */
    --grad-coral      : linear-gradient(90deg,
                          #c96442 0%, #d97757 25%, #e89478 50%,
                          #d97757 75%, #c96442 100%);

    /* Fonts */
    --font-serif      : "Fraunces", Georgia, serif;
    --font-body       : "Newsreader", Georgia, serif;
    --font-mono       : "JetBrains Mono", ui-monospace, monospace;
  }

  /* ═══════════════════════════════════════════════════════════
     GLOBAL
     ═══════════════════════════════════════════════════════════ */
  .stApp {
    background:
      radial-gradient(ellipse at 50% 0%, rgba(217, 119, 87, 0.05), transparent 55%),
      var(--bg);
    background-attachment: fixed;
  }

  /* Streamlit chrome'u temizle */
  [data-testid="stHeader"]   { background: transparent; height: 0; }
  [data-testid="stToolbar"]  { display: none; }
  #MainMenu                  { display: none; }
  footer                     { display: none; }

  [data-testid="stMainBlockContainer"],
  .main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 4rem;
    max-width: 880px;
  }

  /* Tüm metin defaultları */
  .stApp, .stApp p, .stApp div, .stApp span, .stApp label,
  .stApp li, .stApp a {
    color: var(--text);
    font-family: var(--font-body);
  }

  ::selection {
    background: var(--coral);
    color: var(--text-dark);
  }

  /* Scrollbar */
  ::-webkit-scrollbar              { width: 10px; height: 10px; }
  ::-webkit-scrollbar-track        { background: var(--bg); }
  ::-webkit-scrollbar-thumb        { background: var(--line-strong); border-radius: 5px; }
  ::-webkit-scrollbar-thumb:hover  { background: var(--coral-deep); }

  /* ═══════════════════════════════════════════════════════════
     HERO — Claude Code prompt + animated coral stripe
     ═══════════════════════════════════════════════════════════ */
  .hero {
    margin: 1rem 0 2.8rem 0;
    padding-bottom: 2rem;
    border-bottom: 1px solid var(--line);
    animation: fade-up 0.7s cubic-bezier(0.2, 0.8, 0.2, 1);
  }

  .hero-prompt {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    font-family: var(--font-mono);
    font-size: 0.82rem;
    color: var(--text-muted);
    margin-bottom: 1.1rem;
  }

  .hero-prompt .symbol  { color: var(--coral); font-weight: 600; }
  .hero-prompt .path    { color: var(--text-muted); letter-spacing: 0.02em; }
  .hero-prompt .accent  { color: var(--coral-light); }

  .hero-prompt .cursor {
    display: inline-block;
    width: 8px; height: 14px;
    background: var(--coral);
    margin-left: -2px;
    animation: blink 1.1s infinite steps(2, end);
    vertical-align: middle;
  }

  .hero-prompt .status {
    margin-left: auto;
    font-size: 0.68rem;
    color: var(--gold);
    border: 1px solid var(--gold-deep);
    padding: 2px 9px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
  }

  @keyframes blink {
    0%, 49%   { opacity: 1; }
    50%, 100% { opacity: 0; }
  }

  .hero-bar {
    height: 2px;
    background: var(--grad-coral);
    background-size: 200% 100%;
    margin-bottom: 2rem;
    animation: shimmer-h 6s linear infinite;
  }

  @keyframes shimmer-h {
    0%   { background-position:   0% 50%; }
    100% { background-position: 200% 50%; }
  }

  .hero-title {
    font-family: var(--font-serif);
    font-size: clamp(2.6rem, 5.5vw, 3.8rem);
    font-weight: 500;
    line-height: 1.02;
    letter-spacing: -0.025em;
    color: var(--text);
    margin: 0 0 0.6rem 0;
    font-variation-settings: "opsz" 96, "SOFT" 30;
  }
  .hero-title em {
    font-style: italic;
    color: var(--coral-light);
    font-weight: 400;
  }

  .hero-subtitle {
    font-family: var(--font-mono);
    font-size: 0.78rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.18em;
    margin: 0.4rem 0 0 0;
  }
  .hero-subtitle .sep { color: var(--coral); margin: 0 0.55rem; }

  /* ═══════════════════════════════════════════════════════════
     SECTION LABEL — mono uppercase with coral dot
     ═══════════════════════════════════════════════════════════ */
  .section-label {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    color: var(--text-dim);
    margin: 2.2rem 0 0.9rem 0;
    display: flex;
    align-items: center;
    gap: 0.65rem;
  }
  .section-label::before {
    content: "";
    width: 6px; height: 6px;
    background: var(--coral);
  }

  /* ═══════════════════════════════════════════════════════════
     RADIO — kullanıcı tipi
     ═══════════════════════════════════════════════════════════ */
  [data-testid="stRadio"] > div {
    flex-direction: row;
    gap: 0.7rem;
  }
  [data-testid="stRadio"] label {
    flex: 1;
    padding: 0.8rem 1rem !important;
    border: 1px solid var(--line) !important;
    background: var(--bg-elevated);
    border-radius: 3px;
    transition: all 0.18s ease;
    cursor: pointer;
    font-family: var(--font-body) !important;
    font-size: 0.95rem !important;
  }
  [data-testid="stRadio"] label:hover {
    border-color: var(--coral-deep) !important;
    background: var(--surface);
  }
  [data-testid="stRadio"] label > div:first-child { display: none; }
  [data-testid="stRadio"] label > div:last-child { color: var(--text); }

  /* ═══════════════════════════════════════════════════════════
     BUTONLAR — örnek sorular (secondary) + arama (primary)
     ═══════════════════════════════════════════════════════════ */
  .stButton > button {
    font-family: var(--font-body);
    font-size: 0.92rem;
    text-align: left;
    background: var(--bg-elevated);
    color: var(--text);
    border: 1px solid var(--line);
    border-left: 2px solid var(--coral-deep);
    padding: 0.75rem 1rem;
    border-radius: 3px;
    transition: all 0.22s cubic-bezier(0.2, 0.8, 0.2, 1);
    font-weight: 400;
    line-height: 1.4;
    white-space: normal;
    height: auto;
    min-height: 3.2rem;
  }
  .stButton > button:hover {
    border-color: var(--coral) !important;
    border-left-color: var(--coral) !important;
    background: var(--surface);
    transform: translateX(3px);
    box-shadow: -3px 0 0 var(--coral-deep);
    color: var(--text) !important;
  }
  .stButton > button:focus:not(:active) {
    border-color: var(--coral) !important;
    box-shadow: 0 0 0 2px rgba(217, 119, 87, 0.15) !important;
    color: var(--text) !important;
  }

  /* PRIMARY — arama başlat */
  .stButton > button[kind="primary"] {
    background: var(--grad-coral);
    background-size: 200% 100%;
    color: var(--text-dark) !important;
    border: none;
    padding: 1rem 1.4rem;
    font-family: var(--font-mono);
    font-size: 0.82rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    text-align: center;
    border-radius: 3px;
    margin-top: 0.5rem;
    transition: all 0.35s ease;
  }
  .stButton > button[kind="primary"]:hover {
    background-position: 100% 50%;
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(217, 119, 87, 0.25) !important;
    color: var(--text-dark) !important;
  }

  /* ═══════════════════════════════════════════════════════════
     INPUT
     ═══════════════════════════════════════════════════════════ */
  [data-testid="stTextInput"] input {
    background: var(--bg-elevated);
    color: var(--text);
    border: 1px solid var(--line);
    border-radius: 3px;
    padding: 0.95rem 1.1rem;
    font-family: var(--font-body);
    font-size: 1.02rem;
    transition: all 0.18s ease;
  }
  [data-testid="stTextInput"] input:focus {
    border-color: var(--coral);
    box-shadow: 0 0 0 3px rgba(217, 119, 87, 0.12);
    outline: none;
  }
  [data-testid="stTextInput"] input::placeholder {
    color: var(--text-dim);
    font-style: italic;
    font-family: var(--font-mono);
    font-size: 0.92rem;
  }

  /* ═══════════════════════════════════════════════════════════
     YANIT KARTI — cream üzerinde, sol kenar coral gradient şerit
     ═══════════════════════════════════════════════════════════ */
  .answer-card {
    background: var(--surface-cream);
    color: var(--text-body-dark);
    padding: 2rem 2.2rem 1.8rem 2.2rem;
    margin: 1.8rem 0 1.5rem 0;
    border-radius: 4px;
    position: relative;
    box-shadow:
      0 1px 0 var(--line-strong),
      0 18px 40px -12px rgba(0, 0, 0, 0.45);
    overflow: hidden;
    animation: fade-up 0.5s cubic-bezier(0.2, 0.8, 0.2, 1);
  }
  .answer-card::before {
    content: "";
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: var(--grad-coral);
    background-size: 100% 200%;
    animation: shimmer-v 4.5s linear infinite;
  }
  @keyframes shimmer-v {
    0%   { background-position: 50%   0%; }
    100% { background-position: 50% 200%; }
  }

  .answer-meta {
    font-family: var(--font-mono);
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    color: var(--coral-deep);
    margin-bottom: 1.1rem;
    display: flex;
    align-items: center;
    gap: 0.7rem;
  }
  .answer-meta .dot {
    width: 5px; height: 5px;
    border-radius: 50%;
    background: var(--coral);
    box-shadow: 0 0 0 3px rgba(217, 119, 87, 0.2);
  }

  .answer-body {
    font-family: var(--font-body);
    font-size: 1.05rem;
    line-height: 1.68;
    color: var(--text-body-dark);
  }
  .answer-body p {
    margin: 0 0 1rem 0;
    color: var(--text-body-dark) !important;
  }
  .answer-body p:last-child { margin-bottom: 0; }
  .answer-body strong {
    color: #6b3a25;
    font-weight: 600;
  }
  .answer-body em {
    color: var(--gold-deep);
    font-style: italic;
  }

  /* ═══════════════════════════════════════════════════════════
     EXPANDERS — TBK + Yargıtay
     ═══════════════════════════════════════════════════════════ */
  [data-testid="stExpander"] {
    background: var(--bg-elevated);
    border: 1px solid var(--line);
    border-radius: 3px;
    margin-top: 1rem !important;
    margin-bottom: 0.5rem;
    transition: border-color 0.18s ease;
    overflow: hidden;
  }
  [data-testid="stExpander"]:hover {
    border-color: var(--line-strong);
  }
  [data-testid="stExpander"] summary,
  [data-testid="stExpander"] details > summary {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: var(--text);
    padding: 0.95rem 1.2rem;
    cursor: pointer;
    letter-spacing: 0.08em;
  }
  [data-testid="stExpander"] summary p {
    font-family: var(--font-mono) !important;
    color: var(--text) !important;
    margin: 0;
  }
  [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    padding: 0.4rem 1.2rem 1rem;
    border-top: 1px solid var(--line);
  }
  [data-testid="stExpander"] p {
    font-family: var(--font-body);
    color: var(--text);
    line-height: 1.6;
    font-size: 0.96rem;
  }
  [data-testid="stExpander"] strong {
    color: var(--coral-light);
    font-family: var(--font-mono);
    font-size: 0.86rem;
    font-weight: 600;
    letter-spacing: 0.02em;
  }
  [data-testid="stExpander"] em {
    color: var(--gold);
    font-family: var(--font-mono);
    font-style: normal;
    font-size: 0.76rem;
    letter-spacing: 0.05em;
  }
  [data-testid="stExpander"] hr {
    border: none;
    border-top: 1px dashed var(--line);
    margin: 1rem 0;
  }

  /* ═══════════════════════════════════════════════════════════
     ALERTS + SPINNER
     ═══════════════════════════════════════════════════════════ */
  [data-testid="stAlert"] {
    background: var(--bg-elevated);
    border: 1px solid var(--line);
    border-left: 3px solid var(--gold);
    color: var(--text);
    border-radius: 3px;
    font-family: var(--font-body);
  }
  [data-testid="stAlert"] p {
    color: var(--text) !important;
    font-family: var(--font-body);
  }

  [data-testid="stSpinner"] {
    color: var(--coral);
    font-family: var(--font-mono);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.18em;
  }
  [data-testid="stSpinner"] > div > div {
    border-top-color: var(--coral) !important;
    border-right-color: rgba(217, 119, 87, 0.2) !important;
    border-bottom-color: rgba(217, 119, 87, 0.2) !important;
    border-left-color: rgba(217, 119, 87, 0.2) !important;
  }

  /* ═══════════════════════════════════════════════════════════
     FOOTER
     ═══════════════════════════════════════════════════════════ */
  .footer {
    margin-top: 4rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--line);
    font-family: var(--font-mono);
    font-size: 0.68rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.2em;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.8rem;
  }
  .footer .warn { color: var(--gold); }

  /* ═══════════════════════════════════════════════════════════
     ANIMATIONS
     ═══════════════════════════════════════════════════════════ */
  @keyframes fade-up {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
  }
</style>
""", unsafe_allow_html=True)


# ── Model ve Client'lar (cache) ────────────────────────────────
@st.cache_resource
def yukle_model():
    return SentenceTransformer("intfloat/multilingual-e5-base")

@st.cache_resource
def yukle_qdrant():
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

@st.cache_resource
def yukle_groq():
    return Groq(api_key=GROQ_API_KEY)

model  = yukle_model()
qdrant = yukle_qdrant()
groq   = yukle_groq()


# ── Retrieval ──────────────────────────────────────────────────
def vektorle(soru: str):
    return model.encode(f"query: {soru}", normalize_embeddings=True).tolist()


def ilgili_maddeleri_getir(vektor) -> list[dict]:
    sonuclar = qdrant.query_points(
        collection_name=KANUN_KOLEKSIYON,
        query=vektor, limit=TOP_KANUN, with_payload=True
    ).points
    return [{
        "madde_no": s.payload["madde_no"],
        "baslik"  : s.payload["baslik"],
        "icerik"  : s.payload["icerik"],
        "skor"    : round(s.score, 3),
    } for s in sonuclar]


def ilgili_kararlari_getir(vektor) -> list[dict]:
    try:
        sonuclar = qdrant.query_points(
            collection_name=KARAR_KOLEKSIYON,
            query=vektor, limit=TOP_KARAR, with_payload=True
        ).points
    except Exception:
        return []
    return [{
        "esas_no"     : s.payload["esas_no"],
        "karar_no"    : s.payload["karar_no"],
        "tarih"       : s.payload["tarih"],
        "ilgili_madde": s.payload["ilgili_madde"],
        "konu"        : s.payload["konu"],
        "icerik"      : s.payload["icerik"],
        "skor"        : round(s.score, 3),
    } for s in sonuclar]


# ── LLM ────────────────────────────────────────────────────────
def cevap_uret(soru, maddeler, kararlar):
    kanun = "\n\n".join([
        f"TBK Madde {m['madde_no']} — {m['baslik']}:\n{m['icerik']}"
        for m in maddeler
    ])
    karar = "\n\n".join([
        f"Yargıtay Kararı [E. {k['esas_no']} / K. {k['karar_no']} / {k['tarih']}] "
        f"(İlgili: TBK m.{k['ilgili_madde']} — {k['konu']}):\n{k['icerik']}"
        for k in kararlar
    ])
    baglam = "═══ TBK MADDELERİ ═══\n\n" + kanun
    if karar:
        baglam += "\n\n═══ YARGITAY KARARLARI ═══\n\n" + karar

    sistem = """Sen Türk kira hukuku konusunda uzman bir hukuki asistansın.
Sana Türk Borçlar Kanunu'ndan ilgili maddeler ve Yargıtay kararları verilecek.
Yalnızca bu kaynaklara dayanarak yanıtla.

Kurallar:
- Kanun atıfı: "TBK Madde 344'e göre..." biçiminde
- Yargıtay atıfı: "Yargıtay'ın E. 2014/4518, K. 2015/27, 12.01.2015 tarihli kararında..." biçiminde
- Yargıtay alıntılarında kanun lafzını tekrar etme; sadece somut yorum/uygulamayı aktar
- İçtihadı kanunla birlikte yorumla — sadece kanun lafzı yeterli değildir
- Sade Türkçe, hukuki terimleri açıkla
- Kaynaklarda cevap yoksa açıkça söyle, uydurma
- Cevabı 3-5 paragrafla sınırla, kısa ve öz tut
- Sonda: "Bu bilgiler genel bilgi amaçlıdır, hukuki danışmanlık için avukata başvurunuz." """

    yanit = groq.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": sistem},
            {"role": "user", "content":
                f"Aşağıdaki kaynaklar bağlamında soruyu yanıtla:\n\n{baglam}\n\n---\nSoru: {soru}"}
        ],
        temperature=0.2,
        max_tokens=1000,
    )
    return yanit.choices[0].message.content


# ── Markdown → HTML (cevap kartı için) ─────────────────────────
def cevap_to_html(text: str) -> str:
    """Groq cevabını güvenli HTML'e çevir: bold/italic + paragraflar."""
    text = html_lib.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    return '\n'.join(f'<p>{p}</p>' for p in paragraphs)


# ╔══════════════════════════════════════════════════════════════╗
# ║  HERO                                                          ║
# ╚══════════════════════════════════════════════════════════════╝
st.markdown("""
<div class="hero">
  <div class="hero-prompt">
    <span class="symbol">▎</span>
    <span class="path">~/yargitay <span class="accent">×</span> tbk</span>
    <span class="cursor"></span>
    <span class="status">● healthy</span>
  </div>
  <div class="hero-bar"></div>
  <h1 class="hero-title">Kira Hukuku <em>Asistanı</em></h1>
  <p class="hero-subtitle">Türk Borçlar Kanunu <span class="sep">×</span> Yargıtay İçtihatları</p>
</div>
""", unsafe_allow_html=True)


# ── Perspektif ─────────────────────────────────────────────────
st.markdown('<div class="section-label">perspektif</div>', unsafe_allow_html=True)

kullanici_tipi = st.radio(
    "Perspektif",
    ["🏠  Kiracıyım", "🔑  Ev Sahibiyim"],
    horizontal=True,
    label_visibility="collapsed",
)

# ── Örnek sorular ──────────────────────────────────────────────
st.markdown('<div class="section-label">örnek sorular</div>', unsafe_allow_html=True)

# Oturum durumunu (state) kontrol et
if "input_soru" not in st.session_state:
    st.session_state.input_soru = ""

ornek_sorular = {
    "🏠  Kiracıyım": [
        "Ev sahibi kirayı TÜFE üzerinde artırabilir mi?",
        "10 yıldır oturuyorum, ev sahibi sebepsiz çıkarabilir mi?",
        "Kirayı geç ödedim, ihtarname geldi — ne yapmalıyım?",
        "Kiracı olarak tadilat yaptırabilir miyim?",
    ],
    "🔑  Ev Sahibiyim": [
        "Kira artış sınırı nasıl belirlenir, üstüne çıkabilir miyim?",
        "10 yıldır oturan kiracıyı nasıl tahliye edebilirim?",
        "Kira ödenmedi, kaç günlük ihtarname çekmeliyim?",
        "Kiracı evi hasarlı bırakırsa ne yapabilirim?",
    ],
}

cols = st.columns(2)
for i, ornek in enumerate(ornek_sorular[kullanici_tipi]):
    # Butona basıldığında soruyu session_state'e ata
    if cols[i % 2].button(ornek, use_container_width=True, key=f"ornek_{i}"):
        st.session_state.input_soru = ornek

# ── Soru ───────────────────────────────────────────────────────
st.markdown('<div class="section-label">sorunuz</div>', unsafe_allow_html=True)

# text_input'u key ile session_state'e bağladık
soru_input = st.text_input(
    "Soru",
    key="input_soru", 
    placeholder="kira sözleşmesiyle ilgili sorunuzu yazın…",
    label_visibility="collapsed",
)

sor_butonu = st.button("⚖  aramayı başlat", type="primary", use_container_width=True)

# ── Yanıt (DÜZELTİLMİŞ MANTIK) ──────────────────────────────────
# ── Yanıt (DÜZELTİLMİŞ VE BUTONLARI GERİ GETİRİLMİŞ BÖLÜM) ──────
if sor_butonu:
    # 1. Hata Kontrolü
    if not st.session_state.input_soru.strip():
        st.warning("lütfen bir soru girin.")
    else:
        # 2. Arama ve cevap üretme
        with st.spinner("kanun ve içtihat aranıyor…"):
            vektor   = vektorle(st.session_state.input_soru)
            maddeler = ilgili_maddeleri_getir(vektor)
            kararlar = ilgili_kararlari_getir(vektor)

        with st.spinner("yanıt hazırlanıyor…"):
            cevap = cevap_uret(st.session_state.input_soru, maddeler, kararlar)

        # 3. Yanıt kartı
        st.markdown(f"""
        <div class="answer-card">
          <div class="answer-meta">
            <span class="dot"></span>
            <span>response · {len(maddeler)} madde · {len(kararlar)} karar</span>
          </div>
          <div class="answer-body">{cevap_to_html(cevap)}</div>
        </div>
        """, unsafe_allow_html=True)

        # 4. Kaynaklar (KAYBOLAN BUTONLAR BURADA!)
        with st.expander(f"📖   TBK MADDELERİ   ·   {len(maddeler)}"):
            for m in maddeler:
                st.markdown(f"**Madde {m['madde_no']} — {m['baslik']}** *({m['skor']})*")
                st.markdown(m['icerik'])
                st.markdown("---")

        if kararlar:
            with st.expander(f"⚖   YARGITAY KARARLARI   ·   {len(kararlar)}"):
                for k in kararlar:
                    st.markdown(f"**E. {k['esas_no']} · K. {k['karar_no']}** *{k['tarih']} · {k['skor']}*")
                    st.markdown(k['icerik'])
                    st.markdown("---")
        else:
            st.info("bu soru için yargıtay kararı bulunamadı.")