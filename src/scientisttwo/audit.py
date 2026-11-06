from __future__ import annotations

import json
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .core import now

DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
ARXIV_RE = re.compile(r"^(?:\d{4}\.\d{4,5}|[a-z.-]+/\d{7})(?:v\d+)?$", re.I)


def _run_json_command(root: Path, command: list[str]) -> tuple[bool, dict[str, Any] | None, str]:
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        return False, None, "command must be a non-empty array of strings"
    try:
        proc = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=3600, check=False)
    except Exception as exc:
        return False, None, str(exc)
    if proc.returncode != 0:
        return False, None, f"exit={proc.returncode}; stderr={proc.stderr[-2000:]}"
    try:
        data = json.loads(proc.stdout)
        if not isinstance(data, dict):
            raise ValueError("stdout JSON must be an object")
        return True, data, "ok"
    except Exception as exc:
        return False, None, f"stdout is not valid JSON: {exc}"


def _verify_doi(doi: str) -> tuple[bool, str]:
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    req = urllib.request.Request(url, headers={"User-Agent": "ScientistTwo-Codex-Audit/0.1 (mailto:research@example.org)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        item = payload.get("message", {})
        return bool(item.get("DOI")), str(item.get("title", ["Crossref record found"])[0])
    except Exception as exc:
        return False, str(exc)


def _verify_arxiv(arxiv_id: str) -> tuple[bool, str]:
    clean_id = re.sub(r"v\d+$", "", arxiv_id)
    url = "https://export.arxiv.org/api/query?id_list=" + urllib.parse.quote(clean_id, safe="")
    req = urllib.request.Request(url, headers={"User-Agent": "ScientistTwo-Codex-Audit/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
        ok = "<entry>" in body and "<id>" in body
        return ok, "arXiv entry found" if ok else "No arXiv entry returned"
    except Exception as exc:
        return False, str(exc)


def run_audit(root: Path, manifest_path: str, online: bool = False) -> dict[str, Any]:
    path = (root / manifest_path).resolve()
    if root.resolve() not in path.parents:
        raise ValueError("Manifest must be inside the project root")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    results: dict[str, Any] = {"created_at": now(), "manifest": str(path.relative_to(root)), "online_reference_check": online}

    # 1. Score verification: replay each claim and compare a JSON metric.
    score_items = []
    for claim in manifest.get("score_claims", []):
        ok, output, detail = _run_json_command(root, claim.get("replay_command", []))
        metric = claim.get("metric")
        if ok:
            values = output.get("metrics", output)
            actual = values.get(metric) if isinstance(values, dict) else None
            expected = claim.get("reported_value")
            tol = float(claim.get("tolerance", 0.0))
            passed = isinstance(actual, (int, float)) and isinstance(expected, (int, float)) and abs(float(actual) - float(expected)) <= tol
            score_items.append({"id": claim.get("id"), "status": "PASS" if passed else "FAIL", "reported": expected, "replayed": actual, "tolerance": tol, "detail": detail if passed else "metric missing or outside tolerance"})
        else:
            score_items.append({"id": claim.get("id"), "status": "FAIL", "detail": detail})
    results["score_verification"] = {"status": "INCOMPLETE" if not score_items else ("PASS" if all(x["status"] == "PASS" for x in score_items) else "FAIL"), "items": score_items}

    # Agent attestations are required for semantic checks that cannot be reduced to file/path tests.
    attestations = {item.get("agent"): item for item in manifest.get("agent_attestations", []) if item.get("agent")}
    attestation_items = []
    for agent_name in ("spec_validator", "reference_verifier", "method_code_auditor"):
        item = attestations.get(agent_name)
        if not item:
            attestation_items.append({"agent": agent_name, "status": "INCOMPLETE", "detail": "No agent attestation supplied"})
            continue
        report_path = item.get("report_path")
        report_exists = False
        if report_path:
            candidate_path = (root / report_path).resolve()
            report_exists = root.resolve() in candidate_path.parents and candidate_path.exists()
        passed = item.get("status") == "PASS" and report_exists
        attestation_items.append({"agent": agent_name, "status": "PASS" if passed else "INCOMPLETE", "report_path": report_path, "detail": "PASS requires status=PASS and an existing report file"})
    results["agent_attestations"] = {"status": "PASS" if all(x["status"] == "PASS" for x in attestation_items) else "INCOMPLETE", "items": attestation_items}

    # 2. Specification compliance: benchmark-specific commands must exit zero.
    spec_items = []
    for check in manifest.get("specification_checks", []):
        command = check.get("command", [])
        if not isinstance(command, list) or not command:
            spec_items.append({"id": check.get("id"), "status": "FAIL", "detail": "missing command"})
            continue
        try:
            proc = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=3600, check=False)
            passed = proc.returncode == 0
            spec_items.append({"id": check.get("id"), "status": "PASS" if passed else "FAIL", "exit_code": proc.returncode, "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:]})
        except Exception as exc:
            spec_items.append({"id": check.get("id"), "status": "FAIL", "detail": str(exc)})
    spec_commands_pass = bool(spec_items) and all(x["status"] == "PASS" for x in spec_items)
    spec_attested = attestations.get("spec_validator", {}).get("status") == "PASS"
    results["specification_compliance"] = {"status": "PASS" if spec_commands_pass and spec_attested and results["agent_attestations"]["items"][0]["status"] == "PASS" else ("FAIL" if any(x["status"] == "FAIL" for x in spec_items) else "INCOMPLETE"), "items": spec_items, "semantic_agent_attestation": spec_attested}

    # 3. Reference verification: syntax-only offline; Crossref/arXiv lookup online.
    ref_items = []
    for ref in manifest.get("references", []):
        doi = ref.get("doi")
        arxiv_id = ref.get("arxiv_id")
        if doi:
            if not DOI_RE.match(doi):
                ref_items.append({"id": ref.get("id"), "status": "FAIL", "detail": "invalid DOI syntax"})
            elif online:
                ok, detail = _verify_doi(doi)
                ref_items.append({"id": ref.get("id"), "status": "PASS" if ok else "FAIL", "detail": detail})
            else:
                ref_items.append({"id": ref.get("id"), "status": "INCOMPLETE", "detail": "DOI syntax valid; run with --online to verify Crossref record"})
        elif arxiv_id:
            if not ARXIV_RE.match(arxiv_id):
                ref_items.append({"id": ref.get("id"), "status": "FAIL", "detail": "invalid arXiv identifier syntax"})
            elif online:
                ok, detail = _verify_arxiv(arxiv_id)
                ref_items.append({"id": ref.get("id"), "status": "PASS" if ok else "FAIL", "detail": detail})
            else:
                ref_items.append({"id": ref.get("id"), "status": "INCOMPLETE", "detail": "arXiv syntax valid; run with --online to verify record"})
        else:
            ref_items.append({"id": ref.get("id"), "status": "FAIL", "detail": "reference has neither DOI nor arXiv ID"})
    ref_records_pass = bool(ref_items) and all(x["status"] == "PASS" for x in ref_items)
    ref_attested = attestations.get("reference_verifier", {}).get("status") == "PASS"
    results["reference_verification"] = {"status": "PASS" if ref_records_pass and ref_attested and results["agent_attestations"]["items"][1]["status"] == "PASS" else ("FAIL" if any(x["status"] == "FAIL" for x in ref_items) else "INCOMPLETE"), "items": ref_items, "semantic_agent_attestation": ref_attested}

    # 4. Method-code alignment: structural path traceability; semantic review remains an LLM/human task.
    align_items = []
    for mapping in manifest.get("method_code_mappings", []):
        missing = []
        for raw in mapping.get("code_paths", []) + mapping.get("evidence_paths", []):
            candidate = (root / raw).resolve()
            if root.resolve() not in candidate.parents and candidate != root.resolve():
                missing.append(f"path escapes project: {raw}")
            elif not candidate.exists():
                missing.append(f"missing: {raw}")
        enough = bool(mapping.get("claim")) and bool(mapping.get("paper_section")) and bool(mapping.get("code_paths")) and bool(mapping.get("evidence_paths"))
        passed = enough and not missing
        align_items.append({"claim": mapping.get("claim"), "status": "PASS" if passed else "FAIL", "missing": missing, "note": "Path traceability only; semantic alignment must be reviewed by method_code_auditor."})
    alignment_paths_pass = bool(align_items) and all(x["status"] == "PASS" for x in align_items)
    alignment_attested = attestations.get("method_code_auditor", {}).get("status") == "PASS"
    results["method_code_alignment"] = {"status": "PASS" if alignment_paths_pass and alignment_attested and results["agent_attestations"]["items"][2]["status"] == "PASS" else ("FAIL" if any(x["status"] == "FAIL" for x in align_items) else "INCOMPLETE"), "items": align_items, "semantic_agent_attestation": alignment_attested}

    statuses = [results[k]["status"] for k in ("score_verification", "specification_compliance", "reference_verification", "method_code_alignment")]
    results["overall"] = "PASS" if all(s == "PASS" for s in statuses) else ("FAIL" if "FAIL" in statuses else "INCOMPLETE")
    out_dir = root / "research" / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "audit-report.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return results
