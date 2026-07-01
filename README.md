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

## Add a skill

1. Create `skills/<kebab-name>/SKILL.md`. The `name:` in the frontmatter **must equal the folder name**
   (lowercase, hyphens, ≤64 chars). Write a `description:` that says both **what** it does and **when**
   to trigger it (≤1024 chars, no `<`/`>`).
2. Keep the `SKILL.md` body focused (under ~500 lines); move long reference material into a
   `references/` subfolder and executable helpers into `scripts/`.
3. Add a row to the **Skills** table above.
4. See [`template/SKILL.md`](template/SKILL.md) for a starting point (or run `npx skills init <name>`).

## License

[MIT](LICENSE) © 2026 Alexander Wittmann. Each skill may bundle its own tools/scripts; see the skill
folder for any additional notices.
