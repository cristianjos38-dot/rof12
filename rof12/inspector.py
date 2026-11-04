"""Inspeccion de documentos PDF (solo libreria estandar).

Capas:
  1. Estructura       -> JavaScript, OpenAction, Launch, archivos embebidos, URIs
  2. Ocultamiento     -> texto blanco, fuente diminuta, render invisible, fuera de pagina, metadatos
  3. Contenido        -> patrones de inyeccion (override, autoridad falsa, accion, exfiltracion...)
  4. Riesgo           -> score 0-100 -> LOW / MEDIUM / HIGH / CRITICAL -> veredicto

Limitaciones honestas: no interpreta fuentes CID/Type0, XObjects de formulario, object streams
ni transformaciones `cm`. Cuando detecta algo de eso lo reporta como `coverage_gaps`.
"""
import hashlib, math, re, zlib
from dataclasses import dataclass, field

DEFAULT_W, DEFAULT_H = 612.0, 792.0


# ----------------------------------------------------------------------------- datos
@dataclass
class Span:
    page: int
    text: str
    x: float
    y: float
    size: float
    color: tuple
    render_mode: int
    flags: list = field(default_factory=list)

    @property
    def hidden(self) -> bool:
        return bool(self.flags)


@dataclass
class Report:
    path: str
    sha256: str
    pages: int
    structure: list
    spans: list
    metadata: dict
    metadata_hits: list
    findings: list          # [{category, weight, scope, evidence}]
    coverage_gaps: list
    score: int
    level: str
    verdict: str            # ALLOW | REQUIRE_APPROVAL | DENY

    @property
    def hidden_spans(self):
        return [s for s in self.spans if s.hidden]

    @property
    def visible_text(self) -> str:
        return "\n".join(s.text for s in self.spans if not s.hidden)

    @property
    def naive_text(self) -> str:
        """Lo que ve un extractor de texto convencional: todo, sin mirar el estilo."""
        return "\n".join(s.text for s in self.spans)


# ----------------------------------------------------------------------------- parser PDF
OBJ_RE = re.compile(rb"(\d+)\s+(\d+)\s+obj(.*?)endobj", re.S)
STREAM_RE = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.S)
STRUCT_KEYS = {
    b"/JavaScript": ("JavaScript embebido", 30), b"/JS": ("JavaScript embebido", 30),
    b"/OpenAction": ("Accion automatica al abrir (OpenAction)", 30),
    b"/Launch": ("Accion Launch (ejecuta programas)", 30),
    b"/EmbeddedFile": ("Archivo embebido", 15), b"/SubmitForm": ("Envio de formulario", 15),
    b"/RichMedia": ("Contenido RichMedia", 15), b"/URI": ("Accion URI (enlace externo)", 5),
}


def _decode_stream(dict_part: bytes, raw: bytes):
    if b"/FlateDecode" in dict_part:
        try:
            return zlib.decompress(raw)
        except zlib.error:
            return None
    if b"/Filter" in dict_part:
        return None  # filtro no soportado
    return raw


def _parse_pdf_string(s: bytes) -> str:
    out, i = bytearray(), 0
    while i < len(s):
        c = s[i]
        if c == 0x5C and i + 1 < len(s):
            i += 1
            m = {ord("n"): 10, ord("r"): 13, ord("t"): 9}.get(s[i])
            out.append(m if m is not None else s[i])
        else:
            out.append(c)
        i += 1
    b = bytes(out)
    if b.startswith(b"\xfe\xff"):
        return b[2:].decode("utf-16-be", "replace")
    return b.decode("latin-1")


