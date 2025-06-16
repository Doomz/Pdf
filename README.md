# PDF Viewer

This project provides a synchronized side-by-side PDF viewer built with Tkinter.

## Features
- Drag-and-drop file loading for the left and right panes
- Synchronized zoom and page navigation
- Manual highlights with color selection and erasing
- Compare numbers with green/magenta highlight overlay
- Insert blank pages into either pane
- Export both panes as a side-by-side PDF
- Page number display in `current / total` format
- Save and load annotations (JSON)
- Sync checkbox to enable or disable page synchronization

## Requirements
- Python 3.x
- `tkinter` (usually included with standard Python)
- `Pillow`
- `PyMuPDF`

Install the Python dependencies using:

```bash
pip install pillow pymupdf
```

## Running

Run the viewer with:

```bash
python pdf_viewer.py
```

Use the toolbar buttons or drag-and-drop to load PDFs. Zoom, navigation, highlighting and other features are available through the interface.
