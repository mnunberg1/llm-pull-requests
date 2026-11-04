# AI generated from scripts.md; do not edit by hand.
import sys as _sys
if _sys.version_info < (3, 14):
    _sys.exit("this needs Python 3.14+ (argparse color=False); found " + ".".join(map(str, _sys.version_info[:3])))
import argparse, json, re, subprocess, sys
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
MAX_DIFF = 150_000

DEFAULT_QUESTION = (
    "Explain why you gave these scores (atomicity, description, readability) and each comment. Quote the "
    "rubric or guideline text you relied on, and say where it was ambiguous.")

PREFIX = (
    "You previously reviewed the pull request below. Answer the question at the "
    "end in plain text, not JSON. The length limits in the grading prompt apply "
    "to the grade, not to this answer. Be honest if the rubric is ambiguous or "
    "you would now weigh something differently.\n"
    "The diff below has the new-file line number in front of each added or "
    "unchanged line (`   42| +code`); those numbers are not part of the code. When "
    "your answer points at code in the diff, cite it as `[[<path>:<line>]]` or "
    "`[[<path>:<start>-<end>]]`, with the path as it appears in the diff and those "
    "line numbers, so the reader can jump to it. Cite only lines that exist in the "
    "diff, keep each range short (about 10 lines at most), and put each citation "
    "next to the point it supports. Do not cite for points about the title, "
    "description or commits.\n")

ANNOTATE_PREFIX = (
    "You previously reviewed the pull request below. For each comment in your "
    "previous answer, point to the code in the diff that it is about: 0 to 3 "
    "locations, each at most 10 lines. Use none for a comment about the title, "
    "description, commits or the pull request as a whole. The diff has the "
    "new-file line number in front of each added or unchanged line "
    "(`   42| +code`); those numbers are not part of the code.\n"
    "Return ONLY a JSON object, no prose, no code fences:\n"
    '{"annotations": [{"comment": <1-based comment number>, "refs": '
    '[{"file": "<path as in the diff>", "start": <line>, "end": <line>}]}]}\n')

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)")
REF = re.compile(r"\[\[([^\[\]]+?):(\d+)(?:-(\d+))?\]\]")


def number_diff(diff):
    """Add new-file line numbers to a unified diff. Returns (text, {path: {line: text}})."""
    out, index, path, n, in_hunk = [], {}, None, 0, False
    for line in diff.splitlines():
        if line.startswith("diff --git"):
            path, in_hunk = line.split(" b/", 1)[-1], False
            out.append(line)
        elif line.startswith("@@"):
            m = HUNK.match(line)
            if m:
                n, in_hunk = int(m[1]), True
            out.append(line)
        elif in_hunk and line[:1] in ("+", " ", ""):
            index.setdefault(path, {})[n] = line
            out.append(f"{n:>5}| {line}")
            n += 1
        elif in_hunk and line.startswith("-"):
            out.append(f"     | {line}")
        else:
            out.append(line)
    return "\n".join(out), index


def lookup(index, path):
    """The diff path that a cited path names (exact, or one is a suffix of the other)."""
    return next((x for x in index if x == path or x.endswith("/" + path) or path.endswith("/" + x)), None)


def check_refs(data, index):
    """Keep only annotations that point at lines that exist in the diff."""
    out = []
    for item in data.get("annotations", []) if isinstance(data, dict) else []:
        try:
            num, refs = int(item["comment"]), []
            for r in item.get("refs") or []:
                path = lookup(index, str(r.get("file", "")))
                a = int(r["start"])
                b = int(r.get("end") or a)
                if not path or a not in index[path]:
                    continue
                b = max(a, min(b, a + 9))
                while b > a and b not in index[path]:
                    b -= 1
                refs.append({"file": path, "start": a, "end": b})
            out.append({"comment": num, "refs": refs[:3]})
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    return {"annotations": out}


def resolve(reply, index):
    """The code each [[path:lines]] citation in the reply points at, from the diff."""
    out, seen = [], set()
    for m in REF.finditer(reply):
        if m[0] in seen:
            continue
        seen.add(m[0])
        path = lookup(index, m[1])
        a = int(m[2])
        b = min(int(m[3] or a), a + 39)
        lines = [f"{k:>5}| {index[path][k]}" for k in range(a, b + 1) if path and k in index[path]]
        out.append(m[0] + "\n" + ("\n".join(lines) if lines else "  (not in the diff)"))
    return "\n\n".join(out)


def default_repo():
    m = re.search(r"github\.com/([\w.-]+)/([\w.-]+)", REPO_FILE.read_text())
    return f"{m[1]}/{m[2]}"


def examples():
    out = ""
    for f in sorted((ROOT / "learning").glob("*.md")):
        out += f"## {f.stem}\n{f.read_text()}\n"
    return f"# Examples\n{out}" if out else ""


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


def build_prompt(d, answer, question, prefix=PREFIX):
    diff = (d / "diff.patch").read_text()
    if len(diff) > MAX_DIFF:
        diff = diff[:MAX_DIFF] + "\n[diff truncated]"
    diff = number_diff(diff)[0]
    return (f"{prefix}\n# Grading prompt you were given\n{(ROOT/'prompt.md').read_text()}\n"
            f"# Guidelines\n{(ROOT/'guidelines.md').read_text()}\n"
            f"# Rubric\n{(ROOT/'rubric.md').read_text()}\n{test_paths_section()}{examples()}{interactive_feedback(d.parent.parent.name, d.name)}"
            f"# PR meta\n{(d/'meta.json').read_text()}\n"
            f"# Commits\n{(d/'commits.json').read_text()}\n# Diff\n{diff}\n"
            f"# Your previous answer\n{answer}\n" + (f"# Question\n{question}\n" if question else ""))


def main():
    p = argparse.ArgumentParser(color=False)
    p.add_argument("--config", help="config file naming the repo file (default: active-config.cfg)")
    p.add_argument("run_id")
    p.add_argument("pr", type=int)
    p.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    p.add_argument("--repo", default=default_repo().replace("/", "_"))
    p.add_argument("--agent", help="claude, codex or a command (default: $PRDOCS_AGENT, `agent=` in the config, claude)")
    p.add_argument("--annotate-source", action="store_true",
                   help="instead of an explanation, print JSON with the diff lines each comment is about")
    p.add_argument("--resolve", action="store_true",
                   help="append the code each [[path:line]] citation points at")
    a = p.parse_args()
    d = ROOT / "data" / a.repo / "prs" / str(a.pr)
    answer = (ROOT / "results" / a.repo / a.run_id / f"{a.pr}.json").read_text()
    prompt = (build_prompt(d, answer, "", ANNOTATE_PREFIX) if a.annotate_source
              else build_prompt(d, answer, a.question))
    r = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "agent.py"), "--config", str(CONFIG_FILE),
                        *(["--agent", a.agent] if a.agent else [])],
                       input=prompt, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr)
    reply = r.stdout.strip()
    if a.annotate_source:
        try:
            data = json.loads(reply[reply.index("{"):reply.rindex("}") + 1])
        except ValueError:
            sys.exit(f"bad output: {reply[:200]}")
        index = number_diff((d / "diff.patch").read_text()[:MAX_DIFF])[1]
        print(json.dumps(check_refs(data, index)))
        return
    print(reply)
    if a.resolve:
        diff = (d / "diff.patch").read_text()[:MAX_DIFF]
        refs = resolve(reply, number_diff(diff)[1])
        if refs:
            print("\nReferenced code:\n" + refs)


main()
