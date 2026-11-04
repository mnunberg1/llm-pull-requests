# AI generated from scripts.md; do not edit by hand.
# Runs inside the pr-grader workflow in the mirror: grades one mirrored PR.
import sys as _sys
if _sys.version_info < (3, 14):
    _sys.exit("this needs Python 3.14+ (argparse color=False); found " + ".".join(map(str, _sys.version_info[:3])))
import json, os, re, shutil, subprocess, sys
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
MARK = "<!-- pr-grader -->"


def default_repo():
    m = re.search(r"github\.com/([\w.-]+)/([\w.-]+)", REPO_FILE.read_text())
    return f"{m[1]}/{m[2]}"


def ignored(author, title):
    """True if the repo file lists this author or a part of this title as ignored."""
    items, section = {}, None
    for line in REPO_FILE.read_text().splitlines():
        if line.startswith("## "):
            section = line[3:].strip().lower()
        elif section and line.startswith("- "):
            items.setdefault(section, []).append(line[2:].strip().lower())
    return (author.lower() in items.get("ignored authors", [])
            or any(t in title.lower() for t in items.get("ignored titles", [])))


def script(name, *args):
    subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / name), *map(str, args)],
                   check=True)


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def report(res, run_id, n, meta):
    head = f"{MARK}\n"
    if res is None:
        status = ("skipped (ignored)" if meta and ignored(meta["author"], meta["title"])
                  else "grading failed")
        return head + f"**PR grader: {status}** (upstream PR {n}, `{run_id}`)\n"
    lines = [head + f"**PR grader: {res['overall']}/5** (upstream PR {n}, `{run_id}`)", ""]
    for c in res.get("comments", []):
        if isinstance(c, str):
            c = {"sentiment": None, "text": c}
        s = c.get("sentiment")
        lines.append(f"- [{s if s is not None else '?'}] {c['text']}")
    e = res.get("effort")
    if e:
        am, rm = e.get("author_minutes", 0), e.get("review_minutes", 0)
        ratio = f"{rm / am:.1f}x" if am else "-"
        lines += ["", f"effort: author ~{am}m, review ~{rm}m ({ratio})"]
    return "\n".join(lines) + "\n"


def upsert_comment(repo, pr, body):
    ids = gh("api", "--paginate", f"repos/{repo}/issues/{pr}/comments", "--jq",
             f'.[] | select(.body | startswith("{MARK}")) | .id').split()
    if ids:
        gh("api", "-X", "PATCH", f"repos/{repo}/issues/comments/{ids[0]}", "-f", f"body={body}")
    else:
        gh("api", f"repos/{repo}/issues/{pr}/comments", "-f", f"body={body}")


def main():
    m = re.fullmatch(r"pr/(\d+)", os.environ.get("GITHUB_HEAD_REF", ""))
    if not m:
        sys.exit("not a mirrored PR (head ref is not pr/<n>)")
    n = int(m[1])
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    mirror_pr = event["pull_request"]["number"]
    run_id = "ci-" + subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                    check=True, capture_output=True, text=True).stdout.strip()

    out = ROOT / "ci-out"
    out.mkdir(exist_ok=True)
    (out / "run-id.txt").write_text(run_id + "\n")
    meta = res = None
    try:
        script("fetch_prs.py", "--pr", n, "--refresh")
        meta_file = ROOT / "data" / default_repo().replace("/", "_") / "prs" / str(n) / "meta.json"
        meta = json.loads(meta_file.read_text())
        script("grade.py", "--run-id", run_id, "--pr", n, "-j", 1)
        f = ROOT / "results" / default_repo().replace("/", "_") / run_id / f"{n}.json"
        if f.exists():
            res = json.loads(f.read_text())
            shutil.copy(f, out / f.name)
    except (subprocess.CalledProcessError, OSError, ValueError) as e:
        print("error:", e, file=sys.stderr)

    text = report(res, run_id, n, meta)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as fh:
            fh.write(text)
    if os.environ.get("PR_GRADER_MODE", "log") == "comment":
        upsert_comment(os.environ["GITHUB_REPOSITORY"], mirror_pr, text)
    if res is None and "skipped" not in text:
        sys.exit(1)


main()
