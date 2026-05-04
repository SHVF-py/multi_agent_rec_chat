import torch
import open_clip
from PIL import Image
from sentence_transformers import SentenceTransformer
from config import Config

class EmbeddingService:
    def __init__(self):
        # Load Text Model (SBERT) — CPU to preserve GPU VRAM for vLLM
        self.text_model = SentenceTransformer(Config.TEXT_MODEL_NAME, device=Config.EMBEDDING_DEVICE)

        # Load Image Model (SigLIP via open_clip) — CPU to preserve GPU VRAM for vLLM
        model, _, preprocess = open_clip.create_model_and_transforms(
            Config.SIGLIP_MODEL, pretrained=Config.SIGLIP_PRETRAINED, device=Config.EMBEDDING_DEVICE
        )
        self.siglip_model = model
        self.siglip_preprocess = preprocess

    def embed_text(self, text: str) -> list[float]:
        embedding = self.text_model.encode(text)
        return embedding.tolist()

    def embed_image(self, image_file) -> list[float]:
        image = Image.open(image_file.file).convert("RGB")
        image_input = self.siglip_preprocess(image).unsqueeze(0).to(Config.EMBEDDING_DEVICE)

        with torch.no_grad():
            image_features = self.siglip_model.encode_image(image_input)
            image_features /= image_features.norm(dim=-1, keepdim=True)

        return image_features.cpu().numpy()[0].tolist()