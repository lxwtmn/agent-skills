---
name: spring-boot-initializr
description: Create and scaffold a new Spring Boot project using the Spring Initializr service (start.spring.io). Use this whenever the user wants to start, generate, bootstrap, or set up a new Spring Boot application or Spring project -- including picking the build tool (Maven/Gradle), language (Java/Kotlin/Groovy), Spring Boot version, Java version, and dependencies such as Spring Web, Spring Data JPA, PostgreSQL, or Security. Trigger this even when the user only says something like "I need a new Spring Boot app with web and a database", references start.spring.io or "Spring Initializr", or asks to create a Spring service -- even if they do not name this skill explicitly. The skill guides the user interactively through the options, downloads and extracts the project, initializes a git repository, and verifies that it builds.
---

# Spring Boot Project Setup (Spring Initializr)

This skill scaffolds a brand-new Spring Boot project by talking to the Spring
Initializr HTTP API (the same engine behind https://start.spring.io and the
"New Spring Boot project" wizard in IntelliJ, STS, and VS Code). It then extracts
the project, sets up version control, and confirms the project actually builds so
the user starts from a known-good state.

The skill is **interactive by design**: rather than silently guessing, walk the
user through the meaningful choices the way the Initializr web form would, always
offering a sensible default they can accept with one word. The goal is a guided,
low-friction experience -- not an interrogation. Honor anything the user already
told you and only ask about what's genuinely undecided.

## Defaults at a glance

When the user expresses no preference on a given point, lean on these, but surface
them so the choice is visible rather than hidden:

- **Build tool:** Maven. This is the skill's own choice; the service marks a
  Gradle type as its default, so do not take this one from the `versions` output.
- **Language:** Java
- **Spring Boot version:** the service's current default (latest stable)
- **Java version:** the major version of the JDK installed on this machine, if the
  service offers it; otherwise the highest offered version below it. The service's
  own default is often an older LTS than the one installed, and a project generated
  for a newer Java than the local JDK will not build. With no JDK installed, fall
  back to the service default and say that the build cannot be verified here.
- **Packaging:** Jar

Never hardcode version numbers from memory -- Spring ships new releases constantly
(and drops end-of-life ones). Always read the current options live in step 2.

---

## Workflow

### 1. Start from what the user already said

Read their request first and extract every decision they've already made: project
name, group/package, build tool, language, Java version, and any capabilities they
described ("REST API", "Postgres", "security", "messaging"). Those are settled --
don't re-ask them. You'll only elicit the remaining gaps in step 3.

### 2. Fetch the live options

