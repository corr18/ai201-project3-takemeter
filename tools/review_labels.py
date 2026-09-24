#!/usr/bin/env python3
"""
TakeMeter label review tool.

Two modes:

  review  (default)  Primary annotator pass. Shows each comment with the
                     machine-proposed label. You accept or override. Writes
                     back to the dataset CSV, recording accepted/overridden
                     per row so the override rate is reportable.

  blind              Second-annotator pass for inter-annotator reliability.
                     Shows a stratified sample with NO proposed label visible.
                     Writes to a separate file; the main dataset is untouched.

No third-party dependencies. Run:

    python3 tools/review_labels.py
    python3 tools/review_labels.py --mode blind --n 40

Then open the URL it prints.
"""

import argparse
import csv
import http.server
import json
import os
import random
import socketserver
import sys
import threading
import webbrowser
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "takemeter_labeled.csv")
BLIND_OUT = os.path.join(ROOT, "data", "annotator2_labels.csv")

LABELS = ["stat_backed", "consensus_take", "hot_take", "reaction"]

LABEL_HELP = {
    "stat_backed": "Cites a specific checkable number that does argumentative work. Load-bearing test: delete the number — is the argument weaker?",
    "consensus_take": "Evaluative claim, no real stats, and r/NBA broadly agrees. Reply test: “yeah, obviously” reads as normal.",
    "hot_take": "Evaluative claim, no real stats, runs against r/NBA consensus. Reply test: “yeah, obviously” reads as sarcastic.",
    "reaction": "Pure in-the-moment emotion, joke or chant. Strip test: remove the caps and emoji — nothing disagreeable survives.",
}

# Columns we manage. proposed_label preserves the original machine label so the
# accepted-vs-overridden split stays computable after an override rewrites label.
MANAGED = ["proposed_label", "review_flag"]


def load_rows():
    with open(DATA, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for i, r in enumerate(rows):
        r.setdefault("notes", "")
        r.setdefault("source_thread_type", "")
        r.setdefault("pre_labeled", "proposed")
        # First run: snapshot the machine label before any override can clobber it.
        if not r.get("proposed_label"):
            r["proposed_label"] = r["label"]
        r.setdefault("review_flag", "")
        r["_i"] = i
    return rows


def fieldnames(rows):
    base = ["text", "label", "notes", "source_thread_type", "pre_labeled"]
    extra = [c for c in MANAGED if c not in base]
    return base + extra


def save_rows(rows):
    fns = fieldnames(rows)
    tmp = DATA + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fns})
    os.replace(tmp, DATA)


def load_blind(sample):
    """Existing second-annotator decisions, keyed by text."""
    out = {}
    if os.path.exists(BLIND_OUT):
        with open(BLIND_OUT, newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                out[r["text"]] = r.get("label2", "")
    return out


def save_blind(sample, decisions):
    tmp = BLIND_OUT + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["text", "label2", "label_primary", "source_thread_type"],
            quoting=csv.QUOTE_ALL,
        )
        w.writeheader()
        for r in sample:
            w.writerow(
                {
                    "text": r["text"],
                    "label2": decisions.get(r["text"], ""),
                    "label_primary": r["label"],
                    "source_thread_type": r.get("source_thread_type", ""),
                }
            )
    os.replace(tmp, BLIND_OUT)


def stratified_sample(rows, n, seed=20250924):
    by = defaultdict(list)
    for r in rows:
        by[r["label"]].append(r)
    rnd = random.Random(seed)
    per = max(1, n // len(LABELS))
    out = []
    for lab in LABELS:
        pool = list(by.get(lab, []))
        rnd.shuffle(pool)
        out.extend(pool[:per])
    rnd.shuffle(out)
    return out[:n]


PAGE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TakeMeter Review</title>
<style>
:root{
  --bg:#f7f7f8; --panel:#fff; --ink:#18181b; --muted:#6b7280; --line:#e4e4e7;
  --accent:#4f46e5; --ok:#15803d; --warn:#b45309;
  --c0:#0e7490; --c1:#15803d; --c2:#b91c1c; --c3:#7c3aed;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#0c0c0f; --panel:#151519; --ink:#f2f2f3; --muted:#9ca3af; --line:#2a2a31;
  --accent:#818cf8; --ok:#4ade80; --warn:#fbbf24;
  --c0:#22d3ee; --c1:#4ade80; --c2:#f87171; --c3:#c4b5fd;
}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--panel);border-bottom:1px solid var(--line);
  padding:10px 16px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.bar{flex:1;min-width:140px;height:7px;background:var(--line);border-radius:4px;overflow:hidden}
