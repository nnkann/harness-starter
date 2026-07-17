#!/usr/bin/env python3
"""Audit the Harness CPS doc_ops / Honcho wiki / Kanban promotion handoff contract.

This is the Maat-style semantic checklist for the Discord handoff thread.
It intentionally checks source_ref-visible terms, not just file existence, so future
implementations cannot claim completion while omitting CPS/Honcho/agent-management
requirements.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[3]
checks=[]
def has(path, terms, label):
    p=root/path
    if not p.exists():
        checks.append((False,label,f'missing {path}'))
        return
    text=p.read_text(encoding='utf-8')
    miss=[t for t in terms if t not in text]
    checks.append((not miss,label,('missing terms '+str(miss)) if miss else 'ok'))

def exists(path,label):
    checks.append(((root/path).exists(),label, 'ok' if (root/path).exists() else f'missing {path}'))

# Handoff 1: hermes-kann and thoth
has('AGENTS.md',['digest_first_tool_use','cps_before_execution','owner_approval_boundary','project_context_routing','honcho_context_merge','raw_output_hygiene'],'hermes-kann obligations in default runtime')
has('docs/harness/agents/thoth.md',['compile root goal into CPS expression','define task_AC','define owner_approval_boundary','define prohibited_actions','define evidence_acquisition.C/P/S','identify required_docs','identify doc_ops_needed','propose actor_binding','implementation','commit/push','raw stdout/git/log/sqlite/test dump prefetch','direct Honcho policy write without source_ref'],'thoth full contract')
# Handoff 2
has('docs/harness/agents/maat.md',['cps_audit_and_project_digest_gate','project-specific skill digest','allowed evidence request','count','path','top_error','line_ref','artifact_ref','schema_field_presence','full raw stdout','full git diff/log','full sqlite dump','full test output','full skill/document dump'],'maat audit+skill digest gate')
for agent in ['ptah','anubis','sekhmet','sia']:
    has(f'docs/harness/agents/{agent}.md',['CPS','task_AC','frontmatter','owner_approval_boundary','prohibited_actions','evidence_acquisition','source_refs','artifact_refs','packet_ref','doc_refs'],f'{agent} required context')
has('docs/harness/agents/seshat.md',['create/update required md files','enforce frontmatter schema','maintain docs in git as source of truth','generate doc_ops_manifest','generate honcho_ingest_manifest','track source_path, line_ref, commit_ref, doc_type','detect stale or missing required docs','prepare digest artifacts for Honcho ingestion'],'seshat doc_ops')
# Handoff 3 required docs
for path in ['docs/harness/contracts/cp_frontmatter_schema.md','docs/harness/contracts/cp_cps_evidence_acquisition.md','docs/harness/contracts/cp_owner_approval_boundary.md','docs/harness/contracts/cp_agent_role_contracts.md','docs/harness/contracts/cp_kanban_promotion_contract.md','docs/harness/contracts/cp_honcho_doc_wiki_boundary.md','docs/harness/contracts/cp_harness_defect_collection_fix_loop.md']:
    exists(path,'required contract '+path)
for path in ['docs/harness/agents/thoth.md','docs/harness/agents/maat.md','docs/harness/agents/seshat.md','docs/harness/agents/ptah.md','docs/harness/agents/anubis.md','docs/harness/agents/sekhmet.md','docs/harness/agents/honcho_archivist.md','docs/harness/agents/honcho_librarian.md','docs/harness/agents/honcho_context.md','docs/harness/agents/sia.md']:
    exists(path,'required agent '+path)
has('docs/harness/contracts/cp_frontmatter_schema.md',['title:','description:','domain:','status:','c:','problem:','s:','tags:','relates-to:','owner_approval_boundary:','prohibited_actions:'],'frontmatter schema fields')
has('docs/harness/contracts/cp_honcho_doc_wiki_boundary.md',['Repo / Harness starter is authoritative source','Honcho is an indexed wiki','honcho_doc_digest','source_path','source_commit','doc_type','frontmatter_summary','line_refs','artifact_refs'],'Honcho plane boundary')
for agent,terms in {
'honcho_archivist':['ingest required md digest into Honcho','preserve source_path/source_commit/line_ref/artifact_ref','classify doc_type','store frontmatter_summary','avoid raw stdout/log archival'],
'honcho_librarian':['verify required md files are indexed','detect stale docs','compare repo source vs Honcho digest','flag missing CPS/frontmatter/evidence sections','report drift'],
'honcho_context':['retrieve project-relevant docs','provide source_ref candidates','suggest prior CPS patterns','provide context without overriding Harness policy','Honcho must not override Harness policy'],
}.items():
    has(f'docs/harness/agents/{agent}.md',terms,agent+' full role')
has('docs/harness/contracts/cp_kanban_promotion_contract.md',['keep_kanban: true','keep_auto_decompose: true','native_auto_decompose_for_harness_boards: false','harness_promotion_compiler_required: true','harness_compile_triage(task_id)','write root cps_packet artifact','write doc_ops_manifest','write honcho_ingest_manifest','create compile/audit gate node','create compact implementation/review nodes','promote root as graph container, not completed work'],'Kanban promotion shape')
# Handoff 4 manifests/task body/AC/prohibited
for path in ['.harness/project/runs/_template/cps_packet.yaml','.harness/project/runs/_template/doc_ops_manifest.yaml','.harness/project/runs/_template/honcho_ingest_manifest.yaml']:
    exists(path,'run template '+path)
has('.harness/schemas/kanban-task-node.schema.yaml',['packet_ref','root_goal_id','flow_graph_id','node_id','actor_binding','task_AC','expected_evidence','doc_refs','Do not close the root goal'],'child task body marker schema')
has('.harness/project/runs/_template/doc_ops_manifest.yaml',['required_docs','generated_docs','updated_docs','owner_approval_boundary','prohibited_actions','raw stdout/log archival','Honcho-only policy creation'],'doc_ops_manifest template')
has('.harness/project/runs/_template/honcho_ingest_manifest.yaml',['source_commit','digest_required','frontmatter_summary_required','line_refs_required','artifact_refs_required','full raw stdout/log/test output ingestion','full chat transcript as project policy'],'honcho_ingest_manifest template')
has('.harness/hermes/doc-generation.yaml',['seshat','maat','honcho_archivist','honcho_librarian','honcho_context','native_auto_decompose_for_harness_boards: false','harness_promotion_compiler_required: true'],'workflow lifecycle bindings')


# Enforcement-level checks: not just agent docs, but executable packet/schema/template markers.
has('.harness/schemas/agent-task.schema.yaml',['packet_ref','CPS','frontmatter','task_AC','source_refs','artifact_refs','owner_approval_boundary','prohibited_actions','evidence_acquisition','required_docs','doc_ops_needed','doc_refs'],'agent-task schema enforces execution required context')
has('.harness/hermes/agent-task.template.yaml',['packet_ref','CPS:','frontmatter:','task_AC:','source_refs:','artifact_refs:','owner_approval_boundary:','prohibited_actions:','evidence_acquisition:','doc_refs:'],'agent-task template carries execution required context')
has('.harness/schemas/cps-packet.schema.yaml',['source_refs','artifact_refs','doc_refs','evidence_acquisition','owner_approval_boundary','prohibited_actions'],'cps packet schema enforces source/artifact refs and boundary')
has('.harness/project/runs/_template/cps_packet.yaml',['source_refs:','artifact_refs:','doc_refs:','evidence_acquisition:','owner_approval_boundary:','prohibited_actions:'],'cps packet template carries source/artifact refs and boundary')
has('.harness/schemas/kanban-task-node.schema.yaml',['packet_ref','source_refs','artifact_refs','owner_approval_boundary','prohibited_actions','evidence_acquisition','doc_refs'],'compact node schema enforces inherited refs/boundary/evidence markers')
has('docs/harness/contracts/cp_honcho_agent_management.md',['managed_agents','honcho_archivist','honcho_librarian','honcho_context','authority_order','Honcho-only policy creation'],'Honcho agent management contract exists and is managed')

fail=[(l,d) for ok,l,d in checks if not ok]
print(f'total={len(checks)} fail={len(fail)}')
for l,d in fail:
    print('FAIL:',l,'=>',d)

import sys
sys.exit(1 if fail else 0)
