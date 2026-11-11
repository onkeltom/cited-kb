"""Minimal numpy forward pass for BERT sentence-embedding models (e.g. BAAI/bge-small-en-v1.5).

No torch needed: weights via safetensors, tokenisation via `tokenizers`.
Usage: from kbbert import Encoder; Encoder("models/bge-small").encode(["text", ...])
Returns L2-normalised CLS embeddings (float32), as sentence-transformers does for bge.
"""
import json
from pathlib import Path
import numpy as np


def _ln(x, g, b, eps):
    m = x.mean(-1, keepdims=True)
    v = ((x - m) ** 2).mean(-1, keepdims=True)
    return (x - m) / np.sqrt(v + eps) * g + b


def _erf_fast(x):
    # high-accuracy rational approximation (max abs error ~1.2e-7)
    t = 1.0 / (1.0 + 0.5 * np.abs(x))
    y = 1 - t * np.exp(-x * x - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 +
        t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 +
        t * (-0.82215223 + t * 0.17087277)))))))))
    return np.where(x >= 0, y, -y).astype(np.float32)


class Encoder:
    def __init__(self, path, max_len=256):
        from safetensors.numpy import load_file
        from tokenizers import Tokenizer
        p = Path(path)
        self.cfg = json.loads((p / "config.json").read_text())
        self.w = load_file(str(p / "model.safetensors"))
        self.tok = Tokenizer.from_file(str(p / "tokenizer.json"))
        self.tok.enable_truncation(max_len)
        self.tok.enable_padding(pad_id=0, pad_token="[PAD]")
        self.h = self.cfg["num_attention_heads"]
        self.eps = self.cfg["layer_norm_eps"]
        self.L = self.cfg["num_hidden_layers"]

    def _lin(self, x, name):
        return x @ self.w[name + ".weight"].T + self.w[name + ".bias"]

    def encode(self, texts, batch=16):
        out = []
        for i in range(0, len(texts), batch):
            out.append(self._forward(texts[i:i + batch]))
        E = np.concatenate(out) if out else np.zeros((0, self.cfg["hidden_size"]), np.float32)
        return E / np.maximum(np.linalg.norm(E, axis=1, keepdims=True), 1e-9)

    def _forward(self, texts):
        enc = self.tok.encode_batch(list(texts))
        ids = np.array([e.ids for e in enc])
        mask = np.array([e.attention_mask for e in enc], np.float32)
        B, T = ids.shape
        w = self.w
        x = (w["embeddings.word_embeddings.weight"][ids]
             + w["embeddings.position_embeddings.weight"][:T][None]
             + w["embeddings.token_type_embeddings.weight"][0][None, None])
        x = _ln(x, w["embeddings.LayerNorm.weight"], w["embeddings.LayerNorm.bias"], self.eps)
        H = x.shape[-1]; d = H // self.h
        bias = ((1.0 - mask) * -1e9)[:, None, None, :]
        for l in range(self.L):
            pre = f"encoder.layer.{l}."
            q = self._lin(x, pre + "attention.self.query").reshape(B, T, self.h, d).transpose(0, 2, 1, 3)
            k = self._lin(x, pre + "attention.self.key").reshape(B, T, self.h, d).transpose(0, 2, 3, 1)
            v = self._lin(x, pre + "attention.self.value").reshape(B, T, self.h, d).transpose(0, 2, 1, 3)
            a = q @ k / np.sqrt(d) + bias
            a = np.exp(a - a.max(-1, keepdims=True)); a /= a.sum(-1, keepdims=True)
            c = (a @ v).transpose(0, 2, 1, 3).reshape(B, T, H)
            x = _ln(x + self._lin(c, pre + "attention.output.dense"),
                    w[pre + "attention.output.LayerNorm.weight"], w[pre + "attention.output.LayerNorm.bias"], self.eps)
            f = _erf_gelu(self._lin(x, pre + "intermediate.dense"))
            x = _ln(x + self._lin(f, pre + "output.dense"),
                    w[pre + "output.LayerNorm.weight"], w[pre + "output.LayerNorm.bias"], self.eps)
        return x[:, 0, :].astype(np.float32)


def _erf_gelu(x):
    return 0.5 * x * (1.0 + _erf_fast(x / np.sqrt(2.0)))
