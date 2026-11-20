"""
Schema & Link Portability Validator for 7-Section Engineering Plans.
"""

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Dict, List, Optional


MANDATORY_SECTIONS = [
    ("1. Goal Description", re.compile(r"^##\s+1\.\s+Goal\s+Description\b", re.MULTILINE | re.IGNORECASE)),
    (
        "2. Architecture & Workflow Diagram",
        re.compile(r"^##\s+2\.\s+Architecture\s*(?:&|and)\s*Workflow\s+Diagram\b", re.MULTILINE | re.IGNORECASE),
    ),
    (
        "3. Code Modifications",
        re.compile(r"^##\s+3\.\s+(?:Code|Hardware|Implementation)\b", re.MULTILINE | re.IGNORECASE),
    ),
    (
        "4. Test Updates & Specifications",
        re.compile(r"^##\s+4\.\s+Test\s+Updates\s*(?:&|and)\s*Specifications\b", re.MULTILINE | re.IGNORECASE),
    ),
    ("5. Documentation Updates", re.compile(r"^##\s+5\.\s+Documentation\s+Updates\b", re.MULTILINE | re.IGNORECASE)),
    ("6. Verification Plan", re.compile(r"^##\s+6\.\s+Verification\s+Plan\b", re.MULTILINE | re.IGNORECASE)),
]

TITLE_HEADER_RE = re.compile(r"^#\s+(?:Macro\s+)?Plan\s+[A-Z0-9-]+:\s+.+", re.MULTILINE)
MERMAID_BLOCK_RE = re.compile(r"```mermaid\s+[\s\S]+?```", re.MULTILINE)
FENCED_CODE_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")

FORBIDDEN_PATH_PATTERNS = [
    ("/Volumes/", re.compile(r"/Volumes/[A-Za-z0-9_.\-/ ]+")),
    ("/Users/", re.compile(r"/Users/[A-Za-z0-9_.\-/]+")),
    ("/home/", re.compile(r"/home/(?!detour\b)[A-Za-z0-9_.\-/]+")),
    ("file:///", re.compile(r"file:///[A-Za-z0-9_.\-/]+")),
]


@dataclass
class PlanValidationResult:
    plan_path: Path
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _strip_code_spans_for_link_scan(markdown_text: str) -> str:
    """Remove fenced code blocks before scanning markdown hyperlinks."""
    return FENCED_CODE_RE.sub("", markdown_text)


def validate_plan_file(plan_path: Path, workspace_root: Optional[Path] = None) -> PlanValidationResult:
    """
    Validate a plan markdown document against:
    1. Top-level `# Plan <ID>: <Title>` or `# Macro Plan <ID>: <Title>` heading.
    2. All 6 numbered body sections (Sections 1..6, forming the 7 mandatory sections).
    3. At least one ```mermaid diagram block.
    4. Zero hardcoded local workstation paths (/Volumes/, /Users/, file:///).
    5. 100% of relative markdown links resolving to existing files on disk.
    """
    plan_path = Path(plan_path).resolve()
    errors: List[str] = []
    warnings: List[str] = []

    if not plan_path.exists():
        return PlanValidationResult(
            plan_path=plan_path,
            is_valid=False,
            errors=[f"Plan file does not exist: {plan_path}"],
        )

    text = plan_path.read_text(encoding="utf-8")

    # 1. Title header check
    if not TITLE_HEADER_RE.search(text):
        errors.append("Missing top-level '# Plan <ID>: <Title>' or '# Macro Plan <ID>: <Title>' heading.")

    # 2. Mandatory sections 1..6
    for label, pattern in MANDATORY_SECTIONS:
        if not pattern.search(text):
            errors.append(f"Missing mandatory section: '## {label}'")

    # 3. Mermaid diagram check
    if not MERMAID_BLOCK_RE.search(text):
        errors.append("Missing required Mermaid diagram block (```mermaid ... ```) in Section 2.")

    # 4. Forbidden hardcoded paths check
    for label, pattern in FORBIDDEN_PATH_PATTERNS:
        if pattern.search(text):
            errors.append(f"Contains forbidden hardcoded machine path pattern '{label}'.")

    # 5. Relative markdown link resolution check
    scannable = _strip_code_spans_for_link_scan(text)
    for match in MARKDOWN_LINK_RE.finditer(scannable):
        raw_target = match.group(2).strip()
        if not raw_target or raw_target.startswith(("#", "http://", "https://", "mailto:", "conversation://")):
            continue
        if raw_target.startswith("file://"):
            errors.append(f"Non-portable file:// URI link target: {raw_target}")
            continue
        target_path_str = raw_target.split("#", 1)[0].strip()
        if not target_path_str:
            continue
        candidate_paths = [
            (plan_path.parent / target_path_str).resolve(),
            (plan_path.parent.parent / target_path_str).resolve(),
        ]
        if workspace_root is not None:
            candidate_paths.append((Path(workspace_root).resolve() / target_path_str).resolve())
        if not any(c.exists() for c in candidate_paths):
            errors.append(f"Broken relative markdown link '{raw_target}' (resolved to {candidate_paths[0]})")

    return PlanValidationResult(
        plan_path=plan_path,
        is_valid=(len(errors) == 0),
        errors=errors,
        warnings=warnings,
    )


