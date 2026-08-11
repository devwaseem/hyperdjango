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

# Alpine's valid shorthand attributes (for example ``@click``) are not accepted by
# Pygments' strict HTML lexer. Sphinx retries them in relaxed mode and renders the
# blocks correctly, so do not turn that lexer limitation into a release failure.
suppress_warnings = ["misc.highlighting_failure"]
