# Noteify - AI Study Assistant

An AI powered tool that reads your GoodNotes PDFs and helps you study by:
- Answering questions about your notes
- Generating quizzes
- Creating practice problems with solutions

## Features

- **Smart File Tracking**: Only processes new or updated files to save on API costs by cacheing processed files
- **Handwriting Recognition**: Uses GPT-4o Vision to read handwritten notes
- **Math Support**: Understands mathematical notation and solved problems
- **Search by Filename**: Find files by topic (e.g., "quiz 4", "chapter 3")
- **Interactive Study Tools**:
  - Ask questions about your notes
  - Generate custom quizzes
  - Create practice problems with solutions

## Setup

### 1. Install Dependencies

First, install Python packages:
```bash
pip install -r requirements.txt
```

### 2. Install Poppler (Required for PDF processing)

**macOS:**
```bash
brew install poppler
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install poppler-utils
```

**Windows:**
Download from: https://github.com/oschwartz10612/poppler-windows/releases/

### 3. Configure API Key

Create a file named `api.env` in the project directory with your OpenAI API key:
```
API_KEY=your_openai_api_key_here
```

### 4. Verify Notes Path

The default path for GoodNotes is set to:
```
~/Library/CloudStorage/GoogleDrive-EMAIL_HERE/My Drive/GoodNotes
```

If your notes folder is in a different location, edit `FOLDER_PATH` in `fileData.py`.

## Usage

Run the program:
```bash
python3 chat.py
```

## How It Works

1. **Get All PDFs**: Scans your notes files for all PDF files
2. **Intelligent File Selection**: GPT analyzes each file name and selects pdf based on relevancy to input
3. **Content Caching**: Checks cache first before going to GPT for image processing
4. **GPT-4o Vision**: Converts pdf pages to images and reads text including handwriting
5. **Intelligent Filtering**: GPT reads inital query and filters output based on requirements. Eg. Asking for hints
6. **Targeted Response**: Generates quizzes, study material, practice problems, etc. based on request
7. **Free Subsequent Access**: After inital processing, all cached content can be accessed without api call

## Cost Optimization

- **Content Caching**: Extracted content gets saved locally, allowing for free access on subsequent queries
- **Smart Updates**: Only re-processes pdfs if they have been modified since last time
- **Page Limits**: Limited to first 10 pages of each pdf, keeping price in mind. Can be changed in code
- **Cost-Effective Model**: Uses GPT-4o, intial processing is a couple cents, almost free to access cached files

## Output

Responses can be saved. If saved, they are outputted in both html and markdown files

- **HTML Output**: Opens in browser for readable math equations
- **Markdown Output**: Compatible with Obsidian, Notion, and other markdown editors
- **LaTeX Support**: Renders math formatted text properly

After each response, you'll be asked if you want to save it. Files are saved to the `outputs/` folder.

## Files

- `chat.py` - Main program with GPT integration and input / output
- `fileData.py` - File scanning, change tracking, and caching
- `api.env` - Your OpenAI API key (create this)
- `state.json` - Tracks processed files (auto-generated)
- `content_cache/` - Stores extracted PDF content (auto-generated)
- `outputs/` - Saved responses with rendered math (auto-generated)
- `requirements.txt` - Python dependencies
- `.gitignore` - Protects sensitive data from version control

## Troubleshooting

**"GoodNotes folder not found"**: Update `FOLDER_PATH` in `fileData.py`

**"Unable to get page count"**: Install poppler (see Setup step 2)

**Want to reprocess a file?**: Delete its cache file from `content_cache/` directory, or delete entire `content_cache/` folder to reprocess everything

**High API costs**: Reduce `max_pages` in `pdf_to_base64_images()` function

