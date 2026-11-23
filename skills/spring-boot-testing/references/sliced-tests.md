# Sliced tests

A slice starts only the auto-configuration one layer needs. It answers what a unit
test cannot: does the mapping resolve, is validation enforced, is the JSON shaped
right, does security apply, does the query return the right rows.

On Spring Boot 4 every technology starter has its own test starter
(`spring-boot-starter-webmvc-test`, `spring-boot-starter-data-jpa-test`, ...) and the
slice annotations moved into those modules, so their imports differ from Boot 3.x.
On Boot 3.x `spring-boot-starter-test` covers all. Packages and starters side by
side: version table in `build-and-speed.md`. The examples below leave imports out;
take them from a neighbouring test in the project.

## `@WebMvcTest`

Loads controllers, `@ControllerAdvice`, filters, `WebMvcConfigurer`, converters,
Spring Security configuration and JSON. Does not load services, repositories or
plain components; mock them with `@MockitoBean`.

```java
@WebMvcTest(CustomerController.class)
class CustomerControllerTest {

    @Autowired
    private MockMvcTester mvc;

    @MockitoBean
    private GetCustomerUseCase getCustomerUseCase;

    @Test
    void shouldReturnNotFoundForUnknownCustomer() {
        when(getCustomerUseCase.execute(42L)).thenReturn(Optional.empty());

        assertThat(mvc.get().uri("/api/customers/42")).hasStatus(HttpStatus.NOT_FOUND);
    }

    @Test
    void shouldRejectEmptyBody() {
        assertThat(mvc.post().uri("/api/customers").contentType(MediaType.APPLICATION_JSON).content("{}"))
            .hasStatus(HttpStatus.BAD_REQUEST);
    }

    @Test
    void shouldReturnCustomerAsJson() {
        when(getCustomerUseCase.execute(1L)).thenReturn(Optional.of(new Customer(1L, "Ada")));

        assertThat(mvc.get().uri("/api/customers/1"))
            .hasStatusOk()
            .bodyJson().extractingPath("$.name").isEqualTo("Ada");
    }
}
```

`MockMvcTester` (AssertJ style) is available from Boot 3.4; older projects use
`MockMvc` with `perform(...).andExpect(...)`. Use whichever the project already uses.

Always name the controller class. A bare `@WebMvcTest` loads every controller and
needs every collaborator mocked. With Spring Security present the filter chain is
active: use `@WithMockUser` or `.with(jwt())` from `spring-security-test`, and
`@AutoConfigureMockMvc(addFilters = false)` only when security is deliberately out
of scope for that test.

Each `@WebMvcTest(X.class)` is its own context. That is fine; do not try to merge
controller tests across controllers to save contexts.

## `@DataJpaTest`

Loads JPA repositories, `TestEntityManager`, Flyway or Liquibase, and swaps in an
embedded database unless told otherwise. Each test runs in a transaction that is
rolled back.

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@ImportTestcontainers(SharedPostgres.class)
class CustomerRepositoryTest {

    @Autowired
    private CustomerRepository repository;

    @Autowired
    private TestEntityManager entityManager;

    @Test
    void shouldFindCustomersByEmailDomain() {
        entityManager.persist(new Customer("ada@example.org"));
        entityManager.persist(new Customer("bob@other.org"));
        entityManager.flush();

        assertThat(repository.findByEmailEndingWith("@example.org"))
            .extracting(Customer::getEmail)
            .containsExactly("ada@example.org");
    }
}
```

```java
public final class SharedPostgres {

    @ServiceConnection
    static final PostgreSQLContainer POSTGRES = new PostgreSQLContainer("postgres:<pinned tag>");
}
```

Use the real engine via Testcontainers when queries use vendor SQL, JSON columns or
when migrations must run. An embedded database is fine for pure JPQL. Pin the image
tag; never `latest`.

## Use-case slice

A service that must be tested with the real database (query semantics, constraints,
the interplay of several repositories) can be loaded into the JPA slice:

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@ImportTestcontainers(SharedPostgres.class)
@Import(OrderFeatureTestConfig.class)
class ReleaseOrdersUseCaseTest extends RepositoryTestSupport {
    ...
}
```

The `@Import` set is part of the context cache key. Define one import set per
feature (a small `@TestConfiguration` or a constant list) and reuse it across that
feature's tests. Thirty test classes with thirty different `@Import` lists are
thirty contexts.

Properties on the annotation (`@DataJpaTest(properties = ...)`) also split the
cache. Put shared properties in the test profile instead.

What this rung cannot answer: `@DataJpaTest` wraps every test in a transaction that
is rolled back, and a service with default propagation joins it instead of opening
its own. So the test never commits, the service's own `@Transactional` boundaries
are not exercised, and lazy loading works where it would fail in production. Flush
before asserting on constraints or generated values, otherwise the SQL may never
run. If the question is about commit behaviour, rollback rules or what happens
outside a transaction, go one rung up to an integration test, or switch the test
transaction off with `@Transactional(propagation = Propagation.NOT_SUPPORTED)` and
clean up the data yourself.

## `@JsonTest`

```java
@JsonTest
class OrderDtoJsonTest {

    @Autowired
    private JacksonTester<OrderDto> json;

    @Test
    void shouldSerializeDateAsIsoString() throws Exception {
        var dto = new OrderDto(LocalDate.of(2026, 10, 21));

        assertThat(json.write(dto)).extractingJsonPathStringValue("$.placedOn").isEqualTo("2026-10-21");
    }
}
```

## Other slices

- `@WebFluxTest(X.class)` with `WebTestClient` for reactive controllers.
- `@RestClientTest(X.class)` with `MockRestServiceServer` for `RestClient`/`RestTemplate` clients; no WireMock needed.
- `@DataJdbcTest`, `@JdbcTest`, `@DataMongoTest`, `@DataRedisTest` for other data layers.
