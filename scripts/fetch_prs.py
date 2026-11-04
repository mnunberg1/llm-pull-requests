# AI generated from scripts.md; do not edit by hand.
import sys as _sys
if _sys.version_info < (3, 14):
    _sys.exit("this needs Python 3.14+ (argparse color=False); found " + ".".join(map(str, _sys.version_info[:3])))
import argparse, re, json, subprocess
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


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


BUCKETS = ["small", "medium", "large"]


def section_paths(label):
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


def classify(diff):
    core_paths, test_paths = section_paths("core source paths"), section_paths("test paths")
    core = test = 0
    path = None
    for line in diff.splitlines():
        if line.startswith("diff --git"):
            path = line.split(" b/", 1)[-1]
        elif path and line[:1] in "+-" and not line.startswith(("+++", "---")):
            text = line[1:].strip()
            if not text or text.startswith(("//", "#", "/*", "*", "*/")):
                continue
            if any(path.startswith(x) for x in core_paths):
                core += 1
            elif any(path.startswith(x) for x in test_paths):
                test += 1
    size = core if core or not test else test
    bucket = "small" if size < 150 else "medium" if size <= 500 else "large"
    return size, bucket


def save_pr(repo, d, n, diff):
    d.mkdir(parents=True, exist_ok=True)
    view = json.loads(gh("pr", "view", str(n), "-R", repo, "--json",
                         "number,title,author,body,labels,state,commits"))
    commits = view.pop("commits")
    meta = {**view, "author": view["author"]["login"],
            "labels": [l["name"] for l in view["labels"]]}
    (d / "meta.json").write_text(json.dumps(meta, indent=2))
    (d / "commits.json").write_text(json.dumps([
        {"oid": c["oid"], "message": c["messageHeadline"] + "\n\n" + c["messageBody"]}
        for c in commits], indent=2))
    (d / "diff.patch").write_text(diff)
    return meta


def fetch_only(repo, base, numbers, refresh):
    for n in numbers:
        d = base / "prs" / str(n)
        if (d / "diff.patch").exists() and not refresh:
            meta = json.loads((d / "meta.json").read_text())
        else:
            meta = save_pr(repo, d, n, gh("pr", "diff", str(n), "-R", repo))
        if ignored(meta["author"], meta["title"]):
            print("ignored", n)
        else:
            print("fetched", n)


def main():
    p = argparse.ArgumentParser(color=False)
    p.add_argument("--config", help="config file naming the repo file (default: active-config.cfg)")
    p.add_argument("--repo", default=default_repo())
    p.add_argument("--per-bucket", type=int, default=10)
    p.add_argument("--scan-limit", type=int, default=300)
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--pr", type=int, action="append")
    a = p.parse_args()

    base = ROOT / "data" / a.repo.replace("/", "_")
    if a.pr:
        fetch_only(a.repo, base, a.pr, a.refresh)
        return
    sel_file = base / "selected.json"
    if sel_file.exists() and not a.refresh:
        print(sel_file.read_text())
        return

    prs = json.loads(gh("pr", "list", "-R", a.repo, "--state", "all",
                        "--limit", str(a.scan_limit), "--json", "number,title,author"))
    chosen = {}
    counts = dict.fromkeys(BUCKETS, 0)
    for pr in prs:
        if all(c >= a.per_bucket for c in counts.values()):
            break
        n = pr["number"]
        if ignored(pr["author"]["login"], pr["title"]):
            continue
        d = base / "prs" / str(n)
        cached = d / "diff.patch"
        diff = cached.read_text() if cached.exists() else gh("pr", "diff", str(n), "-R", a.repo)
        size, bucket = classify(diff)
        if counts[bucket] >= a.per_bucket:
            continue
        counts[bucket] += 1
        chosen[n] = {"bucket": bucket, "size": size}
        if not cached.exists():
            save_pr(a.repo, d, n, diff)
        print("selected", n, bucket, size)

    sel_file.write_text(json.dumps(dict(sorted(chosen.items())), indent=2))
    for b, c in counts.items():
        if c < a.per_bucket:
            print(f"warning: only {c} {b} PRs found in the last {a.scan_limit}")


main()
