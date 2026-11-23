# agent-skills

A small, public collection of [Agent Skills](https://code.claude.com/docs/en/skills) by
[@lxwtmn](https://github.com/lxwtmn) — reusable capabilities you can drop into Claude Code,
Cursor, Codex, Copilot, and other agents that support the open Agent Skills format.

## Install

**Any agent (via [skills.sh](https://skills.sh) / the `npx skills` CLI):**

```bash
# install every skill in this repo
npx skills add lxwtmn/agent-skills

# or pick one
npx skills add lxwtmn/agent-skills --skill spring-boot-initializr

# or just list what's available
npx skills add lxwtmn/agent-skills --list
```

**Claude Code (plugin marketplace):**

```
/plugin marketplace add lxwtmn/agent-skills
/plugin install agent-skills@lxwtmn
```

**Manual:** copy any `skills/<name>/` folder into `~/.claude/skills/` (personal) or a project's
`.claude/skills/`.

## Skills

| Skill | What it does | Install |
| --- | --- | --- |
| [`spring-boot-initializr`](skills/spring-boot-initializr/) | Scaffolds a new Spring Boot project via the Spring Initializr API (`start.spring.io`) — guides you through build tool, language, versions, and dependencies, then downloads, extracts, git-inits, and verifies the build. | `npx skills add lxwtmn/agent-skills --skill spring-boot-initializr` |
| [`spring-boot-testing`](skills/spring-boot-testing/) | Writes, reviews and speeds up tests in Spring Boot projects (Java, JUnit, Mockito, Testcontainers, Maven or Gradle) — picks the cheapest test type that answers the question, follows the project's conventions, protects the Spring context cache, and measures before proposing speed-ups. | `npx skills add lxwtmn/agent-skills --skill spring-boot-testing` |

## Add a skill

1. Create `skills/<kebab-name>/SKILL.md`. The `name:` in the frontmatter **must equal the folder name**
   (lowercase, hyphens, ≤64 chars). Write a `description:` that says both **what** it does and **when**
   to trigger it (≤1024 chars, no `<`/`>`).
2. Keep the `SKILL.md` body focused (under ~500 lines); move long reference material into a
   `references/` subfolder and executable helpers into `scripts/`.
3. Add a row to the **Skills** table above.
4. See [`template/SKILL.md`](template/SKILL.md) for a starting point (or run `npx skills init <name>`).
5. Add at least one eval case under `evals/` that fails without the skill (see below).

## Testing and evals

Three layers, cheapest first. Run the first two on every change; they are free and take seconds.

**1. Static checks** validate the manifests and every skill's frontmatter:

```bash
claude plugin validate .
```

**2. Script tests** cover the bundled helper scripts against recorded data, without network access:

```bash
python3 -m unittest discover -s tests
```

**3. Behaviour evals** run a real agent on a task twice, once with the skills loaded and once
without, and grade both results. The difference between the two scores is what a skill is worth;
a case that passes equally well without the skill is not testing anything the skill adds. Cases live
in `evals/<case>/`: `prompt.md` is the task, `fixture.sh` builds the sample project the agent works
in, and each file in `graders/` is one pass/fail check.

| Case | What it checks |
| --- | --- |
| `initializr-plan-with-database` | The plan uses live versions and real dependency IDs, and raises the database question before generating. |
| `testing-write-delegating-use-case` | A forwarding class gets a Mockito unit test in the project's style, not a Spring context. |
| `testing-boot4-real-http-test` | A `TestRestTemplate` test on Spring Boot 4 gets the annotation, import and dependency that version needs. |
| `testing-speed-diagnosis` | A slow suite is diagnosed from the reports, and the measured hotspot ranks above context caching. |

These runs call the model and cost money, so start with one case and one run:

```bash
claude plugin eval . --scaffold --case testing-boot4-real-http-test --runs 1 --allow-tools Write Edit
```

The full suite (4 cases, 3 runs each, with and without the skills) needs write access for the
agent, Python for the helper scripts, and network access to start.spring.io:

```bash
claude plugin eval . --scaffold --max-cost-usd 15 --allow-tools Write Edit Bash "WebFetch(domain:start.spring.io)"
```

Grant `Bash` as a whole rather than a pattern such as `Bash(python3 *)`: the agent chains commands
(`cd <skill dir> && python3 ...; java -version`), and a chain that a pattern does not fully cover is
denied, which makes the case fail for a reason that has nothing to do with the skill. Every shell
command in an eval run is confined by Claude Code's OS sandbox: it can write only inside the run's
temporary workspace and reach only the domains granted here. The sandbox cannot see a JDK installed
under your home directory, so `java -version` fails inside a run.

`--scaffold` lets the cases run their `fixture.sh`; only pass it for case files you trust. Results
and an HTML report land in `evals/results/`, which is ignored by git. `claude plugin eval` needs a
logged-in Claude Code CLI (`claude auth login`) or an API key in the environment.

## License

[MIT](LICENSE) © 2026 Alexander Wittmann. Each skill may bundle its own tools/scripts; see the skill
folder for any additional notices.
