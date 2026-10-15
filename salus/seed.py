"""Load universal multi-domain demo tenant into FalkorDB (salus:acme)."""

from __future__ import annotations

import time

from salus.config import settings
from salus.graph import ensure_indexes, query, select_graph

SEED_CYPHER = r"""
CREATE (t:Tenant {
  id: 'acme',
  name: 'Acme Campus',
  industries: ['finance', 'healthcare', 'security', 'facilities'],
  created_at: $now
})

CREATE (a_inv:Agent {id: 'agent:investigator', name: 'Investigator', role: 'investigator',
  capabilities: ['multi_hop', 'graph_algo', 'explain']})
CREATE (a_router:Agent {id: 'agent:router', name: 'Router', role: 'router',
  capabilities: ['classify', 'handoff', 'memory_recall']})
CREATE (a_scribe:Agent {id: 'agent:scribe', name: 'Scribe', role: 'scribe',
  capabilities: ['episodic', 'semantic', 'procedural']})
CREATE (a_actor:Agent {id: 'agent:actor', name: 'Actor', role: 'actor',
  capabilities: ['assign', 'escalate', 'update_ticket', 'page']})

CREATE (a_inv)-[:FOR_TENANT]->(t)
CREATE (a_router)-[:FOR_TENANT]->(t)
CREATE (a_scribe)-[:FOR_TENANT]->(t)
CREATE (a_actor)-[:FOR_TENANT]->(t)

CREATE (fin:Team {id: 'team:payments', name: 'Payments Platform', mission: 'Money movement', domain: 'finance'})
CREATE (care:Team {id: 'team:clinical-it', name: 'Clinical IT', mission: 'EHR & patient systems', domain: 'healthcare'})
CREATE (sec:Team {id: 'team:physical-sec', name: 'Physical Security', mission: 'Access & badges', domain: 'security'})
CREATE (fac:Team {id: 'team:facilities', name: 'Facilities', mission: 'HVAC & building ops', domain: 'facilities'})
CREATE (sre:Team {id: 'team:sre', name: 'SRE', mission: 'Reliability across domains', domain: 'ops'})

CREATE (maya:Person {id: 'person:maya', name: 'Maya Chen', email: 'maya@acme.test', role: 'Staff Payments Engineer', status: 'active'})
CREATE (leo:Person {id: 'person:leo', name: 'Leo Okonkwo', email: 'leo@acme.test', role: 'Fraud Analyst', status: 'active'})
CREATE (dr_kim:Person {id: 'person:kim', name: 'Dr. Ana Kim', email: 'ana.kim@acme.test', role: 'Clinical Systems Lead', status: 'active'})
CREATE (jordan:Person {id: 'person:jordan', name: 'Jordan Blake', email: 'jordan@acme.test', role: 'Security Operations', status: 'active'})
CREATE (ravi:Person {id: 'person:ravi', name: 'Ravi Patel', email: 'ravi@acme.test', role: 'HVAC Controls Engineer', status: 'active'})
CREATE (priya:Person {id: 'person:priya', name: 'Priya Nair', email: 'priya@acme.test', role: 'SRE Lead', status: 'active'})
CREATE (sam:Person {id: 'person:sam', name: 'Sam Rivera', email: 'sam@acme.test', role: 'Campus Ops PM', status: 'active'})

CREATE (maya)-[:MEMBER_OF {role: 'tech_lead', since: 1700000000}]->(fin)
CREATE (leo)-[:MEMBER_OF {role: 'analyst', since: 1710000000}]->(fin)
CREATE (dr_kim)-[:MEMBER_OF {role: 'lead', since: 1695000000}]->(care)
CREATE (jordan)-[:MEMBER_OF {role: 'operator', since: 1705000000}]->(sec)
CREATE (ravi)-[:MEMBER_OF {role: 'engineer', since: 1712000000}]->(fac)
CREATE (priya)-[:MEMBER_OF {role: 'lead', since: 1690000000}]->(sre)
CREATE (sam)-[:MEMBER_OF {role: 'pm', since: 1680000000}]->(sre)
CREATE (maya)-[:REPORTS_TO]->(sam)
CREATE (leo)-[:REPORTS_TO]->(sam)
CREATE (dr_kim)-[:REPORTS_TO]->(sam)
CREATE (jordan)-[:REPORTS_TO]->(sam)
CREATE (ravi)-[:REPORTS_TO]->(sam)
CREATE (priya)-[:REPORTS_TO]->(sam)

CREATE (sk_pay:Skill {id: 'skill:payments', name: 'payments', domain: 'finance'})
CREATE (sk_fraud:Skill {id: 'skill:fraud', name: 'fraud-detection', domain: 'finance'})
CREATE (sk_ehr:Skill {id: 'skill:ehr', name: 'ehr', domain: 'healthcare'})
CREATE (sk_badge:Skill {id: 'skill:badge', name: 'access-control', domain: 'security'})
CREATE (sk_hvac:Skill {id: 'skill:hvac', name: 'hvac-controls', domain: 'facilities'})
CREATE (sk_k8s:Skill {id: 'skill:k8s', name: 'kubernetes', domain: 'ops'})

CREATE (maya)-[:KNOWS {level: 5, last_used: $now}]->(sk_pay)
CREATE (leo)-[:KNOWS {level: 5, last_used: $now}]->(sk_fraud)
CREATE (dr_kim)-[:KNOWS {level: 5, last_used: $now}]->(sk_ehr)
CREATE (jordan)-[:KNOWS {level: 5, last_used: $now}]->(sk_badge)
CREATE (ravi)-[:KNOWS {level: 5, last_used: $now}]->(sk_hvac)
CREATE (priya)-[:KNOWS {level: 5, last_used: $now}]->(sk_k8s)
CREATE (priya)-[:KNOWS {level: 3, last_used: $now}]->(sk_pay)

CREATE (proj_pay:Project {id: 'proj:checkout', name: 'Checkout v3', status: 'active', priority: 'P0', domain: 'finance', started_at: 1715000000})
CREATE (proj_ehr:Project {id: 'proj:ehr-uptime', name: 'EHR Uptime', status: 'active', priority: 'P0', domain: 'healthcare', started_at: 1710000000})
CREATE (proj_sec:Project {id: 'proj:campus-access', name: 'Campus Access', status: 'active', priority: 'P1', domain: 'security', started_at: 1708000000})
CREATE (proj_hvac:Project {id: 'proj:comfort', name: 'Building Comfort', status: 'active', priority: 'P1', domain: 'facilities', started_at: 1711000000})

CREATE (api:System {id: 'sys:payments-api', name: 'payments-api', kind: 'service', env: 'prod', criticality: 'critical', domain: 'finance'})
CREATE (ledger:System {id: 'sys:ledger', name: 'ledger-db', kind: 'database', env: 'prod', criticality: 'critical', domain: 'finance'})
CREATE (riskeng:System {id: 'sys:risk-engine', name: 'risk-engine', kind: 'service', env: 'prod', criticality: 'high', domain: 'finance'})
CREATE (gateway:System {id: 'sys:card-gateway', name: 'card-gateway', kind: 'saas', env: 'prod', criticality: 'critical', domain: 'finance'})
CREATE (ehr:System {id: 'sys:ehr', name: 'ehr-core', kind: 'service', env: 'prod', criticality: 'critical', domain: 'healthcare'})
CREATE (pacs:System {id: 'sys:pacs', name: 'imaging-pacs', kind: 'service', env: 'prod', criticality: 'high', domain: 'healthcare'})
CREATE (badge:System {id: 'sys:badge', name: 'badge-controller', kind: 'device-fleet', env: 'prod', criticality: 'critical', domain: 'security'})
CREATE (cams:System {id: 'sys:cameras', name: 'camera-nvr', kind: 'device-fleet', env: 'prod', criticality: 'high', domain: 'security'})
CREATE (bms:System {id: 'sys:bms', name: 'building-mgmt', kind: 'controller', env: 'prod', criticality: 'high', domain: 'facilities'})
CREATE (hvac:System {id: 'sys:hvac-wing-b', name: 'hvac-wing-b', kind: 'controller', env: 'prod', criticality: 'high', domain: 'facilities'})

CREATE (fin)-[:OWNS {since: 1715000000}]->(proj_pay)
CREATE (care)-[:OWNS {since: 1710000000}]->(proj_ehr)
CREATE (sec)-[:OWNS {since: 1708000000}]->(proj_sec)
CREATE (fac)-[:OWNS {since: 1711000000}]->(proj_hvac)
CREATE (maya)-[:OWNS {since: 1715000000}]->(api)
CREATE (priya)-[:OWNS {since: 1700000000}]->(ledger)
CREATE (leo)-[:OWNS {since: 1712000000}]->(riskeng)
CREATE (dr_kim)-[:OWNS {since: 1710000000}]->(ehr)
CREATE (jordan)-[:OWNS {since: 1708000000}]->(badge)
CREATE (ravi)-[:OWNS {since: 1711000000}]->(hvac)
CREATE (ravi)-[:OWNS {since: 1711000000}]->(bms)

CREATE (maya)-[:WORKS_ON {allocation: 0.6, since: 1715000000}]->(proj_pay)
CREATE (sam)-[:WORKS_ON {allocation: 0.4, since: 1715000000}]->(proj_pay)
CREATE (dr_kim)-[:WORKS_ON {allocation: 0.8, since: 1710000000}]->(proj_ehr)
CREATE (jordan)-[:WORKS_ON {allocation: 0.7, since: 1708000000}]->(proj_sec)
CREATE (ravi)-[:WORKS_ON {allocation: 0.9, since: 1711000000}]->(proj_hvac)

CREATE (proj_pay)-[:USES]->(api)
CREATE (proj_pay)-[:USES]->(riskeng)
CREATE (proj_ehr)-[:USES]->(ehr)
CREATE (proj_ehr)-[:USES]->(pacs)
CREATE (proj_sec)-[:USES]->(badge)
CREATE (proj_sec)-[:USES]->(cams)
CREATE (proj_hvac)-[:USES]->(bms)
CREATE (proj_hvac)-[:USES]->(hvac)

CREATE (api)-[:DEPENDS_ON {kind: 'sync'}]->(ledger)
CREATE (api)-[:DEPENDS_ON {kind: 'sync'}]->(gateway)
CREATE (riskeng)-[:DEPENDS_ON {kind: 'async'}]->(api)
CREATE (ehr)-[:DEPENDS_ON {kind: 'sync'}]->(pacs)
CREATE (badge)-[:DEPENDS_ON {kind: 'sync'}]->(cams)
CREATE (hvac)-[:DEPENDS_ON {kind: 'sync'}]->(bms)
CREATE (ehr)-[:DEPENDS_ON {kind: 'facility'}]->(hvac)
CREATE (badge)-[:DEPENDS_ON {kind: 'facility'}]->(bms)

CREATE (ch:Channel {id: 'chan:incidents', name: '#campus-incidents', platform: 'slack'})

CREATE (rb_pay:Document {id: 'doc:rb-payments', title: 'Payments API incident runbook', source: 'notion',
  url: 'https://docs.acme.test/runbooks/payments-api', domain: 'finance', updated_at: $now,
  summary: 'Page owner, check ledger lag, freeze risky merchants'})
CREATE (rb_hvac:Document {id: 'doc:rb-hvac', title: 'Wing B HVAC loss SOP', source: 'notion',
  url: 'https://docs.acme.test/runbooks/hvac-wing-b', domain: 'facilities', updated_at: $now,
  summary: 'Check BMS link, page HVAC eng, notify clinical if OR/wards affected'})
CREATE (rb_badge:Document {id: 'doc:rb-badge', title: 'Badge controller outage SOP', source: 'notion',
  url: 'https://docs.acme.test/runbooks/badge', domain: 'security', updated_at: $now,
  summary: 'Fail-secure doors, dispatch security ops, verify camera NVR'})
CREATE (rb_ehr:Document {id: 'doc:rb-ehr', title: 'EHR degradation playbook', source: 'notion',
  url: 'https://docs.acme.test/runbooks/ehr', domain: 'healthcare', updated_at: $now,
  summary: 'Page clinical IT, check PACS and facility cooling dependencies'})

CREATE (adr:Decision {id: 'dec:adr-12', title: 'ADR-12: Route high-risk txs through risk-engine',
  status: 'accepted', domain: 'finance', decided_at: 1720000000,
  rationale: 'Reduce chargebacks without blocking good customers'})
CREATE (pol:Decision {id: 'dec:pol-hvac-clinical', title: 'Policy: EHR depends on Wing B cooling',
  status: 'accepted', domain: 'healthcare', decided_at: 1718000000,
  rationale: 'Server room and imaging suites share Wing B HVAC'})

CREATE (maya)-[:AUTHORED {at: $now}]->(rb_pay)
CREATE (ravi)-[:AUTHORED {at: $now}]->(rb_hvac)
CREATE (jordan)-[:AUTHORED {at: $now}]->(rb_badge)
CREATE (dr_kim)-[:AUTHORED {at: $now}]->(rb_ehr)
CREATE (sam)-[:AUTHORED {at: 1720000000}]->(adr)
CREATE (dr_kim)-[:AUTHORED {at: 1718000000}]->(pol)
CREATE (adr)-[:DECIDED_FOR]->(proj_pay)
CREATE (adr)-[:REFERENCES]->(riskeng)
CREATE (pol)-[:DECIDED_FOR]->(proj_ehr)
CREATE (pol)-[:REFERENCES]->(hvac)
CREATE (pol)-[:REFERENCES]->(ehr)
CREATE (rb_pay)-[:REFERENCES]->(api)
CREATE (rb_pay)-[:REFERENCES]->(ledger)
CREATE (rb_hvac)-[:REFERENCES]->(hvac)
CREATE (rb_hvac)-[:REFERENCES]->(bms)
CREATE (rb_badge)-[:REFERENCES]->(badge)
CREATE (rb_ehr)-[:REFERENCES]->(ehr)
CREATE (rb_pay)-[:POSTED_IN]->(ch)
CREATE (rb_hvac)-[:POSTED_IN]->(ch)

CREATE (tkt:Ticket {id: 'tkt:inc-441', key: 'INC-441', title: 'Spike in declined checkout txs',
  status: 'open', severity: 'SEV-1', domain: 'finance', created_at: $now})
CREATE (tkt)-[:ABOUT]->(api)
CREATE (tkt)-[:ABOUT]->(proj_pay)
CREATE (tkt)-[:ASSIGNED_TO {at: $now}]->(priya)
CREATE (tkt)-[:REFERENCES]->(rb_pay)
CREATE (tkt)-[:POSTED_IN]->(ch)

CREATE (proc:Procedure {id: 'proc:universal-sev', name: 'Universal SEV response',
  steps_json: '["classify domain","blast radius","who owns/knows","recall episodes/facts","propose actions","write EvidencePath"]',
  success_rate: 0.88, updated_at: $now})

CREATE (fact1:Fact {id: 'fact:ledger-lag-causes-declines',
  statement: 'Ledger replication lag above 2s correlates with false declines on payments-api',
  confidence: 0.91, valid_from: 1726000000, valid_to: null, source: 'postmortem-INC-318'})
CREATE (fact1)-[:ABOUT_ENTITY]->(ledger)
CREATE (fact1)-[:ABOUT_ENTITY]->(api)
CREATE (fact1)-[:LEARNED_FROM]->(rb_pay)

CREATE (fact2:Fact {id: 'fact:hvac-affects-ehr',
  statement: 'Wing B HVAC loss degrades ehr-core and imaging-pacs within 15 minutes',
  confidence: 0.94, valid_from: 1718000000, valid_to: null, source: 'policy-pol-hvac-clinical'})
CREATE (fact2)-[:ABOUT_ENTITY]->(hvac)
CREATE (fact2)-[:ABOUT_ENTITY]->(ehr)
CREATE (fact2)-[:LEARNED_FROM]->(pol)

CREATE (ep_old:Episode {id: 'ep:inc-318',
  summary: 'INC-318: ledger lag caused checkout declines; Maya fixed replica',
  at: 1726000000, importance: 0.9})
CREATE (ep_old)-[:ABOUT_ENTITY]->(api)
CREATE (ep_old)-[:ABOUT_ENTITY]->(ledger)
CREATE (ep_old)-[:ABOUT_ENTITY]->(maya)
CREATE (ep_old)-[:UPDATED_PROCEDURE]->(proc)
CREATE (fact1)-[:LEARNED_FROM]->(ep_old)

CREATE (ep_hvac:Episode {id: 'ep:inc-209',
  summary: 'INC-209: BMS link flap cooled Wing B; EHR latency spiked; Ravi restored controller',
  at: 1722000000, importance: 0.92})
CREATE (ep_hvac)-[:ABOUT_ENTITY]->(hvac)
CREATE (ep_hvac)-[:ABOUT_ENTITY]->(ehr)
CREATE (ep_hvac)-[:ABOUT_ENTITY]->(ravi)

CREATE (state:SharedState {id: 'state:active-incident', key: 'active_incident',
  value_json: '{"ticket":"INC-441","severity":"SEV-1","domain":"finance","phase":"triage"}',
  version: 1, updated_at: $now})
CREATE (a_inv)-[:SHARES {mode: 'write'}]->(state)
CREATE (a_router)-[:SHARES {mode: 'read'}]->(state)
CREATE (a_actor)-[:SHARES {mode: 'write'}]->(state)
CREATE (a_scribe)-[:SHARES {mode: 'read'}]->(state)

CREATE (finding:Finding {id: 'find:441', kind: 'checkout_decline_spike',
  title: 'Decline rate 14% (baseline 1.2%) on payments-api', severity: 'critical',
  raw_json: '{"metric":"decline_rate","value":0.14,"domain":"finance"}', detected_at: $now})

CREATE (inv:Investigation {id: 'inv:441', status: 'open', started_at: $now, closed_at: null,
  hypothesis: 'Possible ledger lag or risk-engine overblock'})
CREATE (inv)-[:TRIGGERED_BY]->(finding)
CREATE (inv)-[:TRIGGERED_BY]->(tkt)
CREATE (inv)-[:LED_BY]->(a_inv)
CREATE (a_inv)-[:USES_PROCEDURE]->(proc)

CREATE (tc1:ToolCall {id: 'tool:441-1', tool: 'graph.blast_radius',
  args_json: '{"system":"payments-api","max_hops":3}',
  result_summary: 'payments-api → ledger, card-gateway', at: $now, latency_ms: 12})
CREATE (tc2:ToolCall {id: 'tool:441-2', tool: 'graph.who_knows',
  args_json: '{"system":"payments-api"}',
  result_summary: 'Maya owner; Priya standby', at: $now, latency_ms: 8})
CREATE (tc3:ToolCall {id: 'tool:441-3', tool: 'memory.recall_episodes',
  args_json: '{"about":"payments-api","limit":3}',
  result_summary: 'INC-318 ledger lag pattern matches', at: $now, latency_ms: 9})
CREATE (inv)-[:QUERIED {step: 1}]->(tc1)
CREATE (inv)-[:QUERIED {step: 2}]->(tc2)
CREATE (inv)-[:QUERIED {step: 3}]->(tc3)
CREATE (tc1)-[:NEXT]->(tc2)
CREATE (tc2)-[:NEXT]->(tc3)

CREATE (path:EvidencePath {id: 'path:441',
  cypher: 'MATCH (api:System {name:\"payments-api\"})-[:DEPENDS_ON]->(dep) RETURN dep',
  node_ids: ['sys:payments-api','sys:ledger','person:maya','ep:inc-318','fact:ledger-lag-causes-declines'],
  rel_types: ['DEPENDS_ON','OWNS','ABOUT_ENTITY','LEARNED_FROM'],
  summary: 'payments-api depends on ledger; INC-318 + lag fact; owners Maya/Priya',
  confidence: 0.88})
CREATE (tc3)-[:PRODUCED]->(path)
CREATE (path)-[:SUPPORTS]->(inv)
CREATE (path)-[:TOUCHES {hop: 0}]->(api)
CREATE (path)-[:TOUCHES {hop: 1}]->(ledger)
CREATE (path)-[:TOUCHES {hop: 2}]->(maya)

CREATE (act:Action {id: 'act:441-page', kind: 'page_owner', status: 'completed',
  params_json: '{"person":"person:maya","ticket":"INC-441"}',
  result_json: '{"paged":true}', at: $now})
CREATE (inv)-[:DECIDED]->(act)
CREATE (act)-[:EXECUTED_BY]->(a_actor)
CREATE (act)-[:AFFECTS]->(tkt)
CREATE (act)-[:AFFECTS]->(maya)
CREATE (path)-[:SUPPORTS]->(act)
CREATE (act)-[:GROUNDED_IN]->(rb_pay)
CREATE (act)-[:GROUNDED_IN]->(ep_old)

CREATE (h1:Handoff {id: 'hand:441-1', reason: 'SEV-1 needs graph investigation',
  payload_json: '{"finding":"find:441"}', at: $now, status: 'done'})
CREATE (h2:Handoff {id: 'hand:441-2', reason: 'Evidence ready; page owner',
  payload_json: '{"investigation":"inv:441"}', at: $now, status: 'done'})
CREATE (a_router)-[:HANDED_OFF]->(h1)
CREATE (h1)-[:RECEIVED]->(a_inv)
CREATE (a_inv)-[:HANDED_OFF]->(h2)
CREATE (h2)-[:RECEIVED]->(a_actor)

CREATE (sess:Session {id: 'sess:u-sam-1', user_id: 'person:sam', started_at: $now, ended_at: null, status: 'open'})
CREATE (sess)-[:FOR_TENANT]->(t)
CREATE (m1:Message {id: 'msg:1', role: 'user', content: 'Why are checkouts failing and who should own this?', at: $now, token_count: 14})
CREATE (m2:Message {id: 'msg:2', role: 'agent', content: 'Decline spike on payments-api. Path points to ledger lag from INC-318. Paging Maya.', at: $now, token_count: 28})
CREATE (m1)-[:IN_SESSION {seq: 1}]->(sess)
CREATE (m2)-[:IN_SESSION {seq: 2}]->(sess)
CREATE (m1)-[:SENT_BY]->(sam)
CREATE (m2)-[:SENT_BY]->(a_inv)
CREATE (sess)-[:REMEMBERS]->(ep_old)
CREATE (sess)-[:REMEMBERS]->(fact1)
"""


def clear_graph(tenant_id: str | None = None) -> None:
    query("MATCH (n) DETACH DELETE n", tenant_id=tenant_id)


def load_seed(tenant_id: str | None = None, *, reset: bool = True) -> str:
    tid = tenant_id or settings.tenant_id
    graph_name = f"{settings.graph_prefix}:{tid}"
    # Touch graph
    select_graph(tid)
    if reset:
        clear_graph(tid)
    ensure_indexes(tid)
    query(SEED_CYPHER, {"now": int(time.time())}, tenant_id=tid)
    return graph_name


def main() -> None:
    name = load_seed(reset=True)
    # Sanity counts
    nodes = query("MATCH (n) RETURN count(n)", readonly=True)[0][0]
    rels = query("MATCH ()-[r]->() RETURN count(r)", readonly=True)[0][0]
    domains = query(
        "MATCH (s:System) RETURN collect(DISTINCT s.domain)",
        readonly=True,
    )[0][0]
    print(f"Loaded SALUS graph `{name}` — {nodes} nodes, {rels} relationships")
    print(f"System domains: {domains}")


if __name__ == "__main__":
    main()
