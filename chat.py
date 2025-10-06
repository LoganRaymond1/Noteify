from openai import OpenAI
import fileData
from dotenv import load_dotenv
import os
import base64
from pdf2image import convert_from_path
from pathlib import Path
import json
import re
from io import BytesIO


# Load environment variables
load_dotenv("api.env")
api_key = os.getenv("API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)


def pdf_to_base64_images(pdf_path, max_pages=10):
    # convert pdf to base64 images for gpt to process
    try:
        images = convert_from_path(pdf_path, dpi=200)
        
        if not images:
            print(f"  WARNING: No images extracted from {pdf_path}")
            return []
        
        print(f"  Extracted {len(images)} page(s), processing first {min(len(images), max_pages)}...")
        
        # debug folder to ensure images are being processed correctly
        debug_dir = Path(__file__).parent / "debug_images"
        debug_dir.mkdir(exist_ok=True)
        
        base64_images = []
        # save images to debug folder
        for i, image in enumerate(images[:max_pages]):
            debug_path = debug_dir / f"page_{i+1}.png"
            image.save(debug_path)
            print(f"  Page {i+1}: saved to {debug_path} (size: {image.size})")
            
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            base64_images.append(img_str)
            print(f"  Page {i+1}: {len(img_str)} chars in base64")
        
        return base64_images
    except Exception as e:
        print(f"Error converting PDF {pdf_path}: {e}")
        return []


# read each image with gpt and extract content
def read_pdf_with_gpt(pdf_path):
    print(f"Processing {pdf_path.name}...")
    
    base64_images = pdf_to_base64_images(pdf_path)
    
    if not base64_images:
        return None
    
    # prompt for saving image text to cache
    content = [
        {
            "type": "text",
            "text": """These are my personal study notes containing practice problems. Please extract:

1. Every problem/question exactly as written, preserving all mathematical notation
2. The TYPE of each problem (proof, computation, true/false, etc.)
3. Key concepts and theorems referenced
4. The difficulty level demonstrated by each problem

Format each problem clearly. Include the full problem statement but do NOT include solutions or answers - I want to practice solving them myself."""
        }
    ]
    
    # add each image to prompt
    for img in base64_images:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img}",
                "detail": "high"
            }
        })
    
    try:
        print(f"  Sending {len(base64_images)} image(s) to GPT-4o...")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            max_tokens=4096
        )
        
        result = response.choices[0].message.content
        
        # check if gpt is refusing to process
        if "unable" in result.lower() or "can't" in result.lower() or "cannot" in result.lower():
            print(f"  WARNING: GPT may be refusing to process. Response: {result[:200]}...")
        
        return result
    except Exception as e:
        print(f"  ERROR calling OpenAI API: {e}")
        import traceback
        traceback.print_exc()
        return None

# use gpt to select relevant files based on user query
def select_relevant_files(user_query, all_pdf_files):
    if not all_pdf_files:
        return []
    
    # Create a list of filenames for GPT to analyze
    file_list = "\n".join([f"{i+1}. {pdf.name}" for i, pdf in enumerate(all_pdf_files)])
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a helpful assistant that selects relevant PDF files for student queries.

Given a list of PDF filenames and a student's query, select which files would be most relevant.

Consider:
- Course names/codes matching the query
- Document types (notes, quizzes, assignments, exams, etc.)
- Topics and chapters mentioned
- Related materials that might help

Return ONLY a JSON array of the file numbers (as integers) that are relevant. If none are relevant, return an empty array [].

Be generous - include files that might be helpful even if not a perfect match."""
                },
                {
                    "role": "user",
                    "content": f"""Student's query: {user_query}

Available PDF files:
{file_list}

