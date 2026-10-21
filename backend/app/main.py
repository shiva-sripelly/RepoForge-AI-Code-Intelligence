import os
import re
import json
import base64
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="RepoForge AI", version="1.0.0", description="Public GitHub repository analysis")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8080").split(","), allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])
MAX_FILES = 120
MAX_FILE_BYTES = 100_000
CODE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".rs", ".rb", ".php", ".cs"}
SKIP_PARTS = {"node_modules", "vendor", "dist", "build", ".git", "coverage", ".next", "__pycache__"}

class AnalyzeRequest(BaseModel):
    repository: str = Field(min_length=3, max_length=250)

def parse_repo(value: str):
    value = value.strip().rstrip("/")
    if value.startswith("https://github.com/"):
        parts = urlparse(value).path.strip("/").split("/")
    elif re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        parts = value.split("/")
    else:
        raise HTTPException(422, "Enter a public GitHub URL or owner/repository")
    if len(parts) != 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", p) for p in parts):
        raise HTTPException(422, "Invalid GitHub repository path")
    return parts[0], parts[1].removesuffix(".git")

def github_get(path):
    req = urllib.request.Request("https://api.github.com" + path, headers={"Accept": "application/vnd.github+json", "User-Agent": "RepoForge-AI/1.0", **({"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"]} if os.getenv("GITHUB_TOKEN") else {})})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        if e.code == 404: raise HTTPException(404, "Repository not found or not public")
        if e.code in (403, 429): raise HTTPException(429, "GitHub API rate limit reached. Configure GITHUB_TOKEN.")
        raise HTTPException(502, f"GitHub API returned {e.code}")
    except (urllib.error.URLError, TimeoutError):
        raise HTTPException(502, "Could not reach GitHub")

def scan_text(path, text):
    findings = []
    patterns = [
        ("high", "Possible hardcoded credential", r"(?i)(?:password|secret|api_key|access_token)\s*[:=]\s*['\"]([^'\"\n]{8,})['\"]"),
        ("medium", "Python dynamic execution", r"\b(?:eval|exec)\s*\("),
        ("medium", "Potentially unsafe subprocess shell", r"shell\s*=\s*True"),
        ("low", "Debug statement", r"\b(?:console\.log|debugger\s*;|print)\s*\("),
        ("low", "TODO or FIXME", r"\b(?:TODO|FIXME)\b"),
    ]
    for line_no, line in enumerate(text.splitlines(), 1):
        for severity, title, pattern in patterns:
            if re.search(pattern, line):
                findings.append({"file": path, "line": line_no, "severity": severity, "title": title, "message": "Heuristic match; verify manually before treating as a vulnerability."})
                if len(findings) >= 150: return findings
    return findings

def analyze_files(files):
    findings = []
    extensions = Counter()
    total_lines = 0
    for path, content in files.items():
        ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else "(none)"
        extensions[ext] += 1
        total_lines += len(content.splitlines())
        findings.extend(scan_text(path, content))
    findings = findings[:150]
    counts = Counter(f["severity"] for f in findings)
    score = max(0, 100 - counts["high"] * 12 - counts["medium"] * 5 - counts["low"])
    return {"files_analyzed": len(files), "lines_analyzed": total_lines, "languages_by_extension": dict(extensions.most_common(12)), "findings": findings, "severity_counts": {s: counts[s] for s in ("high", "medium", "low")}, "heuristic_quality_score": score}

@app.get("/api/health")
def health(): return {"status": "ok", "service": "RepoForge AI"}

@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    owner, repo = parse_repo(request.repository)
    metadata = github_get(f"/repos/{owner}/{repo}")
    if metadata.get("private"):
        raise HTTPException(403, "Only public repositories are supported")
    branch = metadata["default_branch"]
    from urllib.parse import quote
    tree = github_get(f"/repos/{owner}/{repo}/git/trees/{quote(branch, safe='')}?recursive=1")
    entries = [x for x in tree.get("tree", []) if x.get("type") == "blob" and x.get("size", 0) <= MAX_FILE_BYTES and x["path"].rsplit(".", 1)[-1].lower() in {e[1:] for e in CODE_EXTENSIONS} and not (set(x["path"].split("/")) & SKIP_PARTS)]
    selected = entries[:MAX_FILES]
    files = {}
    for entry in selected:
        try:
            blob = github_get(f"/repos/{owner}/{repo}/git/blobs/{entry['sha']}")
            if blob.get("encoding") == "base64":
                files[entry["path"]] = base64.b64decode(blob["content"]).decode("utf-8", errors="replace")
        except HTTPException as e:
            if e.status_code == 429: break
            continue
    metrics = analyze_files(files)
    return {"repository": {"full_name": metadata["full_name"], "description": metadata.get("description"), "html_url": metadata["html_url"], "stars": metadata.get("stargazers_count", 0), "forks": metadata.get("forks_count", 0), "language": metadata.get("language"), "default_branch": branch}, "metrics": metrics, "repository_code_files_found": len(entries), "limited_scan": len(selected) < len(entries) or tree.get("truncated", False) or len(files) < len(selected), "analyzed_at": datetime.now(timezone.utc).isoformat(), "disclaimer": "Static heuristic analysis only. Not a security audit or actual test-coverage measurement."}
