"""레거시 PHP(OpenCart 계열)용 경량 토크나이저와 구조 파서. 2단계(ZDV-346).

문자열·주석·heredoc 을 인식해 토큰을 만들고, 중괄호 깊이로 클래스/메서드/함수 범위(줄 번호)를 잡는다.
코드 본문은 어디에도 저장하지 않는다 — 호출자는 토큰에서 이름·줄 번호·테이블 토큰만 뽑아 쓴다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

TOKEN_RE = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<comment>//[^\n]*|\#(?!\[)[^\n]*|/\*.*?\*/)
  | (?P<heredoc><<<[ \t]*(?P<hq>['"]?)(?P<hid>[A-Za-z_]\w*)(?P=hq)\r?\n.*?\r?\n[ \t]*(?P=hid)\b)
  | (?P<dq>"(?:[^"\\]|\\.)*")
  | (?P<sq>'(?:[^'\\]|\\.)*')
  | (?P<var>\$[A-Za-z_\x80-\U0010ffff][\w\x80-\U0010ffff]*)
  | (?P<num>\d[\w.]*)
  | (?P<ident>[A-Za-z_\x80-\U0010ffff][\w\x80-\U0010ffff]*)
  | (?P<punct>\?->|->|::|\.=|=>|===|!==|==|!=|<=>|<=|>=|&&|\|\||\+\+|--|\.\.\.|<<|>>|\*\*|[-+*/%=<>!&|^~.,;:?()\[\]{}@\\])
  | (?P<other>.)
    """,
    re.S | re.X,
)

STRING_KINDS = ("dq", "sq", "heredoc")


@dataclass(frozen=True)
class Tok:
    kind: str   # str | var | ident | num | punct | other
    text: str   # str 이면 따옴표를 벗긴 값
    line: int


def _unescape_dq(body: str) -> str:
    return re.sub(r'\\([\\"$nrt])', lambda m: {"n": "\n", "r": "\r", "t": "\t"}.get(m.group(1), m.group(1)), body)


def _unescape_sq(body: str) -> str:
    return body.replace("\\'", "'").replace("\\\\", "\\")


def tokenize(src: str) -> list[Tok]:
    toks: list[Tok] = []
    line = 1
    # `<?php` / `?>` 는 토큰이 아니다. 뷰 파일은 스캔하지 않으니 HTML 조각은 고려하지 않는다.
    for m in TOKEN_RE.finditer(src):
        kind = m.lastgroup
        text = m.group(0)
        start_line = line
        line += text.count("\n")
        if kind in ("ws", "comment"):
            continue
        if kind == "dq":
            toks.append(Tok("str", _unescape_dq(text[1:-1]), start_line))
        elif kind == "sq":
            toks.append(Tok("str", _unescape_sq(text[1:-1]), start_line))
        elif kind == "heredoc":
            body = text.split("\n", 1)[1] if "\n" in text else ""
            body = body.rsplit("\n", 1)[0] if "\n" in body else ""
            toks.append(Tok("str", body, start_line))
        elif kind == "hq" or kind == "hid":
            continue
        else:
            if kind == "ident" and text in ("<?php",):
                continue
            toks.append(Tok(kind or "other", text, start_line))
    return toks


MODIFIERS = {"public", "private", "protected", "static", "abstract", "final", "var", "readonly"}


@dataclass
class Method:
    name: str
    line_start: int
    line_end: int
    visibility: str
    is_static: bool
    body: list[Tok]            # `{` 와 `}` 사이. abstract 면 빈 리스트
    abstract: bool = False


@dataclass
class StaticArray:
    name: str
    line: int
    items: list[tuple[str, str]]   # 평탄한 스칼라 키·값만. 중첩이면 비어 있음
    flat: bool


@dataclass
class ClassDef:
    name: str
    kind: str                   # class | trait | interface
    line_start: int
    line_end: int
    parent: str | None
    methods: list[Method] = field(default_factory=list)
    static_arrays: list[StaticArray] = field(default_factory=list)


