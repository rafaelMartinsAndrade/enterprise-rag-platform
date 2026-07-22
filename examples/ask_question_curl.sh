curl -X POST "http://localhost:8000/api/v1/chat/ask" \
  -H "Authorization: Bearer change-me" \
  -H "X-Organization-Slug: acme-erp" \
  -H "X-User-Email: ana@acme.demo" \
  -H "Content-Type: application/json" \
  -d @examples/ask_question_request.json
