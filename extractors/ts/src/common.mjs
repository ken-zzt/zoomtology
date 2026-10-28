// 공통: ts-morph 프로젝트 열기, 레코드 생성, 파일·클래스·메서드 노드. 코드 본문은 어디에도 넣지 않는다 (ADR 0003).
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { Node, Project, SyntaxKind } from 'ts-morph'

export const SOURCE = 'ts@1'

export class Out {
  constructor(repo) {
    this.repo = repo
    this.nodes = new Map()
    this.edges = new Map()
    this.report = {}   // key → count or list
  }
  node(rec) {
    if (!this.nodes.has(rec.uid)) this.nodes.set(rec.uid, rec)
    return rec.uid
  }
  edge(rec) {
    const key = `${rec.from}\u0000${rec.type}\u0000${rec.to}`
    const prev = this.edges.get(key)
    if (prev) {
      // 같은 관계가 또 나오면 lines/ops 를 합친다
      for (const k of ['lines', 'ops']) {
        if (Array.isArray(rec.props?.[k])) {
          prev.props[k] = [...new Set([...(prev.props[k] ?? []), ...rec.props[k]])].sort((a, b) => (a > b ? 1 : a < b ? -1 : 0))
        }
      }
      if (prev.props.count !== undefined && rec.props?.count !== undefined) prev.props.count += rec.props.count
      return
    }
    this.edges.set(key, rec)
  }
  count(key, n = 1) {
    this.report[key] = (this.report[key] ?? 0) + n
  }
  list(key, item, max = 60) {
    const arr = (this.report[key] ??= [])
    if (arr.length < max && !arr.includes(item)) arr.push(item)
  }
  records() {
    return [...[...this.nodes.values()].map((n) => ({ kind: 'node', ...n })), ...[...this.edges.values()].map((e) => ({ kind: 'edge', ...e }))]
  }
}

export function nodeRec(uid, label, name, { summary = null, props = {}, status = 'active', sourceRef = null } = {}) {
  return { uid, label, name, summary, props, source: SOURCE, confidence: 'auto', status, sourceRef }
}

export function edgeRec(from, type, to, { props = {}, status = 'active', sourceRef = null } = {}) {
  return { from, type, to, props, source: SOURCE, confidence: 'auto', status, sourceRef }
}

export function openProject(root) {
  const tsconfig = path.join(root, 'tsconfig.json')
  return new Project({ tsConfigFilePath: tsconfig, skipAddingFilesFromTsConfig: false, skipFileDependencyResolution: true })
}

export function relPath(root, sf) {
  return path.relative(root, sf.getFilePath()).split(path.sep).join('/')
}

export function isSourceFile(rel) {
  return rel.startsWith('src/') && !rel.includes('/node_modules/') && !/\.(spec|test|e2e-spec)\.ts$/.test(rel) && !rel.endsWith('.d.ts') && !/\s/.test(rel)
}

/** 문자열/템플릿 리터럴을 경로 문자열로. `${…}` 는 ':param', 단 식에 pred 가 참이면 '' (서버 URL 접두사 제거용) */
export function templateToPath(node, dropExpr = () => false) {
  if (Node.isStringLiteral(node) || Node.isNoSubstitutionTemplateLiteral(node)) return node.getLiteralText()
  if (Node.isTemplateExpression(node)) {
    let s = node.getHead().getLiteralText()
    for (const span of node.getTemplateSpans()) {
      s += dropExpr(span.getExpression().getText()) ? '' : ':param'
      s += span.getLiteral().getLiteralText()
    }
    return s
  }
  return null
}

export function lineOf(node) {
  return node.getStartLineNumber()
}

export function ref(repo, rel, node) {
  if (!node) return `${repo}/${rel}`
  const a = node.getStartLineNumber()
  const b = node.getEndLineNumber()
  return a === b ? `${repo}/${rel}:${a}` : `${repo}/${rel}:${a}-${b}`
}

