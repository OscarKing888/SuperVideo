"""TOPIQ aesthetic quality scoring model."""

from abc import ABC, abstractmethod
from typing import Optional
import copy
import os
import sys
from collections import OrderedDict
from pathlib import Path

import numpy as np
import torch
from torch import nn
import torch.nn.functional as F
import torchvision.transforms.functional as TF
import torchvision.transforms as T
from PIL import Image
import timm

from supervideo_bird_classifier.device import get_best_device

_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]


class Scorer(ABC):
    @abstractmethod
    def score(self, image: Image.Image) -> Optional[float]:
        ...


def _get_clones(module, n):
    return nn.ModuleList([copy.deepcopy(module) for _ in range(n)])


def _get_activation_fn(activation):
    if activation == "relu":
        return F.relu
    if activation == "gelu":
        return F.gelu
    raise RuntimeError(f"Unknown activation: {activation}")


def _dist_to_mos(dist_score: torch.Tensor) -> torch.Tensor:
    num_classes = dist_score.shape[-1]
    mos_score = dist_score * torch.arange(1, num_classes + 1).to(dist_score)
    return mos_score.sum(dim=-1, keepdim=True)


class _TransformerEncoderLayer(nn.Module):
    def __init__(self, d_model, nhead, dim_feedforward=2048, dropout=0.1, activation="gelu"):
        super().__init__()
        self.self_attn = nn.MultiheadAttention(d_model, nhead, dropout=dropout)
        self.linear1 = nn.Linear(d_model, dim_feedforward)
        self.dropout = nn.Dropout(dropout)
        self.linear2 = nn.Linear(dim_feedforward, d_model)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.dropout1 = nn.Dropout(dropout)
        self.dropout2 = nn.Dropout(dropout)
        self.activation = _get_activation_fn(activation)

    def forward(self, src):
        src2 = self.norm1(src)
        src2, _ = self.self_attn(src2, src2, value=src2)
        src = src + self.dropout1(src2)
        src2 = self.norm2(src)
        src2 = self.linear2(self.dropout(self.activation(self.linear1(src2))))
        return src + self.dropout2(src2)


class _TransformerDecoderLayer(nn.Module):
    def __init__(self, d_model, nhead, dim_feedforward=2048, dropout=0.1, activation="gelu"):
        super().__init__()
        self.multihead_attn = nn.MultiheadAttention(d_model, nhead, dropout=dropout)
        self.linear1 = nn.Linear(d_model, dim_feedforward)
        self.dropout = nn.Dropout(dropout)
        self.linear2 = nn.Linear(dim_feedforward, d_model)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.norm3 = nn.LayerNorm(d_model)
        self.dropout2 = nn.Dropout(dropout)
        self.dropout3 = nn.Dropout(dropout)
        self.activation = _get_activation_fn(activation)

    def forward(self, tgt, memory):
        memory = self.norm2(memory)
        tgt2 = self.norm1(tgt)
        tgt2, _ = self.multihead_attn(query=tgt2, key=memory, value=memory)
        tgt = tgt + self.dropout2(tgt2)
        tgt2 = self.norm3(tgt)
        tgt2 = self.linear2(self.dropout(self.activation(self.linear1(tgt2))))
        return tgt + self.dropout3(tgt2)


class _TransformerEncoder(nn.Module):
    def __init__(self, layer, num_layers):
        super().__init__()
        self.layers = _get_clones(layer, num_layers)

    def forward(self, src):
        for layer in self.layers:
            src = layer(src)
        return src


class _TransformerDecoder(nn.Module):
    def __init__(self, layer, num_layers):
        super().__init__()
        self.layers = _get_clones(layer, num_layers)

    def forward(self, tgt, memory):
        for layer in self.layers:
            tgt = layer(tgt, memory)
        return tgt