Which files are relevant? Return only the numbers as a JSON array."""
                }
            ],
            max_tokens=300,
            temperature=0.3
        )

        result = response.choices[0].message.content.strip()        
        
        # try to extract json from response
        json_match = re.search(r'\[[\d,\s]+\]', result)
        if json_match:
            selected_indices = json.loads(json_match.group())
            # get actual file objects
            selected_files = [all_pdf_files[i-1] for i in selected_indices if 0 < i <= len(all_pdf_files)]
            return selected_files
        else:
            return []
            
    except Exception as e:
        print(f"Error selecting files: {e}")
        # fallback to keyword matching
        words = user_query.lower().split()
        keywords = [w for w in words if len(w) > 3][:5]
        matching = []
        for pdf in all_pdf_files:
            filename_lower = pdf.stem.lower()
            if any(kw in filename_lower for kw in keywords):
                matching.append(pdf)
        return matching

# send user message to gpt with context of notes
def chat_with_notes(notes_content, user_message):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a helpful tutor. The user has provided their notes below. Help them study by answering questions, creating quizzes, generating practice problems, or whatever they ask for.

CRITICAL RULES: 
1. When generating practice problems, quizzes, or questions: ONLY provide the bare question/problem statement. DO NOT include:
   - Step-by-step outlines
   - Solution structures  
   - Hints or tips
   - "Instructions" on how to solve
   - Proof frameworks or templates
   - Answers or solutions
   UNLESS the user explicitly asks for help, hints, or a solution. Just state the problem and nothing more.

2. Generate questions at the EXACT same difficulty and complexity as the problems in the notes. 
   - If notes show multi-part proofs, generate multi-part proofs
   - If notes have computational problems with specific techniques, match those techniques
   - If notes show problems requiring 10+ steps, your problems should also require 10+ steps
   - Look at the SPECIFIC problems in the notes and create problems of identical structure and difficulty
   - Do NOT simplify or make "introductory" versions

3. If the user mentions specific sections/chapters (e.g., "sections 2.3-2.8"), focus ONLY on the content from those sections in the notes. The notes may contain multiple chapters/sections, so extract and use only the relevant parts.

4. For mathematical notation, use LaTeX format:
   - Inline math: $equation$
   - Display math: $$equation$$
   - Examples: $x^2$, $\\frac{a}{b}$, $$\\int_0^1 x^2 dx$$

Be thorough and educational."""
                },
                {
                    "role": "user",
                    "content": f"Here are my notes:\n\n{notes_content}\n\n---\n\n{user_message}"
                }
            ],
            max_tokens=4096
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error: {e}")
        return None