export const uid = {
  file: (repo, rel) => `file:${repo}/${rel}`,
  code: (repo, rel, sym, method) => `code:${repo}/${rel}#${sym}${method ? `::${method}` : ''}`,
  module: (repo, p, sym) => `module:${repo}/${p}${sym ? `#${sym}` : ''}`,
  route: (repo, method, p) => `route:${repo} ${method} ${p}`,
  table: (name, db) => (db ? `table:${db}/${name}` : `table:${name}`),
  msg: (role, key) => `msg:${role}/${key}`,
  queue: (role) => `queue:${role}`,
  svc: (repo, inst) => `svc:${repo}/${inst}`,
  ext: (slug) => `ext:${slug}`,
}

/** 파일·모듈(ts-dir)·클래스·메서드·함수 노드와 CONTAINS. 반환: { classes: Map<ClassDeclaration, uid>, units: Map<node, uid> } */
export function emitStructure(out, root, sf, rel, { classKind = () => 'class' } = {}) {
  const repo = out.repo
  const text = sf.getFullText()
  const fuid = out.node(nodeRec(uid.file(repo, rel), 'File', path.basename(rel), {
    props: { repo, path: rel, lang: rel.endsWith('.tsx') ? 'tsx' : 'ts', loc: text.split('\n').length, sha1: createHash('sha1').update(text).digest('hex') },
    sourceRef: `${repo}/${rel}`,
  }))
  const parts = rel.split('/')
  const dir = parts.length > 2 ? `${parts[0]}/${parts[1]}` : parts[0]
  const muid = out.node(nodeRec(uid.module(repo, dir), 'Module', dir, { props: { kind: 'ts-dir', repo, path: dir }, sourceRef: `${repo}/${dir}` }))
  out.edge(edgeRec(`repo:${repo}`, 'CONTAINS', muid, { sourceRef: `${repo}/${dir}` }))
  out.edge(edgeRec(muid, 'CONTAINS', fuid, { sourceRef: `${repo}/${rel}` }))

  const units = new Map()
  for (const cls of sf.getClasses()) {
    const name = cls.getName()
    if (!name) continue
    const cuid = uid.code(repo, rel, name)
    const props = { kind: classKind(cls), lineStart: cls.getStartLineNumber(), lineEnd: cls.getEndLineNumber(), methodCount: cls.getMethods().length }
    const parent = cls.getExtends()?.getExpression().getText()
    if (parent) props.parent = parent
    const decos = cls.getDecorators().map((d) => d.getName())
    if (decos.length) props.decorators = decos
    out.node(nodeRec(cuid, 'CodeUnit', name, { props, sourceRef: ref(repo, rel, cls) }))
    out.edge(edgeRec(fuid, 'CONTAINS', cuid, { sourceRef: `${repo}/${rel}:${cls.getStartLineNumber()}` }))
    units.set(cls, cuid)
    for (const m of cls.getMethods()) {
      const mname = m.getName()
      const mu = uid.code(repo, rel, name, mname)
      const mp = { kind: 'method', lineStart: m.getStartLineNumber(), lineEnd: m.getEndLineNumber(), class: name, visibility: m.getScope() ?? 'public' }
      if (m.isStatic()) mp.isStatic = true
      const md = m.getDecorators().map((d) => d.getName())
      if (md.length) mp.decorators = md
      out.node(nodeRec(mu, 'CodeUnit', `${name}::${mname}`, { props: mp, sourceRef: ref(repo, rel, m) }))
      out.edge(edgeRec(fuid, 'CONTAINS', mu, { sourceRef: `${repo}/${rel}:${m.getStartLineNumber()}` }))
      units.set(m, mu)
    }
  }
  for (const fn of sf.getFunctions()) {
    const name = fn.getName()
    if (!name) continue
    const fu = uid.code(repo, rel, name)
    out.node(nodeRec(fu, 'CodeUnit', name, { props: { kind: 'function', lineStart: fn.getStartLineNumber(), lineEnd: fn.getEndLineNumber() }, sourceRef: ref(repo, rel, fn) }))
    out.edge(edgeRec(fuid, 'CONTAINS', fu, { sourceRef: `${repo}/${rel}:${fn.getStartLineNumber()}` }))
    units.set(fn, fu)
  }
  // export const x = async function / () => … 도 함수 유닛으로
  for (const vs of sf.getVariableStatements()) {
    for (const d of vs.getDeclarations()) {
      const init = d.getInitializer()
      if (!init) continue
      if (Node.isArrowFunction(init) || Node.isFunctionExpression(init)) {
        const name = d.getName()
        const fu = uid.code(repo, rel, name)
        out.node(nodeRec(fu, 'CodeUnit', name, { props: { kind: 'function', lineStart: d.getStartLineNumber(), lineEnd: d.getEndLineNumber() }, sourceRef: ref(repo, rel, d) }))
        out.edge(edgeRec(fuid, 'CONTAINS', fu, { sourceRef: `${repo}/${rel}:${d.getStartLineNumber()}` }))
        units.set(init, fu)
      }
    }
  }
  return { fuid, units }
}

