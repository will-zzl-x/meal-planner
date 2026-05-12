"""Cross-view navigation registry.

`st.page_link` needs an `st.Page` object, but those are built in `app.py`.
This module gives views a one-line way to grab the Page they want to link
to without an awkward import chain back into `app`.

`app.py` calls `set_pages(...)` each rerun before invoking the active page;
views call `page("plan")` (or any registered key) when they want a
navigation button or link.
"""
from __future__ import annotations

from typing import Dict, Optional

import streamlit as st

_PAGES: Dict[str, "st.Page"] = {}


def set_pages(pages: Dict[str, "st.Page"]) -> None:
    """Register the current rerun's Page objects under stable string keys."""
    _PAGES.clear()
    _PAGES.update(pages)


def page(key: str) -> Optional["st.Page"]:
    """Look up a registered Page by key. Returns None if the user isn't
    in the authenticated shell (e.g. on the login screen)."""
    return _PAGES.get(key)
