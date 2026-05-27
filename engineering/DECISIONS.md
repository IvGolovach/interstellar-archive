# Engineering Decisions Log

## D-0001 - Publish A Reviewed Snapshot Instead Of The Source History

Status: accepted
Date: 2026-05-20T00:57:40Z
Author: Repository Maintainer
Related commits: https://github.com/IvGolovach/interstellar-archive/commit/44e2c76e1014bb5f2246f9d2fef09d90abb23f17

### Context
The project is published as a reviewable research artifact. The retained source repository contains operational metadata, branch names, pull-request traces, and historical cleanup details that are not part of the research surface.

### Options considered
1. Open the existing source repository directly.
2. Rewrite the existing repository history in place.
3. Retain the source history separately and publish a reviewed snapshot.

### Decision
Adopt option 3. The source history remains retained for provenance and development records. This repository starts from a clean baseline and carries only the files, metadata, and validation contracts needed for public review.

### Rationale
A reviewed snapshot avoids exposing operational metadata while preserving the ability to describe the real development timeline in reader-facing documents. It also prevents old branch names, pull-request titles, and generated cleanup artifacts from becoming part of the public surface.

### Trade-offs
This repository does not expose the original commit-by-commit source history. Timeline and release documents must therefore summarize the development phases clearly and avoid implying that the public snapshot commits are the full provenance chain.

### Future reconsideration trigger
Revisit if the project receives external contributors who need direct access to retained source-history records or if a formal archival process requires publishing selected provenance records.
