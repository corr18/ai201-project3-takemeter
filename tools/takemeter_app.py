#!/usr/bin/env python3
"""
TakeMeter - local interface for the fine-tuned classifier.

Paste an r/NBA comment, get the predicted label and the confidence across all
four labels. This is the committed version of the stretch "deployed interface";
Section 9 of takemeter_colab.ipynb runs the same model behind a Gradio share
link, which is the one convenient to film.

Setup:

    pip install torch transformers
    unzip takemeter_model.zip          # downloaded from the Colab notebook
    python3 tools/takemeter_app.py

Then open http://127.0.0.1:8080/.

Serving is stdlib-only, so the sole dependency is the model runtime itself.
"""

import argparse
import html
import http.server
import json
import os
import socketserver
import sys
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL = os.path.join(ROOT, "takemeter_model")

LABELS = ["stat_backed", "consensus_take", "hot_take", "reaction"]

BLURB = {
    "stat_backed": "cites a checkable number that does argumentative work",
    "consensus_take": "unsupported claim r/NBA broadly agrees with",
    "hot_take": "unsupported claim that runs against r/NBA consensus",
    "reaction": "in-the-moment emotion, joke or chant — no claim survives stripping it",
}

EXAMPLES = [
    "He averaged 27.4 on 61% TS after the All-Star break in 28 games, that's a better stretch than his MVP year.",
    "Jokic is the best passing big man of all time and it isn't particularly close.",
    "Curry is the most overrated player in league history, it's not even debatable.",
    "BRO WHAT WAS THAT \U0001f62d\U0001f62d no shot he actually hit that",
    "LeBron is overrated, his playoff record against 1-seeds is under .500.",
]


def load_model(path):
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError:
        sys.exit("Missing runtime. Install it with:\n\n    pip install torch transformers\n")

    if not os.path.isdir(path):
        sys.exit(
            f"No model at {path}\n\n"
            "Download takemeter_model.zip from the Colab notebook (Section 8) and unzip it\n"
            "into the repo root, or pass --model /path/to/model.\n"
        )

    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForSequenceClassification.from_pretrained(path)
    model.eval()

    # id2label may be saved as {"0": "stat_backed"} or {"LABEL_0": ...}; normalise.
    cfg = model.config.id2label or {}
    order = [cfg.get(i, cfg.get(str(i), LABELS[i])) for i in range(model.config.num_labels)]
    if any(str(l).startswith("LABEL_") for l in order):
        order = LABELS[: model.config.num_labels]

    def predict(text):
        with torch.no_grad():
            enc = tok(text, truncation=True, max_length=256, return_tensors="pt")
            probs = torch.softmax(model(**enc).logits, dim=1)[0].tolist()
        scores = sorted(zip(order, probs), key=lambda kv: -kv[1])
        return [{"label": l, "score": round(float(s), 4)} for l, s in scores]

    return predict


