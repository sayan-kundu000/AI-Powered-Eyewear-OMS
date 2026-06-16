import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List

class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, :x.size(1)]

class CustomMultiHeadAttention(nn.Module):
    def __init__(self, d_model: int, n_heads: int):
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        
        assert self.head_dim * n_heads == d_model, "d_model must be divisible by n_heads"
        
        self.q_linear = nn.Linear(d_model, d_model)
        self.k_linear = nn.Linear(d_model, d_model)
        self.v_linear = nn.Linear(d_model, d_model)
        self.out_linear = nn.Linear(d_model, d_model)

    def forward(self, q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, mask: torch.Tensor = None) -> torch.Tensor:
        batch_size = q.size(0)
        
        # Project and reshape to: [batch, n_heads, seq_len, head_dim]
        Q = self.q_linear(q).view(batch_size, -1, self.n_heads, self.head_dim).transpose(1, 2)
        K = self.k_linear(k).view(batch_size, -1, self.n_heads, self.head_dim).transpose(1, 2)
        V = self.v_linear(v).view(batch_size, -1, self.n_heads, self.head_dim).transpose(1, 2)
        
        # Scaled dot-product attention
        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.head_dim)
        
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
            
        attn = F.softmax(scores, dim=-1)
        context = torch.matmul(attn, V)
        
        # Reshape context back to: [batch, seq_len, d_model]
        context = context.transpose(1, 2).contiguous().view(batch_size, -1, self.d_model)
        return self.out_linear(context)

class TransformerEncoderLayer(nn.Module):
    def __init__(self, d_model: int, n_heads: int, d_ff: int, dropout: float = 0.1):
        super().__init__()
        self.attn = CustomMultiHeadAttention(d_model, n_heads)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        
        self.feed_forward = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model)
        )
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, mask: torch.Tensor = None) -> torch.Tensor:
        attn_out = self.attn(x, x, x, mask)
        x = self.norm1(x + self.dropout(attn_out))
        ff_out = self.feed_forward(x)
        x = self.norm2(x + self.dropout(ff_out))
        return x

class PrescriptionTransformer(nn.Module):
    """
    Custom Transformer model for:
    1. Entity Extraction / Labeling (outputs tags for prescription parameters).
    2. Embedding Generation (projects SPH/CYL/AXIS to dense vector space).
    3. NLP query intent classification for the AI Assistant.
    """
    def __init__(self, vocab_size: int = 1000, d_model: int = 128, n_heads: int = 4, num_layers: int = 2, num_classes: int = 5):
        super().__init__()
        self.d_model = d_model
        self.token_embedding = nn.Embedding(vocab_size, d_model)
        self.pos_encoder = PositionalEncoding(d_model)
        
        self.layers = nn.ModuleList([
            TransformerEncoderLayer(d_model, n_heads, d_model * 4)
            for _ in range(num_layers)
        ])
        
        # Projection layer for numerical vectors (e.g. SPH, CYL, AXIS) to d_model
        self.num_projection = nn.Linear(9, d_model)
        
        # Token classification head (for entity extraction)
        self.token_classifier = nn.Linear(d_model, num_classes)
        
        # Sequence classification head (for NLP query intent classification)
        self.intent_classifier = nn.Linear(d_model, 4) # 4 main intents: query_orders, explain_delay, show_analytics, greeting

    def forward_tokens(self, src: torch.Tensor, mask: torch.Tensor = None) -> torch.Tensor:
        """
        Input shape: [batch_size, seq_len] of token IDs
        Returns token logits: [batch_size, seq_len, num_classes]
        """
        x = self.token_embedding(src) * math.sqrt(self.d_model)
        x = self.pos_encoder(x)
        for layer in self.layers:
            x = layer(x, mask)
        return self.token_classifier(x)

    def forward_intent(self, src: torch.Tensor) -> torch.Tensor:
        """
        Classifies short NLP sentences to query intents.
        Returns logits: [batch_size, 4]
        """
        x = self.token_embedding(src) * math.sqrt(self.d_model)
        x = self.pos_encoder(x)
        for layer in self.layers:
            x = layer(x)
        # Global average pooling
        x = x.mean(dim=1)
        return self.intent_classifier(x)

    def generate_embeddings(self, numerical_values: torch.Tensor) -> torch.Tensor:
        """
        Numerical values shape: [batch, 9] (SPH/CYL/AXIS for both eyes, PD)
        Projects to d_model, processes via self-attention, and returns dense vector representation.
        Returns embedding: [batch, d_model]
        """
        # Projects to [batch, 1, d_model]
        x = self.num_projection(numerical_values).unsqueeze(1)
        # Apply layers
        for layer in self.layers:
            x = layer(x)
        # Remove extra dim: [batch, d_model]
        embedding = x.squeeze(1)
        # Normalize to unit length for cosine similarity
        embedding = F.normalize(embedding, p=2, dim=1)
        return embedding

# Instantiate default model
model = PrescriptionTransformer()
model.eval()

# Vocabulary helper for basic keyword matching & index encoding for assistant NLP
VOCAB = ["<pad>", "<unk>", "show", "orders", "delayed", "progressive", "single", "vision", "mumbai", "delhi", "bangalore", "qc", "failed", "customer", "explain"]
word_to_id = {w: idx for idx, w in enumerate(VOCAB)}

def tokenize_query(query: str) -> torch.Tensor:
    tokens = query.lower().split()
    ids = [word_to_id.get(t, 1) for t in tokens]  # fallback to 1 (<unk>)
    # Pad or truncate to fixed length 10
    if len(ids) < 10:
        ids += [0] * (10 - len(ids))
    else:
        ids = ids[:10]
    return torch.tensor([ids], dtype=torch.long)
