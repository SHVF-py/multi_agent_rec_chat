import torch

class Config:
    # LLM
    VLLM_URL = "http://localhost:8001/v1/chat/completions"
    MODEL_NAME = "microsoft/Phi-3-mini-4k-instruct"
    
    # Embeddings
    TEXT_MODEL_NAME = "BAAI/bge-small-en-v1.5"
    SIGLIP_MODEL = "ViT-B-16-SigLIP"
    SIGLIP_PRETRAINED = "webli"
    
    # Hardware
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    EMBEDDING_DEVICE = "cpu"  # Embedding models run on CPU to reserve GPU VRAM for vLLM