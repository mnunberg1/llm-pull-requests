# AI generated from scripts.md; do not edit by hand.
# One model call for the other scripts: prompt on stdin, reply on stdout.
import sys as _sys
if _sys.version_info < (3, 14):
    _sys.exit("this needs Python 3.14+ (argparse color=False); found " + ".".join(map(str, _sys.version_info[:3])))
import argparse, os, shlex, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEVELS = ["low", "medium", "high", "xhigh", "max"]


def config_value(key, path):
    """`key=value` from the config file (--config, else $PRDOCS_CONFIG, else active-config.cfg), or ''."""
    f = Path(path or os.environ.get("PRDOCS_CONFIG") or ROOT / "active-config.cfg")
    if not f.is_file():
        return ""
    for line in f.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if k.strip() == key:
                return v.strip()
    return ""


def command(agent, effort, model):
    """The command line for an agent: `claude`, `codex`, or any command that reads the prompt on stdin."""
    if agent == "claude":
        cmd = ["claude", "-p", "--model", model or "sonnet", "--tools", "", "--no-session-persistence"]
        return cmd + (["--effort", effort] if effort else [])
    if agent == "codex":
        cmd = ["codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only"]
        if effort:  # codex has no xhigh or max
            cmd += ["-c", f'model_reasoning_effort="{"high" if effort in ("xhigh", "max") else effort}"']
        return cmd + (["-m", model] if model else []) + ["-"]
    return shlex.split(agent)


def main():
    p = argparse.ArgumentParser(color=False, description=__doc__)
    p.add_argument("--config", help="config file whose `agent=` line is used (default: active-config.cfg)")
    p.add_argument("--agent", help="claude, codex, or a command that reads the prompt on stdin and prints "
                   "the reply (default: $PRDOCS_AGENT, else `agent=` in the config, else claude)")
    p.add_argument("--effort", choices=LEVELS, help="reasoning effort (default: the agent's own setting)")
    p.add_argument("--model", help="model name (default: $PRDOCS_MODEL; claude: sonnet; else the agent's own)")
    a = p.parse_args()
    agent = a.agent or os.environ.get("PRDOCS_AGENT") or config_value("agent", a.config) or "claude"
    model = a.model or os.environ.get("PRDOCS_MODEL") or ""
    cmd = command(agent, a.effort, model)
    if not cmd or not shutil.which(cmd[0]):
        sys.exit(f"agent command not found: {cmd[0] if cmd else agent!r}. Install it, or choose another with "
                 "--agent, $PRDOCS_AGENT or `agent=` in the config (claude, codex, or a command).")
    env = {**os.environ, "PRDOCS_EFFORT": a.effort or "", "PRDOCS_MODEL": model}
    r = subprocess.run(cmd, input=sys.stdin.read(), capture_output=True, text=True, env=env)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    sys.exit(r.returncode)


main()
