import os
import json
import hashlib
from pathlib import Path
from datetime import datetime

# path to notes folder

# add notes file here
FOLDER_PATH = Path.home() / "Library/CloudStorage/GoogleDrive-logan@theraymonds.ca/My Drive/TEST"

STATE_FILE = Path(__file__).parent / "state.json"
CACHE_DIR = Path(__file__).parent / "content_cache"

# create cache folder
CACHE_DIR.mkdir(exist_ok=True)

# load state file
def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

# save state file
def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# get all pdfs
def get_all_pdfs():
    if not FOLDER_PATH.exists():
        print(f"Warning: GoodNotes folder not found at {FOLDER_PATH}")
        return []
    
    pdf_files = list(FOLDER_PATH.rglob("*.pdf"))
    return pdf_files

# search files by name
def search_files_by_name(query):
    all_pdfs = get_all_pdfs()
    query_lower = query.lower()
    
    matching_files = [
        pdf for pdf in all_pdfs 
        if query_lower in pdf.stem.lower()
    ]
    
    return matching_files

# search files by terms
def search_files_by_terms(search_terms):
    all_pdfs = get_all_pdfs()
    
    if not search_terms:
        return []
    
    # convert all terms to lowercase
    terms_lower = [term.lower() for term in search_terms]
    
    # find corresponding files
    matching_files = set()
    for pdf in all_pdfs:
        filename_lower = pdf.stem.lower()
        # check if any search term is in the filename
        for term in terms_lower:
            if term in filename_lower:
                matching_files.add(pdf)
                break
    
    return list(matching_files)

# check which files have been modified since last processing
def get_modified_files(file_paths):
    state = load_state()
    new_files = []
    updated_files = []
    
    for file_path in file_paths:
        file_key = str(file_path)
        mod_time = file_path.stat().st_mtime
        
        if file_key not in state:
            new_files.append(file_path)
        elif state[file_key] < mod_time:
            updated_files.append(file_path)
    
    return {
        "new": new_files,
        "updated": updated_files,
        "all": file_paths
    }

# mark files as processed
def mark_files_processed(file_paths):
    state = load_state()
    
    for file_path in file_paths:
        file_key = str(file_path)
        mod_time = file_path.stat().st_mtime
        state[file_key] = mod_time
    
    save_state(state)

# generate cache key
def get_cache_key(file_path):
        # use hash of absolute path to create a valid filename
    path_hash = hashlib.md5(str(file_path.absolute()).encode()).hexdigest()
    return path_hash

# save extracted content to cache
def save_content_to_cache(file_path, content):
    cache_key = get_cache_key(file_path)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    cache_data = {
        "file_path": str(file_path),
        "file_name": file_path.name,
        "content": content,
        "cached_at": datetime.now().isoformat(),
        "mod_time": file_path.stat().st_mtime
    }
    
    with open(cache_file, "w") as f:
        json.dump(cache_data, f, indent=2)

# load content from cache
def load_content_from_cache(file_path):
    cache_key = get_cache_key(file_path)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, "r") as f:
            cache_data = json.load(f)
        
        # check if cache is still valid
        current_mod_time = file_path.stat().st_mtime
        cached_mod_time = cache_data.get("mod_time")
        
        if cached_mod_time and current_mod_time <= cached_mod_time:
            return cache_data["content"]
        else:
            # cache is stale
            return None
    except Exception as e:
        print(f"Error reading cache: {e}")
        return None

# search files to process
# return dict with file lists and metadata
def get_files_to_process(query):
    matching_files = search_files_by_name(query)
    
    if not matching_files:
        return {
            "found": False,
            "message": f"No files found matching '{query}'",
            "files": []
        }
    
    file_status = get_modified_files(matching_files)
    
    return {
        "found": True,
        "total": len(matching_files),
        "new": file_status["new"],
        "updated": file_status["updated"],
        "unchanged": [f for f in matching_files if f not in file_status["new"] and f not in file_status["updated"]],
        "all_files": matching_files
    }

# search files by terms
def get_files_by_terms(search_terms):
    matching_files = search_files_by_terms(search_terms)
    
    if not matching_files:
        return {
            "found": False,
            "message": f"No files found matching search terms: {', '.join(search_terms[:3])}{'...' if len(search_terms) > 3 else ''}",
            "files": []
        }
    
    file_status = get_modified_files(matching_files)
    
    return {
        "found": True,
        "total": len(matching_files),
        "search_terms": search_terms,
        "new": file_status["new"],
        "updated": file_status["updated"],
        "unchanged": [f for f in matching_files if f not in file_status["new"] and f not in file_status["updated"]],
        "all_files": matching_files
    }