# save gpt response to markdown and html files to view in brower with proper math syntax
def save_response_to_file(query, response, files_used):
    from datetime import datetime
    
    # create output folder if it doesn't exist
    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(exist_ok=True)
    
    # generate filename from timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # save as markdown file
    md_filename = output_dir / f"response_{timestamp}.md"
    with open(md_filename, "w") as f:
        f.write(f"# Query\n\n{query}\n\n")
        f.write(f"## Files Used\n\n")
        for file in files_used:
            f.write(f"- {file.name}\n")
        f.write(f"\n## Response\n\n{response}\n")
    
    # save as html file
    html_filename = output_dir / f"response_{timestamp}.html"
    
    # format response for html
    files_list = ''.join([f'<li>{file.name}</li>' for file in files_used])
    formatted_response = response.replace('\n', '<br>')
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Noteify Response</title>
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            line-height: 1.6;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .query {{ background: #ecf0f1; padding: 15px; border-left: 4px solid #3498db; margin: 20px 0; }}
        .files {{ background: #f8f9fa; padding: 15px; border-radius: 4px; margin: 20px 0; }}
        .files ul {{ margin: 10px 0; padding-left: 20px; }}
        pre {{ background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 4px; overflow-x: auto; }}
        code {{ background: #ecf0f1; padding: 2px 6px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎓 Noteify Response</h1>
        
        <h2>📝 Your Query</h2>
        <div class="query">{query}</div>
        
        <h2>📚 Files Used</h2>
        <div class="files">
            <ul>
                {files_list}
            </ul>
        </div>
        
        <h2>🤖 AI Response</h2>
        <div class="response">
            {formatted_response}
        </div>
    </div>
</body>
</html>"""
    
    with open(html_filename, "w") as f:
        f.write(html_content)
    
    print(f"✅ Saved to:")
    print(f"   📄 Markdown: {md_filename}")
    print(f"   🌐 HTML: {html_filename}")
    print(f"   (Open the HTML file in your browser for rendered math notation)")

# load files from cache or process with gpt
def load_and_process_files(file_list):
    all_notes = []
    files_to_process = []
    cached_count = 0
    
    print("\nLoading content...")
    for pdf_file in file_list:
        # try to load from cache first
        cached_content = fileData.load_content_from_cache(pdf_file)
        
        if cached_content:
            print(f"  ✓ {pdf_file.name} (from cache)")
            all_notes.append(f"=== {pdf_file.name} ===\n{cached_content}")
            cached_count += 1
        else:
            # need to process with gpt
            files_to_process.append(pdf_file)
    
    # process uncached files with gpt
    if files_to_process:
        print(f"\nProcessing {len(files_to_process)} file(s) with GPT Vision (this may take a moment)...")
        
        for pdf_file in files_to_process:
            print(f"  Processing {pdf_file.name}...")
            content = read_pdf_with_gpt(pdf_file)
            
            if content:
                all_notes.append(f"=== {pdf_file.name} ===\n{content}")
                # add file to cache
                fileData.save_content_to_cache(pdf_file, content)
                print(f"  ✓ {pdf_file.name} (processed & cached)")
        
        # mark files as processed
        fileData.mark_files_processed(files_to_process)
    
    if cached_count > 0:
        print(f"\n💾 Loaded {cached_count} file(s) from cache (no API cost!)")
    
    return "\n\n".join(all_notes)


def main():
    print("=== Noteify - Getting you the A from AI ===\n")
    print("Ask me anything! I can:")
    print("  • Find and read your notes")
    print("  • Create quizzes and practice problems")
    print("  • Answer questions about your material")
    print("  • Help you study for exams\n")
    print("Type 'exit' to quit.\n")
    print("="*70 + "\n")
    
    while True:
        user_query = input("You: ").strip()
        
        if not user_query:
            continue
            
        if user_query.lower() in ['exit', 'quit', 'bye']:
            print("Goodbye!")
            break
        
        # get all pdfs
        print("\n🔍 Searching your notes...")
        all_pdfs = fileData.get_all_pdfs()
        
        if not all_pdfs:
            print("\n❌ No PDF files found in your GoodNotes folder.")
            print("Please check the FOLDER_PATH in fileData.py\n")
            continue
        
        # get relevant files from gpt
        print(f"   Analyzing {len(all_pdfs)} files...")
        relevant_files = select_relevant_files(user_query, all_pdfs)
        
        if not relevant_files:
            print("\n❌ No relevant files found for your query.")
            print("Try rephrasing or being more specific.\n")
            continue
        
        print(f"\n📚 Selected {len(relevant_files)} relevant file(s):")
        for f in relevant_files:
            print(f"   • {f.name}")
        
        # load and process files
        combined_notes = load_and_process_files(relevant_files)
        
        if not combined_notes.strip():
            print("\n❌ No content could be loaded. Please try again.\n")
            continue
        
        # generate response based on the original query
        print("\n💭 Generating response...\n")
        print("AI: ", end="", flush=True)
        response = chat_with_notes(combined_notes, user_query)
        
        if response:
            print(response + "\n")
            
            # ask if user wants to save to file
            save_choice = input("💾 Save this response to a file? (y/n): ").strip().lower()
            if save_choice == 'y':
                save_response_to_file(user_query, response, relevant_files)
                print()
        else:
            print("Sorry, there was an error. Please try again.\n")


if __name__ == "__main__":
    main()
    