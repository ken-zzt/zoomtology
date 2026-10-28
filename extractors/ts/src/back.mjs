// zoomzoom-back: AccessRule 리터럴 → Route(accessrule). 컨트롤러는 `@Controller('*')` 하나라 첫 경로 조각(zoomzoom|partner|admin)이 서비스를 고른다.
import { Node, SyntaxKind, edgeRec, emitStructure, enumValue, isSourceFile, nodeRec, openProject, relPath, uid } from './common.mjs'

const SERVICE_FILES = { 'src/api/services/zoomzoom.ts': 'zoomzoom', 'src/api/services/partner.ts': 'partner', 'src/api/services/admin.ts': 'admin', 'src/api/services/external.ts': 'external', 'src/api/services/document.ts': 'document', 'src/api/services/operation.ts': 'operation' }

export function extractBack(repo, root, { out }) {
  const project = openProject(root)
  const files = project.getSourceFiles().map((sf) => [sf, relPath(root, sf)]).filter(([, rel]) => isSourceFile(rel))
  out.count('files', files.length)
  const enums = new Map()
  for (const [sf] of files) for (const e of sf.getEnums()) enums.set(e.getName(), e)

  for (const [sf, rel] of files) {
    emitStructure(out, root, sf, rel, { classKind: (cls) => (cls.getDecorator('Controller') ? 'controller' : 'class') })
    const service = SERVICE_FILES[rel]
    if (!service) continue
    const cls = sf.getClass('AccessMiddleware')
    const holder = cls ? uid.code(repo, rel, 'AccessMiddleware') : uid.file(repo, rel)
    for (const ne of sf.getDescendantsOfKind(SyntaxKind.NewExpression)) {
      if (ne.getExpression().getText() !== 'AccessRule') continue
      const args = ne.getArguments()
      if (args.length < 2) continue
      const methodText = args[0].getText()
      const mm = /^HttpMethod\.(\w+)$/.exec(methodText)
      const method = mm ? enumValue(enums.get('HttpMethod'), mm[1]) : null
      const regex = Node.isStringLiteral(args[1]) || Node.isNoSubstitutionTemplateLiteral(args[1]) ? args[1].getLiteralText() : null
      if (!method || regex === null) {
        out.list('accessrule-unparsed', `${repo}/${rel}:${ne.getStartLineNumber()}`)
        continue
      }
      const target = args[2] && (Node.isStringLiteral(args[2]) || Node.isNoSubstitutionTemplateLiteral(args[2])) ? args[2].getLiteralText() : null
      const flag = (i) => (args[i] ? args[i].getText() === 'true' : undefined)
      const version = args[5] && Node.isNumericLiteral(args[5]) ? Number(args[5].getText()) : undefined
      const line = ne.getStartLineNumber()
      const ruid = uid.route(repo, method, regex.replace(/\s/g, '%20'))
      out.node(nodeRec(ruid, 'Route', `${method} ${service}/${regex}`, {
        props: { repo, kind: 'accessrule', method, path: regex, service, target, auth: flag(3), login: flag(4), version, apiPath: literalPath(target ?? regex), matchKind: matchKind(regex, target) },
        sourceRef: `${repo}/${rel}:${line}`,
      }))
      out.edge(edgeRec(holder, 'DEFINES', ruid, { sourceRef: `${repo}/${rel}:${line}` }))
      out.count(`rules-${service}`)
    }
  }
  return out
}

/** 정규식에서 첫 메타문자 앞까지의 리터럴 경로. `^order/[0-9]+/rejected$` → `order/` */
export function literalPath(regex) {
  let s = regex.replace(/^\^/, '')
  const m = /[\[\]().*+?|\\$]/.exec(s)
  if (m) s = s.slice(0, m.index)
  return s.replace(/\/$/, '')
}

export function matchKind(regex, target) {
  if (target) return 'target'
  const body = regex.replace(/^\^/, '').replace(/\$$/, '')
  if (!/[\[\]().*+?|\\]/.test(body) && regex.endsWith('$')) return 'exact'
  return 'regex'
}
