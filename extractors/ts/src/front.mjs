// zoomzoom-front: src/apis/**·src/** 의 fetchClient.get(InstanceType.Back, 'zoomzoom/…') / fetchClient.request(InstanceType.Back, ApiMethodType.POST, 'path') → CALLS_HTTP(raw).
import { Node, SyntaxKind, chainOf, edgeRec, emitStructure, enclosingUnit, enumValue, isSourceFile, nodeRec, openProject, relPath, templateToPath, uid } from './common.mjs'

const INSTANCE_REPO = { Back: 'zoomzoom-back', ZztApi: 'zoomzoom-auth', Api: 'zoomzoom-api' }

export function extractFront(repo, root, { out }) {
  const project = openProject(root)
  const files = project.getSourceFiles().map((sf) => [sf, relPath(root, sf)]).filter(([, rel]) => isSourceFile(rel) && (rel.startsWith('src/apis/') || rel.startsWith('src/helpers/') || rel.startsWith('src/app/') || rel.startsWith('src/pages/') || rel.startsWith('src/components/') || rel.startsWith('src/hooks/') || rel.startsWith('src/store/')))
  out.count('files', files.length)
  const enums = new Map()
  for (const sf of project.getSourceFiles()) for (const e of sf.getEnums()) enums.set(e.getName(), e)

  for (const [sf, rel] of files) {
    const { fuid, units } = emitStructure(out, root, sf, rel)
    for (const ce of sf.getDescendantsOfKind(SyntaxKind.CallExpression)) {
      const chain = chainOf(ce)
      if (chain[0] !== 'fetchClient' || chain.length !== 2) continue
      const args = ce.getArguments()
      let method = null
      let pathArg = null
      if (chain[1] === 'request' && args.length >= 3) {
        const mm = /^ApiMethodType\.(\w+)$/.exec(args[1].getText())
        method = mm ? (enumValue(enums.get('ApiMethodType'), mm[1]) ?? mm[1]).toUpperCase().replace(/^DEL$/, 'DELETE') : null
        pathArg = args[2]
      } else if (/^(get|post|put|patch|delete|del)$/.test(chain[1]) && args.length >= 2) {
        method = chain[1] === 'del' ? 'DELETE' : chain[1].toUpperCase()
        pathArg = args[1]
      } else continue
      const im = /^InstanceType\.(\w+)$/.exec(args[0].getText())
      const targetRepo = im ? INSTANCE_REPO[im[1]] : null
      if (!targetRepo || !method) {
        out.list('front-call-unparsed', `${repo}/${rel}:${ce.getStartLineNumber()}`)
        continue
      }
      const p0 = templateToPath(pathArg)
      let p = p0
      if (p === null) {
        out.list('front-call-unparsed', `${repo}/${rel}:${ce.getStartLineNumber()}`)
        continue
      }
      p = '/' + p.replace(/^\//, '').replace(/\?.*$/, '').replace(/\/$/, '')
      const line = ce.getStartLineNumber()
      const unit = enclosingUnit(ce, units) ?? fuid
      const ruid = uid.route(targetRepo, method, p)
      out.node(nodeRec(ruid, 'Route', `${method} ${p}`, { props: { repo: targetRepo, kind: 'http', method, path: p, placeholder: true }, status: 'missing-from-source', sourceRef: `${repo}/${rel}:${line}` }))
      out.edge(edgeRec(unit, 'CALLS_HTTP', ruid, { props: { method, path: p, lines: [line], raw: true }, sourceRef: `${repo}/${rel}:${line}` }))
      out.count('http-calls')
    }
  }
  return out
}
