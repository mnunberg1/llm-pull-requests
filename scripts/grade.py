# AI generated from scripts.md; do not edit by hand.
import sys as _sys
if _sys.version_info < (3, 14):
    _sys.exit("this needs Python 3.14+ (argparse color=False); found " + ".".join(map(str, _sys.version_info[:3])))
import argparse, re, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
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

MAX_DIFF = 150_000

OUTPUT_FORMAT = """Return ONLY a JSON object, no prose, no code fences:
{"pr": <number>, "scores": {"atomicity": <integer 1-5>, "description": <integer 1-5>, "readability": <integer 1-5>, "test_readability": <integer 1-5, or null if no test files changed>}, "files": [{"path": "<path as in the diff>", "readability": <integer 1-5>}, ...], "comments": [{"sentiment": <integer 1-5>, "text": "<comment>"}, ...], "effort": {"author_minutes": <integer>, "review_minutes": <integer>}}
"""

# Weights of the three scores in the overall grade (they sum to 1).
WEIGHTS = {"readability": 0.75, "atomicity": 0.125, "description": 0.125}


def overall(scores):
    """Weighted average of the three scores, rounded half up (readability is the source code's)."""
    return int(sum(w * scores[k] for k, w in WEIGHTS.items()) + 0.5)


def score_ok(v):
    return isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 5


def check_scores(res):
    """Return the scores (the three, and test_readability or None), or raise ValueError."""
    scores = res.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("no scores")
    out = {k: scores[k] for k in WEIGHTS}
    if not all(score_ok(v) for v in out.values()):
        raise ValueError("scores must be integers 1-5")
    tr = scores.get("test_readability")
    if tr is not None and not score_ok(tr):
        raise ValueError("test_readability must be an integer 1-5 or null")
    return {**out, "test_readability": tr}


def section_paths(label):
    """Path prefixes listed under `label` in the repo file's `Size classification` section."""
    paths, on = [], False
    for line in REPO_FILE.read_text().splitlines():
        if line.startswith("## "):
            on = line[3:].strip().lower() == "size classification"
        elif on and line.rstrip(":").strip().lower() == label:
            paths.append(None)
        elif on and paths and line.startswith("- "):
            paths.append(line[2:].split(" (")[0].strip())
        elif on and paths and line.strip() and not line.startswith("- "):
            break
    return [x for x in paths if x]


def is_test(path):
    return any(path.startswith(x) for x in section_paths("test paths"))


def changed_lines(diff):
    """{path: added + deleted lines, not counting blank or comment-only lines}."""
    out, path = {}, None
    for line in diff.splitlines():
        if line.startswith("diff --git"):
            path = line.split(" b/", 1)[-1]
            out.setdefault(path, 0)
        elif path and line[:1] in "+-" and not line.startswith(("+++", "---")):
            text = line[1:].strip()
            if text and not text.startswith(("//", "#", "/*", "*", "*/")):
                out[path] += 1
    return out


def file_scores(res, lines):
    """The model's per-file readability, for files in the diff, with the test flag and line count."""
    out, seen = [], set()
    for f in res.get("files") or []:
        if not isinstance(f, dict) or f.get("path") not in lines or f["path"] in seen \
                or not score_ok(f.get("readability")):
            continue
        seen.add(f["path"])
        out.append({"path": f["path"], "readability": f["readability"],
                    "tests": is_test(f["path"]), "lines": lines[f["path"]]})
    return out


def dir_scores(files):
    """Per directory above the scored files: mean file readability weighted by changed lines."""
    acc = {}
    for f in files:
        parts = f["path"].split("/")[:-1]
        for i in range(1, len(parts) + 1):
            a = acc.setdefault("/".join(parts[:i]), [0, 0, 0, 0])
            w = max(f["lines"], 1)
            a[0] += w * f["readability"]
            a[1] += w
            a[2] += 1
            a[3] += f["lines"]
    return [{"path": d, "readability": round(a[0] / a[1], 1), "files": a[2], "lines": a[3]}
            for d, a in sorted(acc.items())]


def overall_with_tests(scores, lines):
    """Like overall(), with readability and test readability weighted by their share of changed lines."""
    tests = sum(n for p, n in lines.items() if is_test(p))
    source = sum(lines.values()) - tests
    tr = scores.get("test_readability")
    if tr is None or tests == 0:
        return overall(scores)
    share = tests / (tests + source)
    return overall({**scores, "readability": (1 - share) * scores["readability"] + share * tr})


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


