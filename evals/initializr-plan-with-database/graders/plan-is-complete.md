---
type: llm
---

PASS if the response is a plan to confirm, not a finished project, and states all of:
build tool Maven, language, a concrete Spring Boot version number, a concrete Java
version number, group `com.acme`, artifact `order-service`, and a dependency list.
FAIL if any of those is missing or left as a placeholder such as "latest" or
"current LTS" without a number, or if the response claims the project was generated.