PAGE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TakeMeter</title>
<style>
:root{--bg:#f7f7f8;--panel:#fff;--ink:#18181b;--muted:#6b7280;--line:#e4e4e7;--accent:#4f46e5;
  --c0:#0e7490;--c1:#15803d;--c2:#b91c1c;--c3:#7c3aed}
@media (prefers-color-scheme:dark){:root{--bg:#0c0c0f;--panel:#151519;--ink:#f2f2f3;--muted:#9ca3af;
  --line:#2a2a31;--accent:#818cf8;--c0:#22d3ee;--c1:#4ade80;--c2:#f87171;--c3:#c4b5fd}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:720px;margin:0 auto;padding:32px 16px 64px}
h1{margin:0 0 4px;font-size:26px;letter-spacing:-.02em}
.sub{color:var(--muted);font-size:13.5px;margin-bottom:22px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:16px}
textarea{width:100%;min-height:120px;padding:13px;border:1px solid var(--line);border-radius:10px;
  background:var(--bg);color:var(--ink);font:inherit;resize:vertical}
textarea:focus{outline:none;border-color:var(--accent)}
.row{display:flex;gap:10px;align-items:center;margin-top:12px;flex-wrap:wrap}
button{background:var(--accent);color:#fff;border:0;border-radius:9px;padding:10px 20px;
  font:inherit;font-weight:600;cursor:pointer}
button:disabled{opacity:.5;cursor:default}
.ex{background:transparent;color:var(--muted);border:1px solid var(--line);font-weight:400;
  font-size:12.5px;padding:6px 11px;border-radius:999px}
.ex:hover{border-color:var(--accent);color:var(--ink)}
.exwrap{display:flex;gap:7px;flex-wrap:wrap;margin-top:14px}
.top{font-size:21px;font-weight:700;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  letter-spacing:-.01em}
.l0{color:var(--c0)}.l1{color:var(--c1)}.l2{color:var(--c2)}.l3{color:var(--c3)}
.why{color:var(--muted);font-size:13.5px;margin:6px 0 20px}
.b{margin-bottom:11px}
.bh{display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.bt{height:8px;background:var(--line);border-radius:5px;overflow:hidden}
.bt>i{display:block;height:100%;border-radius:5px;transition:width .35s ease}
.f0{background:var(--c0)}.f1{background:var(--c1)}.f2{background:var(--c2)}.f3{background:var(--c3)}
.muted{color:var(--muted)}
</style></head><body><main>
<h1>TakeMeter</h1>
<div class="sub">Fine-tuned DistilBERT sorting r/NBA comments by what kind of support the take offers.</div>
<div class="card">
  <textarea id="t" placeholder="Paste an r/NBA comment..." autofocus></textarea>
  <div class="row"><button id="go">Classify</button>
    <span class="muted" style="font-size:12.5px">or press ⌘/Ctrl + Enter</span></div>
  <div class="exwrap" id="ex"></div>
</div>
<div id="out"></div>
<script>
const LABELS=__LABELS__, BLURB=__BLURB__, EXAMPLES=__EXAMPLES__;
const $=s=>document.querySelector(s);
const esc=s=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

$('#ex').innerHTML=EXAMPLES.map((e,i)=>`<button class="ex" data-i="${i}">${esc(e.slice(0,42))}…</button>`).join('');
document.querySelectorAll('.ex').forEach(b=>b.onclick=()=>{$('#t').value=EXAMPLES[+b.dataset.i];run();});

async function run(){
  const text=$('#t').value.trim();
  if(!text){ $('#out').innerHTML=''; return; }
  $('#go').disabled=true; $('#go').textContent='...';
  try{
    const r=await fetch('/api/classify',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text})});
    const d=await r.json();
    if(d.error){ $('#out').innerHTML=`<div class="card">${esc(d.error)}</div>`; return; }
    const top=d.scores[0], ti=LABELS.indexOf(top.label);
    $('#out').innerHTML=`<div class="card">
      <div class="top l${ti}">${top.label}</div>
      <div class="why">${(top.score*100).toFixed(1)}% confidence — ${esc(BLURB[top.label]||'')}</div>
      ${d.scores.map(s=>{const i=LABELS.indexOf(s.label);return `<div class="b">
        <div class="bh"><span class="l${i}">${s.label}</span><span>${(s.score*100).toFixed(1)}%</span></div>
        <div class="bt"><i class="f${i}" style="width:${(s.score*100).toFixed(1)}%"></i></div></div>`}).join('')}
    </div>`;
  } finally { $('#go').disabled=false; $('#go').textContent='Classify'; }
}
$('#go').onclick=run;
$('#t').addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key==='Enter')run();});
</script></main></body></html>"""


def build_handler(predict):
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
            if self.path != "/":
                return self._send(404, "not found", "text/plain")
            page = (
                PAGE.replace("__LABELS__", json.dumps(LABELS))
                .replace("__BLURB__", json.dumps(BLURB))
                .replace("__EXAMPLES__", json.dumps(EXAMPLES))
            )
            self._send(200, page, "text/html; charset=utf-8")

        def do_POST(self):
            if self.path != "/api/classify":
                return self._send(404, "not found", "text/plain")
            n = int(self.headers.get("Content-Length", 0))
            try:
                text = json.loads(self.rfile.read(n) or b"{}").get("text", "")
                out = {"scores": predict(text[:2000])}
            except Exception as e:
                out = {"error": f"{type(e).__name__}: {e}"}
            self._send(200, json.dumps(out), "application/json")

    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--text", help="classify one comment and exit, no server")
    args = ap.parse_args()

    print(f"loading model from {args.model} ...")
    predict = load_model(args.model)

    if args.text:
        for s in predict(args.text):
            print(f"  {s['label']:<16} {s['score']:.4f}")
        return

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), build_handler(predict)) as httpd:
        url = f"http://127.0.0.1:{args.port}/"
        print(f"\n  TakeMeter running at {url}\n  Ctrl-C to stop.\n")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")


if __name__ == "__main__":
    main()
