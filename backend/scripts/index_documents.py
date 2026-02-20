import os
import glob
import logging
from dotenv import load_dotenv
load_dotenv(override=True)

# document loaders and splitters
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# azure components import
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch

#Setup logging 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
    )
logger = logging.getLogger("indexer")

def index_docs():
    '''
    Read the PDF's, chunk them, and upload them to azure AI search
    '''
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
    # define paths, we looks for data folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_folder = os.path.join(current_dir, "../../backend/data")
    # check on env variables
    logger.info("="*60)
    logger.info(f"Environment Configuration Check: ")
    logger.info(f"AZURE_OPENAI_ENDPOINT: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    logger.info(f"AZURE_OPENAI_API_VERSION: {os.getenv('AZURE_OPENAI_API_VERSION')}")
    logger.info(f"Embedding Deployment: {os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-3-small')}")
    logger.info(f"AZURE_SEARCH_ENDPOINT: {os.getenv('AZURE_SEARCH_ENDPOINT')}")
    logger.info(f"AZURE_SEARCH_INDEX_NAME: {os.getenv('AZURE_SEARCH_INDEX_NAME')}")
    logger.info("="*60)

    # validate the required env variables
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_INDEX_NAME",
        "AZURE_SEARCH_API_KEY"
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please check your .env file and ensure all required variables are set.")
        return
    
    # initialize embedding model : turns texts into vector
    try:
        logger.info("Initializing Azure OpenAI Embedding model...")
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"),
            azure_endpoint = os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT"),
            api_key = os.getenv("AZURE_OPENAI_EMBEDDING_API_KEY"),
            openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        )
        logger.info("Embedding model initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize embedding model: {e}")
        logger.error("Please check your Azure OpenAI deployment name and endpoint")
        return
    
    # initialize vector store : azure search

    try:
        logger.info("Initializing Azure AI Search vector store...")
        vector_store = AzureSearch(
            azure_search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT"),
            azure_search_key = os.getenv("AZURE_SEARCH_API_KEY"),
            index_name = index_name,
            embedding_function = embeddings.embed_query
        )
        logger.info(f"Vector store initialized for index : {index_name}")
        
    except Exception as e:
        logger.error(f"Failed to initialize Azure Search: {e}")
        logger.error("Please check your Azure Search Endpoint, API Key, and Index Name")
        return
    
    # find document files (PDF and TXT)
    pdf_files = glob.glob(os.path.join(data_folder, "*.pdf"))
    txt_files = glob.glob(os.path.join(data_folder, "*.txt"))
    all_files = pdf_files + txt_files

    if not all_files:
        logger.warning(f"No documents found in data folder: {data_folder}. Please add PDF or TXT files.")
    
    logger.info(f"Found {len(all_files)} files to process : {[os.path.basename(f) for f in all_files]}")
    
    all_splits = []
    from langchain_community.document_loaders import TextLoader

    for doc_path in all_files:
        try:
            logger.info(f"Processing file: {os.path.basename(doc_path)}")
            
            if doc_path.endswith('.pdf'):
                loader = PyPDFLoader(doc_path)
                raw_docs = loader.load()
            elif doc_path.endswith('.txt'):
                loader = TextLoader(doc_path, encoding='utf-8')
                raw_docs = loader.load()
            else:
                continue

            # split the documents into chunks strategy
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size = 1000,
                chunk_overlap = 200,
            )

            splits = text_splitter.split_documents(raw_docs)
            for split in splits:
                split.metadata["source"] = os.path.basename(doc_path)
            all_splits.extend(splits)
            logger.info(f" - Split into {len(splits)} chunks.")

        except Exception as e:
            logger.error(f"Failed to process {doc_path}: {e}")

    # upload to Azure (moved OUTSIDE the for loop)
    if all_splits:
        logger.info(f"Uploading {len(all_splits)} document chunks to Azure AI Search Index '{index_name}'")

        try:
            # azure search accepts batch automatically via this method
            vector_store.add_documents(documents = all_splits)
            logger.info("="*60)
            logger.info("Indexing completed successfully. Knowledge base is ready for compliance audit.")
            logger.info(f"Total chunks indexed: {len(all_splits)}")
            logger.info("="*60)

        except Exception as e:
            logger.error(f"Failed to upload documents to Azure Search: {e}")
            logger.error("Please check your Azure Search index configuration and network connectivity.")
    else:
        logger.warning("No document chunks were processed.")

if __name__ == "__main__":
    index_docs()