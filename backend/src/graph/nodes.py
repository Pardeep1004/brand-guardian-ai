import json
import os
import logging
import re
from typing import Any, Dict, List, Optional, TypedDict

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

# import state schema
from backend.src.graph.state import VideoAuditState, ComplianceIssue

# import services
from backend.src.services.video_indexer import VideoIndexerService

# configure logger
logger = logging.getLogger("brand-guardian")
logging.basicConfig(level=logging.INFO)

# Node 1 : Indexer
# function responsible for converting video url into text - transcript, ocr, metadata
def index_video_node(state: VideoAuditState) -> Dict[str, Any]:

    """
    Download the youtube video from url, uploads to the azure video indexer
    extracts the insights
    """
    video_url = state.get("video_url")
    video_id_input = state.get("video_id", "vid_demo")

    logger.info(f"---- [Node:Indexer] Processing :{video_url}")

    local_filename = "temp_audit_video.mp4"

    try:
        vi_service = VideoIndexerService()
        # download  using yt-dlp
        if "youtube.com" in video_url or "youtu.be" in video_url:
            # download youtube video
            local_path = vi_service.download_youtube_video(
                video_url, output_path =local_filename)
        else:
            raise ValueError("Unsupported video URL. Only YouTube URLs are supported in this" )    
        # upload to azure video indexer
        azure_video_id = vi_service.upload_video(local_path, video_name=video_id_input)
        logger.info(f"Uploaded Success video to Azure Video Indexer with ID: {azure_video_id}")
        # cleanup local file
        if os.path.exists(local_path):
            os.remove(local_path)
        #wait
        raw_insights = vi_service.wait_for_processing(azure_video_id)
        # every 30 sec it will ask azure whetther its done
        #extract
        clean_data = vi_service.extract_data(raw_insights)
        logger.info(f"----[Node:Indexer] Extraction completed ----")
        return clean_data
    
    except Exception as e:
        logger.error(f"Video Indexer Failed : {e}")
        return{
            "errors": [str(e)],
            "final_status": "FAIL",
            "transcript": "",
            "ocr_text": []
        }
    
# Node 2 : Compliance Auditor
def compliance_audit_node(state: VideoAuditState) -> Dict[str, Any]:
    """
    Perform RAG to Audit the content - brand video with regional context
    """
    region = state.get("region", "Global")
    logger.info(f"---- [Node:Auditor] Region: {region} | Querying knowledge base & LLM")
    
    transcript = state.get("transcript", "")
    ocr_text = state.get("ocr_text", [])
    detected_brands = state.get("detected_brands", [])

    if not transcript and not ocr_text:
        logger.warning("No content available for audit. Skipping....")
        return {
            "final_status": "FAIL",
            "final_report": "Audit failed: No speech or text content could be extracted from this video."
        }
    
    # initialize clients
    llm = AzureChatOpenAI(
        azure_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION"),
        temperature = 0.0
    )

    embeddings = AzureOpenAIEmbeddings(
        azure_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"),
        azure_endpoint = os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT"),
        api_key = os.getenv("AZURE_OPENAI_EMBEDDING_API_KEY"),
        openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    )

    vectorstore = AzureSearch(
        azure_search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT"),
        index_name = os.getenv("AZURE_SEARCH_INDEX_NAME"),
        azure_search_key = os.getenv("AZURE_SEARCH_API_KEY"),
        embedding_function = embeddings.embed_query
    )

    # RAG retrieve relevant documents with regional emphasis
    query_text = f"Compliance rules for {region}: {transcript[:500]} {' '.join(ocr_text[:200])}"
    docs = vectorstore.similarity_search(query_text, k=5) 
    retrieved_rules = "\n\n".join([doc.page_content for doc in docs]) 

    # prepare prompt
    system_prompt = f"""
            You are an Elite Global Brand Compliance Auditor specializing in the {region} region.
            
            OFFICIAL COMPLIANCE REPOSITORY:
            {retrieved_rules}
            
            YOUR MISSION:
            1. Analyze the video data provided (Transcript, OCR, Brands, Metadata).
            2. Evaluate compliance based on {region} laws and YouTube 2026 specs.
            3. PAY SPECIAL ATTENTION TO:
               - LEGAL DISCLOSURE: Are mandatory AI labels or influencer 'Paid Partner' mentions present?
               - TONE & STYLE: Is the tonality appropriate for the {region} market (avoiding aggression, dark patterns, or misleading claims)?
               - VISUAL COMPLIANCE: Are detected brands/logos consistent with the campaign? Flag competitor logos.
               - RESTRICTED CONTENT: Check for Greenwashing, HFSS, Alcohol, or Tobacco violations if applicable.
            
            RESPONSE FORMAT (Strict JSON):
            IMPORTANT:
            - Output MUST be valid JSON.
            - The 'final_report' field must be a SINGLE string containing the markdown report.
            - You MUST escape all double quotes (") and newlines (\\n) inside the string values.
            - Do not include any text outside the JSON block.

            {{
                "compliance_results": [
                    {{
                        "category": "Legal Disclosure | Brand Safety | Greenwashing | Tonality",
                        "description": "Specific violation detail",
                        "severity": "CRITICAL | HIGH | MEDIUM | LOW"
                    }}
                ],
                "status": "PASS | FAIL",
                "final_report": "A professional, detailed markdown report summarizing the audit for the {region} market. Use \\n for newlines."
            }}
            """
    
    user_message = f"""
            TARGET REGION: {region}
            TRANSCRIPT: {transcript}
            ON-SCREEN TEXT (OCR): {ocr_text}
            DETECTED BRANDS/LOGOS: {detected_brands}
            VIDEO METADATA: {state.get("video_metadata", {})}
            """

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])
        content = response.content
        
        # Robust JSON extraction
        # 1. Try to find JSON within code blocks
        json_match = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        
        # 2. Cleanup whitespace
        content = content.strip()
        
        # 3. Parse
        audit_data = json.loads(content)
        
        return {
            "compliance_results": audit_data.get("compliance_results", []),
            "final_status": audit_data.get("status", "FAIL"),
            "final_report": audit_data.get("final_report", "No Report Generated.")
        }
    except json.JSONDecodeError as e:
        logger.error(f"JSON Parse Error: {e}")
        logger.error(f"Raw Output: {response.content}")
        return {
            "errors": ["Failed to parse AI response. Check logs for raw output."],
            "final_status": "FAIL",
            "final_report": f"AI Parsing Error. Raw output start: {response.content[:100]}..."
        }
    except Exception as e:
        logger.error(f"Auditor Node Error: {str(e)}")
        return { "errors": [str(e)], "final_status": "FAIL" }
