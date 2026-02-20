
import os
import json
import uuid
from dotenv import load_dotenv
load_dotenv(override=True)

from backend.src.graph.workflow import app

def audit_video(url):
    session_id = str(uuid.uuid4())
    initial_inputs = {
        "video_url": url,
        "video_id": f"vid_{session_id[:8]}",
        "compliance_results": [],
        "errors": []
    }
    
    print(f"Running audit for: {url}")
    try:
        final_state = app.invoke(initial_inputs)
        print("\n=== AUDIT RESULTS ===")
        print(f"Status: {final_state.get('final_status')}")
        print(f"Report:\n{final_state.get('final_report')}")
        print("\n=== VIOLATIONS ===")
        for issue in final_state.get("compliance_results", []):
            print(f"- [{issue.get('severity')}] {issue.get('category')}: {issue.get('description')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    audit_video("https://www.youtube.com/watch?v=iL88A5F9V3k")