def _tokenize(data: bytes):
    """Tokeniza un content stream. Emite (tipo, valor): num, str, name, op, [ , ]"""
    i, n = 0, len(data)
    delim = b"()<>[]{}/%"
    ws = b" \t\r\n\f\x00"
    while i < n:
        ch = data[i:i + 1]
        if ch in ws:
            i += 1
        elif ch == b"%":
            while i < n and data[i] not in (10, 13):
                i += 1
        elif ch == b"(":
            depth, i, buf = 1, i + 1, bytearray()
            while i < n and depth:
                c = data[i]
                if c == 0x5C and i + 1 < n:
                    nxt = data[i + 1]
                    if 48 <= nxt <= 55:  # octal
                        j = i + 1
                        while j < n and j < i + 4 and 48 <= data[j] <= 55:
                            j += 1
                        buf.append(int(data[i + 1:j], 8) & 0xFF)
                        i = j
                        continue
                    buf.append({ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12}.get(nxt, nxt))
                    i += 2
                    continue
                if c == 0x28:
                    depth += 1
                elif c == 0x29:
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                buf.append(c)
                i += 1
            yield ("str", bytes(buf))
        elif ch == b"<" and data[i + 1:i + 2] == b"<":
            yield ("op", "<<"); i += 2
        elif ch == b">" and data[i + 1:i + 2] == b">":
            yield ("op", ">>"); i += 2
        elif ch == b"<":
            j = data.find(b">", i)
            j = n if j < 0 else j
            hx = re.sub(rb"\s", b"", data[i + 1:j])
            if len(hx) % 2:
                hx += b"0"
            try:
                yield ("str", bytes.fromhex(hx.decode()))
            except ValueError:
                pass
            i = j + 1
        elif ch in (b"[", b"]"):
            yield (ch.decode(), None); i += 1
        elif ch in (b"{", b"}", b")", b">"):
            i += 1
        elif ch == b"/":
            j = i + 1
            while j < n and data[j:j + 1] not in ws and data[j:j + 1] not in delim:
                j += 1
            yield ("name", data[i + 1:j].decode("latin-1")); i = j
        else:
            j = i
            while j < n and data[j:j + 1] not in ws and data[j:j + 1] not in delim:
                j += 1
            tok = data[i:j].decode("latin-1")
            i = max(j, i + 1)
            try:
                yield ("num", float(tok))
            except ValueError:
                yield ("op", tok)
                if tok == "ID":  # imagen inline: saltar hasta EI
                    m = re.search(rb"\sEI(\s|$)", data[i:])
                    i = i + m.end() if m else n


def _cmyk_to_rgb(c, m, y, k):
    return ((1 - min(1, c + k)), (1 - min(1, m + k)), (1 - min(1, y + k)))


def _is_white(c, thr=0.95):
    return c is not None and all(v >= thr for v in c)


def _extract_spans(content: bytes, page_no: int, w: float, h: float, gaps: set):
    spans, stack = [], []
    fill, size, tr = (0.0, 0.0, 0.0), 12.0, 0
    tm, line, leading = [1, 0, 0, 1, 0, 0], [0.0, 0.0], 0.0
    rects, pending_rect = [], None
    operands, arr = [], None

    def eff_size():
        scale = math.hypot(tm[2], tm[3]) or 1.0
        return abs(size * scale)

    def on_colored_bg(x, y):
        for rx, ry, rw, rh, col in rects:
            if min(rx, rx + rw) <= x <= max(rx, rx + rw) and min(ry, ry + rh) <= y <= max(ry, ry + rh):
                return True
        return False

    def emit(raw: bytes):
        text = raw.decode("latin-1")
        if not re.search(r"[A-Za-z0-9]", text):
            return
        s = Span(page_no, text, tm[4], tm[5], eff_size(), fill, tr)
        if tr == 3:
            s.flags.append("invisible_render_mode")
        if _is_white(fill) and not on_colored_bg(s.x, s.y):
            s.flags.append("white_text")
        if s.size < 3.0:
            s.flags.append("micro_font")
        if s.x < -5 or s.x > w + 5 or s.y < -5 or s.y > h + 5:
            s.flags.append("off_page")
        spans.append(s)

    def nums():
        return [v for t, v in operands if t == "num"]

    for kind, val in _tokenize(content):
        if kind == "[":
            arr = []; continue
        if kind == "]":
            operands.append(("arr", arr or [])); arr = None; continue
        if kind in ("num", "str", "name"):
            (arr if arr is not None else operands).append((kind, val)); continue
        op, ns = val, nums()
        if op == "q":
            stack.append((fill, size, tr))
        elif op == "Q" and stack:
            fill, size, tr = stack.pop()
        elif op == "rg" and len(ns) >= 3:
            fill = tuple(ns[-3:])
        elif op == "g" and ns:
            fill = (ns[-1],) * 3
        elif op == "k" and len(ns) >= 4:
            fill = _cmyk_to_rgb(*ns[-4:])
        elif op in ("sc", "scn"):
            if len(ns) >= 4:
                fill = _cmyk_to_rgb(*ns[-4:])
            elif len(ns) == 3:
                fill = tuple(ns)
            elif len(ns) == 1:
                fill = (ns[0],) * 3
        elif op == "Tf" and ns:
            size = ns[-1]
        elif op == "Tr" and ns:
            tr = int(ns[-1])
        elif op == "BT":
            tm, line = [1, 0, 0, 1, 0, 0], [0.0, 0.0]
        elif op == "Tm" and len(ns) >= 6:
            tm = list(ns[-6:]); line = [tm[4], tm[5]]
        elif op in ("Td", "TD") and len(ns) >= 2:
            line = [line[0] + ns[-2], line[1] + ns[-1]]
            tm[4], tm[5] = line
            if op == "TD":
                leading = -ns[-1]
        elif op == "TL" and ns:
            leading = ns[-1]
        elif op == "T*":
            line[1] -= leading; tm[4], tm[5] = line
        elif op == "Tj" and operands and operands[-1][0] == "str":
            emit(operands[-1][1])
        elif op == "'" and operands and operands[-1][0] == "str":
            line[1] -= leading; tm[4], tm[5] = line; emit(operands[-1][1])
        elif op == '"' and operands and operands[-1][0] == "str":
            line[1] -= leading; tm[4], tm[5] = line; emit(operands[-1][1])
        elif op == "TJ" and operands and operands[-1][0] == "arr":
            parts = []
            for t, v in operands[-1][1]:
                if t == "str":
                    parts.append(v.decode("latin-1"))
                elif t == "num" and v < -200:
                    parts.append(" ")
            emit("".join(parts).encode("latin-1"))
        elif op == "re" and len(ns) >= 4:
            pending_rect = tuple(ns[-4:])
        elif op in ("f", "F", "f*", "B", "B*", "b", "b*"):
            if pending_rect and not _is_white(fill):
                rects.append((*pending_rect, fill))
            pending_rect = None
        elif op == "n":
            pending_rect = None
        elif op == "cm":
            gaps.add("transformaciones 'cm' no aplicadas a coordenadas")
        elif op == "Do":
            gaps.add("XObjects (Do) no inspeccionados")
        operands = []
    return spans


