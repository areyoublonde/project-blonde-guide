"""Tiny Chrome DevTools Protocol driver (stdlib only): launch headless Chrome, click, type, read, screenshot.

Used by review.py to actually operate the site the way a visitor would. Uses a throw-away profile and
only ever stops the Chrome process it started.
"""
import base64, json, os, socket, struct, subprocess, tempfile, time, urllib.request

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


class Chrome:
    def __init__(self, port=9377):
        self.dir = tempfile.mkdtemp(prefix="pb-review-")
        self.proc = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={self.dir}", "--no-first-run", "--disable-gpu",
                                      "--hide-scrollbars", "--window-size=1440,900", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=1).read())
                page = next(t for t in tabs if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.2)
        else:
            raise RuntimeError("Chrome did not start")
        url = page["webSocketDebuggerUrl"]
        host, path = url[5:].split("/", 1)
        self.s = socket.create_connection(("127.0.0.1", port))
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(f"GET /{path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n".encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(4096)
        self.buf, self.id, self.events = buf.split(b"\r\n\r\n", 1)[1], 0, []
        for d in ("Page", "Runtime"):
            self.send(f"{d}.enable")

    # --- websocket framing
    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.s.recv(1 << 16)
            if not chunk:
                raise RuntimeError("socket closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def _recv(self):
        data = b""
        while True:
            b1, b2 = self._read(2)
            n = b2 & 127
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(n)
            if b1 & 15 == 9:      # ping
                continue
            data += payload
            if b1 & 128:
                return json.loads(data)

    def send(self, method, **params):
        self.id += 1
        msg = json.dumps({"id": self.id, "method": method, "params": params}).encode()
        mask = os.urandom(4)
        head = bytes([0x81]) + (bytes([0x80 | len(msg)]) if len(msg) < 126 else bytes([0x80 | 126]) + struct.pack(">H", len(msg)) if len(msg) < 65536 else bytes([0x80 | 127]) + struct.pack(">Q", len(msg)))
        self.s.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(msg)))
        while True:
            m = self._recv()
            if m.get("id") == self.id:
                if "error" in m:
                    raise RuntimeError(f"{method}: {m['error']}")
                return m.get("result", {})
            self.events.append(m)

    # --- actions
    def viewport(self, w, h, scale=1, mobile=False):
        self.send("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=scale, mobile=mobile)
        self.send("Emulation.setTouchEmulationEnabled", enabled=mobile)
        self.w, self.h = w, h

    def js(self, expr):
        for attempt in range(3):   # a navigation can interrupt an evaluation; retry once the new page is there
            try:
                r = self.send("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
                break
            except RuntimeError as e:
                if "navigated" not in str(e) and "context" not in str(e).lower() or attempt == 2:
                    raise
                time.sleep(0.6)
        if "exceptionDetails" in r:
            raise RuntimeError(r["exceptionDetails"].get("exception", {}).get("description", str(r["exceptionDetails"])))
        return r["result"].get("value")

    def wait(self, expr, timeout=5):
        t = time.time()
        while time.time() - t < timeout:
            if self.js(expr):
                return True
            time.sleep(0.1)
        return False

    def nav(self, url):
        self.send("Page.navigate", url=url)
        self.wait("document.readyState==='complete'", 10)
        time.sleep(0.5)

    def url(self):
        return self.js("location.pathname+location.search+location.hash")

    def point(self, sel, nth=0):
        return self.js(f"""(()=>{{const e=[...document.querySelectorAll({json.dumps(sel)})].filter(e=>e.getClientRects().length)[{nth}];if(!e)return null;
            e.scrollIntoView({{block:'center',behavior:'instant'}});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}})()""")

    def click(self, sel, nth=0):
        p = self.point(sel, nth)
        if not p:
            raise RuntimeError(f"nothing visible to click: {sel}")
        time.sleep(0.15)
        p = self.point(sel, nth)
        for t in ("mousePressed", "mouseReleased"):
            self.send("Input.dispatchMouseEvent", type=t, x=p[0], y=p[1], button="left", clickCount=1)
        time.sleep(0.35)

    def hover(self, sel, nth=0):
        p = self.point(sel, nth)
        self.send("Input.dispatchMouseEvent", type="mouseMoved", x=p[0], y=p[1])
        time.sleep(0.2)

    def type(self, text):
        self.send("Input.insertText", text=text)
        time.sleep(0.5)

    def key(self, key, code=None, vk=0):
        for t in ("keyDown" if len(key) == 1 else "rawKeyDown", "keyUp"):
            self.send("Input.dispatchKeyEvent", type=t, key=key, code=code or key, windowsVirtualKeyCode=vk, text=(key if len(key) == 1 and t == "keyDown" else ""))
        time.sleep(0.4)

    def shot(self, path, full=False):
        args = {"format": "png"}
        if full:
            h = self.js("Math.ceil(document.documentElement.scrollHeight)")
            args.update(captureBeyondViewport=True, clip={"x": 0, "y": 0, "width": self.w, "height": min(h, 12000), "scale": 1})
        data = self.send("Page.captureScreenshot", **args)["data"]
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))

    def close(self):
        try:
            self.s.close()
        finally:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
