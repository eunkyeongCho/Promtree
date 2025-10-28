# PromTree

PromTree is a Python library for converting PDF documents to Markdown format. It uses OCR and layout detection to accurately preserve document structure and formatting.

## Features

- Convert PDF documents to Markdown with preserved formatting
- Automatic layout detection using Surya OCR
- Support for text, images, and section headers
- Command-line interface and Python API
- Optional cleanup of intermediate files

## Requirements

- Python 3.12.10
- PyMuPDF 1.26.5
- Surya OCR 0.17.0
- PyTorch 2.9.0
- Transformers 4.57.1
- Additional dependencies listed in `requirements.txt`

Note: First run will download Surya OCR models from Hugging Face (approximately 1-2GB). An internet connection is required for initial setup.

## Installation

### Install from PyPI

```bash
pip install promtree
```

### Install from source

```bash
git clone https://github.com/Team-PromTree/promtree.git
cd promtree
pip install -e .
```

### Install dependencies only

```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

Basic conversion:

```bash
promtree path/to/document.pdf
```

Specify output file:

```bash
promtree path/to/document.pdf --output-md output.md
```

Enable cleanup mode (removes intermediate files):

```bash
promtree path/to/document.pdf --cleanup
```

### Python API

```python
from promtree import PromTree

# Basic conversion
PromTree(pdf_path="document.pdf")

# With custom output path
PromTree(pdf_path="document.pdf", output_md="output.md")

# With cleanup enabled
PromTree(pdf_path="document.pdf", cleanup=True)
```

## How It Works

PromTree processes PDF documents through a four-stage pipeline:

1. **PDF to PNG Conversion**: Converts each PDF page to high-resolution images
2. **Text Extraction**: Extracts text elements and images with bounding box coordinates
3. **Layout Detection**: Analyzes page layout using Surya OCR to identify sections and structure
4. **Markdown Assembly**: Combines extracted text with layout information to generate formatted Markdown

## Output Structure

For a PDF file named `document.pdf`, PromTree generates:

```
document/
|-- images/           # Extracted images from PDF
|-- layouts/          # Layout detection results
|   |-- results.json
|   |-- *_layout.png  # Annotated images showing detected regions
|-- outputs/          # PNG images of each page
|-- output.md         # 최종 결과물
|-- output.txt        # Intermediate text extraction results
```

Final Markdown output: `output.md` (or custom path specified with `--output-md`)

Use `--cleanup` flag to automatically remove intermediate directories after conversion.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Repository

https://github.com/Team-PromTree/promtree

## Authors

Team.PromTree (effort-result@naver.com)