def parse_pdf(path: str):
    with open(path, "rb") as fh:
        raw = fh.read()
    gaps = set()
    objs = {int(m.group(1)): m.group(3) for m in OBJ_RE.finditer(raw)}
    pages, content_to_page = [], {}
    for oid, body in objs.items():
        d = body.split(b"stream")[0]
        if re.search(rb"/Type\s*/Page(?![a-z])", d):
            mb = re.search(rb"/MediaBox\s*\[([^\]]+)\]", d)
            w, h = DEFAULT_W, DEFAULT_H
            if mb:
                v = [float(x) for x in mb.group(1).split()]
                if len(v) == 4:
                    w, h = v[2] - v[0], v[3] - v[1]
            refs = []
            mc = re.search(rb"/Contents\s*(\[[^\]]*\]|\d+\s+\d+\s+R)", d)
            if mc:
                refs = [int(x) for x in re.findall(rb"(\d+)\s+\d+\s+R", mc.group(1))]
            pages.append({"w": w, "h": h, "refs": refs})
            for r in refs:
                content_to_page[r] = len(pages)
    if b"/ObjStm" in raw:
        gaps.add("object streams presentes (escaneo profundo limitado)")
    if b"/Encrypt" in raw:
        gaps.add("PDF cifrado: contenido no inspeccionable")

    spans = []
    for oid, body in objs.items():
        sm = STREAM_RE.search(body)
        if not sm:
            continue
        data = _decode_stream(body.split(b"stream")[0], sm.group(1))
        if data is None:
            gaps.add("stream con filtro no soportado")
            continue
        if b"BT" in data and b"ET" in data:
            pno = content_to_page.get(oid, 1)
            pg = pages[pno - 1] if pages and pno <= len(pages) else {"w": DEFAULT_W, "h": DEFAULT_H}
            spans += _extract_spans(data, pno, pg["w"], pg["h"], gaps)
        if re.search(rb"/Type\s*/Font", body) and re.search(rb"/Type0|/CIDFont|Identity-H", body):
            gaps.add("fuentes CID: el texto puede no ser legible")
    for oid, body in objs.items():
        if re.search(rb"/Subtype\s*/(Type0|CIDFontType)", body) or b"Identity-H" in body:
            gaps.add("fuentes CID: el texto puede no ser legible")

    structure = []
    for key, (label, weight) in STRUCT_KEYS.items():
        if key in raw:
            if not any(s["label"] == label for s in structure):
                structure.append({"key": key.decode(), "label": label, "weight": weight})

    meta = {}
    for body in objs.values():
        if re.search(rb"/(Title|Author|Subject|Keywords|Creator|Producer)\s*\(", body):
            for k in ("Title", "Author", "Subject", "Keywords", "Creator", "Producer"):
                m = re.search(rb"/" + k.encode() + rb"\s*\(((?:\\.|[^\\)])*)\)", body)
                if m:
                    meta[k] = _parse_pdf_string(m.group(1))
    return raw, max(len(pages), 1), spans, meta, structure, sorted(gaps)


