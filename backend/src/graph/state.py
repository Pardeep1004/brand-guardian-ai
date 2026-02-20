import operator

from typing import Any, Dict, List, Optional, TypedDict, Annotated

# define the schema for a single compliance results
# Error report for a single compliance issue found in the video
class ComplianceIssue(TypedDict):
    category : str
    description : str # specific details of violations
    severity : str # critical, high, medium, low }WARNING
    timestamp : Optional[str]
# Define the global graph state for video audit processing
# Define the state that gets passed around the agentic workflow
class VideoAuditState(TypedDict):
    '''
    Define the data schema for langgrah execution content
    Main container: holds all the information related to a single video audit process
    right from initial url ingestion to final report generation
    '''
    # input parameters
    video_url : str
    video_id : str
    region : Optional[str] # Global, Europe, North America, Asia
    
    # ingestion and extraction data
    local_file_path : Optional[str]
    video_metadata : Dict[str, Any]
    transcript : Optional[str]
    ocr_text : Optional[str]
    detected_brands : List[str] # List of brand names/logos found in video
    
    # analysis results
    compliance_results : Annotated[List[ComplianceIssue], operator.add]

    # final deliverables
    final_status : str # Passed, Fail
    final_report : str # markdown format

    # system observability
    # errors: API timeouts, file not found, unsupported format, system level errors
    # lists of system level crashes or errors encountered 
    errors : Annotated[List[str], operator.add]


