# Documentation Generation Guide

This guide explains how to generate static documentation for the XPCS Power User Tools project in various formats.

## Prerequisites

Ensure you have the necessary dependencies installed:

```bash
# For MkDocs (HTML)
pip install mkdocs mkdocs-material mkdocstrings mkdocstrings-python

# For Sphinx (HTML/PDF)
pip install sphinx sphinx-rtd-theme myst-parser
```

## Option 1: Generate HTML Documentation with MkDocs

MkDocs is configured to generate a modern, material-design themed documentation website.

### Build the documentation:
```bash
mkdocs build
```

This creates a `site/` directory containing the static HTML files.

### Preview locally:
```bash
mkdocs serve
```
Then open http://127.0.0.1:8000 in your browser.

### Deploy to GitHub Pages:
```bash
mkdocs gh-deploy
```

## Option 2: Generate HTML Documentation with Sphinx

Sphinx provides more traditional documentation with support for multiple output formats.

### Build HTML documentation:
```bash
cd docs
sphinx-build -b html . _build/html
```

The HTML files will be in `docs/_build/html/`.

### Preview the documentation:
```bash
cd docs/_build/html
python -m http.server 8000
```
Then open http://localhost:8000 in your browser.

## Option 3: Generate PDF Documentation

### Method 1: Using LaTeX (Recommended)

1. First, generate LaTeX files:
```bash
cd docs
sphinx-build -b latex . _build/latex
```

2. If you have LaTeX installed (e.g., MacTeX, TeX Live, or MiKTeX):
```bash
cd _build/latex
make
```

This will generate `xpcspowerusertools.pdf`.

### Method 2: Using rst2pdf

1. Install rst2pdf:
```bash
pip install rst2pdf
```

2. Add to your `docs/conf.py`:
```python
extensions.append('rst2pdf.pdfbuilder')

# PDF output options
pdf_documents = [
    ('index', 'xpcs_poweruser_tools', 'XPCS Power User Tools', 'Miaoqi Chu'),
]
```

3. Build PDF:
```bash
cd docs
sphinx-build -b pdf . _build/pdf
```

### Method 3: Using WeasyPrint (Alternative)

If you encounter issues with system dependencies, you can install them:

**On macOS:**
```bash
brew install cairo pango gdk-pixbuf libffi
```

**On Ubuntu/Debian:**
```bash
sudo apt-get install libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev libffi-dev
```

Then generate PDF:
```bash
cd docs
sphinx-build -b simplepdf . _build/pdf
```

## Directory Structure After Building

```
poweruser-xpcs/
├── site/                    # MkDocs HTML output
│   ├── index.html
│   ├── css/
│   ├── js/
│   └── ...
├── docs/
│   ├── _build/
│   │   ├── html/           # Sphinx HTML output
│   │   │   ├── index.html
│   │   │   └── ...
│   │   ├── latex/          # Sphinx LaTeX output
│   │   │   ├── xpcspowerusertools.tex
│   │   │   ├── xpcspowerusertools.pdf  # (after running make)
│   │   │   └── ...
│   │   └── pdf/            # Direct PDF output (if configured)
│   └── ...
```

## Quick Commands Summary

```bash
# MkDocs HTML
mkdocs build              # Build static site
mkdocs serve              # Preview locally
mkdocs gh-deploy          # Deploy to GitHub Pages

# Sphinx HTML
cd docs && sphinx-build -b html . _build/html

# Sphinx PDF (via LaTeX)
cd docs && sphinx-build -b latex . _build/latex
cd _build/latex && make

# Clean build directories
rm -rf site/              # Clean MkDocs output
rm -rf docs/_build/       # Clean Sphinx output
```

## Troubleshooting

1. **Missing dependencies**: Install all required packages as shown in Prerequisites.

2. **LaTeX not found**: Install a LaTeX distribution:
   - macOS: `brew install --cask mactex` or download from https://www.tug.org/mactex/
   - Ubuntu: `sudo apt-get install texlive-full`
   - Windows: Download MiKTeX from https://miktex.org/

3. **WeasyPrint system dependencies**: Follow the installation guide at https://doc.courtbouillon.org/weasyprint/stable/first_steps.html

4. **Sphinx warnings about toctree**: These warnings indicate that some documents aren't included in the main table of contents. They don't affect the build but can be fixed by adding the documents to the appropriate toctree directive in index.md.

## Recommended Approach

For most users, we recommend:
- **For web documentation**: Use MkDocs (Option 1) - it's simpler and produces modern-looking documentation
- **For PDF documentation**: Use Sphinx with LaTeX (Option 3, Method 1) - it produces the highest quality PDFs

Both MkDocs and Sphinx are configured and ready to use in this project!
