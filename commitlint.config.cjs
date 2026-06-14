module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    // Dependabot's auto-generated bodies (and humans pasting changelog/compare
    // URLs or dependency metadata) routinely exceed 100 chars per line. We can't
    // control that text, and release-please only reads the subject + footers to
    // compute the next version, so the body line-length cap adds no value while
    // breaking every dependency bump — disable it. Subject/type enforcement,
    // which the release automation actually relies on, stays on.
    "body-max-line-length": [0, "always", Infinity],
    // `.github/dependabot.yml` labels python dependency bumps with the `deps`
    // prefix, which isn't one of the default conventional types. Add it so those
    // auto-generated commits pass. release-please ignores unknown types, so
    // `deps` bumps correctly don't cut a release on their own.
    "type-enum": [
      2,
      "always",
      [
        "build",
        "chore",
        "ci",
        "deps",
        "docs",
        "feat",
        "fix",
        "perf",
        "refactor",
        "revert",
        "style",
        "test",
      ],
    ],
  },
};