.bar>i{display:block;height:100%;background:var(--accent);width:0;transition:width .2s}
.counts{display:flex;gap:8px;flex-wrap:wrap;font-size:12px;color:var(--muted)}
.counts b{color:var(--ink);font-weight:600}
main{max-width:860px;margin:0 auto;padding:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px;margin-bottom:14px}
.meta{font-size:12px;color:var(--muted);margin-bottom:10px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.pill{border:1px solid var(--line);border-radius:999px;padding:2px 9px}
.text{font-size:19px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word}
.proposed{margin:16px 0 4px;font-size:13px;color:var(--muted)}
.opts{display:grid;gap:8px;margin-top:10px}
button.opt{display:flex;gap:11px;align-items:flex-start;text-align:left;width:100%;cursor:pointer;
  background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:11px 13px;font:inherit}
button.opt:hover{border-color:var(--accent)}
button.opt.sel{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
button.opt.prop{border-style:dashed}
.key{flex:none;width:22px;height:22px;border-radius:6px;background:var(--line);color:var(--ink);
  display:grid;place-items:center;font-size:12px;font-weight:700}
.nm{font-weight:650;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13.5px}
.nm.l0{color:var(--c0)}.nm.l1{color:var(--c1)}.nm.l2{color:var(--c2)}.nm.l3{color:var(--c3)}
.hint{font-size:12.5px;color:var(--muted);margin-top:2px}
.tag{font-size:11px;color:var(--warn);font-weight:600;margin-left:6px}
textarea{width:100%;margin-top:12px;min-height:56px;padding:9px 11px;border:1px solid var(--line);
  border-radius:9px;background:var(--bg);color:var(--ink);font:inherit;resize:vertical}
.row{display:flex;gap:10px;align-items:center;margin-top:10px;flex-wrap:wrap}
.btn{background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:7px 13px;
  cursor:pointer;color:var(--ink);font:inherit;font-size:13px}
.btn:hover{border-color:var(--accent)}
.btn.on{background:var(--warn);border-color:var(--warn);color:#000;font-weight:600}
.legend{font-size:12px;color:var(--muted);display:flex;gap:12px;flex-wrap:wrap;justify-content:center;padding:6px 0 28px}
kbd{background:var(--line);border-radius:4px;padding:1px 5px;font-family:ui-monospace,monospace;font-size:11px}
.done{text-align:center;padding:40px 20px}
.done h2{color:var(--ok)}
#save{font-size:12px;color:var(--ok);opacity:0;transition:opacity .2s}
#save.on{opacity:1}
</style></head><body>
<header>
  <strong style="font-size:14px">TakeMeter</strong>
  <span id="mode" class="pill"></span>
  <div class="bar"><i id="fill"></i></div>
  <span id="prog" style="font-size:12.5px;color:var(--muted)"></span>
  <span id="save">saved</span>
  <div class="counts" id="counts"></div>
</header>
<main><div id="app"></div>
<div class="legend">
  <span><kbd>1</kbd>–<kbd>4</kbd> label</span>
  <span id="lg-enter"><kbd>⏎</kbd> accept proposed</span>
  <span><kbd>←</kbd><kbd>→</kbd> move</span>
  <span><kbd>h</kbd> flag hard</span>
  <span><kbd>n</kbd> note</span>
  <span><kbd>u</kbd> next undecided</span>
</div></main>
<script>
const LABELS=__LABELS__, HELP=__HELP__, MODE=__MODE__;
let rows=[], idx=0;

const $=s=>document.querySelector(s);
const esc=s=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const decided=r=>MODE==='blind' ? !!r.label2 : r.pre_labeled==='accepted'||r.pre_labeled==='overridden';

async function boot(){
  rows=await (await fetch('/api/rows')).json();
  const f=rows.findIndex(r=>!decided(r));
  idx=f<0?0:f;
  $('#mode').textContent = MODE==='blind' ? 'blind 2nd-annotator pass' : 'primary review';
  if(MODE==='blind') $('#lg-enter').style.display='none';
  render();
}

function render(){
  const done=rows.filter(decided).length, n=rows.length;
  $('#fill').style.width=(100*done/n)+'%';
  $('#prog').textContent=`${done}/${n} done · #${idx+1}`;

  const c={}; LABELS.forEach(l=>c[l]=0);
  rows.forEach(r=>{const v=MODE==='blind'?r.label2:(decided(r)?r.label:null); if(v&&c[v]!==undefined)c[v]++;});
  $('#counts').innerHTML=LABELS.map((l,i)=>`<span><span class="nm l${i}">${l}</span> <b>${c[l]}</b></span>`).join('');

  if(done===n && !rows[idx]){ return finish(); }
  const r=rows[idx];
  const cur = MODE==='blind' ? r.label2 : (decided(r)? r.label : null);
  const prop = MODE==='blind' ? null : r.proposed_label;

  $('#app').innerHTML=`
  <div class="card">
    <div class="meta">
      <span class="pill">${esc(r.source_thread_type||'—')}</span>
      <span class="pill">${r.text.split(/\s+/).length} words</span>
      ${r.review_flag==='hard'?'<span class="tag">FLAGGED HARD</span>':''}
      ${MODE!=='blind'&&r.pre_labeled==='overridden'?'<span class="tag">OVERRIDDEN</span>':''}
    </div>
    <div class="text">${esc(r.text)}</div>
    ${prop?`<div class="proposed">Machine proposed: <span class="nm l${LABELS.indexOf(prop)}">${prop}</span> — press <kbd>⏎</kbd> to accept</div>`:''}
    <div class="opts">${LABELS.map((l,i)=>`
      <button class="opt ${cur===l?'sel':''} ${prop===l?'prop':''}" data-l="${l}">
        <span class="key">${i+1}</span>
        <span><span class="nm l${i}">${l}</span><div class="hint">${esc(HELP[l])}</div></span>
      </button>`).join('')}</div>
    <textarea id="note" placeholder="Notes — which two labels you were torn between, and which rule decided it">${esc(r.notes||'')}</textarea>
    <div class="row">
      <button class="btn ${r.review_flag==='hard'?'on':''}" id="hard">⚑ hard case</button>
      <button class="btn" id="prev">← prev</button>
      <button class="btn" id="next">next →</button>
      <button class="btn" id="undec">next undecided</button>
    </div>
  </div>`;

  document.querySelectorAll('.opt').forEach(b=>b.onclick=()=>decide(b.dataset.l));
  $('#hard').onclick=()=>toggleHard();
  $('#prev').onclick=()=>go(-1); $('#next').onclick=()=>go(1); $('#undec').onclick=nextUndecided;
  $('#note').onblur=()=>post({note:$('#note').value});
}

function finish(){
  $('#app').innerHTML=`<div class="card done"><h2>All ${rows.length} reviewed</h2>
    <p style="color:var(--muted)">Saved to disk. You can close this tab — then stop the server with Ctrl-C.</p></div>`;
}

async function post(extra){
  const r=rows[idx];
  const body=Object.assign({index:r._i, text:r.text}, extra);
  const res=await fetch('/api/decide',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const upd=await res.json();
  Object.assign(rows[idx], upd);
  $('#save').classList.add('on'); setTimeout(()=>$('#save').classList.remove('on'),700);
}

async function decide(l){ await post({label:l}); advance(); }
async function toggleHard(){ await post({flag: rows[idx].review_flag==='hard'?'':'hard'}); render(); }

function advance(){
  const nxt=rows.findIndex((r,i)=>i>idx && !decided(r));
  idx = nxt<0 ? Math.min(idx+1, rows.length-1) : nxt;
  if(rows.every(decided) && nxt<0){ render(); return finish(); }
  render();
}
function go(d){ idx=Math.max(0,Math.min(rows.length-1, idx+d)); render(); }
function nextUndecided(){ const n=rows.findIndex(r=>!decided(r)); if(n>=0){idx=n;render();} }

document.addEventListener('keydown',e=>{
  if(e.target.tagName==='TEXTAREA'){ if(e.key==='Escape') e.target.blur(); return; }
  // Auto-repeat from a held key is never a judgement about a comment.
  if(e.repeat) { e.preventDefault(); return; }
  if(e.key>='1'&&e.key<='4') return decide(LABELS[+e.key-1]);
  if(e.key==='Enter'&&MODE!=='blind'&&rows[idx]&&rows[idx].proposed_label) return decide(rows[idx].proposed_label);
  if(e.key==='ArrowLeft') return go(-1);
  if(e.key==='ArrowRight') return go(1);
  if(e.key==='h') return toggleHard();
  if(e.key==='u') return nextUndecided();
  if(e.key==='n'){ e.preventDefault(); $('#note').focus(); }
});
boot();
</script></body></html>"""


def build_handler(state):
    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/":
                page = (
                    PAGE.replace("__LABELS__", json.dumps(LABELS))
                    .replace("__HELP__", json.dumps(LABEL_HELP))
                    .replace("__MODE__", json.dumps(state["mode"]))
                )
                return self._send(200, page, "text/html; charset=utf-8")
            if self.path == "/api/rows":
                return self._send(200, json.dumps(state["payload"]()), "application/json")
            self._send(404, "not found", "text/plain")

        def do_POST(self):
            if self.path != "/api/decide":
                return self._send(404, "not found", "text/plain")
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
            with state["lock"]:
                upd = state["apply"](body)
            self._send(200, json.dumps(upd), "application/json")

    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["review", "blind"], default="review")
    ap.add_argument("--n", type=int, default=40, help="sample size for blind mode")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--reset", action="store_true",
                    help="revert every row to 'proposed' and restore the machine label")
    args = ap.parse_args()

    rows = load_rows()

    if args.reset:
        for r in rows:
            r["label"] = r["proposed_label"]
            r["pre_labeled"] = "proposed"
        save_rows(rows)
        print(f"reset {len(rows)} rows to 'proposed' (review_flag and notes kept)")
        return

    if args.mode == "review":
        def payload():
            return [
                {
                    "_i": r["_i"], "text": r["text"], "label": r["label"],
                    "proposed_label": r["proposed_label"], "pre_labeled": r["pre_labeled"],
                    "notes": r.get("notes", ""), "review_flag": r.get("review_flag", ""),
                    "source_thread_type": r.get("source_thread_type", ""),
                }
                for r in rows
            ]

        def apply(b):
            r = rows[b["index"]]
            if "label" in b:
                r["label"] = b["label"]
                r["pre_labeled"] = "accepted" if b["label"] == r["proposed_label"] else "overridden"
            if "note" in b:
                r["notes"] = b["note"]
            if "flag" in b:
                r["review_flag"] = b["flag"]
            save_rows(rows)
            return {k: r[k] for k in ("label", "pre_labeled", "notes", "review_flag")}
    else:
        sample = stratified_sample(rows, args.n)
        decisions = load_blind(sample)
        save_blind(sample, decisions)
        idx_of = {r["text"]: i for i, r in enumerate(sample)}

        def payload():
            return [
                {
                    "_i": i, "text": r["text"], "label2": decisions.get(r["text"], ""),
                    "notes": "", "review_flag": "",
                    "source_thread_type": r.get("source_thread_type", ""),
                }
                for i, r in enumerate(sample)
            ]

        def apply(b):
            r = sample[b["index"]]
            if "label" in b:
                decisions[r["text"]] = b["label"]
            save_blind(sample, decisions)
            return {"label2": decisions.get(r["text"], "")}

    state = {"mode": args.mode, "payload": payload, "apply": apply, "lock": threading.Lock()}

    if args.mode == "review":
        save_rows(rows)  # persist proposed_label / review_flag columns on first run
        done = sum(1 for r in rows if r["pre_labeled"] in ("accepted", "overridden"))
        print(f"Primary review — {len(rows)} rows, {done} already decided.")
    else:
        print(f"Blind second-annotator pass — {len(payload())} rows → {os.path.relpath(BLIND_OUT, ROOT)}")
        print("The primary label is NOT shown in this mode.")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), build_handler(state)) as httpd:
        url = f"http://127.0.0.1:{args.port}/"
        print(f"\n  Open {url}\n  Ctrl-C when done.\n")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped. Progress is saved after every keystroke.")


if __name__ == "__main__":
    main()
