# Spring TestContext caching

## How it works

- `spring-test` keeps every started `ApplicationContext` in a static cache for the JVM.
- A test class reuses a context when its merged configuration produces the same key.
- Default size 32 with LRU eviction (`spring.test.context.cache.maxSize`). A suite with
  more distinct configurations than that evicts and restarts contexts.
- The cache lives per JVM: every Surefire/Failsafe fork or Gradle worker has its own.
- From Spring Framework 7 (Boot 4) a cached context that is not in use is paused:
  its `Lifecycle` beans (listeners, schedulers) are stopped and restarted when a test
  needs the context again. Background work of one context no longer disturbs tests
  of another, but every switch between contexts costs a restart of those beans.
  `spring.test.context.cache.pause=never` turns it off.

## What is in the key

| Mechanism | Examples |
| --- | --- |
| Profiles | `@ActiveProfiles` |
| Properties | `@TestPropertySource`, `@SpringBootTest(properties = ...)`, `@DataJpaTest(properties = ...)` |
| Configuration classes | `@Import`, nested `@TestConfiguration`, `@ContextConfiguration(classes = ...)`, `@SpringBootTest(classes = ...)` |
| Bean overrides | the full set of `@MockitoBean`, `@MockitoSpyBean`, `@TestBean` fields, including inherited ones |
| Customizers | `@DynamicPropertySource`, `@ImportTestcontainers`, `webEnvironment`, every `@AutoConfigure*` annotation |
| Initializers | `@ContextConfiguration(initializers = ...)` |

The set counts as a whole: `{A, B}` and `{A, B, C}` are two contexts. A base class
with `@MockitoBean` fields plus a subclass adding one more is a new context per subclass.

## Diagnosing

1. Count distinct configurations statically:

   ```bash
   grep -rlE "@(SpringBootTest|WebMvcTest|DataJpaTest|JsonTest|WebFluxTest|RestClientTest)" src/test | wc -l
   grep -rhoE "^\s*@(Import|MockitoBean|MockitoSpyBean|ActiveProfiles|TestPropertySource|DynamicPropertySource|ImportTestcontainers)\b.*" src/test | sed 's/^ *//' | sort | uniq -c | sort -rn
   ```

   The first number is test classes that start a context at all, not distinct
   contexts. The second lists the annotations that split the cache, with their
   arguments, so identical lines are candidates for sharing and one-off lines are
   candidates for an extra context. `\s*` matters: `@MockitoBean` and
   `@DynamicPropertySource` sit on indented fields and methods.

2. Get the real number from a run with the cache logger on; the last statistics line
   has `missCount` = contexts started and shows whether `size` hit `maxSize`.

   Maven forwards `-D` properties from the command line into the test JVM:

   ```bash
   ./mvnw test -Dlogging.level.org.springframework.test.context.cache=DEBUG > build.log 2>&1
   grep "cache statistics" build.log | tail -1
   ```

   Gradle does not; a `-D` on `./gradlew` only reaches the build JVM. Add the
   property to the test tasks for the measurement and take it out again afterwards.
   The output lands in the XML reports, not on the console:

   ```kotlin
   tasks.withType<Test> {
       systemProperty("logging.level.org.springframework.test.context.cache", "DEBUG")
   }
   ```

   ```bash
   ./gradlew cleanTest test
   grep -rhoE "cache statistics: .*" build/test-results | tail -1
   ```

   With several forks or workers there is one cache per JVM; add up `missCount`
   across them.

3. Measure what the starts cost instead of estimating. Boot logs one "Started ... in
   N seconds" line per context it starts, slices included:

   ```bash
   grep -ohE "Started .* in [0-9.]+ seconds" build.log | awk '{s += $(NF-1)} END {print NR " context starts, " s " s"}'
   ```

   For Gradle run the same `grep` with `-r` over `build/test-results` instead of
   `build.log`. Put that sum next to the suite's total runtime. If context starts are
   one minute of a six-minute suite, look for the other five first.

