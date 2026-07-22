curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer change-me" \
  -H "X-Organization-Slug: acme-erp" \
  -H "X-User-Email: ana@acme.demo" \
  -F "title=Closing Policy" \
  -F "tags=finance,policy" \
  -F "file=@demo_data/documents/acme-erp/closing_policy.md;type=text/markdown"
