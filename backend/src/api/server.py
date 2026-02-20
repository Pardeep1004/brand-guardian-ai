# fastapi

import uuid
import logging
import os
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel
from typing import List, Optional, Dict
from backend.src.api.models import init_db, SessionLocal, AuditRecord

# Load env variables
from dotenv import load_dotenv
load_dotenv(override=True)

# Initialize Database
init_db()

# Initialize the Telemetry
from backend.src.api.telemetry import setup_telemetry
setup_telemetry()

# import workflow graph
from backend.src.graph.workflow import app as compliance_graph

# configure logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("api-server")

# create fastapi application
app = FastAPI(
    title = "Brand Guardian AI API",
    description = "API for auditing video content against the brand compliance rules.",
    version = "1.0.0"
)

# Setup templates and static files relative to this file's location
current_dir = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))
# Note: Ensure the static directory exists even if empty for now
static_dir = os.path.join(current_dir, "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Serve the frontend
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# define data model (pydantic)
class AuditRequest(BaseModel):
    video_url :str
    region : Optional[str] = "Global"

class ComplianceIssue(BaseModel):
    category :str
    severity: str
    description : str
    timestamp: Optional[str] = None

class AuditResponse(BaseModel):
    task_id : str
    status : str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    video_id: Optional[str] = None
    final_status: Optional[str] = None
    final_report: Optional[str] = None
    compliance_results: List[ComplianceIssue] = []
    errors: List[str] = []
    region: Optional[str] = "Global"
    created_at: Optional[str] = None

def run_audit_background(task_id: str, video_url: str, region: str = "Global"):
    """
    Background worker function that runs the LangGraph workflow.
    Defined as a regular 'def' (not async) so FastAPI runs it in a threadpool.
    Persists results to the database.
    """
    db = SessionLocal()
    try:
        # Update status to PROCESSING
        record = db.query(AuditRecord).filter(AuditRecord.id == task_id).first()
        if record:
            record.status = "PROCESSING"
            db.commit()

        video_id_short = f"vid_{task_id[:8]}"
        initial_inputs = {
            "video_url": video_url,
            "video_id": video_id_short,
            "region": region,
            "detected_brands": [],
            "compliance_results": [],
            "errors": []
        }

        # Execute the graph
        final_state = compliance_graph.invoke(initial_inputs)
        
        # Reload record to avoid detached session issues
        record = db.query(AuditRecord).filter(AuditRecord.id == task_id).first()
        if record:
            record.status = "COMPLETED"
            record.video_id = final_state.get("video_id")
            record.final_status = final_state.get("final_status", "UNKNOWN")
            record.final_report = final_state.get("final_report", "No report Generated")
            record.compliance_results = final_state.get("compliance_results", [])
            record.errors = final_state.get("errors", [])
            db.commit()
            
        logger.info(f"Task {task_id} completed successfully and saved to DB (Region: {region}).")
    except Exception as e:
        logger.error(f"Background Audit Failed for task {task_id}: {str(e)}")
        record = db.query(AuditRecord).filter(AuditRecord.id == task_id).first()
        if record:
            record.status = "FAILED"
            record.errors = [str(e)]
            db.commit()
    finally:
        db.close()

# Define the main Endpoint
@app.post("/audit", response_model=AuditResponse)
async def audit_video(request: AuditRequest, background_tasks: BackgroundTasks):
    '''
    Triggers the compliance audit workflow asynchronously and saves initial record to DB
    '''
    task_id = str(uuid.uuid4())
    logger.info(f"Received Audit request: {request.video_url} (Region: {request.region}, Task ID: {task_id})")
    
    # Save initial record to DB
    db = SessionLocal()
    try:
        new_record = AuditRecord(
            id=task_id,
            video_url=request.video_url,
            region=request.region or "Global",
            status="PENDING"
        )
        db.add(new_record)
        db.commit()
    finally:
        db.close()
    
    # Add to background tasks
    background_tasks.add_task(run_audit_background, task_id, request.video_url, request.region or "Global")
    
    return AuditResponse(task_id=task_id, status="PENDING")

@app.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    '''
    Check the status of a background audit task from the database
    '''
    db = SessionLocal()
    try:
        record = db.query(AuditRecord).filter(AuditRecord.id == task_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return TaskStatusResponse(
            task_id=record.id,
            status=record.status,
            video_id=record.video_id,
            final_status=record.final_status,
            final_report=record.final_report,
            compliance_results=record.compliance_results or [],
            errors=record.errors or [],
            region=record.region or "Global",
            created_at=record.created_at.isoformat() if record.created_at else None
        )
    finally:
        db.close()

@app.get("/history", response_model=List[TaskStatusResponse])
async def get_audit_history(limit: int = 10):
    '''
    Retrieve the most recent audit records from the database
    '''
    db = SessionLocal()
    try:
        records = db.query(AuditRecord).order_by(AuditRecord.created_at.desc()).limit(limit).all()
        return [
            TaskStatusResponse(
                task_id=r.id,
                status=r.status,
                video_id=r.video_id,
                final_status=r.final_status,
                final_report=r.final_report,
                compliance_results=r.compliance_results or [],
                errors=r.errors or [],
                region=r.region or "Global",
                created_at=r.created_at.isoformat() if r.created_at else None
            ) for r in records
        ]
    finally:
        db.close()

# Additional imports for Chat
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# Chat Models
class ChatRequest(BaseModel):
    task_id: str
    message: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat_with_guardian(request: ChatRequest):
    """
    Interactive Q&A about the specific audit report.
    """
    db = SessionLocal()
    try:
        record = db.query(AuditRecord).filter(AuditRecord.id == request.task_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if record.status != "COMPLETED":
             raise HTTPException(status_code=400, detail="Audit not completed yet.")

        # Prepare Context
        context = f"""
        AUDIT REPORT CONTEXT:
        Video ID: {record.video_id}
        Region: {record.region}
        Final Decision: {record.final_status}
        
        FULL COMPLIANCE REPORT:
        {record.final_report}
        
        SPECIFIC VIOLATIONS:
        {record.compliance_results}
        """

        # Initialize LLM
        llm = AzureChatOpenAI(
            azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
            openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            temperature=0.7
        )
        
        system_prompt = """You are the Brand Guardian AI Assistant. 
        You have just audited a video and the user has questions about your findings.
        Answer their questions clearly based ONLY on the provided audit report context.
        If the user asks about the specific timestamp of a violation, try to find it in the violations list.
        Be helpful, professional, and explain clearly why something failed or passed."""

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Context: {context}\n\nUser Question: {request.message}")
        ])
        
        return ChatResponse(response=response.content)

    except Exception as e:
        logger.error(f"Chat Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# Health Check Endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Brand Guardian AI"}
