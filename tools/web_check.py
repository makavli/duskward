"""Plays the browser build in headless Chrome and checks it: serves build/web-src/build/web, waits for it to load,
times the title's frames, clicks through the journey's map to fly and holds to gather, then loads the page again as
index.html#bot8, where the bot flies the last evening to its end (every flock in the air at once: the heaviest
scene), timing it ten seconds at a time. Saves shots/web_title.png, web_journey.png, web_play.png and web_last.png
(the slowest ten seconds), and fails on a Python traceback in the page's console or on slow frames.

    python tools/web_check.py [seconds to load] [seconds of the last evening, 0 to skip it]
                                                     (after bash tools/web_build.sh; needs Chrome or Edge)
"""
import base64
import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

import websocket  # websocket-client

ROOT = os.path.join(os.path.dirname(__file__), "..")
WEB = os.path.join(ROOT, "build", "web-src", "build", "web")
SHOTS = os.path.join(ROOT, "shots")
WAIT = float(sys.argv[1]) if len(sys.argv) > 1 else 40
LAST = float(sys.argv[2]) if len(sys.argv) > 2 else 240      # the bot roosts in the Long Reeds after about 165 s
SLOW_P50 = 34                     # ms: a median frame slower than this is under 30 frames a second
SHARED = bool(os.environ.get("CI"))  # a shared runner's frame times say little: there they are printed, not judged


