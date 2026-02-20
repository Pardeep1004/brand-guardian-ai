'''
Main execution entry point for the compliance QA pipeline or Brand Guardian. 
It initializes the workflow graph and starts the execution with the given input video URL.
1. Sets up the audit request
2. Runs the AI workflow
3. Prints the final compliance audit report in the console
'''
# Standard library imports for basic python functionalities
import os
import uuid      # for generating unique session IDs
import logging   # Records logs for monitoring and debugging "what happens during execution(like a flight recorder)"
import json      # Handle JSON data formatting for input and output states(convert python dict to readable json format for better visualization in console)
from pprint import pprint # Pretty print for better visualization of complex data structures in console
# Load env variables from .env file for configuration management (like azure credentials, API keys)
from dotenv import load_dotenv
load_dotenv(override=True) # override=True ensures that env variables are reloaded and updated if .env file changes during development, in production you can set it to False for better performance

from backend.src.graph.workflow import app
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s"
    # Format : timestamp - logger_name - severity_level - message
    # Example: "2024-01-01 12:00:00 - brand-guardian - INFO - Starting AuditSession: 123e4567-e89b-12d3-a456-426614174000"
)
logger = logging.getLogger("brand-guardian_runner")

def run_cli_simulation():
    """
    Simulation the video complaince audit request.
    This function orchestrates the entire audit process:
    - Creates a unique audit session ID for tracking
    - Prepares the video URL and metadata for the workflow input state
    - Runs it through AI Workflow
    - Displays the final audit report in the console with clear formatting for easy understanding of the results.
    """
    # ========== Step 1: Generate Unique Session ID ==========
    # Create a unique session ID for this audit run, useful for tracking and logging in real applications
    # Example : "123e4567-e89b-12d3-a456-426614174000"
    session_id = str(uuid.uuid4()) # uuid() generates random unique identifier
    logger.info(f"Starting AuditSession: {session_id}") # Log to console/file with session ID for traceability

    # ========== Step 2: Define Initial State for the Workflow ==========
    # This dictionary contains all the input data for the workflow
    # Think of it as the "intake form" for the audit process
    # define the initial state

    initial_inputs = {
        # youtube video to audit
        "video_url": "",
        # Shortened video ID for easier tracking in logs and reports, derived from session ID
        # Example : "vid_123e4567"
        "video_id": f"vid_{session_id[:8]}",

        # Empty list that will store compliance violations found during the audit
        # It will be populated by the Auditor node
        "compliance_results": [],

        # Empty lists for any errors during processing
        # Example : ["Failed to download video", "Transcript unavailable"]
        "errors": []
    }

    # ========== Display Section: Input Summary ==========

    print("---- Initial the Workflow State ----")
    # json.dumps() converts the initial_inputs python dictionary into a nicely formatted JSON string for better readability in the console output
    # indent =2 makes it readable with 2-space indentation
    print(f"Input Payload: {json.dumps(initial_inputs, indent=2)}")

    # ========== Step 3: Execute Graph / Workflow ==========
    # Run the entire workflow
    try:
        # app.invoke()  trigger the LangGraph workflow
        # It passes through : START -> Indexer Node -> Compliance Auditor Node -> END
        # Returns the final state after processing which includes the compliance results and final report

        final_state = app.invoke(initial_inputs)

        # ========== Display Section: Final Execution Complete ==========
        print("---- Final Workflow Execution is Complete ----")
        print("\n Compliance Audit Report: \n")

        # .get() is used to safely retrieve values from the final_state dictionary (returns None if key is missing instead of throwing error
        # Displays the video ID that was Audited
        print(f"Video ID: {final_state.get('video_id')}")

        # Show Pass or Fail status of the audit
        print(f"Final Status: {final_state.get('final_status')}")

        # ========== Display Section: Violations Found ==========
        print("\n [VIOLATIONS FOUND]")
        # Extract the list of compliance violations found during the audit from the final state
        # Default to empty list if no violations found or key is missing
        results = final_state.get("compliance_results", [])

        if results:
            # Loop through each violation and print it
            for issue in results:
                # Each issue is a dictionary with keys: category, severity, description
                # Example Output: "Claim Validation [CRITICAL]: The video makes an unsubstantiated claim about the product's effectiveness."
                print(f"{issue.get('category')} [{issue.get('severity')}]: {issue.get('description')}")
        else:
            # No violations found, the video is compliant
            print("No violations found. The video is compliant.")

            # ========== Final Summary Section ==========
            print("\n [Final Summary]")
            # Displays the AI generated natural language summary
            # Example Output: "The video passed the compliance audit with no violations found. It adheres to all brand guidelines and regulatory requirements."
            print(final_state.get("final_report", ""))
    except Exception as e:
        # ============= Error Handling Section =============
        # If anything goes wrong during the workflow execution, it will be caught here
        logger.error(f"Workflow execution failed: {str(e)}")
        raise e
    
# ============ Main Execution Point ============
# This block only runs if you import this file as a module
if __name__ == "__main__":
    run_cli_simulation() # start the complaince audit simulation when you run this script directly


