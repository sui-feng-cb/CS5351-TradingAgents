# Structural constraints

ADR-001: one upstream application copy under src; CLI imports public services,
domain agents use existing dataflows rather than importing vendor SDKs directly.
Each new architecture element has exactly one owning module, defined in AGENTS.
New modules/functions reference requirement/ADR/invariant IDs in docstrings or
adjacent documentation. No cyclic imports or copy-pasted upstream replacements.

INV-D requires final structured rating to be authoritative over narrative text.
INV-B requires source metadata to be authoritative over model citations. The
upstream layering regression remains mandatory; relocating tests must not make it
silently inspect an empty directory. Interface and security changes need ADRs and
human review. Packaging moves preserve CLI resource files and test assertions.
