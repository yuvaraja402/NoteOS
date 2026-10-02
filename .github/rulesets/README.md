# Default-branch ruleset

`default-branch.json` is the repository's branch policy, not an AWS resource.
GitHub enforces the ruleset only after a repository administrator installs it.
Checking in this file does not configure a fork automatically.

## Policy

- Target the default branch (`main` here), including after a default-branch rename.
- Require a pull request and resolution of review conversations.
- Require `ci-gate` from the GitHub Actions app (integration ID `15368`).
- Require testing against the latest default branch before merging.
- Block branch deletion and force pushes. No bypass actors are configured.

`ci-gate` requires lint/build, API tests, Trivy, both Docker builds and Terraform
validation to succeed. A failed, cancelled, missing or skipped mandatory job
fails the gate. Snyk may be skipped on PRs and on repositories that have not
configured it; an executed Snyk scan must pass. See
[deployment controls](../../infra/DEPLOYMENT.md) before a release.

Approvals are set to **zero** for a solo maintainer: GitHub does not allow
authors to approve their own PRs. This is not independent review. Once another
reviewer is available, set `required_approving_review_count` to at least `1`
and `require_last_push_approval` to `true` in both this file and GitHub.
Independent review is a production-release prerequisite.

Signed commits and merge queues are not required. Enable them only after
contributors have signing configured and CI supports the `merge_group` event.
Rulesets do not replace secret scanning or production environment approvals.

## Install on a fork

1. Enable GitHub Actions and merge the workflow containing `ci-gate` into the
   default branch. Confirm that a CI run completes successfully.
2. In **Settings > Rules > Rulesets**, import `default-branch.json`, inspect the
   settings and save with **Active** enforcement. Public repositories support
   branch rulesets on GitHub Free; private repositories may need another plan.
3. Open a test PR and confirm that `ci-gate` is required. Use PRs for subsequent
   updates to the default branch. Feature branches remain unrestricted.

Alternatively, with GitHub CLI authenticated as a repository administrator,
run from the repository root after step 1. Replace `OWNER/REPO` with your fork:

```bash
gh api --method POST repos/OWNER/REPO/rulesets \
  --input .github/rulesets/default-branch.json
gh api repos/OWNER/REPO/rules/branches/main
```

POST creates a ruleset; do not run it repeatedly. List existing rulesets first
with `gh api repos/OWNER/REPO/rulesets`. To update this policy, use its ID:

```bash
gh api --method PUT repos/OWNER/REPO/rulesets/RULESET_ID \
  --input .github/rulesets/default-branch.json
```

Keep the checked-in policy and live settings in sync. Review changes in a PR,
then have an administrator apply them and verify the returned settings. If a
required check is renamed, update the policy before removing the old check.
Other rulesets and legacy branch protections can add stricter requirements.
Emergency policy changes require administrator access; record the reason in
an issue, restore enforcement and rerun CI before merging. Do not add a
permanent administrator bypass to work around failing checks.

Importing this ruleset, pushing a branch or merging a PR does not deploy AWS
resources, publish container images or sync Argo CD.

References: [About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets),
[available rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
and [ruleset REST API](https://docs.github.com/en/rest/repos/rules).
