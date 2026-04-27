from __future__ import annotations

project = "HyperDjango"
author = "HyperDjango contributors"

extensions = [
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

master_doc = "index"

html_theme = "sphinx_rtd_theme"

myst_enable_extensions = [
    "colon_fence",
]
