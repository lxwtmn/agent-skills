# The Spring Initializr HTTP API

Read this when you need a parameter that the standard `curl` call in `SKILL.md`
does not show, want only a build file, or are talking to a company instance.

## Endpoints

- **Metadata (capabilities):** `GET https://start.spring.io/` with an
  `Accept: application/vnd.initializr.v2.2+json` header returns a JSON document
  listing every available type, language, version, and dependency, each with its
  `id` and the service `default`. The helper script wraps this for you. Plain
  `application/json` returns an older format whose Boot version IDs look like
  `4.2.0.RELEASE`; prefer the vendor media type so the IDs match what you send back.
- **Generate a project:** `https://start.spring.io/starter.zip` (or `starter.tgz`)
  with the parameters below, as a form `POST` (what `curl --data-urlencode` sends)
  or as `GET` query parameters.
- **Build file only:** `pom.xml`, `build.gradle`, and `build.gradle.kts` endpoints
  take the same parameters and return just that file. Handy for checking a
  dependency set without downloading a project.

## Request parameters

- `type`: one of `maven-project`, `gradle-project` (Groovy DSL),
  `gradle-project-kotlin` (Kotlin DSL). This encodes the build tool and the
  build-script language together.
- `language`: `java`, `kotlin`, or `groovy`.
- `bootVersion`: a Spring Boot version ID from the metadata.
- `javaVersion`: whatever the metadata offers, for example `17`, `21`, `25`.
- `packaging`: `jar` or `war`.
- `groupId`, `artifactId`, `name`, `description`, `packageName`, `version`:
  project coordinates (text).
- `dependencies`: comma-separated dependency IDs.
- `baseDir`: top-level folder name inside the archive (set this to `artifactId`).
- `applicationName`: overrides the generated main class name (optional).

Initializr does not let you pin a specific version of an individual dependency.
It selects versions compatible with the chosen Boot version. If the user needs a
non-default dependency version, generate first, then edit the `pom.xml` or
`build.gradle` afterward.

## Errors

The API answers HTTP 400 with a JSON body whose `message` names the problem:
an unknown dependency ID, an unknown `bootVersion`, or a dependency that is "not
compatible with Spring Boot X". The `validate` command of the helper script
catches all three before you generate.

## Custom and enterprise instances

Some organizations run their own Initializr with a curated dependency catalog. The
skill works against any instance: pass `--base-url https://start.mycompany.com` to
the helper script and swap the host in the `curl` command. The instance may offer
different versions, defaults, and dependency IDs than start.spring.io, so read its
metadata rather than assuming.
