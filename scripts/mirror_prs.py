# AI generated from scripts.md; do not edit by hand.
# Recreates upstream PRs as PRs in the writable mirror, for the CI grader.
import sys as _sys
if _sys.version_info < (3, 14):
    _sys.exit("this needs Python 3.14+ (argparse color=False); found " + ".".join(map(str, _sys.version_info[:3])))
import argparse, json, os, re, subprocess, sys, tempfile
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
IDENT = {"GIT_AUTHOR_NAME": "pr-grader", "GIT_COMMITTER_NAME": "pr-grader",
         "GIT_AUTHOR_EMAIL": "pr-grader@users.noreply.github.com",
         "GIT_COMMITTER_EMAIL": "pr-grader@users.noreply.github.com"}
WORKFLOWS = ".github/workflows/"
HARNESS_WF = WORKFLOWS + "pr-grader.yml"
GRADER_BRANCH = "pr-grader"


def default_repo():
    m = re.search(r"github\.com/([\w.-]+)/([\w.-]+)", REPO_FILE.read_text())
    return f"{m[1]}/{m[2]}"


def mirror_repo():
    for line in REPO_FILE.read_text().splitlines():
        m = re.search(r"github\.com/([\w.-]+)/([\w.-]+)", line)
        if m and "mirror" in line.lower():
            return f"{m[1]}/{m[2]}"
    return None  # optional: only needed without write access to the main repo


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


def run(*args, input=None, env=None, cwd=None):
    r = subprocess.run(args, input=input, capture_output=True, text=True, cwd=cwd,
                       env=dict(os.environ, **env) if env else None)
    if r.returncode:
        raise RuntimeError(f"{' '.join(map(str, args))}: {r.stderr.strip()[:500]}")
    return r.stdout


def gh(*args, input=None):
    return run("gh", *args, input=input)


