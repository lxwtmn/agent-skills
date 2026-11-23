# Spring TestContext caching

## How it works

- `spring-test` keeps every started `ApplicationContext` in a static cache for the JVM.
- A test class reuses a context when its merged configuration produces the same key.
- Default size 32 with LRU eviction (`spring.test.context.cache.maxSize`). A suite with
  more distinct configurations than that evicts and restarts contexts.
- The cache lives per JVM: every Surefire/Failsafe fork or Gradle worker has its own.

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
   grep -rhE "^@(Import|MockitoBean|ActiveProfiles|TestPropertySource|DynamicPropertySource|ImportTestcontainers)" src/test | sort | uniq -c | sort -rn
   ```

2. Get the real number from a run with the cache logger on; the last statistics line
   has `missCount` = contexts started and shows whether `size` hit `maxSize`:

   ```bash
   ./mvnw test -Dlogging.level.org.springframework.test.context.cache=DEBUG > build.log 2>&1
   grep "cache statistics" build.log | tail -1
   ```

   On Boot projects `grep -c "Started .* in .* seconds" build.log` gives the same count,
   including slices.

3. Weigh it. Context starts cost roughly one to three seconds each with a database.
   Thirty contexts are a minute; if the suite takes six minutes, look for the other five first.

## Base class per test kind

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
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
| `TestRestTemplate` | yes | real filters, real serialization, real HTTP needed |
