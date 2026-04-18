"""GPU/CPU device detection for PyTorch models."""

import platform
from typing import Optional

import torch


def get_best_device() -> torch.device:
    try:
        system = platform.system()
        if system == "Darwin":
            if torch.backends.mps.is_available():
                return torch.device("mps")
            return torch.device("cpu")
        else:
            if torch.cuda.is_available():
                return torch.device("cuda")
            return torch.device("cpu")
    except Exception:
        return torch.device("cpu")


def get_device_info() -> dict:
    device = get_best_device()
    info = {"device": str(device), "type": device.type}

    if device.type == "cuda":
        info["name"] = torch.cuda.get_device_name(0)
        info["memory_total_mb"] = torch.cuda.get_device_properties(0).total_mem // (1024 * 1024)
        info["memory_allocated_mb"] = torch.cuda.memory_allocated(0) // (1024 * 1024)
    elif device.type == "mps":
        info["name"] = "Apple Silicon GPU"

    return info
