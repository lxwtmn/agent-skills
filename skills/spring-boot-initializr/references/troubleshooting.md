# Troubleshooting

Read this when generation or the build fails.

## Restricted networks and offline environments

Both generating and building reach the internet, so a locked-down environment can
block them:

- **Generation** needs to reach `start.spring.io`. If curl fails with something like
  "host not in allowlist", a connection timeout, or a proxy denial, the environment
  is restricting outbound traffic. Tell the user plainly and offer options: run this
  in an environment with internet access (for example their local machine), add
  `start.spring.io` to the network egress allowlist, or generate the zip themselves
  from the web UI and hand it over for the git and build steps.
- **Building** needs Maven Central and (for Gradle) the Gradle Plugin Portal and
  `services.gradle.org`. If those are blocked, generation may still succeed but the
  build won't; say so rather than letting it look like a project defect.

Don't retry against a blocked host in a loop. Surface the situation once, clearly,
and let the user decide how to proceed.

## Symptoms and causes

- **HTTP 400 on generate**: a bad dependency ID, or one that is incompatible with
  the chosen `bootVersion`. Re-run `validate` with `--boot-version` set to the
  version you are sending; it names the offending ID and the range it requires.
- **Downloaded "zip" won't extract**: you likely captured an error response.
  Make sure `-f` is on the curl command and inspect the file (`file <name>.zip`); if
  it is text, it is an error message to read.
- **`unzip` asks whether to replace files, or hangs**: the target folder already
  existed. Stop and ask the user where the project should go.
- **Build fails immediately with a Java version error**: the installed JDK is older
  than the `javaVersion` the project was generated for. Offer to regenerate for the
  installed JDK or point the user at installing a newer one.
- **Context-load test fails with "Failed to configure a DataSource"**: the project
  has JDBC-based data access and an external database driver, but nothing tells Boot
  where the database is. The scaffold is fine; see step 7 in `SKILL.md`.
- **Test fails with "Could not find a valid Docker environment"**: `testcontainers`
  was selected and Docker is not running.
- **Wrapper "permission denied"**: `chmod +x mvnw gradlew` (exec bits can be lost
  through zipping).
