---
name: spring-boot-testing
description: Testing in Spring Boot projects (Java, JUnit, Mockito, AssertJ, Testcontainers, Maven or Gradle). Use whenever a Spring Boot project is involved and the user wants tests written or added for any class, existing tests reviewed, a slow or flaky test suite diagnosed, or asks which test type to use (unit test, @WebMvcTest, @DataJpaTest, @SpringBootTest). Also for Spring context caching, Testcontainers setup, MockMvc, @MockitoBean, Surefire/Failsafe or Gradle test tasks. Trigger on a plain "add tests" or "write a test" in a Spring Boot project, even if the class under test is plain Java. Recipes are Java; the decision rules also apply to Kotlin projects.
---

# Spring Boot Testing

Use the cheapest test that answers the question, match the project's existing
conventions, and keep the number of distinct Spring contexts small.

## Mode

Decide which of the three jobs you are doing, then follow its workflow below:

- **Write**: add or extend tests for a class.
- **Review**: report what is wrong with existing tests. Findings only, no edits unless asked.
- **Speed**: make the suite faster. Measure before you propose anything.

## Facts before opinions

Read the build file first (`pom.xml` or `build.gradle(.kts)`) and note: Spring Boot
version, JUnit major version, Testcontainers major version, Surefire/Failsafe or
Gradle test tasks, existing base classes under `src/test`. Boot 3.5 and Boot 4
differ in annotations and starters; see the version table in `references/build-and-speed.md`.

Then open the test that is closest to what you are about to write or judge (same
package, same kind of class). Copy its naming pattern, structure, factories and
helpers exactly. If names are `shouldDoX` without a `When` part, do not add one.
Do not introduce `// Arrange` style comments or a `cut` variable unless the project
already uses them.

## The ladder

Stop at the first rung that can answer the question the test must answer:

| Rung | Answers | Tooling | Context |
| --- | --- | --- | --- |
| Unit | Does the logic in this class behave? | JUnit + Mockito + AssertJ, no `org.springframework` import | none |
| Slice | Does one Spring layer work: mapping, validation, JSON, security, JPA queries? | `@WebMvcTest(X.class)`, `@DataJpaTest`, `@JsonTest`, `@RestClientTest`, `@WebFluxTest` | one layer |
| Use-case slice | Does a service work against the real database inside one transaction? | `@DataJpaTest` + `@Import(UseCase.class, ...)` + Testcontainers | one layer plus imports |
| Integration | Do several real components work together over real HTTP or messaging? | `@SpringBootTest` + Testcontainers + WireMock | full |

Never default to `@SpringBootTest`. A class that only delegates to a collaborator
gets a Mockito test that verifies the delegation; if the collaborator's query is
already covered by its own slice test, say so instead of testing it twice.

Details per rung: `references/unit-tests.md`, `references/sliced-tests.md`.

## Style follows the project, test type does not

Naming, structure, factories, assertion style: copy the project, even if you would
do it differently. Test type and context hygiene: apply the ladder and the rules
below even when the project does not; say in one sentence why you deviate. New
tests never use JUnit 4 (`org.junit.Test`, `@RunWith`, `@Before`) even when old
ones do.

## Context cache rules

Spring caches started contexts per JVM (default 32, LRU). Every difference in the
cache key starts another context: `@ActiveProfiles`, `@TestPropertySource`,
`properties = ...` on the test annotation, the set of `@MockitoBean`/`@MockitoSpyBean`
fields, `@Import`, `@TestConfiguration`, `@DynamicPropertySource`,
`@ImportTestcontainers`, `@AutoConfigure*` and `@ContextConfiguration`.

1. One shared base class per test kind carries the slice or `@SpringBootTest`
   annotation, Testcontainers wiring and profile. Subclasses add nothing to it.
2. Use-case slices share an `@Import` set per feature, not one per test class.
3. `@DirtiesContext` only on a single test that corrupts state, never on a base class.
   Prefer cleaning up in `@AfterEach`.
4. Containers are `static` and shared, never one per test class.
5. `@WebMvcTest(X.class)` is one context per controller by design; different mock
   sets across different controllers are not a finding.

Mechanics, diagnosis and base-class recipes: `references/context-caching.md`.

## Workflow: Write

1. Name the class, the question the test answers, and the rung, in one sentence.
2. Find the nearest sibling test and reuse its conventions, factories and base class.
3. Write the test, run it (`./mvnw -q test -Dtest=Name` or `./gradlew test --tests Name`), report the result.
4. Ask only when the question itself is ambiguous (two classes with that name, a
   class that is both controller and service). Otherwise decide and state the reason.

## Workflow: Review

1. Measure before reading: if `target/surefire-reports` or `build/test-results` exist,
   list the slowest classes and the share of total time. Count distinct context
   configurations (`references/context-caching.md`, "Diagnosing").
2. Report findings in this order, each with file and line: wrong rung (too heavy),
   runtime hotspots with their cause, context breakers, assertions that cannot fail,
   mocking smells, JUnit 4 leftovers, missing edge cases.
3. Keep findings proportional to measured impact. A dozen extra contexts that cost
   30 seconds rank below one test class that costs three minutes.

## Workflow: Speed

1. Get numbers: per-class times from the test reports, context count from the cache
   log (`logging.level.org.springframework.test.context.cache=DEBUG`) or from counting
   distinct test configurations, container starts. Open the answer with these three
   numbers in one short table, whatever the proposals turn out to be.
2. Find the cause of the largest item first. Slow tests usually have one concrete
   reason (test data generation, a sleep, a real network call, a per-method container),
   not "Spring is slow".
3. Then, in order: fix the cause, separate slow or Docker-bound tests from the fast
   run (Failsafe `*IT` or Gradle test suite, see `references/build-and-speed.md`),
   reduce distinct contexts, enable local container reuse, and only then parallel forks.
4. Give every lever its measured share, including the ones you rule out: "33 contexts,
   about 15 s, not worth it yet" is a finding; "context caching is not the problem" is not.
   Name how the reader can re-measure (cache log, report timings) so the ranking can be checked.

## Mocking

- `@Mock` in unit tests, `@MockitoBean` in Spring tests. `@MockBean` only on Boot 3.3 and older.
- Do not mock value objects, records, entities or types you do not own.
- More `verify` than `assertThat` is a smell, unless the interaction is the behaviour (delegation, sending).
- Keep `MockitoExtension` strict; unused stubs are bugs.

## References

- `references/unit-tests.md`: Clock injection, Mockito template, boundaries, builders, smells
- `references/sliced-tests.md`: `@WebMvcTest`, `@DataJpaTest`, use-case slice, `@JsonTest`
- `references/context-caching.md`: cache key anatomy, diagnosis commands, base classes, Testcontainers, WireMock
- `references/build-and-speed.md`: Maven and Gradle split, parallel forks, PIT, Boot 3.5 vs 4 table
