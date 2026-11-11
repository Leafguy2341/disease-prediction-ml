"""Actual localhost Chromium UI, with mock LLM/model only. No external API or test CSV."""
import base64
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time

import httpx
import pytest
import uvicorn

from app.backend.chat import ChatRuntime
from app.backend.main import create_app
from src.models.ensemble import phase4_guard
from test_local_chat import answer
from test_phase5b import QueueProvider
from test_prediction_api import deployment, get_service


@pytest.mark.skipif(os.environ.get("DISEASE_BROWSER_SMOKE") != "1", reason="Opt in with DISEASE_BROWSER_SMOKE=1; browser requires local IPC permission")
def test_chromium_chat_clarification_negation_urgent_reset_and_safe_render(deployment, tmp_path):
    websockets = pytest.importorskip("websockets.sync.client")
    browser = next((p for p in (Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
                               Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")) if p.is_file()), None)
    if browser is None:
        pytest.skip("Local Chromium not installed; no claim of actual browser verification")
    service = get_service(deployment)
    from src.agent.offline import OfflineExtractor, OfflinePolicy
    project = Path(__file__).resolve().parents[1]
    provider = OfflineExtractor(service.catalog,project/'configs/synonyms.json')
    runtime = ChatRuntime(service, provider, offline_policy=OfflinePolicy.from_file(project/'configs/phase5b.json'))
    from test_three_model_web import extras
    # Separate real dialogue stores for all synthetic model services.
    app = create_app(service_loader=lambda: service, optional_loader=extras)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", log_level="warning", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    profile = tmp_path / "owned-chromium-profile"
    proc = None
    project = Path(__file__).resolve().parents[1]
    with phase4_guard(project) as guard:
        try:
            thread.start()
            deadline = time.monotonic() + 10
            while not server.started and time.monotonic() < deadline:
                time.sleep(.05)
            assert server.started
            proc = subprocess.Popen([str(browser), "--headless=new", "--disable-gpu", "--no-first-run",
                "--no-default-browser-check", "--disable-background-networking", "--disable-component-update",
                "--disable-sync", "--disable-extensions", "--remote-debugging-port=0",
                f"--user-data-dir={profile}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                env={k: v for k, v in os.environ.items() if k not in {"GEMINI_API_KEY", "GOOGLE_API_KEY"}})
            active = profile / "DevToolsActivePort"
            deadline = time.monotonic() + 15
            while not active.is_file() and time.monotonic() < deadline and proc.poll() is None:
                time.sleep(.05)
            error = proc.stderr.read().decode("utf-8", errors="replace") if proc.poll() is not None else ""
            assert active.is_file(), f"Chromium debugger unavailable (exit={proc.poll()}): {error[:1500]}"
            debug_port = int(active.read_text().splitlines()[0])
            with httpx.Client(trust_env=False) as client:
                pages = client.get(f"http://127.0.0.1:{debug_port}/json/list").json()
            url = next(p["webSocketDebuggerUrl"] for p in pages if p["type"] == "page")
            with websockets.connect(url, proxy=None, open_timeout=10, close_timeout=1) as ws:
                serial = [0]
                def cdp(method, params=None):
                    serial[0] += 1
                    ws.send(json.dumps({"id": serial[0], "method": method, "params": params or {}}))
                    while True:
                        item = json.loads(ws.recv(timeout=15))
                        if item.get("id") == serial[0]:
                            assert "error" not in item, item
                            return item.get("result", {})
                def evaluate(source):
                    result = cdp("Runtime.evaluate", {"expression": source, "awaitPromise": True, "returnByValue": True})
                    assert "exceptionDetails" not in result, result
                    return result.get("result", {}).get("value")
                cdp("Emulation.setDeviceMetricsOverride", {"width": 1200, "height": 900, "deviceScaleFactor": 1, "mobile": False})
                cdp("Page.navigate", {"url": f"http://127.0.0.1:{port}/"})
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if evaluate("!!document.querySelector('#chat-form') && document.readyState === 'complete'"):
                        break
                    time.sleep(.1)
                assert evaluate("document.title").startswith("Lắng nghe")
                evaluate("window.uiWait = async (test) => { const end=Date.now()+8000; while(!test()){ if(Date.now()>end)throw Error('UI wait timeout'); await new Promise(r=>setTimeout(r,40)); } }; true")
                def send(text, count):
                    return evaluate("(async()=>{document.querySelector('#message').value=" + json.dumps(text) +
                        ";document.querySelector('#chat-form').requestSubmit();await uiWait(()=>document.querySelectorAll('.message.assistant').length===" + str(count) +
                        " && !document.querySelector('#send').disabled);return document.querySelectorAll('.message.assistant')[" + str(count-1) + "].textContent;})()")
                assert "âm đạo" in send("Tôi bị ngứa âm đạo.", 1)
                assert evaluate("document.querySelectorAll('.batch-form select').length") == 3
                (tmp_path/'offline-v2-batch.png').write_bytes(base64.b64decode(cdp('Page.captureScreenshot',{'format':'png'})['data']))
                assert evaluate("document.querySelector('#model-select').value") == 'lr_tuned_c2'
                evaluate("document.querySelectorAll('.batch-form select').forEach((e,i)=>e.value=i<2?'present':'denied');document.querySelector('.batch-form').requestSubmit();true")
                evaluate("(async()=>{await uiWait(()=>document.querySelectorAll('.message.assistant').length===2 && !document.querySelector('#send').disabled);return true})()")
                assert evaluate("document.querySelectorAll('.result-row').length") == 3
                evaluate("(async()=>{await new Promise(requestAnimationFrame);document.querySelector('#messages').scrollTop=document.querySelector('#messages').scrollHeight;await new Promise(requestAnimationFrame);return true})()")
                (tmp_path/'offline-v2-result.png').write_bytes(base64.b64decode(cdp('Page.captureScreenshot',{'format':'png'})['data']))
                assert evaluate("Array.from(document.querySelectorAll('.score')).map(e=>e.textContent)") == ["40.0000%", "30.0000%", "10.0000%"]
                send("Tôi nói nhầm, hiện tôi vẫn ho nhưng không sốt.", 3)
                assert evaluate("document.querySelectorAll('.result-box').length") == 1
                assert "khẩn cấp" in send("Khó thở nặng, thở không nổi.", 4)
                assert evaluate("document.querySelectorAll('.message.urgent').length") == 1
                evaluate("document.querySelector('#new-chat').click();true")
                evaluate("(async()=>{await uiWait(()=>document.querySelectorAll('.message.assistant').length===1 && !document.querySelector('#send').disabled);return true})()")
                assert evaluate("document.querySelectorAll('.result-box').length") == 0
                send('Tôi ho.',2)
                evaluate("Array.from(document.querySelectorAll('.dialogue-actions button')).find(e=>!e.disabled && e.textContent==='Xem kết quả tham khảo hiện tại').click();true")
                evaluate("(async()=>{await uiWait(()=>document.querySelectorAll('.message.assistant').length===3 && !document.querySelector('#send').disabled);return true})()")
                assert evaluate("document.querySelectorAll('.result-row').length") == 3
                assert 'Điểm mô hình (%)' in evaluate("document.querySelector('.result-title').textContent")
                assert 'chưa xác minh' in evaluate("document.querySelector('.evaluation-reference').textContent")
                evaluate("document.querySelector('#new-chat').click();true")
                evaluate("(async()=>{await uiWait(()=>document.querySelectorAll('.message.assistant').length===1 && !document.querySelector('#send').disabled);return true})()")
                send("Tôi ho và sốt. <img src=x onerror='window.__xss=1'>", 2)
                assert evaluate("document.querySelectorAll('.messages img').length") == 0
                assert not evaluate("!!window.__xss")
                assert evaluate("document.querySelectorAll('.result-row').length") == 0
                evaluate("document.querySelector('#settings-open').click();document.querySelector('#api-key').value='synthetic-not-a-secret';true")
                assert evaluate("document.querySelector('#api-key').type") == 'password'
                assert evaluate("document.querySelector('#settings-dialog button[disabled]')!==null")
                evaluate("document.querySelector('#settings-dialog').close();true")
                evaluate("(async()=>{await uiWait(()=>document.querySelector('#api-key').value==='');return true})()")
                assert evaluate("localStorage.length===0 && sessionStorage.length===0")
                assert len(deployment[2].calls)==2
                assert evaluate("document.querySelectorAll('#model-select option').length")==3
                evaluate("document.querySelector('#model-select').value='lr_baseline';document.querySelector('#model-select').dispatchEvent(new Event('change'));true")
                evaluate("(async()=>{await uiWait(()=>document.querySelectorAll('.message.assistant').length===1 && !document.querySelector('#send').disabled);return true})()")
                send('Tôi ho.',2)
                evaluate("Array.from(document.querySelectorAll('.dialogue-actions button')).find(e=>!e.disabled && e.textContent==='Xem kết quả tham khảo hiện tại').click();true")
                evaluate("(async()=>{await uiWait(()=>document.querySelectorAll('.message.assistant').length===3 && !document.querySelector('#send').disabled);return true})()")
                assert 'lr_baseline' in evaluate("document.querySelector('.result-title').textContent")
                assert evaluate("document.querySelectorAll('.score').length")==3
                evaluate("document.querySelector('#model-select').value='hard_tuned_lr_svc_knn';document.querySelector('#model-select').dispatchEvent(new Event('change'));true")
                evaluate("(async()=>{await uiWait(()=>document.querySelectorAll('.message.assistant').length===1 && !document.querySelector('#send').disabled);return true})()")
                send('Tôi ho.',2)
                evaluate("Array.from(document.querySelectorAll('.dialogue-actions button')).find(e=>!e.disabled && e.textContent==='Xem kết quả tham khảo hiện tại').click();true")
                evaluate("(async()=>{await uiWait(()=>document.querySelectorAll('.message.assistant').length===3 && !document.querySelector('#send').disabled);return true})()")
                assert evaluate("document.querySelectorAll('.hard-vote .member-vote').length")==3
                assert evaluate("document.querySelectorAll('.score').length")==0
                assert 'HARD VOTING' in evaluate("document.querySelector('.result-title').textContent")
                evaluate("document.querySelector('#mode-select').value='llm';document.querySelector('#mode-select').dispatchEvent(new Event('change'));true")
                assert evaluate("document.querySelector('#send').disabled")
                screenshot = cdp("Page.captureScreenshot", {"format": "png"})["data"]
                (tmp_path / "local-chat-desktop.png").write_bytes(base64.b64decode(screenshot))
                cdp("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
                assert evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                (tmp_path / "local-chat-mobile.png").write_bytes(base64.b64decode(cdp("Page.captureScreenshot", {"format": "png"})["data"]))
                print("CHROMIUM MOCK UI PASS; screenshots:", str(tmp_path))
            assert len(deployment[2].calls) == 3
        finally:
            if proc is not None and proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=10)
            server.should_exit = True
            thread.join(timeout=10)
            listener.close()
    assert not any(guard.values()), guard
