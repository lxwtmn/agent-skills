---
type: regex
target: { source: file, path: src/test/java/com/acme/docs/assignment/UpdateValidityUseCaseTest.java }
pattern: '@SpringBootTest|@DataJpaTest|AbstractIntegrationTest|@MockitoBean|import org\.springframework'
match: not_contains
---
