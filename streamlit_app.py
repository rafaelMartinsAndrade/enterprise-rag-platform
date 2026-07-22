import os
from pathlib import Path

import httpx
import streamlit as st


API_BASE_URL = os.getenv("STREAMLIT_API_BASE_URL", "http://localhost:8000/api/v1").rstrip("/")
DEFAULT_TOKEN = os.getenv("API_TOKEN", "change-me")
DEMO_FILES = {
    "ACME Closing Policy": Path("demo_data/documents/acme-erp/closing_policy.md"),
    "ACME Support Playbook": Path("demo_data/documents/acme-erp/support_playbook.txt"),
    "Northwind Billing Handbook": Path("demo_data/documents/northwind-finance/billing_handbook.md"),
}
DEMO_USERS = {
    "acme-erp": "ana@acme.demo",
    "northwind-finance": "bruno@northwind.demo",
}


st.set_page_config(page_title="Enterprise RAG Platform", page_icon="🧠", layout="wide")
st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(250, 204, 21, 0.20), transparent 35%),
            radial-gradient(circle at top right, rgba(14, 165, 233, 0.18), transparent 32%),
            linear-gradient(180deg, #f8fafc 0%, #fff7ed 100%);
        color: #172554;
        font-family: "Aptos", "Trebuchet MS", sans-serif;
    }
    .hero {
        padding: 1.4rem 1.6rem;
        border-radius: 24px;
        background: linear-gradient(135deg, rgba(15,23,42,0.94), rgba(30,41,59,0.86));
        color: #f8fafc;
        box-shadow: 0 22px 60px rgba(15, 23, 42, 0.18);
        margin-bottom: 1rem;
    }
    .hero h1 {
        margin: 0;
        font-size: 2.2rem;
        letter-spacing: -0.04em;
    }
    .hero p {
        margin: 0.7rem 0 0;
        color: #dbeafe;
        font-size: 1rem;
    }
    .card {
        background: rgba(255,255,255,0.82);
        border: 1px solid rgba(148,163,184,0.22);
        border-radius: 20px;
        padding: 1rem 1.1rem;
        box-shadow: 0 10px 35px rgba(15, 23, 42, 0.08);
    }
    </style>
    <div class="hero">
        <h1>Enterprise RAG Platform</h1>
        <p>Multi-tenant document ingestion, pgvector retrieval, grounded answers, citation-first UX.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def build_headers(organization_slug: str, user_email: str, token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-Slug": organization_slug,
        "X-User-Email": user_email,
    }


def api_get(path: str, *, headers: dict[str, str]) -> httpx.Response:
    with httpx.Client(timeout=30.0) as client:
        return client.get(f"{API_BASE_URL}{path}", headers=headers)


def api_post(path: str, *, headers: dict[str, str], **kwargs) -> httpx.Response:
    with httpx.Client(timeout=60.0) as client:
        return client.post(f"{API_BASE_URL}{path}", headers=headers, **kwargs)


def seed_demo_file(document_label: str, organization_slug: str, user_email: str, token: str) -> tuple[bool, str]:
    file_path = DEMO_FILES[document_label]
    headers = build_headers(organization_slug, user_email, token)
    with file_path.open("rb") as file_handle:
        response = api_post(
            "/documents/upload",
            headers=headers,
            data={"title": file_path.stem.replace("_", " ").title(), "tags": "demo,seeded"},
            files={"file": (file_path.name, file_handle, _guess_mime(file_path))},
        )
    if response.is_success:
        payload = response.json()
        return True, f"queued document {payload['document_id']} task {payload['task_id']}"
    return False, response.text


def list_documents(organization_slug: str, user_email: str, token: str) -> list[dict]:
    headers = build_headers(organization_slug, user_email, token)
    response = api_get("/documents", headers=headers)
    response.raise_for_status()
    return response.json()


def ask_question(organization_slug: str, user_email: str, token: str, question: str) -> dict:
    headers = build_headers(organization_slug, user_email, token)
    response = api_post(
        "/chat/ask",
        headers=headers,
        json={"question": question, "retrieval_mode": "hybrid", "top_k": 5},
    )
    response.raise_for_status()
    return response.json()


def _guess_mime(path: Path) -> str:
    return {
        ".md": "text/markdown",
        ".txt": "text/plain",
    }.get(path.suffix.lower(), "text/plain")


with st.sidebar:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    organization_slug = st.selectbox("Tenant", ["acme-erp", "northwind-finance"])
    default_user = DEMO_USERS[organization_slug]
    user_email = st.text_input("User email", value=default_user)
    api_token = st.text_input("API token", value=DEFAULT_TOKEN, type="password")
    st.caption(f"API base: {API_BASE_URL}")
    st.markdown("</div>", unsafe_allow_html=True)


left, right = st.columns([1.1, 1.3], gap="large")

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Seed or Upload")
    selected_demo = st.selectbox("Demo document", list(DEMO_FILES))
    if st.button("Upload demo file", use_container_width=True):
        ok, detail = seed_demo_file(selected_demo, organization_slug, user_email, api_token)
        if ok:
            st.success(detail)
        else:
            st.error(detail)

    st.divider()
    st.subheader("Tenant documents")
    if st.button("Refresh documents", use_container_width=True):
        st.session_state["documents"] = list_documents(organization_slug, user_email, api_token)
    for document in st.session_state.get("documents", []):
        st.markdown(
            f"**{document['title']}**  \nstatus: `{document['status']}`  \nversion: `{document['current_version_number']}`"
        )
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Grounded chat")
    default_question = "Who approves refunds above 1000 BRL?" if organization_slug == "acme-erp" else "What is the invoice prefix?"
    question = st.text_area("Question", value=default_question, height=120)
    if st.button("Ask knowledge base", use_container_width=True):
        answer = ask_question(organization_slug, user_email, api_token, question)
        st.session_state["last_answer"] = answer

    answer = st.session_state.get("last_answer")
    if answer:
        assistant = answer["assistant_message"]
        st.markdown("### Answer")
        st.write(assistant["content"])
        if assistant["citations"]:
            st.markdown("### Citations")
            for citation in assistant["citations"]:
                st.markdown(
                    f"- **{citation['document_title']}**"
                    f" | score `{citation['score']}`"
                    f" | page `{citation['page_number']}`"
                    f" | {citation['excerpt']}"
                )
        else:
            st.info("No evidence found.")
    st.markdown("</div>", unsafe_allow_html=True)
