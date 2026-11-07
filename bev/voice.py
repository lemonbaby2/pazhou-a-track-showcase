"""离线语音播报。

比赛现场禁止联网，因此只用本地 TTS：
- MockVoice：只打印 + 落日志，用于无音频环境的仿真/CI；
- SapiVoice：Windows 本地 SAPI（离线），适合比赛电脑为 Windows 的情况；
- 也可替换为厂商语音接口（在 adapters 里实现 Voice 协议）。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Optional


class MockVoice:
    def __init__(self, logger=None):
        self.logger = logger

    def say(self, text: str) -> None:
        if self.logger:
            self.logger.log("VOICE", "say", msg=text)


class SapiVoice:
    """Windows 本地离线 SAPI 播报。"""

    def __init__(self, logger=None, rate: int = 0):
        self.logger = logger
        self.rate = rate
        self.available = sys.platform == "win32" and shutil.which("powershell") is not None

    def say(self, text: str) -> None:
        if self.logger:
            self.logger.log("VOICE", "say", msg=text)
        if not self.available:
            return
        ps = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Rate = %d; "
            "$s.Speak([Console]::In.ReadToEnd());"
        ) % self.rate
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                input=text,
                text=True,
                timeout=20,
                capture_output=True,
            )
        except Exception:
            pass


def build_voice(backend: str = "mock", logger=None):
    backend = (backend or "mock").lower()
    if backend == "sapi":
        return SapiVoice(logger=logger)
    return MockVoice(logger=logger)