class _GatedConv(nn.Module):
    def __init__(self, dim, ksz=3):
        super().__init__()
        self.splitconv = nn.Conv2d(dim, dim * 2, 1, 1, 0)
        self.act = nn.GELU()
        self.weight_blk = nn.Sequential(
            nn.Conv2d(dim, 64, 1, stride=1),
            nn.GELU(),
            nn.Conv2d(64, 64, ksz, stride=1, padding=1),
            nn.GELU(),
            nn.Conv2d(64, 1, ksz, stride=1, padding=1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        x1, x2 = self.splitconv(x).chunk(2, dim=1)
        return self.act(x1) * self.weight_blk(x2)


class CFANet(nn.Module):
    def __init__(
        self,
        backbone="resnet50",
        num_class=10,
        inter_dim=512,
        num_heads=4,
        num_attn_layers=1,
        dprate=0.1,
        activation="gelu",
    ):
        super().__init__()
        self.num_class = num_class

        self.semantic_model = timm.create_model(backbone, pretrained=False, features_only=True)
        feat_dims = self.semantic_model.feature_info.channels()

        self.default_mean = torch.Tensor(_IMAGENET_MEAN).view(1, 3, 1, 1)
        self.default_std = torch.Tensor(_IMAGENET_STD).view(1, 3, 1, 1)

        act = nn.GELU() if activation == "gelu" else nn.ReLU()
        dim_ff = min(4 * inter_dim, 2048)

        enc_layer = _TransformerEncoderLayer(inter_dim, num_heads, dim_ff, dprate, activation)

        self.sa_attn_blks = nn.ModuleList()
        self.dim_reduce = nn.ModuleList()
        self.weight_pool = nn.ModuleList()

        for dim in feat_dims:
            self.weight_pool.append(_GatedConv(dim))
            self.dim_reduce.append(nn.Sequential(nn.Conv2d(dim, inter_dim, 1, 1), act))
            self.sa_attn_blks.append(_TransformerEncoder(enc_layer, num_attn_layers))

        dec_layer = _TransformerDecoderLayer(inter_dim, num_heads, dim_ff, dprate, activation)
        self.attn_blks = nn.ModuleList()
        for _ in range(len(feat_dims) - 1):
            self.attn_blks.append(_TransformerDecoder(dec_layer, num_attn_layers))

        self.attn_pool = _TransformerEncoderLayer(inter_dim, num_heads, dim_ff, dprate, activation)
        self.score_linear = nn.Sequential(
            nn.LayerNorm(inter_dim),
            nn.Linear(inter_dim, inter_dim), act,
            nn.LayerNorm(inter_dim),
            nn.Linear(inter_dim, inter_dim), act,
            nn.Linear(inter_dim, num_class),
            nn.Softmax(dim=-1),
        )
        self.h_emb = nn.Parameter(torch.randn(1, inter_dim // 2, 32, 1))
        self.w_emb = nn.Parameter(torch.randn(1, inter_dim // 2, 1, 32))
        nn.init.trunc_normal_(self.h_emb.data, std=0.02)
        nn.init.trunc_normal_(self.w_emb.data, std=0.02)

    def forward(self, x):
        x = (x - self.default_mean.to(x)) / self.default_std.to(x)
        feats = self.semantic_model(x)

        for m in self.semantic_model.modules():
            if isinstance(m, nn.BatchNorm2d):
                m.eval()

        _, _, th, tw = feats[-1].shape
        pos_emb = torch.cat(
            (self.h_emb.repeat(1, 1, 1, self.w_emb.shape[3]),
             self.w_emb.repeat(1, 1, self.h_emb.shape[2], 1)),
            dim=1,
        )

        tokens = []
        for i in reversed(range(len(feats))):
            f = self.weight_pool[i](feats[i])
            if f.shape[2] > th and f.shape[3] > tw:
                f = F.adaptive_avg_pool2d(f, (th, tw))
            pe = F.interpolate(pos_emb, size=f.shape[2:], mode="bicubic", align_corners=False)
            f = self.dim_reduce[i](f).flatten(2).permute(2, 0, 1) + pe.flatten(2).permute(2, 0, 1)
            tokens.append(self.sa_attn_blks[i](f))

        query = tokens[0]
        for i in range(len(tokens) - 1):
            query = self.attn_blks[i](query, tokens[i + 1])

        out = self.attn_pool(query)
        score = self.score_linear(out.mean(dim=0))
        return _dist_to_mos(score)


def _get_weight_path() -> str:
    name = "cfanet_iaa_ava_res50-3cd62bb3.pth"
    search = []
    if hasattr(sys, "_MEIPASS"):
        search.append(os.path.join(sys._MEIPASS, "models", name))
    base = Path(__file__).parent.parent.parent
    search.append(str(base / "models" / name))
    for p in search:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"TOPIQ weights not found. Searched: {search}")


class TOPIQScorer(Scorer):
    def __init__(self, device: Optional[torch.device] = None):
        self.device = device or get_best_device()
        self._model: Optional[CFANet] = None

    def _load_model(self) -> CFANet:
        if self._model is None:
            weight_path = _get_weight_path()
            self._model = CFANet()
            state_dict = torch.load(weight_path, map_location=self.device, weights_only=True)
            if "params" in state_dict:
                state_dict = state_dict["params"]
            cleaned = OrderedDict()
            for k, v in state_dict.items():
                cleaned[k[7:] if k.startswith("module.") else k] = v
            self._model.load_state_dict(cleaned, strict=False)
            self._model.to(self.device)
            self._model.eval()
        return self._model

    def score(self, image: Image.Image) -> Optional[float]:
        try:
            model = self._load_model()
            if image.mode != "RGB":
                image = image.convert("RGB")
            image = image.resize((384, 384), Image.LANCZOS)
            tensor = T.ToTensor()(image).unsqueeze(0).to(self.device)
            with torch.no_grad():
                result = model(tensor)
            val = result.item() if isinstance(result, torch.Tensor) else float(result)
            return max(1.0, min(10.0, val))
        except Exception:
            return None


_scorer_singleton: Optional[TOPIQScorer] = None


def get_scorer(**kwargs) -> TOPIQScorer:
    global _scorer_singleton
    if _scorer_singleton is None:
        _scorer_singleton = TOPIQScorer(**kwargs)
    return _scorer_singleton
