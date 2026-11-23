# Unit tests without Spring

A unit test imports nothing from `org.springframework`. If it needs to, it is not a
unit test; move one rung up.

## Mockito template

```java
@ExtendWith(MockitoExtension.class)
class ReleaseOrderUseCaseTest {

    @Mock
    private OrderRepository orderRepository;

    @Mock
    private PaymentGateway paymentGateway;

    @InjectMocks
    private ReleaseOrderUseCase useCase;

    @Test
    void shouldRejectOrderWhenPaymentFails() {
        var order = anOrder().withTotal(new BigDecimal("42.00")).build();
        when(paymentGateway.charge(order)).thenReturn(PaymentResult.failed("insufficient funds"));

        var result = useCase.execute(order);

        assertThat(result.status()).isEqualTo(OrderStatus.REJECTED);
        assertThat(result.reason()).contains("insufficient funds");
    }
}
```

Blank lines separate arrange, act and assert; no comments needed. Name the instance
the way the project does (`useCase`, `service`, `cut`); do not invent a new convention.
`MockitoExtension` is strict: unused stubs fail the test. Keep it that way.

## Delegation-only classes

A class whose method only forwards to a collaborator gets a test that verifies the
exact forwarded arguments and nothing else:

```java
@Test
void shouldUpdateValidToOfSelectedAssignments() {
    useCase.execute(documentId, new UpdateValidityRequest(customerIds, validTo));

    verify(assignmentRepository).updateValidTo(documentId, customerIds, validTo);
    verifyNoMoreInteractions(assignmentRepository);
}
```

Here `verify` is the assertion, because the interaction is the behaviour. Check
whether the collaborator's own query is already covered by a slice test before
adding a database-backed test for the delegating class.

## Clock injection

`LocalDate.now()`, `Instant.now()`, `UUID.randomUUID()` and `new Random()` inside
production code make tests time- or luck-dependent. Inject the source instead.

```java
@Component
public class BirthdayService {

    private final Clock clock;

    public BirthdayService(Clock clock) {
        this.clock = clock;
    }

    public boolean isTodayBirthday(LocalDate birthday) {
        var today = LocalDate.now(clock);
        return today.getMonth() == birthday.getMonth() && today.getDayOfMonth() == birthday.getDayOfMonth();
    }
}
```

```java
@Configuration
class TimeConfig {

    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
```

```java
@Test
void shouldDetectBirthdayToday() {
    var zone = ZoneId.of("Europe/Berlin");
    var clock = Clock.fixed(LocalDate.of(2026, 5, 15).atStartOfDay(zone).toInstant(), zone);
    var service = new BirthdayService(clock);

    assertThat(service.isTodayBirthday(LocalDate.of(1990, 5, 15))).isTrue();
}
```

Same pattern for ids (`Supplier<UUID>`) and randomness (`Random` or `RandomGenerator`).
When reviewing, list every `now()` call in `src/main` as one finding with a count, not
one finding per call.

## Boundaries

Boundaries are where mutants survive. Cover each edge of a comparison explicitly:

```java
@ParameterizedTest
@CsvSource({
    "999,  true,  0",
    "1000, true,  0",
    "1001, true,  100",
    "1001, false, 0"
})
void shouldApplyDiscountOnlyAboveThresholdForLoyalCustomers(int amount, boolean loyal, int expected) {
    assertThat(service.calculateDiscount(amount, loyal)).isEqualTo(expected);
}
```

## Test data

Never mock records, DTOs or entities. Reuse the project's factories (`*TestFactory`,
`*Builder`, `*Mother`) before writing new ones. If none exists, add a small builder
in the test source tree next to its first user.

## Smells to flag

- `@SpringBootTest` or any slice on a class that tests one service's logic.
- `now()` or `randomUUID()` in the class under test.
- `@Mock` on a record, DTO or entity.
- `verifyNoMoreInteractions` on every mock in a controller test (brittle, asserts nothing about the response).
- Assertions that pass whatever the result (`isNotNull()` on a value the code always returns).
- `any(LocalDate.class)` where the exact date is the behaviour under test.
- `Thread.sleep` instead of Awaitility.
- JUnit 4 imports (`org.junit.Test`, `@RunWith`, `@Before`, `@Rule`); they are silently ignored by the Jupiter engine.