Run the bundled metadata helper (in this skill's `scripts/` directory) so you're
presenting real, current choices rather than stale ones:

```bash
python3 scripts/query_initializr.py versions
```

(Paths shown for the helper are relative to this skill's directory -- substitute
its actual location, e.g. `python3 <skill_dir>/scripts/query_initializr.py`, if
your working directory is the user's project rather than the skill folder.)

This prints the available build tools, languages, Spring Boot versions, Java
versions, and packaging, with the service's default marked. Use its output as the
source of truth for what you offer. Recommend the defaults from "Defaults at a
glance": the service's marker decides the Spring Boot version, but not the build
tool or the Java version.

Check the local JDK in the same step, because it decides which Java version you can
recommend and whether the build in step 7 can run at all:

```bash
java -version
```

### 3. Walk the user through the choices

Ask about the undecided points, presenting the live options and highlighting the
recommended default so the user can simply accept. If you have an interactive
selection UI available (tappable options, a form, etc.), prefer it; otherwise ask
in plain language. Group related questions so this takes a couple of exchanges, not
a dozen. A natural order:

1. **Build tool & language** -- default Maven + Java. (Gradle offers Groovy or
   Kotlin DSL, which maps to the `gradle-project` vs `gradle-project-kotlin` type.)
2. **Spring Boot version & Java version** -- default to the service's Boot default
   and the Java version that matches the installed JDK; only dig in if the user has
   a constraint (e.g. "we're stuck on Java 17"). If they ask for a Java version
   newer than the installed JDK, say that the project will generate but not build
   on this machine.
3. **Project coordinates** -- `groupId` (e.g. `com.example`), `artifactId` (the
   project/folder name, e.g. `order-service`), display `name`, `description`,
   `packageName`, and `packaging` (jar/war). Derive sensible defaults: `name` from
   `artifactId`, `packageName` from `groupId` + sanitized `artifactId`. Let the user
   override any of them.
4. **Dependencies** -- see "Choosing dependencies" below. This is usually where the
   user needs the most help, so invest here.

### 4. Confirm the plan

Before generating, echo back a short, readable summary of every setting and the
final dependency ID list, and get a clear go-ahead. This catches
misunderstandings while they're still free to fix (a typo'd package or a missing
driver is annoying to change afterward). Downloading the project is the first
side-effecting step, so confirmation belongs here.

### 5. Generate and extract the project

Pick a target location (default: a new folder named after `artifactId` in the
current directory; confirm if the user cares where it lands). Setting
`baseDir=<artifactId>` makes the archive self-contained under that one folder, so
extraction never litters the current directory.

If a folder with that name already exists, stop and ask where the project should
go. `unzip` would prompt about replacing files and hang in a non-interactive shell,
and merging a fresh scaffold into existing code is rarely what the user wants.

```bash
curl -fSL https://start.spring.io/starter.zip \
  --data-urlencode "type=maven-project" \
  --data-urlencode "language=java" \
  --data-urlencode "bootVersion=<BOOT_VERSION>" \
  --data-urlencode "javaVersion=<JAVA_VERSION>" \
  --data-urlencode "packaging=jar" \
  --data-urlencode "groupId=<GROUP_ID>" \
  --data-urlencode "artifactId=<ARTIFACT_ID>" \
  --data-urlencode "name=<NAME>" \
  --data-urlencode "description=<DESCRIPTION>" \
  --data-urlencode "packageName=<PACKAGE_NAME>" \
  --data-urlencode "dependencies=<DEP1,DEP2,...>" \
  --data-urlencode "baseDir=<ARTIFACT_ID>" \
  -o <ARTIFACT_ID>.zip

unzip -q <ARTIFACT_ID>.zip && rm <ARTIFACT_ID>.zip
cd <ARTIFACT_ID>
```

Why these flags: `--data-urlencode` safely encodes values that contain spaces or
special characters (the `description` in particular), and `-f` makes curl fail
loudly on an HTTP error instead of silently saving an error page as a ".zip". If a
dependency ID is wrong or incompatible with the Boot version, the API returns 400
with an explanation -- read it and correct the request rather than retrying it
unchanged. Other parameters and endpoints: `references/api.md`.

`unzip` not available? Ask for `starter.tgz` instead and extract with tar:

```bash
curl -fSL https://start.spring.io/starter.tgz --data-urlencode "..." -o <ARTIFACT_ID>.tgz
tar -xzf <ARTIFACT_ID>.tgz && rm <ARTIFACT_ID>.tgz
```

### 6. Initialize git

First check whether the new folder already sits inside a repository (a monorepo, or
a workspace the user has under version control):

```bash
git rev-parse --is-inside-work-tree 2>/dev/null
```

If that prints `true`, do not run `git init`: it would create a nested repository
that the outer one cannot track properly. Leave the files uncommitted, tell the
user, and commit into the surrounding repository only if they ask for it.

Otherwise initialize a fresh repository. The generated project already includes a
suitable `.gitignore`, so a first commit is clean:

```bash
git init -q
git add -A
git commit -q -m "Initial commit from Spring Initializr"
```

### 7. Verify the build

A quick build proves the scaffold is coherent and the toolchain is set up before the
user writes any code. Which command proves that depends on the dependencies, because
the generated `@SpringBootTest` context-load test starts the whole application:

- **Self-contained set** (nothing external, or an embedded database such as `h2`):
  run the tests.
- **`testcontainers` selected:** the generated test imports a
  `TestcontainersConfiguration` and starts real containers, so it needs a running
  Docker daemon. Check with `docker info`. With Docker, run the tests; without it,
  compile only.
- **JDBC-based data access** (`data-jpa`, `data-jdbc`, `jdbc`, `flyway`,
  `liquibase`) **with only an external driver** (`postgresql`, `mysql`, ...) and
  neither `testcontainers` nor an embedded database: the context test fails with
  "Failed to configure a DataSource: 'url' attribute is not specified", because
  nothing tells Boot where the database is. That is expected, not a broken
  scaffold, so compile only.

Make the wrapper executable first (exec bits aren't always preserved through
zipping).

Maven:
```bash
chmod +x mvnw
./mvnw -B -ntp test            # run the tests
./mvnw -B -ntp test-compile    # compile only
```

Gradle:
```bash
chmod +x gradlew
./gradlew test                 # run the tests
./gradlew testClasses          # compile only
```

On Windows use `mvnw.cmd` / `gradlew.bat`. The first run downloads dependencies, so
it can take a minute or two -- that's expected, not a hang. Building needs a JDK at
least as new as the selected `javaVersion` (checked in step 2) plus network access
to Maven Central / the Gradle Plugin Portal.

Say which of the two you ran. "Compiles; the context test was not run because it
needs a database" is a correct result. "Build verified" after a compile-only run is
not. If something fails unexpectedly, see `references/troubleshooting.md`.

### 8. Report and hand off

Summarize what was created: the location, the key settings, the dependencies, and
the build result. Point out the entry points a Spring dev expects -- the
`...Application.java` (or `.kt`) main class, `src/main/resources/application.properties`
(or `.yml`), and how to run it (`./mvnw spring-boot:run` or `./gradlew bootRun`). Keep
it brief; they can explore from there.

---

## Choosing dependencies

Users rarely know the exact Initializr dependency IDs, and the IDs aren't always
obvious (`postgresql`, not `postgres`; `data-jpa`, not `jpa`; `web`, not `spring-web`).
Bridge the gap with the helper script instead of guessing:

- Turn a plain-language need into candidate IDs:
  ```bash
  python3 scripts/query_initializr.py search postgres
  python3 scripts/query_initializr.py search security
  ```
- Browse a category when the user is unsure:
  ```bash
  python3 scripts/query_initializr.py deps SQL
  ```
- Validate the final set before generating. This catches typos and suggests near
  matches, checks every dependency against the Boot version's compatibility range,
  and exits non-zero if anything is wrong. Pass `--boot-version` whenever the user
  chose something other than the service default; without it the check runs
  against the default:
  ```bash
  python3 scripts/query_initializr.py validate web,data-jpa,postgresql
  python3 scripts/query_initializr.py validate web,data-jpa,postgresql --boot-version <BOOT_VERSION>
  ```
  If a dependency is incompatible, tell the user which Boot versions it supports
  and let them choose between another Boot version and dropping the dependency.

When the set contains JDBC-based data access plus a real database driver, raise the
test question now instead of discovering it in step 7: the generated context test
only runs if the project also has `testcontainers` (tests then need Docker) or an
embedded database such as `h2`. Offer both and the option of neither; do not add a
dependency the user did not agree to.

Confirm the resolved list with the user in the step-4 summary. When a user asks for
something common, these are the usual IDs (still validate them, since availability
and compatibility ranges shift by Boot version): `web` (Spring MVC), `webflux`
(reactive), `data-jpa`, `data-jdbc`, `jdbc`, `postgresql`, `mysql`, `h2`, `flyway`,
`liquibase`, `data-mongodb`, `data-redis`, `security`, `oauth2-client`, `validation`,
`actuator`, `lombok`, `devtools`, `configuration-processor`, `testcontainers`,
`graphql`, `kafka`, `amqp`, `thymeleaf`, `mustache`.

---

## Custom / enterprise Initializr instances

Some organizations run their own Initializr with a curated dependency catalog. Ask
the user whether they have a company instance if the context suggests it (internal
starters, private dependencies). If so, pass `--base-url https://start.mycompany.com`
to the helper script and swap the host in the `curl` command.

## References

- `references/api.md`: endpoints, every request parameter, error responses, details
  on custom instances. Read it when you need something the standard `curl` call
  does not show.
- `references/troubleshooting.md`: restricted networks and offline environments,
  plus a symptom list (HTTP 400, broken zip, Java version errors, DataSource and
  Docker failures). Read it as soon as generation or the build fails, before
  retrying anything.

---

## Non-interactive shortcut

If the user front-loads everything ("Maven, Java 21, Spring Boot latest, group
com.acme, artifact orders, deps web + data-jpa + postgresql"), don't march them
back through the questions. Validate the dependencies, show the one-line summary for
a quick confirm, then generate. Interactive means *helpful and guided*, not
*needlessly repetitive*.
