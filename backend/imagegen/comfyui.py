"""ComfyUI adapter: local SDXL/FLUX via ComfyUI's HTTP API.

Flow: queue a workflow (``POST /prompt``) → poll ``GET /history/{prompt_id}``
until outputs appear → download the first image via ``GET /view``. The
workflow is a template JSON under ``workflows/`` (named by
``imagegen.comfyui.workflow``); prompt text, dimensions and sampler settings
are injected by inspecting the graph rather than string placeholders, so any
API-format workflow with a KSampler + EmptyLatentImage works.
"""

from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path
from typing import Any

import httpx

from backend.core.config import ComfyUIConfig
from backend.imagegen.base import ImageGenerator
from backend.prompting.base import OptimizedPrompt

WORKFLOWS_DIR = Path(__file__).resolve().parent / "workflows"
_POLL_INTERVAL_S = 0.5


class ComfyUIGenerator(ImageGenerator):
    name = "comfyui"

    def __init__(self, images_dir: Path, cfg: ComfyUIConfig) -> None:
        super().__init__(images_dir)
        self._cfg = cfg
        self._workflow_path = WORKFLOWS_DIR / f"{cfg.workflow}.json"
        if not self._workflow_path.exists():
            raise RuntimeError(
                f"ComfyUI workflow {cfg.workflow!r} not found at {self._workflow_path}"
            )
        # Fail at construction when the server isn't reachable so the factory
        # can skip this backend (same pattern as HF's missing-token check).
        try:
            httpx.Client(timeout=2.0).get(f"{cfg.url}/system_stats").raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"ComfyUI not reachable at {cfg.url}: {exc}") from exc

    async def _fetch(self, prompt: OptimizedPrompt, width: int, height: int) -> bytes:
        workflow = json.loads(self._workflow_path.read_text(encoding="utf-8"))
        _inject(workflow, prompt, width, height)

        async with httpx.AsyncClient(timeout=self._cfg.timeout_s) as client:
            resp = await client.post(f"{self._cfg.url}/prompt", json={"prompt": workflow})
            resp.raise_for_status()
            prompt_id = resp.json().get("prompt_id")
            if not prompt_id:
                raise RuntimeError(f"ComfyUI queue rejected the workflow: {resp.json()}")

            image_ref = await self._poll_history(client, prompt_id)

            resp = await client.get(
                f"{self._cfg.url}/view",
                params={
                    "filename": image_ref["filename"],
                    "subfolder": image_ref.get("subfolder", ""),
                    "type": image_ref.get("type", "output"),
                },
            )
            resp.raise_for_status()
            return resp.content

    async def _poll_history(self, client: httpx.AsyncClient, prompt_id: str) -> dict:
        """Wait until the queued prompt has outputs; return the first image ref."""
        deadline = asyncio.get_event_loop().time() + self._cfg.timeout_s
        while asyncio.get_event_loop().time() < deadline:
            resp = await client.get(f"{self._cfg.url}/history/{prompt_id}")
            resp.raise_for_status()
            entry = resp.json().get(prompt_id) or {}
            status = entry.get("status") or {}
            if status.get("status_str") == "error":
                raise RuntimeError(f"ComfyUI workflow failed: {status}")
            for node_output in (entry.get("outputs") or {}).values():
                images = node_output.get("images") or []
                if images:
                    return images[0]
            await asyncio.sleep(_POLL_INTERVAL_S)
        raise RuntimeError(f"ComfyUI generation timed out after {self._cfg.timeout_s}s")


def _inject(workflow: dict[str, Any], prompt: OptimizedPrompt, width: int, height: int) -> None:
    """Fill prompt/sampler/dimension fields in an API-format workflow graph."""
    sampler = next(
        (n for n in workflow.values() if n.get("class_type", "").startswith("KSampler")), None
    )
    if sampler is None:
        raise RuntimeError("workflow has no KSampler node — cannot inject prompt")
    inputs = sampler["inputs"]
    inputs["seed"] = prompt.seed if prompt.seed is not None else random.randrange(2**31)
    inputs["cfg"] = prompt.guidance
    inputs["steps"] = prompt.steps

    # The KSampler's positive/negative inputs point at the text-encode nodes.
    for key, text in (("positive", prompt.positive), ("negative", prompt.negative)):
        node_ref = inputs.get(key)
        if isinstance(node_ref, list) and node_ref and str(node_ref[0]) in workflow:
            workflow[str(node_ref[0])]["inputs"]["text"] = text

    for node in workflow.values():
        if node.get("class_type") == "EmptyLatentImage":
            node["inputs"]["width"] = width
            node["inputs"]["height"] = height
