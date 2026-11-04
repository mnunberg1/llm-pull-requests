# AI generated from scripts.md; do not edit by hand.
import sys as _sys
if _sys.version_info < (3, 14):
    _sys.exit("this needs Python 3.14+ (argparse color=False); found " + ".".join(map(str, _sys.version_info[:3])))
import argparse, re, json, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
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

GRADES = ROOT / "grades"
THRESHOLD = 2


def read_grade(repo, n):
    f = GRADES / repo / f"{n}.txt"
    if not f.exists():
        return {"mine": "", "notes": ""}
    head, _, notes = f.read_text().partition("notes:")
    mine = head.partition(":")[2].strip()
    return {"mine": mine, "notes": notes.strip()}


def load(repo, run):
    out = []
    for f in sorted((ROOT / "results" / repo / run).glob("*.json"), key=lambda f: int(f.stem)):
        res = json.loads(f.read_text())
        comments = [c if isinstance(c, dict) else {"sentiment": None, "text": c}
                    for c in res["comments"]]
        meta = json.loads((ROOT / "data" / repo / "prs" / f.stem / "meta.json").read_text())
        out.append({"pr": int(f.stem), "title": meta["title"], "author": meta["author"],
                    "url": f"https://github.com/{repo.replace('_', '/', 1)}/pull/{f.stem}",
                    "model": res["overall"], "comments": comments, "effort": res.get("effort"),
                    **read_grade(repo, f.stem)})
    return out


def write_summary(repo, run):
    lines = []
    for p in load(repo, run):
        lines.append(f"{p['pr']}\tmodel={p['model']}\tmine={p['mine'] or '-'}")
        lines += [f"  - [{c['sentiment'] or '?'}] {c['text']}" for c in p["comments"]]
        e = p["effort"]
        if e:
            lines.append(f"  effort: author ~{e['author_minutes']}m, review ~{e['review_minutes']}m"
                         f" ({e['review_minutes'] / max(e['author_minutes'], 1):.1f}x)")
    (ROOT / "results" / repo / run / "summary.txt").write_text("\n".join(lines) + "\n")


PAGE = """<!doctype html>
<meta charset=utf-8><title>PR grading</title>
<meta name=color-scheme content="light dark">
<style>
:root{color-scheme:light dark;--bg:#fff;--fg:#1f2328;--muted:#656d76;--border:#d0d7de;--accent:#0969da;--bad:#cf222e;--ok:#1a7f37}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--muted:#8d96a0;--border:#30363d;--accent:#4493f8;--bad:#f85149;--ok:#3fb950}}
body{font:14px system-ui;max-width:900px;margin:1em auto;padding:0 1em;background:var(--bg);color:var(--fg)}
a{color:var(--accent)}
.pr{border:1px solid var(--border);border-radius:6px;padding:.6em;margin:.6em 0}
.pr.disagree{border-color:var(--bad);border-width:2px}
.muted{color:var(--muted)}
.assess{margin:.4em 0;padding-left:1.2em}
.s{display:inline-block;min-width:1.4em;text-align:center;border-radius:4px;margin-right:.5em;font-weight:bold;color:#fff}
.s1{background:var(--bad)}.s2{background:#bc4c00}.s3{background:var(--muted)}.s4{background:#2da44e}.s5{background:var(--ok)}
select,textarea{background:var(--bg);color:var(--fg);border:1px solid var(--border);border-radius:4px}
textarea{width:100%;box-sizing:border-box;margin-top:.4em}
.saved{color:var(--ok)}
</style>
<label><input type=checkbox id=dis> only disagreements of THRESHOLD+ points</label>
<div id=list></div>
<script>
const T=THRESHOLD;
let prs=[];
const d=p=>p.mine!==''&&Math.abs(p.mine-p.model)>=T;
function render(){
  const only=document.getElementById('dis').checked;
  const el=document.getElementById('list');el.innerHTML='';
  for(const p of prs){
    if(only&&!d(p))continue;
    const div=document.createElement('div');
    div.className='pr'+(d(p)?' disagree':'');
    const a=document.createElement('a');a.href=p.url;a.target='_blank';
    a.textContent='#'+p.pr+' '+p.title;
    const meta=document.createElement('div');meta.className='muted';
    meta.textContent=p.author+' | model: '+p.model+'/5';
    const as=document.createElement('ul');as.className='assess';
    for(const c of p.comments){const li=document.createElement('li');const b=document.createElement('span');b.className='s s'+c.sentiment;b.textContent=c.sentiment??'?';li.append(b,c.text);as.appendChild(li);}
    const ef=document.createElement('div');ef.className='muted';
    if(p.effort){ef.textContent='effort: author ~'+p.effort.author_minutes+' min, review ~'+p.effort.review_minutes+' min ('+(p.effort.review_minutes/Math.max(p.effort.author_minutes,1)).toFixed(1)+'x)';}
    const sel=document.createElement('select');
    for(const v of ['','1','2','3','4','5']){
      const o=document.createElement('option');o.value=o.textContent=v;sel.appendChild(o);}
    sel.value=p.mine;
    const st=document.createElement('span');
    const ta=document.createElement('textarea');ta.rows=3;ta.value=p.notes;
    ta.placeholder='notes: what the comments got right or wrong';
    const save=async()=>{
      p.mine=sel.value;p.notes=ta.value;
      await fetch('/save',{method:'POST',body:JSON.stringify({pr:p.pr,mine:p.mine,notes:p.notes})});
      st.className='saved';st.textContent=' saved';
      div.className='pr'+(d(p)?' disagree':'');
    };
    sel.onchange=save;ta.onblur=save;
    div.append(a,meta,as,ef,'my grade (optional): ',sel,st,ta);
    el.appendChild(div);
  }
}
document.getElementById('dis').onchange=render;
fetch('/data').then(r=>r.json()).then(j=>{prs=j;render();});
</script>
""".replace("THRESHOLD", str(THRESHOLD))


def main():
    p = argparse.ArgumentParser(color=False)
    p.add_argument("--config", help="config file naming the repo file (default: active-config.cfg)")
    p.add_argument("run_id")
    p.add_argument("--repo", default=default_repo().replace("/", "_"))
    p.add_argument("--port", type=int, default=8765)
    a = p.parse_args()
    (GRADES / a.repo).mkdir(parents=True, exist_ok=True)

    class H(BaseHTTPRequestHandler):
        def reply(self, body, ctype):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.end_headers()
            self.wfile.write(body.encode())

        def do_GET(self):
            if self.path == "/data":
                self.reply(json.dumps(load(a.repo, a.run_id)), "application/json")
            else:
                self.reply(PAGE, "text/html")

        def do_POST(self):
            j = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            f = GRADES / a.repo / f"{int(j['pr'])}.txt"
            if not j["mine"] and not j["notes"].strip():
                f.unlink(missing_ok=True)
            else:
                f.write_text(f"overall: {j['mine']}\nnotes:\n{j['notes']}\n")
            write_summary(a.repo, a.run_id)
            self.reply("ok", "text/plain")

        def log_message(self, *args):
            pass

    write_summary(a.repo, a.run_id)
    srv = HTTPServer(("127.0.0.1", a.port), H)
    url = f"http://127.0.0.1:{a.port}/"
    print("serving", url)
    webbrowser.open(url)
    srv.serve_forever()


main()
