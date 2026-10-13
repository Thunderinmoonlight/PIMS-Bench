"""Centralized configuration for SkillRefine experiments.

All configuration is loaded from environment variables or .env file.
No hardcoded secrets or paths.

Usage:
    from skillrefine.config import Config
    cfg = Config()
    print(cfg.llm_api_base)
    print(cfg.model_paths["WS"])
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if present
except ImportError:
    pass  # dotenv is optional


def _get_project_root() -> Path:
    """Get project root directory (parent of skillrefine/)."""
    return Path(__file__).resolve().parent.parent


class Config:
    """Centralized configuration loaded from environment variables."""

    def __init__(self, env_file: Optional[str] = None):
        """Initialize configuration.

        Args:
            env_file: Optional path to .env file. If None, uses default .env in project root.
        """
        if env_file:
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
            except ImportError:
                pass

        self.project_root = _get_project_root()

        # LLM API Configuration
        self.llm_api_base = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
        self.llm_api_key = os.getenv("LLM_API_KEY", "")

        # Model paths
        self.model_paths = {
            "WS": {
                "model_dir": os.getenv(
                    "PIMS_MODEL_WS_DIR",
                    str(self.project_root / "data" / "models" / "Weight Sample Experiment")
                ),
                "base_objective": 1036.12,
            },
            "GC": {
                "model_dir": os.getenv(
                    "PIMS_MODEL_GC_DIR",
                    str(self.project_root / "data" / "models" / "Gulf Coast Experiment")
                ),
                "base_objective": 1341.02,
            },
        }

        # Add xls_path dynamically
        for model_key, cfg in self.model_paths.items():
            model_dir = cfg["model_dir"]
            if model_key == "WS":
                cfg["xls_path"] = os.path.join(model_dir, "sample.xls")
            else:
                cfg["xls_path"] = os.path.join(model_dir, "Gulf_Coast.xls")

        # Data paths
        self.data_dir = Path(os.getenv("DATA_DIR", str(self.project_root / "data")))
        self.results_dir = Path(os.getenv("RESULTS_DIR", str(self.project_root / "results")))
        self.skill_libraries_dir = Path(os.getenv(
            "SKILL_LIBRARIES_DIR",
            str(self.project_root / "skill_libraries")
        ))

        # Excel JSON directories
        self.excel_json_ws = self.data_dir / "excel_json"
        self.excel_json_gc = self.data_dir / "excel_json_gc"

        # Knowledge base directory (PIMS documentation)
        self.knowledge_base_dir = Path(os.getenv(
            "KNOWLEDGE_BASE_DIR",
            str(self.data_dir / "knowledge-base")
        ))

        # Benchmark paths
        self.bench_train_path = self.data_dir / "benchmarks" / "bench_train.json"
        self.bench_eval_path = self.data_dir / "benchmarks" / "bench_eval.json"

        # Experiment settings
        self.max_agent_steps = int(os.getenv("MAX_AGENT_STEPS", "50"))
        self.default_model = os.getenv("DEFAULT_MODEL", "deepseek-pro")
        self.temperature = float(os.getenv("TEMPERATURE", "0.5"))
        self.max_tokens = int(os.getenv("MAX_TOKENS", "8192"))

        # Available models
        self.available_models = {
            "deepseek-pro": "DeepSeek-V4-Pro",
            "deepseek-flash": "DeepSeek-V4-Flash",
            "gemma-31b": "gemma-4-31B-it",
            "qwen-27b": "qwen3-27b-fp8",
        }

        # Experimental conditions (matching paper)
        self.conditions = [
            "baseline",           # No external knowledge
            "doconly",            # + raw documentation
            "skill_base",         # + unrefined skills (Phase 1-3)
            "skill_refined",      # + refined skills (Phase 4, SkillRefine)
            "trace2skill",        # Trace2Skill baseline
            "skillopt",           # SkillOpt baseline
        ]

        self.ablation_conditions = [
            "ablation_no_signal1",  # w/o compliance filter (Stage 1)
            "ablation_no_signal2",  # w/o match decomposition (Stage 2)
        ]

        # Condition display names
        self.condition_display = {
            "baseline": "Baseline",
            "doconly": "DocOnly",
            "skill_base": "SkillBase",
            "skill_refined": "SkillRefine",
            "trace2skill": "Trace2Skill",
            "skillopt": "SkillOpt",
            "ablation_no_signal1": "w/o Signal 1",
            "ablation_no_signal2": "w/o Signal 2",
        }

        # Tool assignment per condition (matching paper Table 3)
        self.condition_tools = {
            "baseline": ["list_sheets", "read_sheet", "read_cell", "write_case", "run_pims"],
            "doconly": ["list_sheets", "read_sheet", "read_cell", "write_case", "run_pims", "read_doc"],
            "skill_base": ["list_sheets", "read_sheet", "read_cell", "write_case", "run_pims",
                          "read_doc", "read_skill"],
            "skill_refined": ["list_sheets", "read_sheet", "read_cell", "write_case", "run_pims",
                             "read_doc", "read_skill"],
            "trace2skill": ["list_sheets", "read_sheet", "read_cell", "write_case", "run_pims",
                           "read_doc", "read_skill"],
            "skillopt": ["list_sheets", "read_sheet", "read_cell", "write_case", "run_pims",
                        "read_doc", "read_skill"],
            "ablation_no_signal1": ["list_sheets", "read_sheet", "read_cell", "write_case",
                                    "run_pims", "read_doc", "read_skill"],
            "ablation_no_signal2": ["list_sheets", "read_sheet", "read_cell", "write_case",
                                    "run_pims", "read_doc", "read_skill"],
        }

        # Skill library mapping per condition
        self.skill_library_mapping = {
            "skill_base": "SKILL_BASE",
            "skill_refined": "SKILL_REFINED",
            "trace2skill": "SKILL_TRACE2SKILL",
            "skillopt": "SKILL_SKILLOPT",
            "ablation_no_signal1": "SKILL_STAGE2",  # refined with Signal 2 only
            "ablation_no_signal2": "SKILL_STAGE1",  # refined with Signal 1 only
        }

    def get_model_id(self, model_key: str) -> str:
        """Get full model ID from short key.

        Args:
            model_key: Short model key (e.g., "deepseek-pro")

        Returns:
            Full model ID (e.g., "DeepSeek-V4-Pro")
        """
        return self.available_models.get(model_key, model_key)

    def get_skill_library_path(self, condition: str) -> Path:
        """Get skill library path for a given condition.

        Args:
            condition: Experimental condition name

        Returns:
            Path to skill library directory
        """
        lib_name = self.skill_library_mapping.get(condition, "SKILL_BASE")
        return self.skill_libraries_dir / lib_name

    def validate(self) -> bool:
        """Validate configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        errors = []

        if not self.llm_api_key:
            errors.append("LLM_API_KEY not set")

        if not self.llm_api_base:
            errors.append("LLM_API_BASE not set")

        for model_key, cfg in self.model_paths.items():
            if not os.path.exists(cfg["model_dir"]):
                errors.append(f"Model directory not found for {model_key}: {cfg['model_dir']}")

        if errors:
            print("Configuration errors:")
            for err in errors:
                print(f"  - {err}")
            return False

        return True

    def __repr__(self) -> str:
        return (
            f"Config(llm_api_base={self.llm_api_base!r}, "
            f"default_model={self.default_model!r}, "
            f"project_root={self.project_root!r})"
        )


# Global config instance (lazy initialization)
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
