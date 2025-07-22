# Documentation Setup for XPCS Power User Tools

This project uses two documentation systems:
1. **MkDocs** with Material theme - for user-facing documentation
2. **Sphinx** - for API documentation generation

## Documentation Structure

```
docs/
├── README.md                    # Documentation readme
├── README_DOCUMENTATION.md      # This file - documentation guide
├── conf.py                      # Sphinx configuration
├── index.md                     # MkDocs homepage
├── convert_legacy_datasets.md   # Module documentation
├── convert_nexus_to_csv.md      # Module documentation
├── xpcs_functions.md            # Module documentation
└── api/                         # API reference documentation
    ├── index.md                 # API overview
    ├── cli.md                   # CLI API reference
    ├── convert_legacy_datasets.md
    ├── convert_nexus_to_csv.md
    └── xpcs_functions.md
```

## Building Documentation

### MkDocs

1. **Install dependencies:**
   ```bash
   pip install -e ".[docs]"
   ```

2. **Build static documentation:**
   ```bash
   mkdocs build
   ```
   This creates a `site/` directory with the static HTML files.

3. **Serve documentation locally (with live reload):**
   ```bash
   mkdocs serve
   ```
   Access at: http://127.0.0.1:8000/

4. **Deploy to GitHub Pages:**
   ```bash
   mkdocs gh-deploy
   ```

### Sphinx

1. **Build HTML documentation:**
   ```bash
   cd docs
   sphinx-build -b html . _build/html
   ```

2. **View Sphinx documentation:**
   Open `docs/_build/html/index.html` in a web browser.

## Configuration Files

- **mkdocs.yml**: MkDocs configuration with Material theme settings
- **docs/conf.py**: Sphinx configuration with autodoc settings
- **pyproject.toml**: Contains documentation dependencies under `[project.optional-dependencies.docs]`

## Features Enabled

### MkDocs Features:
- Material theme with dark/light mode toggle
- Navigation tabs and sections
- Code syntax highlighting with copy button
- Search functionality
- API documentation with mkdocstrings
- Automatic docstring extraction from Python code

### Sphinx Features:
- Autodoc for automatic API documentation
- Napoleon for Google/NumPy style docstrings
- MyST parser for Markdown support
- Intersphinx for cross-references to external documentation

## Adding New Documentation

1. **Add a new module documentation:**
   - Create `docs/module_name.md`
   - Create `docs/api/module_name.md` for API reference
   - Update `mkdocs.yml` navigation section

2. **Update existing documentation:**
   - Edit the relevant `.md` files
   - MkDocs will auto-reload if serving locally

## Best Practices

1. Keep module documentation in `docs/` focused on usage and examples
2. Keep API documentation in `docs/api/` focused on technical reference
3. Use docstrings in Python code - they're automatically extracted
4. Include code examples in documentation
5. Update documentation when adding new features or changing APIs

## Troubleshooting

- If mkdocstrings can't find modules, ensure the package is installed in editable mode: `pip install -e .`
- If Sphinx autodoc fails, check that `sys.path` in `conf.py` correctly points to the source directory
- For missing dependencies, reinstall with: `pip install -e ".[docs]"`
