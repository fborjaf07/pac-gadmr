#!/usr/bin/env python3
"""
4_sync_tramites_pac.py
Lee pac_links.json de pac-gadmr, hace login CAS via Playwright,
extrae historial de cada tramite y sube tramites_pac.json a pac-gadmr.
"""

import json, os, re, time, base64, urllib.request
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

CAS_URL    = "https://egob.gadmriobamba.gob.ec:8443/cas/login"
EDOC_BASE  = "http://egobedoc.gadmriobamba.gob.ec:8081"
USUARIO    = os.environ["EDOC_USUARIO"]
CONTRASENA = os.environ["EDOC_CONTRASENA"]
OUTPUT     = "tramites_pac.json"

def login(page):
    print("[...] Login CAS")
    page.goto(f"{CAS_URL}?service={EDOC_BASE}/login/cas", wait_until="networkidle")
    page.fill('input[name="username"]', USUARIO)
    page.fill('input[name="password"]', CONTRASENA)
    page.click('input[type="submit"]')
    page.wait_for_url(f"{EDOC_BASE}/**", timeout=15000)
    print("[OK] Login exitoso")

def extraer_tramite(page, numero):
    try:
        page.goto(f"{EDOC_BASE}/issues/{numero}", wait_until="domcontentloaded", timeout=20000)
        if "cas/login" in page.url:
            return {"numero": numero, "encontrado": False, "error": "Sesion expirada",
                    "movimientos": [], "estado_edoc": "", "descripcion": ""}
        html = page.content()
    except Exception as e:
        return {"numero": numero, "encontrado": False, "error": str(e),
                "movimientos": [], "estado_edoc": "", "descripcion": ""}

    desc = ""
    try: desc = page.locator(".subject").first.inner_text().strip()
    except: pass

    estado = ""
    try: estado = page.locator(".status").first.inner_text().strip()
    except: pass

    movimientos = []
    pat = re.compile(
        r'\(\s*\d+\s*\)\s*#\d+\s+(.*?)\s*\((.*?)\)\s*'
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})(.*?)(?=\(\s*\d+\s*\)\s*#\d+|\Z)', re.S)
    for m in pat.finditer(html):
        nombre  = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        cargo   = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        fecha   = m.group(3).strip()
        resto   = m.group(4)
        nota_m  = re.search(r'Nota[:\s]+(.*?)(?:Documento|Asignado|$)', resto, re.S)
        nota    = re.sub(r'<[^>]+>', '', nota_m.group(1)).strip()[:300] if nota_m else ""
        env_m   = re.search(r'Enviado a\s+(.*?)(?:\n|<)', resto, re.S)
        enviado = re.sub(r'<[^>]+>', '', env_m.group(1)).strip() if env_m else ""
        movimientos.append({"nombre": nombre, "cargo": cargo, "fecha": fecha,
                             "nota": nota, "enviado_a": enviado})

    ultimo = movimientos[0] if movimientos else None
    horas = None
    if ultimo:
        try:
            dt = datetime.strptime(ultimo["fecha"], "%Y-%m-%d %H:%M")
            horas = round((datetime.now() - dt).total_seconds() / 3600, 1)
        except: pass

    return {"numero": numero, "encontrado": True, "descripcion": desc[:200],
            "estado_edoc": estado, "horas_sin_movimiento": horas,
            "tiempo_texto": f"{int(horas)}h" if horas else "",
            "movimientos": movimientos, "ultimo_movimiento": ultimo, "error": None}

def subir_github(data):
    token = os.environ.get("PAC_GADMR_TOKEN", "")
    if not token: print("[WARN] Sin PAC_GADMR_TOKEN"); return
    repo  = "fborjaf07/pac-gadmr"
    fname = "tramites_pac.json"
    url   = f"https://api.github.com/repos/{repo}/contents/{fname}"
    content = base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode()).decode()
    sha = None
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"token {token}",
              "Accept": "application/vnd.github.v3+json"})
        sha = json.loads(urllib.request.urlopen(req).read())["sha"]
    except: pass
    body = {"message": "sync: tramites_pac", "content": content}
    if sha: body["sha"] = sha
    req2 = urllib.request.Request(url, data=json.dumps(body).encode(), method="PUT",
        headers={"Authorization": f"token {token}", "Content-Type": "application/json",
                 "Accept": "application/vnd.github.v3+json"})
    urllib.request.urlopen(req2)
    print(f"[OK] tramites_pac.json → {repo}")

if __name__ == "__main__":
    print("=" * 60)
    print(f"Sync Trámites PAC — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Leer pac_links.json desde pac-gadmr
    numeros = []
    try:
        url = "https://raw.githubusercontent.com/fborjaf07/pac-gadmr/main/pac_links.json?_=" + str(int(time.time()))
        links = json.loads(urllib.request.urlopen(url).read())
        numeros = sorted(set(
            str(v.get("tramite_edoc","")).strip()
            for v in links.values() if v.get("tramite_edoc","").strip()
        ))
        print(f"[OK] {len(numeros)} trámites vinculados: {numeros}")
    except Exception as e:
        print(f"[ERROR] pac_links.json: {e}")

    if not numeros:
        output = {"timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                  "total_vinculados": 0, "total_encontrados": 0, "tramites": {}}
        with open(OUTPUT, "w") as f: json.dump(output, f)
        print("[OK] Sin vínculos — tramites_pac.json vacío")
    else:
        resultado = {}
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context(ignore_https_errors=True).new_page()
            login(page)
            for i, num in enumerate(numeros, 1):
                print(f"[{i}/{len(numeros)}] #{num}")
                t = extraer_tramite(page, num)
                resultado[num] = t
                print(f"  {'OK' if t['encontrado'] else 'ERROR'} | estado={t['estado_edoc']!r} | movs={len(t.get('movimientos',[]))}")
                time.sleep(0.3)
            browser.close()

        output = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "total_vinculados": len(resultado),
            "total_encontrados": sum(1 for v in resultado.values() if v.get("encontrado")),
            "tramites": resultado
        }
        with open(OUTPUT, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"[OK] {output['total_encontrados']}/{output['total_vinculados']} encontrados")
        subir_github(output)

    print("=" * 60)