def examples():
    out = ""
    for f in sorted((ROOT / "learning").glob("*.md")):
        out += f"## {f.stem}\n{f.read_text()}\n"
    return f"# Examples\n{out}" if out else ""


def test_paths_section():
    paths = section_paths("test paths")
    if not paths:
        return ""
    return ("# Test paths\nFiles under these path prefixes are test files; all other files are not.\n"
            + "".join(f"- {p}\n" for p in paths) + "\n")


def interactive_feedback(repo, pr):
    """The reviewer's Q&A files for this repo, oldest first, except those for PR `pr` itself."""
    out = ""
    files = sorted((ROOT / "learning" / "interactive-feedback" / repo).glob("*.md"),
                   key=lambda f: f.stem[-15:])
    for f in files:
        if f.stem.split("-")[0] == str(pr):
            continue
        out += f"## {f.stem}\n{re.sub(r'<!--.*?-->', '', f.read_text(), count=1, flags=re.S).strip()}\n\n"
    return f"# Interactive feedback\n{out}" if out else ""


def build_prompt(d):
    meta = (d / "meta.json").read_text()
    commits = (d / "commits.json").read_text()
    diff = (d / "diff.patch").read_text()
    if len(diff) > MAX_DIFF:
        diff = diff[:MAX_DIFF] + "\n[diff truncated]"
    return (f"{(ROOT/'prompt.md').read_text()}\n{OUTPUT_FORMAT}\n# Guidelines\n{(ROOT/'guidelines.md').read_text()}\n"
            f"# Rubric\n{(ROOT/'rubric.md').read_text()}\n{test_paths_section()}{examples()}{interactive_feedback(d.parent.parent.name, d.name)}"
            f"# PR meta\n{meta}\n# Commits\n{commits}\n# Diff\n{diff}\n")


def agent_cmd(effort, agent):
    """scripts/agent.py: one model call, prompt on stdin, reply on stdout (claude by default)."""
    return [sys.executable, "-I", str(ROOT / "scripts" / "agent.py"), "--config", str(CONFIG_FILE),
            "--effort", effort, *(["--agent", agent] if agent else [])]


def grade(d, out, effort, agent):
    dest = out / f"{d.name}.json"
    if dest.exists():
        return
    meta = json.loads((d / "meta.json").read_text())
    if ignored(meta["author"], meta["title"]):
        return
    r = subprocess.run(agent_cmd(effort, agent), input=build_prompt(d), capture_output=True, text=True)
    if r.returncode:
        print(f"PR {d.name}: agent failed: {r.stderr.strip()[-300:]}", file=sys.stderr)
        return
    txt = r.stdout.strip()
    try:
        res = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
        scores = check_scores(res)
    except (ValueError, KeyError):
        print(f"PR {d.name}: bad output: {txt[:200]} {r.stderr[:200]}", file=sys.stderr)
        return
    lines = changed_lines((d / "diff.patch").read_text())
    files = file_scores(res, lines)
    res = {"pr": res.get("pr"), "scores": scores, "overall": overall(scores),
           "overall_with_tests": overall_with_tests(scores, lines), "files": files,
           "dirs": dir_scores(files),
           **{k: v for k, v in res.items()
              if k not in ("pr", "scores", "overall", "overall_with_tests", "files", "dirs")}}
    dest.write_text(json.dumps(res, indent=2))
    print("graded", d.name)


def main():
    p = argparse.ArgumentParser(color=False)
    p.add_argument("--config", help="config file naming the repo file (default: active-config.cfg)")
    p.add_argument("--repo", default=default_repo().replace("/", "_"))
    p.add_argument("--run-id", required=True)
    p.add_argument("-j", type=int, default=4)
    p.add_argument("--pr", type=int, action="append")
    p.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"],
                   help="reasoning effort (default: medium, not the agent's own default)")
    p.add_argument("--agent", help="claude, codex or a command (default: $PRDOCS_AGENT, `agent=` in the config, claude)")
    a = p.parse_args()
    out = ROOT / "results" / a.repo / a.run_id
    out.mkdir(parents=True, exist_ok=True)
    base = ROOT / "data" / a.repo
    sel = base / "selected.json"
    dirs = (sorted(base / "prs" / n for n in json.loads(sel.read_text()))
            if sel.exists() else sorted((base / "prs").iterdir()))
    if a.pr:
        dirs = [base / "prs" / str(n) for n in a.pr]
    with ThreadPoolExecutor(a.j) as ex:
        list(ex.map(lambda d: grade(d, out, a.effort, a.agent), dirs))


main()
