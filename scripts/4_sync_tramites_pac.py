#!/usr/bin/env python3
"""
4_sync_tramites_pac.py
----------------------
Login directo al e-DOC via CAS, extrae historial de cada trámite
vinculado al PAC y genera tramites_pac.json en este mismo repo.

Secrets requeridos en pac-gadmr:
  EDOC_USUARIO     — usuario e-DOC
  EDOC_CONTRASENA  — contraseña e-DOC
  PAC_GADMR_TOKEN  — GitHub PAT con permisos repo
"""

import json, os, re, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone
from http.cookiejar import CookieJar

# ── CONFIG ────────────────────────────────────────────────────────────────────
CAS_URL      = "https://egob.gadmriobamba.gob.ec:8443/cas/login"
EDOC_BASE    = "http://egobedoc.gadmriobamba.gob.ec:8081"
EDOC_SERVICE = f"{EDOC_BASE}/login/cas"
PAC_LINKS    = "pac_links.json"
OUTPUT       = "tramites_pac.json"
USUARIO      = os.environ["EDOC_USUARIO"]
CONTRASENA   = os.environ["EDOC_CONTRASENA"]

# ── HTTP con cookies ──────────────────────────────────────────────────────────
jar = CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(jar),
    urllib.request.HTTPSHandler(context=__import__('ssl').create_default_context())
)
opener.addheaders = [
    ("User-Agent", "Mozilla/5.0 (PAC-Monitor-Bot/1.0)"),
    ("Accept", "text/html,application/xhtml+xml"),
]

def get(url, timeout=30):
    with opener.open(url, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")

def post(url, data, timeout=30):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with opener.open(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")

# ── Login CAS ─────────────────────────────────────────────────────────────────
def login():
    print("[...] Login CAS")
    # 1. GET login page → obtener execution token
    login_url = f"{CAS_URL}?service={urllib.parse.quote(EDOC_SERVICE)}"
    html = get(login_url)
    m = re.search(r'name="execution"\s+value="([^"]+)"', html)
    if not m:
        raise Exception("No se encontró execution token en CAS")
    execution = m.group(1)
    # 2. POST credenciales
    post(login_url, {
        "username":  USUARIO,
        "password":  CONTRASENA,
        "execution": execution,
        "_eventId":  "submit",
        "geolocation": ""
    })
    # 3. Acceder al e-DOC para establecer sesión
    get(EDOC_SERVICE)
    get(f"{EDOC_BASE}/my/pmy")
    print("[OK] Login exitoso")

# ── Extraer historial de un trámite ──────────────────────────────────────────
def extraer_tramite(numero):
    url = f"{EDOC_BASE}/issues/{numero}"
    try:
        html = get(url, timeout=20)
    except Exception as e:
        return {"numero": numero, "encontrado": False, "error": str(e),
                "movimientos": [], "estado_edoc": "", "descripcion": ""}

    if "login" in html.lower() and "cas" in html.lower():
        return {"numero": numero, "encontrado": False, "error": "Sesión expirada",
                "movimientos": [], "estado_edoc": "", "descripcion": ""}

    # Descripción
    desc = ""
    m = re.search(r'<div[^>]*class="[^"]*subject[^"]*"[^>]*>(.*?)</div>', html, re.S)
    if m: desc = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    if not desc:
        m = re.search(r'<title>(.*?)</title>', html, re.S)
        if m: desc = re.sub(r'<[^>]+>', '', m.group(1)).strip()

    # Estado
    estado = ""
    m = re.search(r'Estado[^\:]*:\s*</[^>]+>\s*<[^>]+>(.*?)</[^>]+>', html, re.S)
    if m: estado = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    if not estado:
        m = re.search(r'class="[^"]*status[^"]*"[^>]*>(.*?)</[^>]+>', html, re.S)
        if m: estado = re.sub(r'<[^>]+>', '', m.group(1)).strip()

    # Movimientos del historial
    movimientos = []
    # Buscar bloques del historial interno
    hist_match = re.search(
        r'Hist[oó]rico\s*\(Interno\)(.*?)(?:Hist[oó]rico\s*\(Externo\)|$)',
        html, re.S | re.I
    )
    bloque = hist_match.group(1) if hist_match else html

    # Patrón de cada movimiento
    pat = re.compile(
        r'\(\s*\d+\s*\)\s*#\d+\s+(.*?)\s*\((.*?)\)\s*'
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})'
        r'(.*?)(?=\(\s*\d+\s*\)\s*#\d+|\Z)',
        re.S
    )
    for m in pat.finditer(bloque):
        nombre = m.group(1).strip()
        cargo  = m.group(2).strip()
        fecha  = m.group(3).strip()
        resto  = m.group(4)
        # Nota
        nota_m = re.search(r'Nota[:\s]+(.*?)(?:Documento|Asignado|$)', resto, re.S)
        nota = re.sub(r'<[^>]+>', '', nota_m.group(1)).strip() if nota_m else ""
        # Enviado a
        env_m = re.search(r'Enviado a\s+(.*?)(?:\n|$)', resto, re.S)
        enviado = re.sub(r'<[^>]+>', '', env_m.group(1)).strip() if env_m else ""
        movimientos.append({
            "nombre":    re.sub(r'<[^>]+>', '', nombre),
            "cargo":     re.sub(r'<[^>]+>', '', cargo),
            "fecha":     fecha,
            "nota":      nota[:300] if nota else "",
            "enviado_a": re.sub(r'<[^>]+>', '', enviado)
        })

    # Último movimiento y horas sin movimiento
    ultimo = movimientos[0] if movimientos else None
    horas = None
    if ultimo:
        try:
            dt = datetime.strptime(ultimo["fecha"], "%Y-%m-%d %H:%M")
            horas = round((datetime.now() - dt).total_seconds() / 3600, 1)
        except: pass

    return {
        "numero":              numero,
        "encontrado":          True,
        "descripcion":         desc[:200],
        "estado_edoc":         estado,
        "horas_sin_movimiento": horas,
        "tiempo_texto":        f"{int(horas)}h" if horas else "",
        "movimientos":         movimientos,
        "ultimo_movimiento":   ultimo,
        "error":               None
    }

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print(f"Sync Trámites PAC — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Leer pac_links.json
    if not os.path.exists(PAC_LINKS):
        print(f"[WARN] {PAC_LINKS} no existe — sin vínculos aún")
        resultado = {}
    else:
        with open(PAC_LINKS, encoding="utf-8") as f:
            links = json.load(f)
        numeros = sorted(set(
            str(v.get("tramite_edoc","")).strip()
            for v in links.values()
            if v.get("tramite_edoc","").strip()
        ))
        print(f"[OK] {len(numeros)} trámites a extraer: {numeros}")

        if not numeros:
            resultado = {}
        else:
            login()
            resultado = {}
            for i, num in enumerate(numeros, 1):
                print(f"[{i}/{len(numeros)}] Extrayendo trámite #{num}...")
                t = extraer_tramite(num)
                resultado[num] = t
                found = "✓" if t["encontrado"] else "✗"
                movs  = len(t.get("movimientos", []))
                print(f"  {found} estado={t['estado_edoc']!r} movimientos={movs}")
                time.sleep(0.5)  # Cortesía al servidor

    output = {
        "timestamp":        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "total_vinculados": len(resultado),
        "total_encontrados": sum(1 for v in resultado.values() if v.get("encontrado")),
        "tramites":         resultado
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] {OUTPUT}: {output['total_encontrados']}/{output['total_vinculados']} encontrados")
    print("=" * 60)
