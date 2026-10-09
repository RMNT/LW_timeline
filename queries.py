PREFIXES = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX : <http://purl.org/wittgensteinsource/ont/>
"""
 
# Exact dates: the :created triple is always a plain xsd:date.
exact_ms = PREFIXES + """
SELECT DISTINCT ?remark ?ms_label ?created ?link
WHERE {
  ?remark :created ?created ;
          :hasHtmlView ?link .
  OPTIONAL { ?remark rdfs:label ?ms_label }
}
"""
 
# Estimated dates: the two bounds differ (when they are equal the entry is
# exact, and it already has :created).
range_ms = PREFIXES + """
SELECT DISTINCT ?remark ?ms_label ?madeAfter ?madeBefore ?link
WHERE {
  ?remark :madeAfter ?madeAfter ;
          :madeBefore ?madeBefore ;
          :hasHtmlView ?link .
  FILTER(?madeAfter != ?madeBefore)
  OPTIONAL { ?remark rdfs:label ?ms_label }
}
"""
