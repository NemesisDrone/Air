# Export path to the root of the project
import os
import sys

sys.path.insert(0, os.path.abspath('../..'))

autodoc_member_order = 'bysource'

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Nemesis Air'
copyright = '2023, Nemesis Team'
author = 'Nemesis Team'
release = '0.0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx_markdown_tables',
    'myst_parser',
    'sphinx.ext.autodoc',
]

templates_path = ['_templates']
exclude_patterns = []

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown'
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'logo_only': True,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': True,
    # Toc options
    'collapse_navigation': False,
    'sticky_navigation': False,
    'navigation_depth': 3,
    'includehidden': True,
    'titles_only': False
}
html_title = "Shaft doc"
html_logo = "logo.png"
html_favicon = "logo.png"

html_static_path = ['_static']
