---
type: llm
---

Ground truth for this project: the last run took about 236 seconds in total.
`OrderExportServiceTest` alone took about 182 seconds (roughly 77 %), because each of
its 12 tests waits with a fixed `Thread.sleep` of 15 seconds. Five `@SpringBootTest`
classes with different mock sets and profiles each start their own Spring context and
together took about 51 seconds (roughly 22 %).

PASS if the response does all of the following:
- gives measured numbers from the reports (per-class times or shares), not just a
  qualitative impression;
- names the fixed sleep in `OrderExportServiceTest` as the first thing to fix;
- treats the distinct Spring contexts as a second, smaller lever and attaches a number
  or estimate to it, or says how to measure it;
- does not present parallel execution or context caching as the primary recommendation.

FAIL if context caching, a shared base class or parallel execution is the first or
main recommendation, if no numbers are given, or if the sleep is not identified.