@dataclass
class FunctionDef:
    name: str
    line_start: int
    line_end: int
    body: list[Tok]


@dataclass
class FileStructure:
    classes: list[ClassDef]
    functions: list[FunctionDef]
    namespace: str | None


def _match_close(toks: list[Tok], i: int, open_: str, close: str) -> int:
    """toks[i] 가 open_ 일 때 짝이 맞는 close 의 인덱스. 없으면 len(toks)-1."""
    depth = 0
    for j in range(i, len(toks)):
        t = toks[j].text if toks[j].kind == "punct" else None
        if t == open_:
            depth += 1
        elif t == close:
            depth -= 1
            if depth == 0:
                return j
    return len(toks) - 1


def _is_punct(t: Tok, text: str) -> bool:
    return t.kind == "punct" and t.text == text


def _parse_function(toks: list[Tok], i: int) -> tuple[Method | None, int]:
    """toks[i] 는 `function`. 이름 없는 클로저면 (None, i+1)."""
    j = i + 1
    if j < len(toks) and _is_punct(toks[j], "&"):
        j += 1
    if j >= len(toks) or toks[j].kind != "ident":
        return None, i + 1
    name = toks[j].text
    j += 1
    if j >= len(toks) or not _is_punct(toks[j], "("):
        return None, i + 1
    j = _match_close(toks, j, "(", ")")
    # 반환 타입 등을 건너뛰고 `{` 또는 `;`
    k = j + 1
    while k < len(toks) and not (_is_punct(toks[k], "{") or _is_punct(toks[k], ";")):
        k += 1
    if k >= len(toks):
        return None, i + 1
    mods = set()
    p = i - 1
    while p >= 0 and toks[p].kind == "ident" and toks[p].text in MODIFIERS:
        mods.add(toks[p].text)
        p -= 1
    visibility = "private" if "private" in mods else "protected" if "protected" in mods else "public"
    if _is_punct(toks[k], ";"):
        return Method(name, toks[i].line, toks[k].line, visibility, "static" in mods, [], abstract=True), k + 1
    end = _match_close(toks, k, "{", "}")
    return Method(name, toks[i].line, toks[end].line, visibility, "static" in mods, toks[k + 1:end]), end + 1


def _parse_static_array(toks: list[Tok], i: int) -> tuple[StaticArray | None, int]:
    """toks[i] 는 `static` (클래스 멤버 위치). `static $x = [...]` / `= array(...)` 면 파싱."""
    j = i + 1
    while j < len(toks) and toks[j].kind == "ident" and toks[j].text in MODIFIERS:
        j += 1
    if j >= len(toks) or toks[j].kind != "var":
        return None, i + 1
    name = toks[j].text[1:]
    if j + 1 >= len(toks) or not _is_punct(toks[j + 1], "="):
        return None, i + 1
    k = j + 2
    if k < len(toks) and toks[k].kind == "ident" and toks[k].text == "array" and k + 1 < len(toks) and _is_punct(toks[k + 1], "("):
        open_, close = "(", ")"
        k += 1
    elif k < len(toks) and _is_punct(toks[k], "["):
        open_, close = "[", "]"
    else:
        return None, i + 1
    end = _match_close(toks, k, open_, close)
    inner = toks[k + 1:end]
    items: list[tuple[str, str]] = []
    flat = True
    # 평탄한 `scalar => scalar ,` 반복만 enum 후보
    p = 0
    while p < len(inner):
        t = inner[p]
        if _is_punct(t, ","):
            p += 1
            continue
        if t.kind in ("str", "num") and p + 2 < len(inner) and _is_punct(inner[p + 1], "=>") and inner[p + 2].kind in ("str", "num"):
            if p + 3 < len(inner) and not _is_punct(inner[p + 3], ","):
                flat = False
                break
            items.append((t.text, inner[p + 2].text))
            p += 3
            continue
        flat = False
        break
    return StaticArray(name, toks[i].line, items if flat else [], flat), end + 1


