# Project instructions

<!-- shared-ci:start -->
## Shared CI execution policy

Linux-compatible automated checks belong on the disposable Unraid CI pool.
Use the smallest suitable `ci-light`, `ci-standard` or `ci-heavy` profile.
Native Apple SDK, Xcode, simulator, signing and Metal checks belong on the Mac;
preserve its shared host mutex and free-space admission. Signing/release work
still requires its own authorized credential boundary. Short interactive local
checks are allowed; do not move heavy portable suites onto the Mac.

Routing is recorded in `.github/ci-routing.json`. New jobs and changed runner choices
must pass the CI routing guard. Explain exact platform/credential exceptions
there; do not create an unreviewed fallback or weaken a required check.

Private project jobs use repository-scoped, short-lived runners. Public source
uses the private trusted-main hub; fork/PR checks stay on hosted runners.
Never give public PR code a home runner, reuse a production/deployment runner,
or place operator, production, mailbox, signing or paid-model credentials in
ordinary validation. TEST/PROD data and release policies remain separate.

Connect or refresh any project using the operator checkout of `unraid-ci`:
`./ci onboard /absolute/path/to/project --activate`. This prepares version-pinned
CI configuration and instructions, verifies App access and registers the project.
Review and merge the generated diff through this project's normal PR gates.
An explicit GitHub installation consent or macOS administrator prompt may be
needed for a new repository/native runner; do not bypass either.
<!-- shared-ci:end -->
