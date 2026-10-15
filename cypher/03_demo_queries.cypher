# SALUS demo queries — graph salus:acme

# Blast radius (any industry system)
MATCH (s:System {name: 'payments-api'})-[:DEPENDS_ON*1..3]->(dep:System)
RETURN s.name, s.domain, dep.name, dep.domain

# Cross-industry: HVAC loss impacts EHR
MATCH (h:System {name: 'hvac-wing-b'})<-[:DEPENDS_ON*1..3]-(up:System)
RETURN h.name, up.name, up.domain, up.criticality

# Who knows / owns
MATCH (s:System {name: 'badge-controller'})
OPTIONAL MATCH (o:Person)-[:OWNS]->(s)
OPTIONAL MATCH (e:Person)-[:KNOWS]->(sk:Skill {domain: s.domain})
RETURN s.name, collect(DISTINCT o.name), collect(DISTINCT e.name)

# Memory
MATCH (ep:Episode)-[:ABOUT_ENTITY]->(s:System {name: 'payments-api'})
RETURN ep.summary, ep.importance ORDER BY ep.at DESC

# Domains present
MATCH (s:System) RETURN s.domain AS domain, collect(s.name) AS systems
