'''
Connector : Python and Azure Video Indexer
'''
import os
import time
import logging
import requests
import yt_dlp
from azure.identity import DefaultAzureCredential

logger = logging.getLogger("video_indexer")

class VideoIndexerService:
    def __init__(self):
        # initialize azure video indexer credentials and endpoints from env variables
        self.account_id = os.getenv("AZURE_VI_ACCOUNT_ID")
        self.location = os.getenv("AZURE_VI_LOCATION")
        self.subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        self.resource_group = os.getenv("AZURE_RESOURCE_GROUP")
        self.vi_name = os.getenv("AZURE_VI_NAME", "brandytproject001")
        self.credential = DefaultAzureCredential()

    def get_access_token(self):
        # get access token for azure video indexer API
        '''
        Generate ARM Access Token for Azure Video Indexer API using subscription key
        '''
        try:
            token_object = self.credential.get_token("https://management.azure.com/.default")
            return token_object.token
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            raise 

    def get_account_token(self, arm_access_token):
        # get account level token for video indexer API
        '''
        Exchange the  ARM Access Token for Azure Video Indexer Account Team using ARM token
        '''
        url = (
            f"https://management.azure.com/subscriptions/{self.subscription_id}"
            f"/resourceGroups/{self.resource_group}"
            f"/providers/Microsoft.VideoIndexer/accounts/{self.vi_name}"
            f"/generateAccessToken?api-version=2024-01-01"
        )
        
        headers = {"Authorization": f"Bearer {arm_access_token}"}
        payload = {"permissionType": "Contributor", "scope": "Account" }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"Failed to get VI account access tokenn : response: {response.text}")
        return response.json().get("accessToken")
        
    # function to download youtube video using yt-dlp
    def download_youtube_video(self, url, output_path = "temp_video.mp4"):
        '''
        download_youtube_video: Download video from YouTube using yt-dlp library to local storage for further processing and uploading to Azure Video Indexer
        '''
        logger.info(f"Downloading video from URL: {url}")
        ydl_opts = {
            'format': 'best', # format selection for best quality
            'outtmpl': output_path, # output template for the downloaded video
            'quiet': False, # Control the verbosity of yt-dlp output, set to False to see download progress and logs, put true in production for cleaner logs
            'no_warnings': False, 
            #'overwrites': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            logger.info(f"Video downloaded successfully")
            return output_path
        except Exception as e:
            logger.error(f"Failed to download YouTube video: {str(e)}")
            raise

    # upload video to azure video indexer
    def upload_video(self, video_path, video_name):
        arm_token = self.get_access_token()
        vi_token = self.get_account_token(arm_token)

        api_url = f"https://api.videoindexer.ai/{self.location}/Accounts/{self.account_id}/Videos"
        params = {
            "accessToken": vi_token,
            "name": video_name,
            "privacy": "Private",
            "IndexingPreset": "Default",
            #"videoUrl": None
        }
        logger.info(f"Uploading video to Azure Video Indexer:")

        # OPEN THE FILE IN BINARY MODE AND STREAM TO AZURE VIDEO INDEXER
        with open(video_path, "rb") as video_file:
            files = {"file": video_file}
            response = requests.post(api_url, params=params, files=files)
        if response.status_code != 200:
            raise Exception(f"Failed to upload video on Azure Video Indexer : {response.text}")
        return response.json().get("id")
        
    def wait_for_processing(self, video_id):
        logger.info(f"Waiting for video processing to complete for video ID: {video_id}")
        while True:
            arm_token = self.get_access_token()
            vi_token = self.get_account_token(arm_token)

            # Target the specific video index endpoint
            url = f"https://api.videoindexer.ai/{self.location}/Accounts/{self.account_id}/Videos/{video_id}/Index"
            params = {"accessToken": vi_token, "language": "en-US"}
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                logger.error(f"Failed to get video index: {response.text}")
                time.sleep(30)
                continue

            data = response.json()
            state = data.get("state")
            
            if state == "Processed":
                logger.info(f"Video {video_id} processed successfully")
                return data
            elif state == "Failed":
                raise Exception(f"Video processing failed in Azure Video Indexer for video ID: {video_id}")
            elif state == "Quarantined":
                raise Exception(f"Video is quarantined in Azure Video Indexer (Copyright/Content Policy Violation)")
            
            logger.info(f"Status: {state}. Checking again in 30 seconds...")
            time.sleep(30)

    def extract_data(self, vi_json):
        'Parses the JSON into our state format'
        transcripts_lines = []
        ocr_lines = []
        brands_found = []

        # Helper to extract insights from a block
        def process_block(insights):
            # Transcript
            for item in insights.get("transcript", []):
                if item.get("text"): transcripts_lines.append(item["text"])
            # OCR
            for item in insights.get("ocr", []):
                if item.get("text"): ocr_lines.append(item["text"])
            # Brands/Logos
            for item in insights.get("brands", []):
                if item.get("name"): brands_found.append(item["name"])

        # 1. Check top-level insights
        process_block(vi_json.get("insights", {}))

        # 2. Check per-video insights
        if not vi_json.get("videos"):
            logger.warning(f"No videos found in VI JSON. Keys: {list(vi_json.keys())}")
        
        for v in vi_json.get("videos", []):
            process_block(v.get("insights", {}))

        # Deduplicate while preserving order
        return {
            "transcript": " ".join(list(dict.fromkeys(transcripts_lines))),
            "ocr_text": list(dict.fromkeys(ocr_lines)),
            "detected_brands": list(dict.fromkeys(brands_found)),
            "video_metadata": {
                "duration": vi_json.get("summarizedInsights", {}).get("durationText"),
                "platform": "youtube",
                "id": vi_json.get("id")
            }
        }