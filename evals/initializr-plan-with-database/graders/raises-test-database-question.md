---
type: llm
---

The requested project combines JPA with a PostgreSQL driver. A project generated that
way has a context-load test that fails out of the box, because nothing tells Spring Boot
where the database is, unless the project also gets Testcontainers (tests then need
Docker) or an embedded database.

PASS if the response raises this before generating: it tells the user that the
generated test will not run without a database, or asks whether to add Testcontainers
or an embedded database such as H2, or offers that choice in the plan.
FAIL if the plan lists the dependencies without mentioning the test or database
question at all, or silently adds Testcontainers or H2 without saying why and without
giving the user the choice.