def parse(toks: list[Tok]) -> FileStructure:
    classes: list[ClassDef] = []
    functions: list[FunctionDef] = []
    namespace: str | None = None
    i = 0
    n = len(toks)
    while i < n:
        t = toks[i]
        if t.kind == "ident" and t.text == "namespace" and i + 1 < n and toks[i + 1].kind == "ident":
            parts = []
            j = i + 1
            while j < n and (toks[j].kind == "ident" or _is_punct(toks[j], "\\")):
                parts.append(toks[j].text)
                j += 1
            namespace = "".join(parts)
            i = j
            continue
        if t.kind == "ident" and t.text in ("class", "trait", "interface") and i + 1 < n and toks[i + 1].kind == "ident" \
                and not (i > 0 and (_is_punct(toks[i - 1], "::") or toks[i - 1].text == "new")):
            name = toks[i + 1].text
            parent = None
            j = i + 2
            while j < n and not _is_punct(toks[j], "{"):
                if toks[j].kind == "ident" and toks[j].text == "extends" and j + 1 < n and toks[j + 1].kind == "ident":
                    parent = toks[j + 1].text
                j += 1
            if j >= n:
                break
            end = _match_close(toks, j, "{", "}")
            cls = ClassDef(name, t.text, t.line, toks[end].line, parent)
            k = j + 1
            while k < end:
                tk = toks[k]
                if tk.kind == "ident" and tk.text == "function":
                    m, k2 = _parse_function(toks, k)
                    if m:
                        cls.methods.append(m)
                        k = k2
                        continue
                    # 클로저: 몸통 끝까지 건너뛴다
                    k = _skip_closure(toks, k)
                    continue
                if tk.kind == "ident" and tk.text == "static":
                    sa, k2 = _parse_static_array(toks, k)
                    if sa:
                        cls.static_arrays.append(sa)
                        k = k2
                        continue
                if _is_punct(tk, "{"):
                    k = _match_close(toks, k, "{", "}") + 1
                    continue
                k += 1
            classes.append(cls)
            i = end + 1
            continue
        if t.kind == "ident" and t.text == "function":
            m, i2 = _parse_function(toks, i)
            if m:
                functions.append(FunctionDef(m.name, m.line_start, m.line_end, m.body))
                i = i2
                continue
            i = _skip_closure(toks, i)
            continue
        i += 1
    return FileStructure(classes, functions, namespace)


def _skip_closure(toks: list[Tok], i: int) -> int:
    """`function (` 클로저의 몸통을 건너뛴 다음 인덱스. 구조를 찾지 못하면 i+1."""
    j = i + 1
    while j < len(toks) and not _is_punct(toks[j], "("):
        if _is_punct(toks[j], ";") or _is_punct(toks[j], "{"):
            return i + 1
        j += 1
    if j >= len(toks):
        return i + 1
    j = _match_close(toks, j, "(", ")") + 1
    while j < len(toks) and not (_is_punct(toks[j], "{") or _is_punct(toks[j], ";")):
        j += 1
    if j >= len(toks) or _is_punct(toks[j], ";"):
        return i + 1
    return _match_close(toks, j, "{", "}") + 1


def statements(body: list[Tok]) -> list[list[Tok]]:
    """메서드 몸통을 `;` 와 블록 경계(`{` `}`)로 나눈다. 괄호 안의 `;`(for) 는 나누지 않는다."""
    out: list[list[Tok]] = []
    cur: list[Tok] = []
    depth = 0
    for t in body:
        if t.kind == "punct":
            if t.text in ("(", "["):
                depth += 1
            elif t.text in (")", "]"):
                depth = max(0, depth - 1)
            elif depth == 0 and t.text in (";", "{", "}"):
                if cur:
                    out.append(cur)
                cur = []
                continue
        cur.append(t)
    if cur:
        out.append(cur)
    return out
