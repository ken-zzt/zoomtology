// NestJS 저장소(zoomzoom-api · external-api · data-api · message-consumer) 추출.
// 엔티티→MAPS_TO, 리포지토리/QueryBuilder/EntityManager 호출→READS/WRITES, 컨트롤러→Route+HANDLES,
// DI·CQRS·self→CALLS, `key: SQS*ServiceKey.X`→PUBLISHES, 컨슈머 팩토리→CONSUMES, HttpClient 호출→CALLS_HTTP(raw).
import { Node, SyntaxKind, chainOf, className, classNamesOfType, decoratorArg, edgeRec, emitStructure, enclosingUnit, enumValue, isSourceFile, nodeRec, openProject, ref, relPath, templateToPath, uid } from './common.mjs'

const READ_METHODS = new Set(['find', 'findOne', 'findOneBy', 'findBy', 'findAndCount', 'findAndCountBy', 'findOneOrFail', 'findOneByOrFail', 'findByIds', 'count', 'countBy', 'exist', 'exists', 'existsBy', 'sum', 'average', 'minimum', 'maximum', 'findOneById', 'preload', 'getOne', 'getMany', 'getRawOne', 'getRawMany', 'getCount', 'getManyAndCount', 'getRawAndEntities', 'getExists'])
const WRITE_METHODS = { save: 'upsert', insert: 'insert', update: 'update', upsert: 'upsert', delete: 'delete', remove: 'delete', softDelete: 'update', softRemove: 'update', restore: 'update', recover: 'update', increment: 'update', decrement: 'update', clear: 'truncate' }
const QB_WRITE = { insert: 'insert', update: 'update', delete: 'delete', softDelete: 'update', restore: 'update' }
const HTTP_DECOS = { Get: 'GET', Post: 'POST', Put: 'PUT', Patch: 'PATCH', Delete: 'DELETE', All: 'ALL', Head: 'HEAD', Options: 'OPTIONS' }
const SQS_ROLE = { SQSOrderServiceKey: 'order', SQSEmailServiceKey: 'email', SQSNotificationServiceKey: 'notif', SQSEntityServiceKey: 'entity', SQSEventServiceKey: 'event' }
const DB_BY_DIR = [['src/entities/isolation/', 'iso'], ['src/entities/crawler/', 'wc']]
const SQL_TABLE_RE = /\b(?:from|join|into|update)\s+`?([a-z][a-z0-9_]*)`?/gi

