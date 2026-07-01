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

- **Build tool:** Maven
- **Language:** Java
- **Spring Boot version:** the service's current default (latest stable)
- **Java version:** the current LTS the service defaults to
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
source of truth for what you offer and for the default you recommend.

### 3. Walk the user through the choices

Ask about the undecided points, presenting the live options and highlighting the
recommended default so the user can simply accept. If you have an interactive
selection UI available (tappable options, a form, etc.), prefer it; otherwise ask
in plain language. Group related questions so this takes a couple of exchanges, not
a dozen. A natural order:

1. **Build tool & language** -- default Maven + Java. (Gradle offers Groovy or
   Kotlin DSL, which maps to the `gradle-project` vs `gradle-project-kotlin` type.)
2. **Spring Boot version & Java version** -- default to the service's defaults; only
   dig in if the user has a constraint (e.g. "we're stuck on Java 17").
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
dependency ID is wrong, the API returns 400 with an explanation -- read it and
correct the ID rather than shipping a broken request.

`unzip` not available? Ask for `starter.tgz` instead and extract with tar:

```bash
curl -fSL https://start.spring.io/starter.tgz --data-urlencode "..." -o <ARTIFACT_ID>.tgz
tar -xzf <ARTIFACT_ID>.tgz && rm <ARTIFACT_ID>.tgz
```

### 6. Initialize git

The generated project already includes a suitable `.gitignore`, so a first commit
is clean:

```bash
git init -q
git add -A
git commit -q -m "Initial commit from Spring Initializr"
```

### 7. Verify the build

A quick build proves the scaffold is coherent and the toolchain is set up before the
user writes any code. The generated `@SpringBootTest` context-load test is exactly
the right smoke check. Make the wrapper executable first (exec bits aren't always
preserved through zipping):

Maven:
```bash
chmod +x mvnw
./mvnw -B -ntp test
```

Gradle:
```bash
chmod +x gradlew
./gradlew test
```

On Windows use `mvnw.cmd` / `gradlew.bat`. The first run downloads dependencies, so
it can take a minute or two -- that's expected, not a hang.

Before building, sanity-check the JDK: run `java -version` and, if it's older than
the `javaVersion` you selected, tell the user the build will fail on a version
mismatch and offer to either regenerate for their installed JDK or point them at
installing a newer one. Building needs a matching JDK plus network access to Maven
Central / the Gradle Plugin Portal.

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
- Validate the final set before generating (this catches typos and suggests near
  matches, and exits non-zero if anything is wrong):
  ```bash
  python3 scripts/query_initializr.py validate web,data-jpa,postgresql
  ```

Confirm the resolved list with the user in the step-4 summary. When a user asks for
something common, these are the usual IDs (still validate them, since availability
and compatibility ranges shift by Boot version): `web` (Spring MVC), `webflux`
(reactive), `data-jpa`, `data-jdbc`, `jdbc`, `postgresql`, `mysql`, `h2`, `flyway`,
`liquibase`, `data-mongodb`, `data-redis`, `security`, `oauth2-client`, `validation`,
`actuator`, `lombok`, `devtools`, `configuration-processor`, `testcontainers`,
`graphql`, `kafka`, `amqp`, `thymeleaf`, `mustache`.

---

## The Spring Initializr HTTP API (reference)

- **Metadata (capabilities):** `GET https://start.spring.io/` with an
  `Accept: application/json` (or vendor `application/vnd.initializr.v2.2+json`)
  header returns a JSON document listing every available type, language, version,
  and dependency, each with its `id` and the service `default`. The helper script
  wraps this for you.
- **Generate a project:** `GET`/`POST https://start.spring.io/starter.zip` (or
  `starter.tgz`) with the parameters below. There are also `pom.xml`, `build.gradle`,
  and `build.gradle.kts` endpoints if you only want a build file.

Request parameters:

- `type` -- one of `maven-project`, `gradle-project` (Groovy DSL),
  `gradle-project-kotlin` (Kotlin DSL). This encodes the build tool + build-script
  language together.
- `language` -- `java`, `kotlin`, or `groovy`.
- `bootVersion` -- a Spring Boot version ID from the metadata.
- `javaVersion` -- e.g. `17`, `21`, `25` (whatever the metadata offers).
- `packaging` -- `jar` or `war`.
- `groupId`, `artifactId`, `name`, `description`, `packageName`, `version` -- project
  coordinates (text).
- `dependencies` -- comma-separated dependency IDs.
- `baseDir` -- top-level folder name inside the archive (set this to `artifactId`).
- `applicationName` -- overrides the generated main class name (optional).

Note: Initializr does not let you pin a specific version of an individual
dependency via the API -- it selects versions compatible with the chosen Boot
version. If the user needs a non-default dependency version, generate first, then
edit the `pom.xml`/`build.gradle` afterward.

---

## Restricted networks and offline environments

Both generating and building reach the internet, so a locked-down environment can
block them:

- **Generation** needs to reach `start.spring.io`. If curl fails with something like
  "host not in allowlist", a connection timeout, or a proxy denial, the environment
  is restricting outbound traffic. Tell the user plainly and offer options: run this
  in an environment with internet access (e.g. their local machine / Claude Code),
  add `start.spring.io` to the network egress allowlist, or generate the zip
  themselves from the web UI and hand it over for the git + build steps.
- **Building** needs Maven Central and (for Gradle) the Gradle Plugin Portal /
  `services.gradle.org`. If those are blocked, generation may still succeed but the
  build won't; say so rather than letting it look like a project defect.

Don't quietly retry against a blocked host in a loop -- surface the situation once,
clearly, and let the user decide how to proceed.

## Custom / enterprise Initializr instances

Some organizations run their own Initializr with a curated dependency catalog. The
skill works against any instance: pass `--base-url https://start.mycompany.com` to
the helper script, and swap the host in the `curl` command. Ask the user whether
they have a company instance if the context suggests it (internal starters, private
dependencies).

## Troubleshooting

- **HTTP 400 on generate** -- almost always a bad `dependencyId` or an
  incompatible one for the chosen `bootVersion`. Re-run the `validate` command and
  check the compatibility range shown by `search`.
- **Downloaded "zip" won't extract** -- you likely captured an error response.
  Ensure `-f` is on the curl command and inspect the file (`file <name>.zip`); if
  it's text, it's an error message to read.
- **Build fails immediately with a Java version error** -- JDK/`javaVersion`
  mismatch; see step 7.
- **Wrapper "permission denied"** -- `chmod +x mvnw gradlew` (exec bits can be lost
  through zipping).

---

## Non-interactive shortcut

If the user front-loads everything ("Maven, Java 21, Spring Boot latest, group
com.acme, artifact orders, deps web + data-jpa + postgresql"), don't march them
back through the questions. Validate the dependencies, show the one-line summary for
a quick confirm, then generate. Interactive means *helpful and guided*, not
*needlessly repetitive*.