## Base class per test kind

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureTestRestTemplate
@ActiveProfiles("integration-test")
@ImportTestcontainers(SharedContainers.class)
public abstract class AbstractIntegrationTest {

    @RegisterExtension
    static WireMockExtension paymentApi = WireMockExtension.newInstance()
        .options(wireMockConfig().dynamicPort())
        .build();

    @DynamicPropertySource
    static void overrideProperties(DynamicPropertyRegistry registry) {
        registry.add("payment.api.base-url", paymentApi::baseUrl);
    }

    @Autowired
    protected TestRestTemplate restTemplate;

    @AfterEach
    void resetStubs() {
        paymentApi.resetAll();
    }
}
```

```java
public final class SharedContainers {

    @ServiceConnection
    static final PostgreSQLContainer POSTGRES = new PostgreSQLContainer("postgres:<pinned tag>");

    @ServiceConnection
    static final GenericContainer REDIS = new GenericContainer("redis:<pinned tag>").withExposedPorts(6379);
}
```

This is the Boot 4 form. There `@SpringBootTest` no longer provides a
`TestRestTemplate` by itself: the test needs `@AutoConfigureTestRestTemplate` and
the `spring-boot-resttestclient` test dependency (plus `spring-boot-restclient`),
and the class lives in `org.springframework.boot.resttestclient`. On Boot 3.x drop
the annotation; `TestRestTemplate` is available as soon as a real port is used.

Rules for subclasses: add no `@SpringBootTest`, profile, property, `@MockitoBean`
or `@Import`. If one test truly needs a mock, either move it into the base class or
accept one extra context and say so in the class.

`@DirtiesContext` throws the context away and restarts it for the next class. Use
it on at most one test that genuinely corrupts shared state, never on a base class.
Prefer explicit cleanup in `@AfterEach` (`deleteAllInBatch`, cache clear, WireMock reset).

## Testcontainers

- A container in a `static` field of a class referenced via `@ImportTestcontainers`,
  or a `static @Container` field in the base class, starts once per JVM. A second
  class with its own `@Container` starts a second database; look for stray
  `@Testcontainers`/`@Container` next to the shared one.
- `@ServiceConnection` wires datasource, Redis, Kafka, RabbitMQ, Mongo and more without
  `@DynamicPropertySource`.
- Testcontainers 2.x renamed modules and packages (for example
  `org.testcontainers.postgresql.PostgreSQLContainer`); check the project's imports
  before copying a 1.x snippet.
- Local reuse across JVM runs: `testcontainers.reuse.enable=true` in
  `~/.testcontainers.properties` plus `.withReuse(true)`. Keep it off in CI.
- Spring Boot's Docker Compose support is for running the app locally, not for tests.

## External HTTP

- WireMock (`org.wiremock:wiremock` or `org.wiremock.integrations:wiremock-spring-boot`)
  or MockServer for third-party APIs. Never call the real service from a test.
- Stub per test in the arrange part; verify requests only when the outgoing call is the behaviour.
- A client class tested on its own gets `@RestClientTest` + `MockRestServiceServer` instead.

## Hitting endpoints

| Tool | Real server | Use when |
| --- | --- | --- |
| `MockMvcTester` / `MockMvc` | no | default; fastest; servlet semantics simulated |
| `WebTestClient` | either | reactive apps, or `RANDOM_PORT` with fluent assertions |
| `TestRestTemplate` | yes | real filters, real serialization, real HTTP needed; on Boot 4 needs `@AutoConfigureTestRestTemplate` |
| `RestTestClient` (Boot 4) | either | new code on Boot 4 that wants one fluent client for mock and real server; enable with `@AutoConfigureRestTestClient` |

`MockMvc` and `MockMvcTester` inside a `@SpringBootTest` need `@AutoConfigureMockMvc`;
`@WebMvcTest` brings them along.
