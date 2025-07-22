# Documentation for XPCS Power User Tools

This directory contains the documentation for the XPCS Power User Tools package.

## Structure

- `index.md` - Main documentation page
- `convert_legacy_datasets.md` - Documentation for the legacy dataset conversion module
- `convert_nexus_to_csv.md` - Documentation for HDF5 to CSV conversion (to be added)
- `xpcs_functions.md` - Documentation for core XPCS functions (to be added)

## Building Documentation

To build HTML documentation from these Markdown files, you can use various tools:

### Using MkDocs

1. Install MkDocs:
   ```bash
   pip install mkdocs mkdocs-material
   ```

2. Create `mkdocs.yml` in the project root (see example below)

3. Build the documentation:
   ```bash
   mkdocs build
   ```

4. Serve locally for preview:
   ```bash
   mkdocs serve
   ```

### Using Sphinx

1. Install Sphinx with MyST parser:
   ```bash
   pip install sphinx myst-parser sphinx-rtd-theme
   ```

2. Configure Sphinx to use Markdown files

3. Build the documentation:
   ```bash
   sphinx-build -b html docs docs/_build
   ```

## Contributing

When adding new modules or features:

1. Create a new `.md` file for the module
2. Add a link to it in `index.md`
3. Follow the existing documentation structure
4. Include:
   - Overview and purpose
   - Installation/setup if needed
   - API reference with parameters
   - Usage examples
   - Troubleshooting section