/** node 를 감싸는 가장 가까운 유닛(메서드/함수/클래스)의 uid */
export function enclosingUnit(node, units) {
  let cur = node
  while (cur) {
    if (units.has(cur)) return units.get(cur)
    cur = cur.getParent()
  }
  return null
}

/** 데코레이터 첫 인자: 문자열이면 그 값, 객체면 {key: literal} */
export function decoratorArg(deco) {
  const args = deco.getArguments()
  if (!args.length) return null
  const a = args[0]
  if (Node.isStringLiteral(a) || Node.isNoSubstitutionTemplateLiteral(a)) return a.getLiteralText()
  if (Node.isObjectLiteralExpression(a)) {
    const o = {}
    for (const p of a.getProperties()) {
      if (Node.isPropertyAssignment(p)) {
        const init = p.getInitializer()
        if (init && (Node.isStringLiteral(init) || Node.isNoSubstitutionTemplateLiteral(init))) o[p.getName()] = init.getLiteralText()
        else if (init && (Node.isTrueLiteral(init) || Node.isFalseLiteral(init) || Node.isNumericLiteral(init))) o[p.getName()] = init.getText()
      }
    }
    return o
  }
  return null
}

/** 식의 타입이 가리키는 클래스 선언(들)의 이름 — `OrderEntity[]`, `Promise<X>` 도 벗긴다 */
export function classNamesOfType(type, depth = 0) {
  if (!type || depth > 3) return []
  if (type.isArray()) return classNamesOfType(type.getArrayElementType(), depth + 1)
  if (type.isUnion()) return type.getUnionTypes().flatMap((t) => classNamesOfType(t, depth + 1))
  const sym = type.getSymbol() ?? type.getAliasSymbol()
  const name = sym?.getName()
  if (name === 'Promise' || name === 'Array') {
    return type.getTypeArguments().flatMap((t) => classNamesOfType(t, depth + 1))
  }
  if (name && name !== '__type' && name !== '__object') return [name]
  return []
}

/** `a.b.c(...)` 호출의 속성 이름 체인 ['a','b','c'] (this 포함). 이름을 못 읽으면 null 원소 */
export function chainOf(expr) {
  const names = []
  let cur = expr
  while (cur) {
    if (Node.isCallExpression(cur)) cur = cur.getExpression()
    else if (Node.isPropertyAccessExpression(cur)) {
      names.unshift(cur.getName())
      cur = cur.getExpression()
    } else if (Node.isThisExpression(cur)) {
      names.unshift('this')
      break
    } else if (Node.isIdentifier(cur)) {
      names.unshift(cur.getText())
      break
    } else if (Node.isAwaitExpression(cur) || Node.isParenthesizedExpression(cur) || Node.isNonNullExpression(cur) || Node.isAsExpression(cur)) {
      cur = cur.getExpression()
    } else {
      names.unshift(null)
      break
    }
  }
  return names
}

/** 식별자(import 별칭 포함)가 가리키는 클래스 선언의 이름. 클래스가 아니면 텍스트 그대로 */
export function className(node) {
  if (!node) return null
  try {
    const sym = node.getSymbol?.()
    const aliased = sym && sym.isAlias?.() ? sym.getAliasedSymbol() : sym
    const decl = aliased?.getDeclarations?.()?.[0]
    if (decl && Node.isClassDeclaration(decl) && decl.getName()) return decl.getName()
  } catch {
    /* 타입 해석 실패 — 텍스트로 */
  }
  return node.getText().trim()
}

export function enumValue(enumDecl, member) {
  const m = enumDecl?.getMember(member)
  const v = m?.getValue()
  return typeof v === 'string' ? v : null
}

export { Node, SyntaxKind, readFileSync }
