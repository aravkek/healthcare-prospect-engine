"""
MedPort Wiki — internal knowledge base.
Access: all authenticated users can read. Admins can create and edit pages.
"""

import os
import sys
from datetime import datetime, timezone

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.styles import inject_css, MEDPORT_TEAL, MEDPORT_DARK, MEDPORT_BLUE, DEPT_COLORS, DEPT_LABELS, page_header
from lib.auth import check_auth, is_admin, get_department, render_logout_button
from lib.db import get_wiki_pages, create_wiki_page, update_wiki_page, log_activity

st.set_page_config(
    page_title="Wiki — MedPort",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

name, email = check_auth()
admin = is_admin(email)
dept = get_department(email)

# ─── Constants ────────────────────────────────────────────────────────────────

CATEGORY_OPTIONS = {
    "all":         "All",
    "sop":         "SOPs",
    "playbook":    "Playbooks",
    "onboarding":  "Onboarding",
    "resources":   "Resources",
    "general":     "General",
}

CATEGORY_COLORS = {
    "sop":        ("#eff6ff", "#2563eb"),
    "playbook":   ("#f5f3ff", "#7c3aed"),
    "onboarding": ("#f0fdf9", "#059669"),
    "resources":  ("#fffbeb", "#d97706"),
    "general":    ("#f8fafc", "#64748b"),
}


def _category_badge(category: str) -> str:
    label = CATEGORY_OPTIONS.get(category, category.title())
    bg, fg = CATEGORY_COLORS.get(category, ("#f8fafc", "#64748b"))
    return (
        f'<span style="background:{bg};color:{fg};border-radius:999px;'
        f'font-size:0.75rem;font-weight:700;padding:2px 10px;display:inline-block;">'
        f'{label}</span>'
    )


def _dept_badge(department: str) -> str:
    label = DEPT_LABELS.get(department, department.title())
    return f'<span class="dept-badge dept-{department}">{label}</span>'


def _format_date(ts_str: str) -> str:
    if not ts_str:
        return ""
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return ts.strftime("%b %d, %Y")
    except Exception:
        return ts_str


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f'<span style="font-size:1.1rem;font-weight:800;color:{MEDPORT_TEAL};">MedPort</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:0.8rem;color:#94a3b8;'>Signed in as <b>{name}</b></div>",
        unsafe_allow_html=True,
    )
    st.markdown(_dept_badge(dept), unsafe_allow_html=True)
    st.markdown("---")
    render_logout_button()
    st.markdown("---")

    st.markdown(
        "<div style='font-size:0.75rem;color:#64748b;font-weight:600;text-transform:uppercase;"
        "letter-spacing:0.06em;margin-bottom:0.5rem;'>Category</div>",
        unsafe_allow_html=True,
    )
    selected_category = st.radio(
        "Category",
        options=list(CATEGORY_OPTIONS.keys()),
        format_func=lambda k: CATEGORY_OPTIONS[k],
        key="wiki_category_filter",
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("<div style='font-size:0.75rem;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;'>Navigation</div>", unsafe_allow_html=True)
    st.page_link("medport_dashboard.py", label="Home", icon="🏠")
    st.page_link("pages/1_Team_Hub.py", label="Team Hub", icon="👥")
    st.page_link("pages/3_Tasks.py", label="Tasks", icon="✅")
    st.page_link("pages/6_Settings.py", label="Settings", icon="⚙️")

# ─── Load pages ───────────────────────────────────────────────────────────────

category_filter = None if selected_category == "all" else selected_category
all_pages = get_wiki_pages(category=category_filter)

# ─── Page header + new page button ───────────────────────────────────────────

st.markdown(page_header("Wiki", "Internal knowledge base — SOPs, playbooks, and resources"), unsafe_allow_html=True)

if admin:
    with st.expander("Create New Page", expanded=False):
        wiki_new_title = st.text_input(
            "Title *",
            max_chars=200,
            key="wiki_new_title",
            placeholder="Page title...",
        )
        wiki_new_category = st.selectbox(
            "Category",
            options=["general", "sop", "playbook", "onboarding", "resources"],
            key="wiki_new_category",
            format_func=lambda k: CATEGORY_OPTIONS.get(k, k.title()),
        )
        wiki_new_content = st.text_area(
            "Content",
            height=400,
            max_chars=20000,
            key="wiki_new_content",
            placeholder="Write in Markdown...",
        )
        wiki_preview_on = st.toggle("Preview", value=False, key="wiki_new_preview")
        if wiki_preview_on and wiki_new_content.strip():
            st.markdown("---")
            st.markdown(wiki_new_content)
            st.markdown("---")

        if st.button("Create Page", type="primary", key="wiki_create_btn"):
            title_clean = wiki_new_title.strip()
            content_clean = wiki_new_content.strip()
            if not title_clean:
                st.error("Title is required.")
            elif not content_clean:
                st.error("Content is required.")
            else:
                payload = {
                    "title": title_clean,
                    "category": wiki_new_category,
                    "content": content_clean,
                    "author_name": name,
                    "author_email": email.lower(),
                }
                new_id = create_wiki_page(payload)
                if new_id:
                    log_activity(
                        actor_email=email,
                        actor_name=name,
                        action_type="wiki_page_created",
                        entity_type="wiki_page",
                        entity_id=str(new_id),
                        entity_name=title_clean,
                        details={"category": wiki_new_category},
                    )
                    st.success(f"Page created: {title_clean}")
                    st.rerun()
                else:
                    st.error("Failed to create page. Check Supabase connection.")

    st.markdown("<br>", unsafe_allow_html=True)

# ─── Two-column layout ───────────────────────────────────────────────────────

col_list, col_content = st.columns([1, 2])

# ─── Left column: page list ───────────────────────────────────────────────────

with col_list:
    wiki_search = st.text_input(
        "Search wiki...",
        key="wiki_search",
        placeholder="Search by title...",
    )

    # Filter by search query
    search_query = wiki_search.strip().lower()
    if search_query:
        display_pages = [p for p in all_pages if search_query in (p.get("title") or "").lower()]
    else:
        display_pages = all_pages

    if not display_pages:
        st.markdown(
            '<div style="color:#8a9ab0;font-size:0.875rem;padding:0.75rem 0;">No pages found.</div>',
            unsafe_allow_html=True,
        )
    else:
        for page in display_pages:
            page_id = str(page.get("id", ""))
            page_title = page.get("title", "Untitled")
            page_category = page.get("category", "general")
            updated_at = _format_date(page.get("updated_at") or page.get("created_at", ""))
            page_author = page.get("author_name", "")

            is_selected = st.session_state.get("wiki_selected_id") == page_id

            border_color = MEDPORT_TEAL if is_selected else "#e2e8f0"
            bg_color = "#f0fdf9" if is_selected else "#ffffff"
            cat_badge = _category_badge(page_category)

            st.markdown(
                f"""
                <div class="wiki-card" style="border-color:{border_color};background:{bg_color};">
                  <div class="wiki-title">{page_title}</div>
                  <div class="wiki-meta">
                    {cat_badge}
                    <span style="margin-left:0.4rem;">{updated_at}</span>
                    {"&nbsp;&middot;&nbsp;" + page_author if page_author else ""}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Open", key=f"wiki_select_{page_id}", use_container_width=True):
                st.session_state["wiki_selected_id"] = page_id
                st.rerun()

# ─── Right column: page content ──────────────────────────────────────────────

with col_content:
    selected_id = st.session_state.get("wiki_selected_id")

    if not selected_id:
        st.markdown(
            """
            <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:16px;
              padding:3rem 2rem;text-align:center;margin-top:1rem;">
              <div style="font-size:2rem;margin-bottom:0.75rem;">📖</div>
              <div style="font-size:1rem;font-weight:600;color:#334155;font-family:'Plus Jakarta Sans',sans-serif;">
                Select a page from the left to start reading.
              </div>
              <div style="font-size:0.875rem;color:#94a3b8;margin-top:0.4rem;">
                Use the search box or browse by category.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Find the selected page in the full (unfiltered) list
        all_pages_full = get_wiki_pages(category=None)
        selected_page = next((p for p in all_pages_full if str(p.get("id", "")) == selected_id), None)

        if selected_page is None:
            st.warning("Page not found. It may have been deleted.")
            st.session_state.pop("wiki_selected_id", None)
        else:
            page_title = selected_page.get("title", "Untitled")
            page_category = selected_page.get("category", "general")
            page_content = selected_page.get("content", "")
            page_author = selected_page.get("author_name", "")
            updated_at_raw = selected_page.get("updated_at") or selected_page.get("created_at", "")
            updated_at_str = _format_date(updated_at_raw)
            cat_badge = _category_badge(page_category)

            # Title and meta
            st.markdown(f"## {page_title}")
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:0.6rem;flex-wrap:wrap;margin-bottom:1rem;">
                  {cat_badge}
                  <span style="font-size:0.8125rem;color:#64748b;">
                    Last updated by <b>{page_author or "Unknown"}</b> on {updated_at_str}
                  </span>
                </div>
                <hr style="border:none;border-top:1px solid #e2e8f0;margin-bottom:1rem;">
                """,
                unsafe_allow_html=True,
            )

            # Page body
            st.markdown(page_content)

            # Edit expander (admin only)
            if admin:
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("Edit Page", expanded=False):
                    wiki_edit_content = st.text_area(
                        "Content",
                        value=page_content,
                        height=400,
                        max_chars=20000,
                        key=f"wiki_edit_content_{selected_id}",
                    )
                    wiki_edit_preview = st.toggle("Preview edits", value=False, key=f"wiki_edit_preview_{selected_id}")
                    if wiki_edit_preview and wiki_edit_content.strip():
                        st.markdown("---")
                        st.markdown(wiki_edit_content)
                        st.markdown("---")

                    if st.button("Save Changes", type="primary", key=f"wiki_save_{selected_id}"):
                        content_clean = wiki_edit_content.strip()
                        if not content_clean:
                            st.error("Content cannot be empty.")
                        else:
                            ok = update_wiki_page(selected_id, {"content": content_clean})
                            if ok:
                                log_activity(
                                    actor_email=email,
                                    actor_name=name,
                                    action_type="wiki_page_updated",
                                    entity_type="wiki_page",
                                    entity_id=selected_id,
                                    entity_name=page_title,
                                )
                                st.success("Page saved.")
                                st.rerun()
                            else:
                                st.error("Failed to save. Check Supabase connection.")
