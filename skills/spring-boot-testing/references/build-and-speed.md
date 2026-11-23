# Build setup and speed

## Version table

Check the build file; do not assume.

| Topic | Spring Boot 3.x (3.4+) | Spring Boot 4.x |
| --- | --- | --- |
| Test starter | `spring-boot-starter-test` covers all slices | one starter per slice: `spring-boot-starter-webmvc-test`, `spring-boot-starter-data-jpa-test`, ... |
| Bean mocking | `@MockitoBean` (3.4+), `@MockBean` deprecated | `@MockitoBean` only |
| MockMvc | `MockMvc`; `MockMvcTester` from 3.4 | both, `MockMvcTester` preferred |
| JSON | Jackson 2 (`com.fasterxml.jackson`) | Jackson 3 (`tools.jackson`) |
| JUnit | Jupiter 5 | Jupiter 6 (same annotations) |
| Testcontainers | 1.x (`org.testcontainers:postgresql`) | 2.x (`org.testcontainers:testcontainers-postgresql`, new packages) |

Never write a version number into a test or build file from memory. Take the
current one from the parent BOM or Maven Central.

## Separating fast and slow tests

The goal: `./mvnw test` or `./gradlew test` runs without Docker in well under a
minute, and the full run happens in `verify`/`check` or a dedicated task.

### Maven

Surefire runs `*Test` in `test`, Failsafe runs `*IT` in `integration-test`. Rename
Docker-bound classes to `*IT`, or keep names and select by `@Tag`:

```xml
<plugin>
  <groupId>org.apache.maven.plugins</groupId>
  <artifactId>maven-surefire-plugin</artifactId>
  <configuration>
    <excludedGroups>integration</excludedGroups>
  </configuration>
</plugin>
<plugin>
  <groupId>org.apache.maven.plugins</groupId>
  <artifactId>maven-failsafe-plugin</artifactId>
  <configuration>
    <groups>integration</groups>
    <includes><include>**/*Test.java</include><include>**/*IT.java</include></includes>
  </configuration>
  <executions>
    <execution>
      <goals><goal>integration-test</goal><goal>verify</goal></goals>
    </execution>
  </executions>
</plugin>
```

### Gradle

Preferred: a separate test suite with its own source set and task.

```kotlin
testing {
    suites {
        val integrationTest by registering(JvmTestSuite::class) {
            dependencies {
                implementation(project())
            }
            targets.all {
                testTask.configure { shouldRunAfter(tasks.test) }
            }
        }
    }
}
tasks.check { dependsOn(testing.suites.named("integrationTest")) }
```

Tests go to `src/integrationTest/java`. If the project already uses the Maven
`*IT` naming inside `src/test`, filter instead:

```kotlin
tasks.test { filter { excludeTestsMatching("*IT") } }
val integrationTest by tasks.registering(Test::class) {
    testClassesDirs = sourceSets.test.get().output.classesDirs
    classpath = sourceSets.test.get().runtimeClasspath
    filter { includeTestsMatching("*IT") }
}
```

Tag-based selection (`useJUnitPlatform { excludeTags("integration") }`) works but
relies on nobody forgetting the tag.

## Order of speed levers

1. Measure: per-class times from `target/surefire-reports/*.xml` or
   `build/test-results/test/*.xml`, context count from the cache log, container starts.
2. Fix the cause of the biggest item. Typical: test data generation that scales
   badly, `Thread.sleep`, real network, a container per class, a migration test that
   starts its own database.
3. Separate Docker-bound and slow tests from the default run (above).
4. Reduce distinct contexts (`context-caching.md`).
5. Local container reuse.
6. Parallelism, only after 1 to 5, and only with the checklist below.

## Parallelism checklist

- No static mutable state shared between test classes.
- No fixed ports; `RANDOM_PORT` and `dynamicPort()` everywhere.
- Each JVM fork gets its own containers automatically; threads inside one JVM share them,
  so data isolation per test is required (unique ids, cleanup, or rollback).
- No ordering assumptions between tests.

Maven: `forkCount` and `reuseForks` on Surefire or Failsafe. Gradle: `maxParallelForks`
on the test task. Same-JVM threads: `junit.jupiter.execution.parallel.enabled=true`
in `junit-platform.properties` with `mode.default` and `mode.classes.default` set
to `concurrent`.

## Mutation testing

PIT (`org.pitest:pitest-maven` with `pitest-junit5-plugin`, or the Gradle plugin)
tells whether the assertions can fail. Run it on unit tests only; slices and
integration tests are too slow to mutate. In large projects restrict to changed code
(`pitest-git-plugin`, or `targetClasses` on the feature package). A surviving mutant on
a boundary means a missing boundary case, not a missing test class.
