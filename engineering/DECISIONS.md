# Engineering Decisions Log

## D-0001 - Publish A Clean Mirror Instead Of The Workbench History

Status: accepted
Date: 2026-05-20T00:57:40Z
Author: Repository Maintainer
Related commits: private-provenance:18f33501e24f05efccf3be4fb1f5fc240ab14b8a

### Context
The project is being prepared as a reviewable research artifact. The retained workbench repository contains private operational metadata, branch names, pull-request traces, and historical cleanup details that are not part of the research surface.

### Options considered
1. Open the existing workbench repository directly.
2. Rewrite the existing repository history in place.
3. Keep the workbench private and publish a clean mirror from a reviewed snapshot.

### Decision
Adopt option 3. The workbench remains private for provenance and development records. The mirror starts from a clean baseline and carries only the files, metadata, and validation contracts needed for future public review.

### Rationale
A clean mirror avoids exposing private operational metadata while preserving the ability to describe the real development timeline in reader-facing documents. It also prevents old branch names, pull-request titles, and generated cleanup artifacts from becoming part of the public surface.

### Trade-offs
The mirror does not expose the original commit-by-commit workbench history. Timeline and release documents must therefore summarize the development phases clearly and avoid implying that the mirror's fresh commits are the full private provenance chain.

### Future reconsideration trigger
Revisit if the project receives external contributors who need direct access to the private provenance repository or if a formal archival process requires publishing selected provenance records.
