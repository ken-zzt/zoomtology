#!/usr/bin/env node
// 사용: node src/extract.mjs <repo-name> <repo-root> <out.jsonl>
// 출력: 줄마다 {kind:"node"|"edge", …} — Python 쪽 Collector 레코드와 같은 모양. 코드 본문·SQL 원문은 없다.
import { writeFileSync } from 'node:fs'
import { Out } from './common.mjs'
import { extractNest } from './nest.mjs'
import { extractBack } from './back.mjs'
import { extractFront } from './front.mjs'

const [repo, root, outPath] = process.argv.slice(2)
if (!repo || !root || !outPath) {
  console.error('usage: extract.mjs <repo-name> <repo-root> <out.jsonl>')
  process.exit(2)
}
const started = Date.now()
const out = new Out(repo)
if (repo === 'zoomzoom-back') extractBack(repo, root, { out })
else if (repo === 'zoomzoom-front') extractFront(repo, root, { out })
else extractNest(repo, root, { out })

const lines = out.records().map((r) => JSON.stringify(r))
lines.push(JSON.stringify({ kind: 'report', repo, report: out.report, ms: Date.now() - started }))
writeFileSync(outPath, lines.join('\n') + '\n')
console.error(`${repo}: ${out.nodes.size} nodes, ${out.edges.size} edges, ${Date.now() - started}ms`)
