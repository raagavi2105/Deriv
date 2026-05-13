import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from . import config
from .schemas import LLMLogEntry


def _hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]


def log_llm_call(
    stage: str,
    prompt: str,
    output_artifact: str,
    input_artifacts: List[str],
    few_shot_examples_included: bool = False,
    risk_tier: Optional[str] = None,
    message_id: Optional[int] = None,
) -> None:
    entry = LLMLogEntry(
        stage=stage,
        risk_tier=risk_tier,
        message_id=message_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        provider="Groq",
        model=config.MODEL,
        prompt_hash=_hash_prompt(prompt),
        input_artifacts=input_artifacts,
        output_artifact=output_artifact,
        few_shot_examples_included=few_shot_examples_included,
    )
    with open(config.LLM_LOG_FILE, "a") as f:
        f.write(entry.model_dump_json() + "\n")