"""S7 calibration kit — local web UI on the edge device (stdlib only).

    python -m edge.calibrate --camera edge/cameras/meva_G420_door.yaml [--port 8765]

Grabs one snapshot from the camera's source, serves http://127.0.0.1:8765 where the operator draws the door
line, room polygon, trainer zone, asset zones and timestamp box, and writes them back into the camera YAML.
Bound to 127.0.0.1: the snapshot (which may show people) never leaves the device.
"""
from __future__ import annotations

import argparse
import base64
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

import cv2
import yaml

from edge.ingest import frames

PAGE = """<!doctype html><meta charset=utf-8><title>SAKSHI calibration</title>
<style>body{font:14px system-ui;margin:12px}canvas{max-width:100%;border:1px solid #999;cursor:crosshair}
button{margin:2px;padding:4px 8px}.on{font-weight:bold;outline:2px solid #0072B2}</style>
<p>Click to place points. Door line = 2 points (inside of the room on the <b>right</b> when walking from point 1 to 2).
Polygons: click points, then "close". Timestamp box = 2 corners.</p>
<div id=m></div><canvas id=c></canvas><p><input id=lbl placeholder="asset label (e.g. lathe machine)">
<button onclick=save()>Save to YAML</button> <span id=s></span></p><pre id=o></pre>
<script>
const cfg=__CFG__, img=new Image(); img.src="data:image/jpeg;base64,__IMG__";
const C={door_line:"#D55E00",room_polygon:"#0072B2",trainer_zone:"#E69F00",asset:"#009E73",timestamp_roi:"#CC79A7"};
let mode="door_line",cur=[];const c=document.getElementById("c"),g=c.getContext("2d");
const M=document.getElementById("m");Object.keys(C).forEach(k=>{const b=document.createElement("button");b.textContent=k;
b.onclick=()=>{mode=k;cur=[];draw()};M.appendChild(b)});const cl=document.createElement("button");cl.textContent="close polygon";
cl.onclick=()=>{if(cur.length<3)return;if(mode==="asset"){cfg.assets=cfg.assets||[];cfg.assets.push({asset_id:"ASSET-"+(cfg.assets.length+1),
label:document.getElementById("lbl").value||"asset",zone:cur})}else cfg[mode]=cur;cur=[];draw()};M.appendChild(cl);
img.onload=()=>{c.width=img.width;c.height=img.height;draw()};
c.onclick=e=>{const r=c.getBoundingClientRect(),p=[Math.round((e.clientX-r.left)*c.width/r.width),Math.round((e.clientY-r.top)*c.height/r.height)];
if(mode==="door_line"){cur.push(p);if(cur.length===2){cfg.door_line=cur;cur=[]}}
else if(mode==="timestamp_roi"){cur.push(p);if(cur.length===2){const[a,b]=cur;cfg.timestamp_roi=[Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.abs(b[0]-a[0]),Math.abs(b[1]-a[1])];cur=[]}}
else cur.push(p);draw()};
function poly(p,col,close){if(!p||!p.length)return;g.strokeStyle=col;g.lineWidth=3;g.beginPath();p.forEach((q,i)=>i?g.lineTo(...q):g.moveTo(...q));if(close)g.closePath();g.stroke()}
function draw(){g.drawImage(img,0,0);poly(cfg.door_line,C.door_line);poly(cfg.room_polygon,C.room_polygon,1);poly(cfg.trainer_zone,C.trainer_zone,1);
(cfg.assets||[]).forEach(a=>poly(a.zone,C.asset,1));if(cfg.timestamp_roi){const[x,y,w,h]=cfg.timestamp_roi;g.strokeStyle=C.timestamp_roi;g.strokeRect(x,y,w,h)}
poly(cur,C[mode]||"#000");[...document.querySelectorAll("#m button")].forEach(b=>b.className=b.textContent===mode?"on":"");
document.getElementById("o").textContent=JSON.stringify({door_line:cfg.door_line,room_polygon:cfg.room_polygon,trainer_zone:cfg.trainer_zone,assets:cfg.assets,timestamp_roi:cfg.timestamp_roi},null,1)}
async function save(){const r=await fetch("/save",{method:"POST",body:JSON.stringify(cfg)});document.getElementById("s").textContent=await r.text()}
</script>"""

KEYS = ("door_line", "room_polygon", "trainer_zone", "assets", "timestamp_roi")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", required=True)
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.camera))
    frame, _ = next(frames(cfg["source"], 1, cfg.get("start_time")))
    jpg = base64.b64encode(cv2.imencode(".jpg", frame)[1].tobytes()).decode()
    page = PAGE.replace("__CFG__", json.dumps({k: cfg.get(k) for k in KEYS})).replace("__IMG__", jpg).encode()

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers(); self.wfile.write(page)

        def do_POST(self):
            new = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            cfg.update({k: new.get(k) for k in KEYS if new.get(k) is not None})
            with open(a.camera, "w") as f:
                yaml.safe_dump(cfg, f, sort_keys=False)
            self.send_response(200); self.end_headers(); self.wfile.write(f"saved {a.camera}".encode())

    print(f"calibration UI → http://127.0.0.1:{a.port}  (Ctrl-C to stop)")
    HTTPServer(("127.0.0.1", a.port), H).serve_forever()


if __name__ == "__main__":
    main()
