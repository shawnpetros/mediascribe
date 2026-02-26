"""Hardware detection for concurrency and model selection recommendations."""

from __future__ import annotations

import platform
from dataclasses import dataclass

import psutil


@dataclass
class HardwareProfile:
    """Detected hardware capabilities."""

    cpu_count: int
    cpu_brand: str
    ram_gb: float
    has_gpu: bool
    gpu_name: str | None
    os_name: str
    arch: str

    @property
    def recommended_concurrency(self) -> int:
        """Suggest max concurrent jobs based on hardware."""
        if self.ram_gb < 8:
            return 1
        if self.ram_gb < 16:
            return 2
        return min(4, self.cpu_count // 2)

    @property
    def recommended_compute_type(self) -> str:
        """Suggest Whisper compute type."""
        if self.has_gpu:
            return "float16"
        if self.arch == "arm64":
            return "int8"  # Apple Silicon, optimized
        return "int8"

    @property
    def recommended_whisper_device(self) -> str:
        if self.has_gpu:
            return "cuda"
        return "auto"  # lets ctranslate2 decide (cpu or coreml)


def detect_hardware() -> HardwareProfile:
    """Detect current hardware capabilities."""
    has_gpu = False
    gpu_name = None

    # Check for CUDA GPU
    try:
        import torch

        if torch.cuda.is_available():
            has_gpu = True
            gpu_name = torch.cuda.get_device_name(0)
    except ImportError:
        pass

    # Check for Apple Silicon MPS
    if not has_gpu and platform.machine() == "arm64" and platform.system() == "Darwin":
        gpu_name = "Apple Silicon (MPS)"
        # Not setting has_gpu=True because faster-whisper uses CPU/CoreML on Mac

    return HardwareProfile(
        cpu_count=psutil.cpu_count(logical=True) or 1,
        cpu_brand=platform.processor() or "unknown",
        ram_gb=psutil.virtual_memory().total / (1024**3),
        has_gpu=has_gpu,
        gpu_name=gpu_name,
        os_name=platform.system(),
        arch=platform.machine(),
    )


def estimate_transcription_time(duration_sec: float, hw: HardwareProfile) -> tuple[float, float]:
    """Estimate transcription time in minutes (min, max).

    Based on observed benchmarks:
    - Apple Silicon M-series: ~2-4x real-time for large-v3
    - CUDA GPU: ~0.5-1.5x real-time
    - CPU only: ~4-8x real-time
    """
    duration_min = duration_sec / 60

    if hw.has_gpu:
        return (duration_min * 0.5, duration_min * 1.5)
    if hw.arch == "arm64":
        return (duration_min * 1.5, duration_min * 3.5)
    return (duration_min * 4, duration_min * 8)