def chrome():
    for p in (os.environ.get("CHROME", ""), r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", shutil.which("google-chrome") or "",
              shutil.which("chromium") or "", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        if p and os.path.exists(p):
            return p
    sys.exit("no Chrome found: set CHROME")


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


GAPS = ("window.gaps = []; (function f(t0) { requestAnimationFrame(t => { gaps.push(t - t0); f(t) }) })"
        "(performance.now())")
STATS = """JSON.stringify((() => {
    const g = gaps.slice().sort((a, b) => a - b), q = p => Math.round(g[Math.floor(p * (g.length - 1))]);
    let a = null;
    try { const s = Module.SDL2; a = [s.audioContext.sampleRate, s.audio.scriptProcessorNode.bufferSize] } catch (e) {}
    return {frames: g.length, p50: q(0.5), p95: q(0.95), max: q(1), audio: a} })())"""


def main():
    if not os.path.exists(os.path.join(WEB, "index.html")):
        sys.exit("no build: run bash tools/web_build.sh first")
    srv = http.server.ThreadingHTTPServer((   # threads: Chrome keeps idle connections open
        "127.0.0.1", 0), functools.partial(Quiet, directory=WEB))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    profile = tempfile.mkdtemp()
    proc = subprocess.Popen([chrome(), "--headless=new", "--mute-audio", "--remote-debugging-port=0",
                             "--user-data-dir=" + profile, "--autoplay-policy=no-user-gesture-required",
                             "--window-size=1280,720", "--no-first-run", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    lines, n = [], [0]
    try:
        for _ in range(100):                       # Chrome picks a free loopback port and writes it in the profile
            try:
                with open(os.path.join(profile, "DevToolsActivePort")) as f:
                    debug = int(f.readline())
                tabs = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json" % debug))
                break
            except (OSError, ValueError):
                time.sleep(0.2)
        ws = websocket.create_connection([t for t in tabs if t["type"] == "page"][0]["webSocketDebuggerUrl"])

        def call(method, **params):
            n[0] += 1
            ws.send(json.dumps({"id": n[0], "method": method, "params": params}))
            ws.settimeout(60)                      # a page that stops answering fails the check: it never hangs it
            while True:
                m = json.loads(ws.recv())
                if m.get("id") == n[0]:
                    return m.get("result", {})
                note(m)

        def note(m):
            if m.get("method") == "Runtime.consoleAPICalled":
                lines.append(" ".join(str(a.get("value", a.get("description", ""))) for a in m["params"]["args"]))
            elif m.get("method") == "Runtime.exceptionThrown":
                lines.append("EXCEPTION " + m["params"]["exceptionDetails"].get("text", ""))
            elif m.get("method") == "Page.javascriptDialogOpening":     # the page asks before it is left: yes
                ws.send(json.dumps({"id": 10 ** 6, "method": "Page.handleJavaScriptDialog", "params": {"accept": True}}))
            elif m.get("method") == "Log.entryAdded" and m["params"]["entry"]["level"] == "error":
                e = m["params"]["entry"]
                lines.append("browser %s: %s %s" % (e["source"], e["text"], e.get("url", "")))

        def pump(seconds):
            end = time.time() + seconds
            ws.settimeout(0.2)
            while time.time() < end:
                try:
                    note(json.loads(ws.recv()))
                except websocket.WebSocketTimeoutException:
                    pass

        def shot(name):
            data = call("Page.captureScreenshot", format="png")["data"]
            os.makedirs(SHOTS, exist_ok=True)
            with open(os.path.join(SHOTS, name), "wb") as f:
                f.write(base64.b64decode(data))

        def mouse(kind, x, y):
            call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", clickCount=1)

        def say(*words):
            print(time.strftime("%H:%M:%S"), *words, flush=True)

        def seen(text):
            return any(text in ln for ln in lines)

        def stats():
            return json.loads(call("Runtime.evaluate", returnByValue=True, expression=STATS)["result"]["value"])

        call("Runtime.enable")
        call("Log.enable")
        call("Page.enable")
        call("Page.navigate", url="http://127.0.0.1:%d/" % port)
        pump(WAIT)                                 # built with --ume_block 0: the game starts without a click
        call("Runtime.evaluate", expression=GAPS)
        pump(5)
        title = stats()
        shot("web_title.png")
        say("the title:", title)
        for name in ("web_journey.png", None):     # the journey's map, then: fly
            mouse("mousePressed", 700, 300)
            mouse("mouseReleased", 700, 300)
            pump(2)
            if name:
                shot(name)
        say("flying")
        mouse("mousePressed", 760, 320)            # hold to gather, and steer
        for k in range(10):
            mouse("mouseMoved", 760 + k * 20, 320 - k * 8)
            pump(0.4)
        mouse("mouseReleased", 960, 240)
        pump(2)
        shot("web_play.png")
        flew, worst, ended = seen("Duskward: evening 1"), None, False
        if LAST:
            say("the last evening, by the bot")
            call("Page.navigate", url="http://127.0.0.1:%d/?last#bot8" % port)
            pump(WAIT)
            call("Runtime.evaluate", expression=GAPS)
            for _ in range(int(LAST / 10)):
                if ended:
                    break
                call("Runtime.evaluate", expression="gaps.length = 0")
                pump(10)
                now = stats()
                say("  ten seconds:", now["frames"], "frames, p50", now["p50"], "ms")
                if now["frames"] and (not worst or now["p50"] > worst["p50"]):
                    worst = now
                    shot("web_last.png")
                ended = seen("Duskward: evening 8 ended")
    finally:
        proc.terminate()
        proc.wait(timeout=10)
        shutil.rmtree(profile, ignore_errors=True)
        srv.shutdown()
    text = "\n".join(lines)
    bad = [ln for ln in lines if "Traceback" in ln or "Error" in ln.split(":")[0] or ln.startswith("EXCEPTION")]
    print("\n".join(lines[-20:]))
    print("screenshots: shots/web_title.png web_journey.png web_play.png web_last.png")
    print("title frames (260 birds): %(frames)d, p50 %(p50)s ms, p95 %(p95)s ms, max %(max)s ms" % title)
    if not title["frames"] or (title["p50"] > SLOW_P50 and not SHARED):
        bad.append("the title runs under 30 frames a second in the browser")
    if not flew:
        bad.append("two clicks on the title did not start an evening")
    if LAST:
        print("the last evening:", next((ln for ln in lines if "evening 8 ended" in ln), "not ended"))
        if not ended:
            bad.append("the bot's last evening did not end in %d s" % LAST)
        if not worst:
            bad.append("the last evening drew no frames")
        else:
            print("the last evening by the bot, its slowest ten seconds: %(frames)d frames, p50 %(p50)s ms, "
                  "p95 %(p95)s ms, max %(max)s ms" % worst)
            if worst["p50"] > SLOW_P50 and not SHARED:
                bad.append("the last evening runs under 30 frames a second in the browser")
    if not title["audio"]:
        bad.append("could not read the page's sound buffer (Module.SDL2)")
    else:
        rate, size = title["audio"]
        print("sound: device %d Hz, buffer %d frames = %.0f ms" % (rate, size, 1000 * size / rate))
        if 1000 * size / rate < 40:
            bad.append("the sound buffer is shorter than a slow frame: the sound ticks")
    if not any(ln.startswith("pythons.js") for ln in lines):
        bad.insert(0, "the page's loader never ran: pythons.js and Python come from the pygame-web CDN, did it load?")
    if bad or "Traceback" in text:
        print("FAIL:", *bad[:5], sep="\n  ")
        sys.exit(1)
    print("web check passed")


if __name__ == "__main__":
    main()