# ----------------------------------------------------------------------------- analisis de contenido
PATTERNS = [
    ("instruction_override", 35,
     r"ignore (all |any )?(the )?(previous|prior|above|earlier) (instructions|rules|directions)"
     r"|disregard (all |any )?(previous|prior|above)|new (system )?instructions?\b|you are now\b"
     r"|override (the )?(policy|rules|limits?)|ignore (the )?(refund )?polic(y|ies)"
     r"|ignora (todas )?las instrucciones anteriores|olvida (todas )?las (reglas|instrucciones)"),
    ("authority_spoofing", 20,
     r"(^|\n)\s*(system|admin|root|developer)\s*:|\[(system|admin|assistant)\]|pre-?authori[sz]ed"
     r"|already approved|approved by (the )?(ceo|cfo|admin|manager|security)|administrator mode"
     r"|(skip|bypass) (the )?(approval|verification|checks?|review)"
     r"|without (human |further )?(approval|review|confirmation)|sin (pedir )?aprobaci[oó]n"),
    ("action_directive", 25,
     r"\b(issue|process|send|make|create|initiate|execute|approve)\b.{0,40}\b(refunds?|payments?|transfers?|wire|payouts?|reembolso)\b"
     r"|\b(refund|transfer|wire)\b.{0,40}\$\s?\d[\d,\.]*"
     r"|\b(export|dump|download|exfiltrate)\b.{0,50}\b(customers?|database|records|credentials|clientes)\b"
     r"|\brun\b.{0,20}\b(command|script|shell)\b|\bdelete\b.{0,30}\b(logs?|records?|audit)\b"),
    ("exfiltration", 25,
     r"[\w.+-]+@[\w-]+\.[\w.-]+|https?://\S+|\b(api[_ -]?key|password|secret|credentials?)\b"),
    ("concealment", 20,
     r"do not (tell|mention|inform|reveal|notify|show)|don'?t (tell|mention|inform|reveal)"
     r"|without (telling|informing|notifying|alerting)|keep (this|it) (secret|hidden|confidential)"
     r"|\b(silently|quietly)\b|no (le )?(digas|menciones|avises)"),
    ("agent_addressing", 15,
     r"\b(dear|attention|note to|hey) (ai|assistant|agent|llm|model)\b"
     r"|\b(ai|assistant|agent|llm)s?\b.{0,30}\b(must|should|need to|has to)\b"
     r"|\byou must\b"),
]
_COMPILED = [(c, w, re.compile(p, re.I)) for c, w, p in PATTERNS]


def analyze_text(text: str, scope: str):
    """scope: 'hidden' (peso completo) | 'visible' (medio peso, sin exfil aislada)."""
    hits = []
    for cat, weight, rx in _COMPILED:
        m = rx.search(text)
        if m:
            ev = text[max(0, m.start() - 15): m.end() + 25].replace("\n", " ").strip()
            hits.append({"category": cat, "weight": weight, "scope": scope, "evidence": ev})
    if scope == "visible" and len([h for h in hits if h["category"] != "exfiltration"]) < 2:
        hits = [h for h in hits if h["category"] != "exfiltration"]
    if scope == "visible":
        for h in hits:
            h["weight"] = h["weight"] / 2
    return hits


def classify(score: float, thresholds: dict):
    if score <= thresholds["low_max"]:
        return "LOW", "ALLOW"
    if score <= thresholds["medium_max"]:
        return "MEDIUM", "REQUIRE_APPROVAL"
    if score <= thresholds["high_max"]:
        return "HIGH", "DENY"
    return "CRITICAL", "DENY"


def inspect_pdf(path: str, thresholds: dict) -> Report:
    raw, npages, spans, meta, structure, gaps = parse_pdf(path)
    hidden_text = "\n".join(s.text for s in spans if s.hidden)
    visible_text = "\n".join(s.text for s in spans if not s.hidden)
    meta_text = "\n".join(meta.values())

    findings = []
    findings += analyze_text(hidden_text, "hidden")
    findings += analyze_text(meta_text, "metadata")
    findings += analyze_text(visible_text, "visible")
    metadata_hits = [f for f in findings if f["scope"] == "metadata"]

    # un mismo categoria no suma dos veces: se queda con el mayor peso
    best = {}
    for f in findings:
        if f["category"] not in best or f["weight"] > best[f["category"]]["weight"]:
            best[f["category"]] = f
    score = sum(f["weight"] for f in best.values())

    hidden_spans = [s for s in spans if s.hidden]
    techniques = {fl for s in hidden_spans for fl in s.flags}
    if hidden_spans:
        score += 25 + min(20, 10 * (len(techniques) - 1))
    score += min(60, sum(s["weight"] for s in structure))
    score = int(min(100, round(score)))

    level, verdict = classify(score, thresholds)
    return Report(path, hashlib.sha256(raw).hexdigest(), npages, structure, spans, meta,
                  metadata_hits, sorted(findings, key=lambda f: -f["weight"]), gaps,
                  score, level, verdict)