class Git:
    def __init__(self, path):
        self.path = path
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            run("git", "init", "-q", "--bare", str(path))

    def __call__(self, *args, input=None, env=None):
        return run("git", "--git-dir", str(self.path), *args, input=input, env=env).strip()

    def tree(self, base, remove=(), add=None):
        """Tree of `base` (None: empty) minus `remove` plus `add` {path: file}."""
        with tempfile.TemporaryDirectory() as td:
            env = {"GIT_INDEX_FILE": f"{td}/index"}
            self("read-tree", base, env=env) if base else self("read-tree", "--empty", env=env)
            if remove:
                self("update-index", "-z", "--index-info", env=env,
                     input="".join(f"0 {'0' * 40}\t{p}\0" for p in remove))
            for path, src in (add or {}).items():
                blob = self("hash-object", "-w", str(src))
                self("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
            return self("write-tree", env=env)

    def commit(self, tree, parent, msg, date=None):
        env = dict(IDENT)
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        args = ["commit-tree", "--no-gpg-sign", tree, "-m", msg]
        return self(*args, *(["-p", parent] if parent else []), env=env)


def remote_refs(git, url):
    out = git("ls-remote", url, f"refs/heads/{GRADER_BRANCH}", "refs/heads/pr/*",
              "refs/heads/base/*")
    return {ref: sha for sha, ref in (l.split("\t") for l in out.splitlines() if l)}


def push(git, url, updates, dry):
    """updates: {ref: sha}; force-pushes them atomically."""
    if not updates:
        return
    specs = [f"+{sha}:{ref}" for ref, sha in updates.items()]
    if dry:
        print("  would push", *specs)
        return
    git("push", "--atomic", url, *specs)


def push_grader(git, url, refs, dry):
    files = {n: ROOT / n for n in ("prompt.md", "rubric.md", "guidelines.md")}
    files["active-config.cfg"] = CONFIG_FILE
    files[REPO_FILE.relative_to(ROOT).as_posix()] = REPO_FILE
    files.update({f"learning/{f.name}": f for f in sorted((ROOT / "learning").glob("*.md"))})
    files.update({f"scripts/{f.name}": f for f in sorted((ROOT / "scripts").glob("*.py"))})
    tree = git.tree(None, add=files)
    ref = f"refs/heads/{GRADER_BRANCH}"
    parent = refs.get(ref)
    if parent:
        git("fetch", "-q", "--no-tags", url, parent)
        if git("rev-parse", f"{parent}^{{tree}}") == tree:
            print("grader bundle unchanged")
            return
    head = run("git", "rev-parse", "--short", "HEAD", cwd=ROOT).strip()
    if run("git", "status", "--porcelain", cwd=ROOT).strip():
        head += "-dirty"
    sha = git.commit(tree, parent, f"pr-grader bundle from {head}")
    push(git, url, {ref: sha}, dry)
    refs[ref] = sha
    print("pushed grader bundle", sha[:12], f"({head})")


def fence(body):
    longest = max((len(m) for m in re.findall(r"`+", body)), default=0)
    return "`" * max(3, longest + 1)


def pr_title(v):
    return re.sub(r"([@#])", "\\1\u200b", v["title"]) + f" (upstream {v['number']})"


def pr_body(v):
    body = (v.get("body") or "").strip()
    f = fence(body)
    return (f"<!-- pr-grader upstream={v['number']} -->\n"
            "Mirror of an upstream pull request, for testing the PR grader. Do not merge.\n\n"
            f"Upstream: `{v['url']}` by `{v['author']['login']}`\n\n"
            "<details><summary>Original description</summary>\n\n"
            f"{f}text\n{body}\n{f}\n\n</details>\n")


def harness(git, mb, pr_paths, n):
    wf = git("ls-tree", "-r", "-z", "--name-only", mb, "--", WORKFLOWS)
    remove = [p for p in wf.split("\0") if p and p not in pr_paths]
    tree = git.tree(mb, remove, {HARNESS_WF: ROOT / "scripts" / "pr-grader.yml"})
    date = git("show", "-s", "--format=%cI", mb)
    return git.commit(tree, mb, f"pr-grader harness for upstream PR {n} (not part of the PR)",
                      date)


def mirror_one(git, a, n, refs, state):
    v = json.loads(gh("pr", "view", str(n), "-R", a.repo, "--json",
                      "number,title,author,body,state,isDraft,baseRefOid,headRefOid,"
                      "files,changedFiles,url"))
    if ignored(v["author"]["login"], v["title"]):
        print("ignored", n)
        return
    head, base = v["headRefOid"], v["baseRefOid"]
    git("fetch", "-q", "--no-tags", f"https://github.com/{a.repo}.git",
        f"+refs/pull/{n}/head:refs/upstream/pr/{n}", base)
    mb = git("merge-base", base, head)

    gh_paths = {f["path"] for f in v["files"]}
    git_paths = set(git("diff", "--name-only", "-M", mb, head).splitlines())
    same = (git_paths == gh_paths if len(gh_paths) == v["changedFiles"]
            else len(git_paths) == v["changedFiles"] and gh_paths <= git_paths)
    if not same:
        print(f"skip {n}: diff differs from upstream "
              f"(git {len(git_paths)} files, GitHub {v['changedFiles']})")
        return
    pr_paths = git_paths | set(git("diff", "--name-only", "--no-renames", mb, head).splitlines())
    h = harness(git, mb, pr_paths, n)

    want = {f"refs/heads/pr/{n}": head, f"refs/heads/base/{n}": h}
    changed = {r: s for r, s in want.items() if refs.get(r) != s}
    push(git, a.push_url, changed, a.dry_run)

    title, body = pr_title(v), pr_body(v)
    found = json.loads(gh("pr", "list", "-R", a.mirror, "--head", f"pr/{n}", "--state", "all",
                          "--json", "number,state,title,body"))
    what = "updated" if changed else "unchanged"
    if not found:
        what = "created"
        if a.dry_run:
            print(f"  would create PR pr/{n} -> base/{n}: {title}")
            m = None
        else:
            url = gh("pr", "create", "-R", a.mirror, "--head", f"pr/{n}", "--base", f"base/{n}",
                     "--title", title, "--body-file", "-", input=body).strip()
            m = int(url.rstrip("/").rsplit("/", 1)[-1])
    else:
        m = found[0]["number"]
        if found[0]["title"] != title or found[0]["body"].strip() != body.strip():
            what = "updated"
            if a.dry_run:
                print(f"  would edit {a.mirror}#{m}")
            else:
                gh("pr", "edit", str(m), "-R", a.mirror, "--title", title, "--body-file", "-",
                   input=body)
        if found[0]["state"] == "CLOSED" and v["state"] == "OPEN":
            what = "reopened"
            if a.dry_run:
                print(f"  would reopen {a.mirror}#{m}")
            else:
                gh("pr", "reopen", str(m), "-R", a.mirror)
    if not a.dry_run:
        state[str(n)] = {"mirror_pr": m, "head": head, "base": h}
    print(f"mirrored {n} -> {a.mirror}#{m if m else '?'} ({what})")


def close_done(a, state):
    for n, s in state.items():
        if json.loads(gh("pr", "view", n, "-R", a.repo, "--json", "state"))["state"] == "OPEN":
            continue
        m = str(s["mirror_pr"])
        if json.loads(gh("pr", "view", m, "-R", a.mirror, "--json", "state"))["state"] != "OPEN":
            continue
        if a.dry_run:
            print(f"  would close {a.mirror}#{m}")
        else:
            gh("pr", "close", m, "-R", a.mirror)
        print("closed", n)


def main():
    p = argparse.ArgumentParser(color=False)
    p.add_argument("--config", help="config file naming the repo file (default: active-config.cfg)")
    p.add_argument("--repo", default=default_repo())
    p.add_argument("--mirror")
    p.add_argument("--pr", type=int, action="append", default=[])
    p.add_argument("--selected", action="store_true")
    p.add_argument("--open", action="store_true")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--close", action="store_true")
    p.add_argument("--push-grader", action="store_true")
    p.add_argument("--push-url")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if not (a.pr or a.selected or a.open or a.close or a.push_grader):
        p.print_usage()
        sys.exit(2)
    a.mirror = a.mirror or mirror_repo()
    if not a.mirror:
        if a.pr or a.selected or a.open or a.close:
            sys.exit("no mirror repo in the repo file; mirroring PRs is only needed "
                     "when you cannot run the workflow on the main repo")
        a.mirror = a.repo  # --push-grader straight to the main repo
    a.push_url = a.push_url or f"https://github.com/{a.mirror}.git"

    base = ROOT / "data" / a.repo.replace("/", "_")
    git = Git(base / "git")
    state_file = base / "mirror.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    refs = remote_refs(git, a.push_url)

    if a.push_grader:
        push_grader(git, a.push_url, refs, a.dry_run)

    numbers = list(a.pr)
    if a.selected:
        numbers += [int(n) for n in json.loads((base / "selected.json").read_text())]
    if a.open:
        numbers += [x["number"] for x in json.loads(gh(
            "pr", "list", "-R", a.repo, "--state", "open", "--limit", str(a.limit),
            "--json", "number"))]
    numbers = list(dict.fromkeys(numbers))
    if numbers and f"refs/heads/{GRADER_BRANCH}" not in refs:
        if not a.dry_run:
            sys.exit(f"{a.mirror} has no {GRADER_BRANCH} branch; run with --push-grader first")
        print(f"warning: {a.mirror} has no {GRADER_BRANCH} branch yet")

    try:
        for n in numbers:
            try:
                mirror_one(git, a, n, refs, state)
            except RuntimeError as e:
                print(f"error {n}: {e}", file=sys.stderr)
        if a.close:
            close_done(a, state)
    finally:
        if not a.dry_run:
            state_file.write_text(json.dumps(dict(sorted(state.items(), key=lambda x: int(x[0]))),
                                             indent=2))


main()
