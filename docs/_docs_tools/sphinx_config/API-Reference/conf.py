# Configuration file for the Sphinx documentation builder.

import tomllib  # Python 3.11+; for 3.10 use `tomli`
import os
import sys
from pathlib import Path

# Add your source directory to sys.path for autodoc
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# --------------------------------------------------
# Load project metadata from pyproject.toml
# --------------------------------------------------

with open(project_root / "pyproject.toml", "rb") as f:
    pyproject = tomllib.load(f)

meta = pyproject.get("project") or pyproject.get("tool", {}).get("poetry", {})

project = meta.get("name", "ProjectTemplate")
authors = meta.get("authors", [])
if isinstance(authors[0], dict):
    authors = [item["name"] for item in authors]
print(authors)
author = (
    ", ".join(authors)
    if isinstance(meta.get("authors"), list)
    else meta.get("author", "Unknown")
)
release = meta.get("version", "0.0.0")

# --------------------------------------------------
# General configuration
# --------------------------------------------------
extensions = [
    "myst_parser",  # Markdown support
    "sphinx.ext.autodoc",  # API docs from docstrings
    "sphinx.ext.napoleon",  # Google/NumPy style docstrings
    "sphinx.ext.viewcode",  # Link to highlighted source code
]

# Allow both .rst and .md as source files
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# The master toctree document (can be index.md)
master_doc = "README"

# --------------------------------------------------
# HTML output
# --------------------------------------------------
html_theme = "furo"

# Custom static files (CSS, JS) — optional
html_static_path = ["_static"]

# Example: add a custom CSS file
# html_css_files = ["custom.css"]
