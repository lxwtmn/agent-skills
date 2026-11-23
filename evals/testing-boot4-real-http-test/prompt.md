---
max_turns: 25
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Last week a servlet filter broke GET /api/customers/{id} in production and none of our tests noticed, because they all go through MockMvc. I want one test that hits that endpoint over real HTTP on a random port with TestRestTemplate: one case for an existing customer, one for an unknown id. Put it in src/test/java/com/acme/customers/CustomerApiIT.java and change whatever the build needs. You can't run the build here, so write it carefully.
