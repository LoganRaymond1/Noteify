from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import chat
import fileData

app = FastAPI(title="Noteify API", description="API for Noteify", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    files_used: List[str]

class FileListResponse(BaseModel):
    files: List[str]

@app.get("/")
def root():
    return {"message": "Noteify API is running"}

@app.get("/api/files", response_model=FileListResponse)
def get_files():
    try:
        pdfs = fileData.get_all_pdfs()
        return FileListResponse(files=[pdf.name for pdf in pdfs])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        all_pdfs = fileData.get_all_pdfs()

        if not all_pdfs:
            raise HTTPException(status_code=404, detail="No PDF files found")
        
        relevant_files = chat.select_relevant_files(request.message, all_pdfs)

        if not relevant_files:
            raise HTTPException(status_code=404, detail="No relevant files found")

        combined_notes = chat.load_and_process_files(relevant_files)

        if not combined_notes.strip():
            raise HTTPException(status_code=404, detail="No content could be loaded")

        response = chat.chat_with_notes(combined_notes, request.message)

        if not response:
            raise HTTPException(status_code=404, detail="No response could be generated")

        return ChatResponse(
            response=response,
            files_used=[f.name for f in relevant_files]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))