"""WorkflowGenerator - loads ComfyUI templates, fills via LLM, validates."""

from __future__ import annotations

import json
import os
import re
from typing import Optional


def _simple_llm_fill(template_json: dict, intent: str) -> dict:
    """Minimal LLM fill: replaces {prompt} with intent, sets reasonable defaults."""
    workflow = template_json.copy()
    workflow.setdefault("nodes", [])

    def replace_prompt(obj):
        if isinstance(obj, dict):
            return {k: replace_prompt(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_prompt(v) for v in obj]
        elif isinstance(obj, str):
            return obj.replace("{prompt}", intent)
        return obj

    return replace_prompt(workflow)


class WorkflowGenerator:
    def __init__(self, templates_path: str = "workflows/templates", logger=None):
        self._templates_path = templates_path
        self._log = logger.info if logger else lambda m: None
        self._templates = {}
        self._load_templates()

    def _load_templates(self):
        # Resolve relative paths relative to the templates_path (not cwd)
        base = self._templates_path
        templates_dir = base if base.endswith("templates") else os.path.join(base, "templates")
        if not os.path.exists(templates_dir):
            os.makedirs(templates_dir, exist_ok=True)
            self._create_defaults(templates_dir)
        for fname in os.listdir(templates_dir):
            if fname.endswith(".json"):
                name = fname[:-5]
                with open(os.path.join(templates_dir, fname)) as f:
                    self._templates[name] = json.load(f)
        self._log(f"Loaded {len(self._templates)} workflow templates: {list(self._templates.keys())}")

    def _create_defaults(self, templates_dir: str = None):
        templates_dir = templates_dir or self._templates_path
        default = {
            "nodes": [
                {"id": 1, "type": "CheckpointLoaderSimple", "attrs": {"model": "sd_xl_base_1.0.safetensors"}},
                {"id": 2, "type": "CLIPTextEncode", "attrs": {"text": "{prompt}"}},
                {"id": 3, "type": "CLIPTextEncode", "attrs": {"text": "masterpiece, best quality"}},
                {"id": 4, "type": "KSampler", "attrs": {"steps": 50, "cfg": 7.0, "seed": 0, "sampler_name": "euler"}},
                {"id": 5, "type": "VAEDecode", "attrs": {}},
                {"id": 6, "type": "SaveImage", "attrs": {"filename_prefix": "MokaGen"}}
            ],
            "links": [[2, 1, 4], [3, 1, 4], [4, 5], [5, 6]]
        }
        for cat in ["portrait", "landscape", "anime", "default"]:
            path = os.path.join(templates_dir, f"{cat}.json")
            if not os.path.exists(path):
                with open(path, "w") as f:
                    json.dump(default, f)

    def match_template(self, intent: str) -> str:
        intent_lower = intent.lower()
        keywords = {
            "portrait": ["portrait", "face", "person", "headshot", "selfie"],
            "landscape": ["landscape", "scenery", "outdoor", "nature", "mountain", "forest"],
            "anime": ["anime", "manga", "cell shaded", "illustrated"],
        }
        for cat, words in keywords.items():
            if any(w in intent_lower for w in words):
                return cat
        return "default"

    def generate(self, intent: str, template_category: Optional[str] = None) -> dict:
        cat = template_category or self.match_template(intent)
        template = self._templates.get(cat, self._templates.get("default"))
        if not template:
            raise ValueError(f"No template found for category: {cat}")
        return _simple_llm_fill(template, intent)

    def validate(self, workflow_json: dict) -> bool:
        """Check it has required nodes and no duplicate IDs."""
        if "nodes" not in workflow_json:
            return False
        ids = [n["id"] for n in workflow_json["nodes"]]
        if len(ids) != len(set(ids)):
            return False
        return True