DEFAULT_SUPERVISOR_CONFIG: Dict[str, Any] = {
    "mode": "auto_on_risk",
    "reviewer_model": "pro",
    "min_modified_files": 4,
    "require_for_macro_plans": True,
    "risk_keywords": [
        "database.py",
        "migration",
        "firmware",
        "deploy.sh",
        "agy_bridge",
        "sudoers",
    ],
}

_FILE_MARKER_RE = re.compile(r"\*\*`?\[(?:NEW|MODIFY|DELETE)\]`?\*\*\s+(?:`([^`]+)`|\[[^\]]+\]\(([^)]+)\))", re.IGNORECASE)
_SUPERVISOR_SECTION_RE = re.compile(
    r"^##\s+Supervisor\s+Sign-off\b[^\n]*\n([\s\S]*?)(?=^##\s+|\Z)",
    re.MULTILINE | re.IGNORECASE,
)
_SUPERVISOR_PASS_RE = re.compile(r"\b(?:PASS|APPROVED|SKIPPED)\b", re.IGNORECASE)
_SUPERVISOR_REJECT_RE = re.compile(
    r"(?:(?:verdict|gate\s+[ab]|status)\s*[:\-]\s*(?:NOT\s+APPROVED|BLOCKERS|PENDING|FAILED)\b|^(?:[-*]\s*)?(?:NOT\s+APPROVED|BLOCKERS|PENDING|FAILED)\b)",
    re.MULTILINE | re.IGNORECASE,
)


def has_supervisor_signoff(plan_text: str) -> bool:
    """Returns True iff the `## Supervisor Sign-off` section body has a PASS/APPROVED/SKIPPED token without negative/pending markers."""
    m = _SUPERVISOR_SECTION_RE.search(plan_text or "")
    if not m:
        return False
    body = m.group(1)
    if _SUPERVISOR_REJECT_RE.search(body):
        return False
    return bool(_SUPERVISOR_PASS_RE.search(body))


def classify_plan_risk(
    plan_path: Any,
    supervisor_cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Deterministic, zero-LLM-cost risk classifier for a plan file.
    Flags high-risk plans (Macro M* plans, >= min_modified_files unique file paths, or risk keywords)
    that require Gate A / Gate B Supervisor review when `mode == 'auto_on_risk'`.
    """
    plan_path = Path(plan_path)
    cfg = dict(DEFAULT_SUPERVISOR_CONFIG)
    if isinstance(supervisor_cfg, dict):
        cfg.update(supervisor_cfg)

    reviewer = str(cfg.get("reviewer_model") or "pro")
    mode = str(cfg.get("mode") or "auto_on_risk").strip().lower()
    if mode == "off":
        return {"high_risk": False, "reasons": [], "mode": mode, "reviewer_model": reviewer, "signed_off": True}

    if not plan_path.exists():
        return {
            "high_risk": False,
            "reasons": [],
            "mode": mode,
            "reviewer_model": reviewer,
            "signed_off": False,
            "missing": True,
        }

    text = plan_path.read_text(encoding="utf-8")
    reasons: List[str] = []

    if mode == "always":
        reasons.append("supervisor mode=always")

    if cfg.get("require_for_macro_plans", True):
        if re.match(r"^M\d+\b", plan_path.name) or re.search(r"^#\s+Macro\s+Plan\s+M\d+", text, re.MULTILINE):
            reasons.append("Macro Plan (M*)")

    # Count unique modified/new/deleted file paths (avoid double-counting across Sections 3, 4, 5)
    sec3_match = re.search(r"^##\s+3\.\s+[\s\S]*?(?=^##\s+|\Z)", text, re.MULTILINE)
    scan_text = sec3_match.group(0) if sec3_match else text
    unique_paths = {
        (m.group(1) or m.group(2) or "").strip()
        for m in _FILE_MARKER_RE.finditer(scan_text)
        if (m.group(1) or m.group(2) or "").strip()
    }
    raw_min = cfg.get("min_modified_files")
    min_files = 4 if raw_min is None else int(raw_min)
    if len(unique_paths) >= min_files:
        reasons.append(f"modifies {len(unique_paths)} files (>= {min_files})")

    low_text = text.lower()
    for kw in cfg.get("risk_keywords") or []:
        kw_str = str(kw).strip()
        if kw_str and kw_str.lower() in low_text:
            reasons.append(f"matches risk keyword '{kw_str}'")

    return {
        "high_risk": bool(reasons),
        "reasons": reasons,
        "mode": mode,
        "reviewer_model": reviewer,
        "signed_off": has_supervisor_signoff(text),
    }
