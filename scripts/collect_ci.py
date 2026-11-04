# AI generated from scripts.md; do not edit by hand.
# Pulls grades made by the pr-grader workflow into results/<owner_name>/<run-id>/.
import sys as _sys
if _sys.version_info < (3, 14):
    _sys.exit("this needs Python 3.14+ (argparse color=False); found " + ".".join(map(str, _sys.version_info[:3])))
import argparse, json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def _load_config():
    """Config file (--config arg, else $PRDOCS_CONFIG, else ROOT/active-config.cfg).
    Format: key=value lines; `repo=repos/<name>.md` names the repo file."""
    import os, sys
    path = os.environ.get("PRDOCS_CONFIG") or ROOT / "active-config.cfg"
    for i, x in enumerate(sys.argv):
        if x == "--config" and i + 1 < len(sys.argv):
            path = sys.argv[i + 1]
        elif x.startswith("--config="):
            path = x.split("=", 1)[1]
    path = Path(path).resolve()
    if not path.is_file():
        sys.exit(f"config file not found: {path}")
    kv = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip()
    if "repo" not in kv:
        sys.exit(f"{path}: missing repo=<file>")
    return path, (ROOT / kv["repo"]).resolve()

CONFIG_FILE, REPO_FILE = _load_config()
import os as _os
_os.environ["PRDOCS_CONFIG"] = str(CONFIG_FILE)  # inherited by child scripts


def default_repo():
    m = re.search(r"github\.com/([\w.-]+)/([\w.-]+)", REPO_FILE.read_text())
    return f"{m[1]}/{m[2]}"


def mirror_repo():
    for line in REPO_FILE.read_text().splitlines():
        m = re.search(r"github\.com/([\w.-]+)/([\w.-]+)", line)
        if m and "mirror" in line.lower():
            return f"{m[1]}/{m[2]}"
    return None  # optional: only needed without write access to the main repo


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def main():
    p = argparse.ArgumentParser(color=False)
    p.add_argument("--config", help="config file naming the repo file (default: active-config.cfg)")
    p.add_argument("--mirror")
    p.add_argument("--repo", default=default_repo().replace("/", "_"))
    p.add_argument("--limit", type=int, default=100)
    a = p.parse_args()
    mirror = a.mirror or mirror_repo() or default_repo()  # no mirror: main repo

    # Filter by name: the workflow file lives only on base/* branches, so
    # --workflow may not resolve it.
    runs = [r for r in json.loads(gh("run", "list", "-R", mirror, "--json",
                                     "databaseId,workflowName,status", "-L", str(a.limit)))
            if r["workflowName"] == "pr-grader" and r["status"] == "completed"]
    collected = set()
    for r in runs:
        with tempfile.TemporaryDirectory() as td:
            dl = subprocess.run(["gh", "run", "download", str(r["databaseId"]), "-R", mirror,
                                 "-D", td], capture_output=True, text=True)
            if dl.returncode:
                continue
            for rid in Path(td).rglob("run-id.txt"):
                run_id = rid.read_text().strip()
                for f in rid.parent.glob("*.json"):
                    dest = ROOT / "results" / a.repo / run_id / f.name
                    if dest.exists():
                        continue
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(f, dest)
                    collected.add(int(f.stem))
                    print("collected", run_id, f.stem)

    prs = ROOT / "data" / a.repo / "prs"
    missing = sorted(n for n in collected if not (prs / str(n) / "meta.json").exists())
    if missing:
        subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "fetch_prs.py"),
                        *[x for n in missing for x in ("--pr", str(n))]], check=True)


main()
