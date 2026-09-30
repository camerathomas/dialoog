import streamlit as st
import requests
import time
from datetime import datetime

# ============================================================
# Configuratie
# ============================================================
OLLAMA_URL = "http://localhost:11434/api/chat"
TAGS_URL = "http://localhost:11434/api/tags"

st.set_page_config(
    page_title="Qwen ↔ Llama Dialoog",
    page_icon="🤖",
    layout="wide"
)

# ============================================================
# Ollama helpers
# ============================================================
def get_beschikbare_modellen():
    """Haalt de lijst met lokale Ollama-modellen op."""
    try:
        r = requests.get(TAGS_URL, timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []

def chat(model, messages, system_prompt=None, temperature=0.8, timeout=180):
    """Stuurt een chatverzoek naar Ollama."""
    msgs = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    msgs.extend(messages)

    payload = {
        "model": model,
        "messages": msgs,
        "stream": False,
        "options": {"temperature": temperature}
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()["message"]["content"]
    except requests.exceptions.ConnectionError:
        return "⚠️ Kan geen verbinding maken met Ollama. Draait `ollama serve`?"
    except Exception as e:
        return f"⚠️ Fout: {e}"

# ============================================================
# Sidebar – instellingen
# ============================================================
st.sidebar.title("⚙️ Instellingen")

beschikbare_modellen = get_beschikbare_modellen()

if not beschikbare_modellen:
    st.sidebar.error("Geen modellen gevonden. Draait Ollama?")
    st.error(
        "**Ollama is niet bereikbaar.**\n\n"
        "Start Ollama in een terminal met:\n\n"
        "```\nollama serve\n```\n\n"
        "En herlaad deze pagina."
    )
    st.stop()

# Standaardmodellen kiezen (Qwen en Llama als ze er zijn)
default_a = next((m for m in beschikbare_modellen if "qwen" in m.lower()), beschikbare_modellen[0])
default_b = next((m for m in beschikbare_modellen if "llama" in m.lower()), beschikbare_modellen[-1])

model_a = st.sidebar.selectbox(
    "🅰️ Model A",
    beschikbare_modellen,
    index=beschikbare_modellen.index(default_a)
)
model_b = st.sidebar.selectbox(
    "🅱️ Model B",
    beschikbare_modellen,
    index=beschikbare_modellen.index(default_b)
)

st.sidebar.markdown("---")
st.sidebar.subheader("🎭 Rollen")

prompt_a = st.sidebar.text_area(
    "System prompt A",
    value="Jij bent een nieuwsgierige filosoof. Je stelt diepe vragen, daagt aannames uit en denkt graag buiten de gebaande paden. Houd je antwoorden kort (max 3 zinnen) en eindig altijd met een vraag.",
    height=120
)
prompt_b = st.sidebar.text_area(
    "System prompt B",
    value="Jij bent een nuchtere wetenschapper. Je baseert je op feiten, logica en empirisch bewijs. Je relativeert graag. Houd je antwoorden kort (max 3 zinnen) en reageer direct op de vraag.",
    height=120
)

st.sidebar.markdown("---")
st.sidebar.subheader("🔧 Parameters")

rondes = st.sidebar.slider("Aantal rondes", 1, 10, 3)
temperature = st.sidebar.slider("Temperature", 0.0, 1.5, 0.8, 0.1)
pauze = st.sidebar.slider("Pauze tussen berichten (sec)", 0.0, 5.0, 1.0, 0.5)

# ============================================================
# Hoofdinterface
# ============================================================
st.title("🤖 Qwen ↔ Llama Dialoog")
st.caption(f"Twee lokale modellen in gesprek via Ollama · {model_a} vs {model_b}")

start_bericht = st.text_area(
    "🎬 Startvraag / stelling",
    value="Is bewustzijn iets wat je kunt programmeren in een AI, of is het fundamenteel anders dan wat wij als machines kunnen bouwen?",
    height=80
)

col1, col2 = st.columns([1, 1])
with col1:
    start_btn = st.button("▶️ Start dialoog", type="primary", use_container_width=True)
with col2:
    stop_btn = st.button("⏹️ Stop", use_container_width=True)

# Placeholders
status = st.empty()
gesprek_container = st.container()

# ============================================================
# Dialoog uitvoeren
# ============================================================
def render_bericht(naam, tekst, kleur, icoon, tijd):
    with gesprek_container:
        with st.chat_message(naam, avatar=icoon):
            st.markdown(f"**{naam}** · _{tijd}_")
            st.markdown(tekst)
            st.markdown(
                f"<div style='height:4px;background:{kleur};border-radius:2px;margin-top:8px'></div>",
                unsafe_allow_html=True
            )

if start_btn:
    if not start_bericht.strip():
        st.warning("Vul eerst een startvraag in.")
        st.stop()

    # Reset state
    st.session_state["stop"] = False
    geschiedenis_a = [{"role": "user", "content": start_bericht}]

    with gesprek_container:
        with st.chat_message("user", avatar="🎬"):
            st.markdown(f"**Startvraag** · _{datetime.now().strftime('%H:%M:%S')}_")
            st.markdown(start_bericht)

    vorige_boodschap = start_bericht

    for ronde in range(1, rondes + 1):
        if st.session_state.get("stop", False):
            status.warning("⏹️ Gestopt door gebruiker.")
            break

        # --- Model A ---
        status.info(f"🔄 Ronde {ronde}/{rondes} · **{model_a}** denkt na...")
        antwoord_a = chat(model_a, geschiedenis_a, prompt_a, temperature)
        tijd = datetime.now().strftime("%H:%M:%S")
        render_bericht(f"{model_a} (A)", antwoord_a, "#4A90E2", "🅰️", tijd)

        geschiedenis_a.append({"role": "assistant", "content": antwoord_a})
        vorige_boodschap = antwoord_a

        if pauze:
            time.sleep(pauze)
        if st.session_state.get("stop", False):
            status.warning("⏹️ Gestopt door gebruiker.")
            break

        # --- Model B ---
        status.info(f"🔄 Ronde {ronde}/{rondes} · **{model_b}** denkt na...")
        antwoord_b = chat(
            model_b,
            [{"role": "user", "content": vorige_boodschap}],
            prompt_b,
            temperature
        )
        tijd = datetime.now().strftime("%H:%M:%S")
        render_bericht(f"{model_b} (B)", antwoord_b, "#E27D4A", "🅱️", tijd)

        geschiedenis_a.append({"role": "user", "content": antwoord_b})

        if pauze:
            time.sleep(pauze)

    status.success("✅ Dialoog afgerond.")

    # Download-knop voor transcript
    transcript = "\n\n".join(
        f"[{m['role']}]\n{m['content']}" for m in geschiedenis_a
    )
    st.download_button(
        "💾 Download transcript",
        data=transcript,
        file_name=f"dialoog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain"
    )

# Stop-knop logica (zet een vlag)
if stop_btn:
    st.session_state["stop"] = True
    st.warning("Stop-signaal verzonden. De huidige ronde wordt nog afgemaakt.")
