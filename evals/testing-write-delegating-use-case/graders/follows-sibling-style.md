---
type: llm
focus: { source: file, path: src/test/java/com/acme/docs/assignment/UpdateValidityUseCaseTest.java }
---

The project's existing unit test for a sibling class looks like this: JUnit 5 with
`@ExtendWith(MockitoExtension.class)`, a `@Mock AssignmentRepository assignmentRepository`
field, the instance under test in an `@InjectMocks` field named `useCase`, test method
names of the form `shouldDoSomething` without a `When...` suffix convention, blank lines
instead of comments between setup, call and assertion, and AssertJ for assertions.

PASS if the file follows those conventions: Mockito extension, the instance under test
named `useCase`, every test method name starting with `should`, and no `// Arrange`,
`// Act`, `// Assert`, `// given`, `// when` or `// then` comments.
FAIL if it introduces a different convention on any of those points (for example a
variable named `cut` or `sut`, `test...` or `given_when_then` method names, or
arrange/act/assert comments), or if the file is missing.