function normPath(...parts) {
  const p = parts.filter((x) => x !== undefined && x !== null).join('/').replace(/\/+/g, '/').replace(/\/$/, '')
  return '/' + p.replace(/^\//, '')
}

function snake(s) {
  return s.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase()
}

export function extractNest(repo, root, opts = {}) {
  const project = openProject(root)
  const out = opts.out
  const files = project.getSourceFiles().map((sf) => [sf, relPath(root, sf)]).filter(([, rel]) => isSourceFile(rel))
  out.count('files', files.length)

  // --- 1차: 색인 (엔티티, 클래스 선언, 핸들러, enum) -------------------------------------
  const entity = new Map()      // ClassName → { table, db, tuid, rel, relations: Map<prop, ClassName>, columns: [] }
  const classes = new Map()     // ClassName → { rel, cls }
  const handlers = new Map()    // Command/Query class name → handler class name
  const enums = new Map()       // EnumName → EnumDeclaration
  for (const [sf, rel] of files) {
    for (const e of sf.getEnums()) enums.set(e.getName(), e)
    for (const cls of sf.getClasses()) {
      const name = cls.getName()
      if (!name) continue
      if (!classes.has(name)) classes.set(name, { rel, cls })
      const ent = cls.getDecorator('Entity')
      if (ent) {
        const arg = decoratorArg(ent)
        const table = typeof arg === 'string' ? arg : arg?.name
        if (!table) {
          out.list('entity-without-name', `${repo}/${rel}`)
          continue
        }
        let db = null
        for (const [prefix, handle] of DB_BY_DIR) if (rel.startsWith(prefix)) db = handle
        const relations = new Map()
        const cascades = new Map()   // prop → {target, ops}
        const columns = []
        for (const p of cls.getProperties()) {
          const rd = p.getDecorators().find((d) => ['ManyToOne', 'OneToMany', 'OneToOne', 'ManyToMany'].includes(d.getName()))
          if (rd) {
            const a0 = rd.getArguments()[0]
            const body = a0 && Node.isArrowFunction(a0) ? a0.getBody() : null
            if (body) {
              const target = className(body)
              relations.set(p.getName(), target)
              // cascade: true | ['insert','update',…] → 부모를 save/insert/update 하면 자식 테이블에도 쓴다
              const opts = rd.getArguments().find((a) => Node.isObjectLiteralExpression(a))
              const cas = opts?.getProperty('cascade')
              if (cas && Node.isPropertyAssignment(cas)) {
                const init = cas.getInitializer()
                let ops = null
                if (init && Node.isTrueLiteral(init)) ops = ['insert', 'update', 'remove']
                else if (init && Node.isArrayLiteralExpression(init)) ops = init.getElements().map((e) => e.getText().replace(/['"]/g, ''))
                if (ops && ops.length) cascades.set(p.getName(), { target, ops })
              }
            }
            continue
          }
          const cd = p.getDecorators().find((d) => /Column$/.test(d.getName()) || d.getName() === 'Column')
          if (cd) {
            const a = decoratorArg(cd)
            columns.push(typeof a === 'object' && a?.name ? a.name : snake(p.getName()))
          }
        }
        entity.set(name, { table, db, tuid: uid.table(table, db), rel, relations, cascades, columns, database: typeof arg === 'object' ? arg.database : undefined })
      }
      for (const dn of ['CommandHandler', 'QueryHandler', 'EventsHandler']) {
        const d = cls.getDecorator(dn)
        if (d) {
          const a = d.getArguments()[0]
          if (a) handlers.set(className(a), name)
        }
      }
    }
  }
  out.count('entities', entity.size)

  const classUid = (cname) => {
    const c = classes.get(cname)
    return c ? uid.code(repo, c.rel, cname) : null
  }
  const methodUid = (cname, mname) => {
    const c = classes.get(cname)
    if (!c) return null
    // 부모 클래스까지 올라가며 메서드를 찾는다
    let cur = c
    for (let i = 0; i < 6 && cur; i++) {
      if (cur.cls.getMethod(mname) || cur.cls.getProperty(mname)) return uid.code(repo, cur.rel, cur.cls.getName(), mname)
      const parent = cur.cls.getExtends()?.getExpression().getText()
      cur = parent ? classes.get(parent) : null
    }
    out.count('calls-placeholder')
    return uid.code(repo, c.rel, cname, mname)   // placeholder (빌드가 missing-from-source 노드로 만든다)
  }
  const resolveEntity = (cname) => (cname && entity.has(cname) ? entity.get(cname) : null)

  // --- 2차: 파일별 추출 ----------------------------------------------------------------
  for (const [sf, rel] of files) {
    const classKind = (cls) => (cls.getDecorator('Controller') ? 'controller' : cls.getDecorator('Entity') ? 'entity' : cls.getDecorators().some((d) => /Handler$/.test(d.getName())) ? 'handler' : cls.getDecorator('Injectable') ? 'class' : 'class')
    const { units } = emitStructure(out, root, sf, rel, { classKind })

    for (const cls of sf.getClasses()) {
      const cname = cls.getName()
      if (!cname) continue
      const cuid = uid.code(repo, rel, cname)

      // 엔티티 → MAPS_TO
      const ent = entity.get(cname)
      if (ent && ent.rel === rel) {
        const n = out.nodes.get(cuid)
        if (n) {
          n.props.columns = ent.columns
          n.props.table = ent.table
          if (ent.db) n.props.db = ent.db
        }
        out.edge(edgeRec(cuid, 'MAPS_TO', ent.tuid, { props: { via: 'typeorm-entity' }, sourceRef: ref(repo, rel, cls) }))
      }

      // 생성자 주입: 리포지토리·서비스·버스
      const repoProps = new Map()     // prop → entity class
      const diProps = new Map()       // prop → class name (프로젝트 안 클래스)
      const busProps = new Set()
      const ctor = cls.getConstructors()[0]
      const params = ctor ? ctor.getParameters() : []
      for (const p of params) {
        const pname = p.getName()
        const ir = p.getDecorator('InjectRepository')
        if (ir) {
          const a = ir.getArguments()[0]
          if (a) repoProps.set(pname, className(a))
          continue
        }
        const tnode = p.getTypeNode()
        const tname = tnode?.getText().replace(/<.*$/, '').trim()
        if (tname && /^Repository$/.test(tname)) {
          const targNode = tnode.getTypeArguments?.()?.[0]
          const targ = targNode ? className(targNode.getFirstChildByKind?.(SyntaxKind.Identifier) ?? targNode) : null
          if (targ) repoProps.set(pname, targ)
          continue
        }
        if (tname && /(CommandBus|QueryBus|EventBus)$/.test(tname)) {
          busProps.add(pname)
          continue
        }
        if (tname && classes.has(tname)) diProps.set(pname, tname)
      }
      // 클래스 프로퍼티에 달린 @InjectRepository 도
      for (const p of cls.getProperties()) {
        const ir = p.getDecorator('InjectRepository')
        if (ir) {
          const a = ir.getArguments()[0]
          if (a) repoProps.set(p.getName(), className(a))
        }
      }

      // 컨트롤러 → Route + HANDLES
      const ctrl = cls.getDecorator('Controller')
      const prefix = ctrl ? decoratorArg(ctrl) : null
      const isTask = rel.startsWith('src/task/')
      for (const m of cls.getMethods()) {
        const munit = uid.code(repo, rel, cname, m.getName())
        if (ctrl) {
          for (const d of m.getDecorators()) {
            const http = HTTP_DECOS[d.getName()]
            if (!http) continue
            const sub = decoratorArg(d)
            const p = normPath(typeof prefix === 'string' ? prefix : '', typeof sub === 'string' ? sub : '')
            const ruid = uid.route(repo, http, p)
            out.node(nodeRec(ruid, 'Route', `${http} ${p}`, {
              props: { repo, kind: isTask ? 'task' : 'http', method: http, path: p, controller: cname, handler: m.getName() },
              sourceRef: ref(repo, rel, m),
            }))
            out.edge(edgeRec(munit, 'HANDLES', ruid, { sourceRef: `${repo}/${rel}:${m.getStartLineNumber()}` }))
            out.count('routes')
          }
        }
        analyzeBody(m, munit, { repo, rel, out, repoProps, diProps, busProps, cname, entity, resolveEntity, handlers, methodUid, classUid, classes, enums })
      }
      // 클래스 밖 함수들
    }
    for (const [node, u] of units) {
      if (Node.isFunctionDeclaration(node) || Node.isArrowFunction(node) || Node.isFunctionExpression(node)) {
        analyzeBody(node, u, { repo, rel, out, repoProps: new Map(), diProps: new Map(), busProps: new Set(), cname: null, entity, resolveEntity, handlers, methodUid, classUid, classes, enums })
      }
    }
  }
  return out
}

function analyzeBody(fn, unitUid, ctx) {
  const { repo, rel, out, repoProps, diProps, busProps, cname, entity, resolveEntity, handlers, methodUid, classUid, classes, enums } = ctx
  const body = fn.getBody?.()
  if (!body) return
  const rw = new Map()   // tuid → {ops:Set, lines:Set, handle}
  const CASCADE_OP = { upsert: ['insert', 'update'], insert: ['insert'], update: ['update'], delete: ['remove'] }
  // cascade 는 TypeORM 의 save/remove/softRemove/recover 에서만 일어난다. update()/insert()/delete()·QueryBuilder 는 cascade 하지 않는다.
  const CASCADING_METHODS = new Set(['save', 'remove', 'softRemove', 'recover'])
  const touch = (ent, op, line, handle = 'typeorm', cascading = false, seen = new Set()) => {
    if (!ent) return
    const e = rw.get(ent.tuid) ?? { ops: new Set(), lines: new Set(), handle }
    e.ops.add(op)
    e.lines.add(line)
    rw.set(ent.tuid, e)
    if (!cascading) return
    const base = op.startsWith('cascade:') ? op.slice(8) : op
    const wanted = CASCADE_OP[base]
    if (!wanted || !ent.cascades || seen.has(ent.tuid)) return
    seen.add(ent.tuid)
    for (const [, c] of ent.cascades) {
      if (!c.ops.some((o) => wanted.includes(o))) continue
      const child = resolveEntity(c.target)
      if (child && !seen.has(child.tuid)) touch(child, `cascade:${base}`, line, handle, true, seen)
    }
  }
  const calls = new Map()  // target uid → {kind, lines}
  const call = (target, kind, line) => {
    if (!target || target === unitUid) return
    const e = calls.get(target) ?? { kind, lines: new Set() }
    e.lines.add(line)
    calls.set(target, e)
  }

  for (const ce of body.getDescendantsOfKind(SyntaxKind.CallExpression)) {
    const chain = chainOf(ce)
    const line = ce.getStartLineNumber()
    const callee = chain[chain.length - 1]
    if (!callee) continue
    const args = ce.getArguments()

    // --- QueryBuilder 체인: createQueryBuilder 를 포함하는 가장 바깥 호출에서 한 번만 처리
    if (callee === 'createQueryBuilder') {
      analyzeQb(ce, chain, line, { touch, repoProps, resolveEntity, entity, out, unitUid })
      continue
    }
    // --- 리포지토리/매니저 호출
    if (READ_METHODS.has(callee) || WRITE_METHODS[callee]) {
      const op = WRITE_METHODS[callee] ?? 'select'
      let ent = null
      // this.<repo>.<m>(
      if (chain[0] === 'this' && chain.length === 3 && repoProps.has(chain[1])) ent = resolveEntity(repoProps.get(chain[1]))
      // ….getRepository(X).<m>(  /  manager.<m>(X, …)
      if (!ent) {
        const inner = ce.getExpression()
        const recv = Node.isPropertyAccessExpression(inner) ? inner.getExpression() : null
        if (recv && Node.isCallExpression(recv)) {
          const rc = chainOf(recv)
          if (rc[rc.length - 1] === 'getRepository' && recv.getArguments()[0]) ent = resolveEntity(className(recv.getArguments()[0]))
        }
        if (!ent && (chain.includes('manager') || chain.includes('entityManager') || chain.includes('dataSource') || chain.includes('transactionalEntityManager')) && args[0]) {
          const a0 = args[0]
          if (Node.isIdentifier(a0) && entity.has(className(a0))) ent = resolveEntity(className(a0))
          else if (callee === 'save' || callee === 'remove' || callee === 'softRemove' || callee === 'insert' || callee === 'recover') {
            const names = classNamesOfType(a0.getType())
            const hit = names.find((n) => entity.has(n))
            if (hit) ent = resolveEntity(hit)
          }
        }
      }
      if (ent) touch(ent, op, line, 'typeorm', CASCADING_METHODS.has(callee))
      else if (chain[0] === 'this' && chain.length === 3 && repoProps.has(chain[1])) {
        out.count('repo-call-unresolved-entity')
        out.list('repo-entity-unresolved', repoProps.get(chain[1]))
      }
      else if (chain.includes('manager') || chain.includes('entityManager')) out.count('manager-call-unresolved')
      // 아래 self/DI 판정으로 이어가지 않는다
      if (chain[0] === 'this' && chain.length === 3 && repoProps.has(chain[1])) continue
    }
    // --- 원시 SQL: dataSource.query / manager.query / repository.query
    if (callee === 'query' && args[0] && (chain.includes('dataSource') || chain.includes('manager') || chain.includes('connection') || (chain[0] === 'this' && repoProps.has(chain[1])))) {
      const text = args[0].getText()
      const seen = new Set()
      let m
      SQL_TABLE_RE.lastIndex = 0
      while ((m = SQL_TABLE_RE.exec(text))) seen.add(m[1].toLowerCase())
      const stmt = /^\s*[`'"]\s*(insert|update|delete|replace)/i.exec(text)
      for (const t of seen) {
        const tuid = uid.table(t)
        const e = rw.get(tuid) ?? { ops: new Set(), lines: new Set(), handle: 'raw-sql' }
        e.ops.add(stmt ? stmt[1].toLowerCase() : 'select')
        e.lines.add(line)
        rw.set(tuid, e)
      }
      if (!seen.size) out.list('raw-query-no-table', `${repo}/${rel}:${line}`)
      continue
    }
    // --- HttpClient.<Method>(`${process.env.BACK_API_SERVER_URL}/zoomzoom/…`)
    if (chain[0] === 'HttpClient' && /^(Get|Post|Put|Patch|Delete|Request)$/.test(callee) && args[0]) {
      const tpl = args[0]
      const text = tpl.getText()
      const raw = /API_SERVER_URL/.test(text) ? templateToPath(tpl, (x) => /API_SERVER_URL/.test(x)) : null
      if (raw !== null) {
        const p = normPath(raw.replace(/\?.*$/, ''))
        const method = callee === 'Request' ? 'ANY' : callee.toUpperCase()
        const ruid = uid.route('zoomzoom-back', method, p)
        out.node(nodeRec(ruid, 'Route', `${method} ${p}`, { props: { repo: 'zoomzoom-back', kind: 'http', method, path: p, placeholder: true }, status: 'missing-from-source', sourceRef: `${repo}/${rel}:${line}` }))
        out.edge(edgeRec(unitUid, 'CALLS_HTTP', ruid, { props: { method, path: p, lines: [line], raw: true }, sourceRef: `${repo}/${rel}:${line}` }))
        out.count('http-calls')
      } else out.list('http-call-unparsed', `${repo}/${rel}:${line}`)
      continue
    }
    // --- CQRS: bus.execute(new XCommand())
    if (callee === 'execute' && chain[0] === 'this' && busProps.has(chain[1]) && args[0]) {
      const a0 = args[0]
      const cmd = Node.isNewExpression(a0) ? className(a0.getExpression()) : null
      const handler = cmd ? handlers.get(cmd) : null
      if (handler) call(methodUid(handler, 'execute'), 'cqrs', line)
      else out.list('cqrs-unresolved', cmd ?? `${repo}/${rel}:${line}`)
      continue
    }
    // --- DI: this.<svc>.<m>(
    if (chain[0] === 'this' && chain.length === 3 && diProps.has(chain[1])) {
      call(methodUid(diProps.get(chain[1]), callee), 'di', line)
      continue
    }
    // --- self: this.<m>(
    if (chain[0] === 'this' && chain.length === 2 && cname) {
      call(methodUid(cname, callee), 'self', line)
      continue
    }
    // --- static: Class.m(
    if (chain.length === 2 && chain[0] && classes.has(chain[0]) && chain[0] !== cname) {
      call(methodUid(chain[0], callee), 'static', line)
      continue
    }
  }

  // --- PUBLISHES: 객체 리터럴의 key: SQS*ServiceKey.X
  for (const pa of body.getDescendantsOfKind(SyntaxKind.PropertyAssignment)) {
    if (pa.getName() !== 'key') continue
    const init = pa.getInitializer()
    if (!init || !Node.isPropertyAccessExpression(init)) continue
    const enumName = init.getExpression().getText()
    const role = SQS_ROLE[enumName]
    if (!role) continue
    const value = enumValue(enums.get(enumName), init.getName())
    if (!value) {
      out.list('sqs-key-unresolved', `${enumName}.${init.getName()}`)
      continue
    }
    const line = pa.getStartLineNumber()
    out.node(nodeRec(uid.queue(role), 'Queue', role, { props: { role }, sourceRef: `${repo}/${rel}:${line}` }))
    out.node(nodeRec(uid.msg(role, value), 'QueueMessage', value, { props: { queue: role, key: value, enumName: `${enumName}.${init.getName()}` }, sourceRef: `${repo}/${rel}:${line}` }))
    out.edge(edgeRec(unitUid, 'PUBLISHES', uid.msg(role, value), { props: { lines: [line], heuristic: 'key: SQS*ServiceKey.X' }, sourceRef: `${repo}/${rel}:${line}` }))
    out.count('publishes')
  }

  // --- CONSUMES: 팩토리의 map.set(SQS*Key.X, new YService())
  for (const ce of body.getDescendantsOfKind(SyntaxKind.CallExpression)) {
    const chain = chainOf(ce)
    if (chain[chain.length - 1] !== 'set' || ce.getArguments().length < 2) continue
    const [k, v] = ce.getArguments()
    if (!Node.isPropertyAccessExpression(k) || !Node.isNewExpression(v)) continue
    const enumName = k.getExpression().getText()
    const role = SQS_ROLE[enumName]
    if (!role) continue
    const value = enumValue(enums.get(enumName), k.getName())
    const svc = v.getExpression().getText()
    const line = ce.getStartLineNumber()
    if (!value) {
      out.list('sqs-key-unresolved', `${enumName}.${k.getName()}`)
      continue
    }
    out.node(nodeRec(uid.queue(role), 'Queue', role, { props: { role, consumerService: uid.svc(repo, role) }, sourceRef: `${repo}/${rel}:${line}` }))
    out.node(nodeRec(uid.msg(role, value), 'QueueMessage', value, { props: { queue: role, key: value, enumName: `${enumName}.${k.getName()}` }, sourceRef: `${repo}/${rel}:${line}` }))
    const target = methodUid(svc, 'execute')
    if (target) out.edge(edgeRec(target, 'CONSUMES', uid.msg(role, value), { props: { lines: [line], factory: cname }, sourceRef: `${repo}/${rel}:${line}` }))
    else out.list('consumer-service-unresolved', svc)
    out.count('consumes')
  }

  for (const [tuid, e] of rw) {
    const ops = [...e.ops].sort()
    const isWrite = ops.some((o) => o !== 'select')
    const reads = ops.filter((o) => o === 'select')
    const writes = ops.filter((o) => o !== 'select')
    const lines = [...e.lines].sort((a, b) => a - b)
    if (reads.length) out.edge(edgeRec(unitUid, 'READS', tuid, { props: { ops: reads, lines, handle: e.handle }, sourceRef: `${repo}/${rel}:${lines[0]}` }))
    if (isWrite) out.edge(edgeRec(unitUid, 'WRITES', tuid, { props: { ops: writes, lines, handle: e.handle }, sourceRef: `${repo}/${rel}:${lines[0]}` }))
  }
  for (const [target, e] of calls) {
    const lines = [...e.lines].sort((a, b) => a - b)
    out.edge(edgeRec(unitUid, 'CALLS', target, { props: { kind: e.kind, lines }, sourceRef: `${repo}/${rel}:${lines[0]}` }))
  }
}

/** createQueryBuilder(...) 를 품은 체인 전체를 본다: from/join/update/insert.into/delete → 테이블·연산 */
function analyzeQb(ce, chain, line, { touch, repoProps, resolveEntity, entity, out, unitUid }) {
  // 체인의 꼭대기(가장 바깥 CallExpression)까지 올라가며 메서드 이름·인자를 모은다
  let top = ce
  while (true) {
    const p = top.getParent()
    if (p && Node.isPropertyAccessExpression(p) && p.getParent() && Node.isCallExpression(p.getParent()) && p.getParent().getExpression() === p) top = p.getParent()
    else break
  }
  const steps = []   // [{name, args}]
  let cur = top
  while (cur && Node.isCallExpression(cur)) {
    const ex = cur.getExpression()
    if (Node.isPropertyAccessExpression(ex)) {
      steps.unshift({ name: ex.getName(), args: cur.getArguments() })
      cur = ex.getExpression()
    } else break
  }
  // 기준 엔티티: this.<repo>.createQueryBuilder('a') / createQueryBuilder(Entity, 'a') / manager.createQueryBuilder(Entity,'a')
  const alias = new Map()   // alias → entity
  const base = chain.length >= 3 && chain[0] === 'this' && repoProps.has(chain[1]) ? resolveEntity(repoProps.get(chain[1])) : null
  const cqb = steps.find((s) => s.name === 'createQueryBuilder')
  let primary = base
  if (cqb) {
    const a = cqb.args
    if (a[0] && Node.isIdentifier(a[0]) && entity.has(className(a[0]))) {
      primary = resolveEntity(className(a[0]))
      if (a[1] && Node.isStringLiteral(a[1])) alias.set(a[1].getLiteralText(), primary)
    } else if (a[0] && Node.isStringLiteral(a[0]) && primary) alias.set(a[0].getLiteralText(), primary)
  }
  let op = 'select'
  let touched = false
  const resolveRef = (node) => {
    // 'alias.relation' | Entity 식별자
    if (Node.isIdentifier(node)) {
      const n = className(node)
      return entity.has(n) ? resolveEntity(n) : null
    }
    const txt = node.getText()
    const m = /^['"`]([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)['"`]$/.exec(txt)
    if (m) {
      const e = alias.get(m[1])
      const target = e?.relations.get(m[2])
      return target ? resolveEntity(target) : null
    }
    return null
  }
  for (const s of steps) {
    const a = s.args
    if (['from', 'addFrom'].includes(s.name) && a[0]) {
      const e = resolveRef(a[0])
      if (e) {
        if (!primary) primary = e
        if (a[1] && Node.isStringLiteral(a[1])) alias.set(a[1].getLiteralText(), e)
        touch(e, op === 'delete' ? 'delete' : 'select', line)
        touched = true
      }
    } else if (/^(innerJoin|leftJoin|innerJoinAndSelect|leftJoinAndSelect|leftJoinAndMapOne|leftJoinAndMapMany|innerJoinAndMapOne|innerJoinAndMapMany|rightJoin)$/.test(s.name) && a[0]) {
      const e = resolveRef(a[0])
      if (e) {
        if (a[1] && Node.isStringLiteral(a[1])) alias.set(a[1].getLiteralText(), e)
        touch(e, 'select', line)
        touched = true
      } else if (!/subquery|Subquery|=>/i.test(a[0].getText())) out.list('qb-join-unresolved', a[0].getText().slice(0, 60))
    } else if (QB_WRITE[s.name]) {
      op = QB_WRITE[s.name]
      const e = a[0] ? resolveRef(a[0]) : null
      if (e) {
        primary = e
        touch(e, op, line)
        touched = true
      }
    } else if (s.name === 'into' && a[0]) {
      const e = resolveRef(a[0])
      if (e) {
        touch(e, 'insert', line)
        touched = true
      }
    }
  }
  if (primary) {
    touch(primary, op, line)
    touched = true
  }
  if (!touched) {
    out.count('qb-unresolved')
    out.list('qb-unresolved-sites', `${line}:${chain.join('.')}`)
  }
}
