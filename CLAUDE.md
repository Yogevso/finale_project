# Working in this repository

Document platform: FastAPI backend, React + TipTap/ProseMirror frontend, Yjs/Hocuspocus
collaboration. Its hard problem is converting Intel release notes and specifications
(DOCX and PDF) into HTML that stays faithful to the source, with a table of contents
that matches the document rather than guessing at the rendered HTML.

## Read this before running anything

**The app runs in Docker; the local venv is not a substitute.** `backend/venv` holds
65 of the 119 pinned packages. `fonttools`, `defusedxml`, `chromadb` and
`beautifulsoup4` are among the missing, and their absence degrades quietly rather
than failing:

- Without `fonttools`, `pdf_fidelity` cannot repair fonts lifted out of a PDF, falls
  back to embedding the raw program, and the browser silently rejects it. The render
  drops to a serif default and looks broken when it is not.
- Without `defusedxml`, `docx_extractor` will not import at all.

Run conversions and tests inside the container:

```bash
docker exec -i v2-backend python -m pytest tests/ -q
```

`ruff` *is* installed locally and the pre-push hook needs it on PATH:

```bash
PATH="$HOME/finale_project/backend/venv/bin:$PATH" git push
```

**uvicorn runs without `--reload`.** The container bind-mounts `backend/` to `/app`, so
edited files are visible immediately, but the running process keeps the modules it
imported at boot. Backend changes need `docker restart v2-backend`. The frontend is
Vite and does hot-reload.

**pytest is absent from the backend image** (it is a production build) and crashes in
the local venv on `tests/conftest.py`. Install it into the container when needed; it
does not survive a rebuild.

## The test baseline

**51 backend tests fail on a clean checkout.** They check for scripts outside the
bind mount, assert `MAX_UPLOAD_SIZE` of 50MB against a 10MB environment, and cover
rate limiting and auth. Establish the baseline before blaming a change:

```
backend   51 failed, ~1726 passed
frontend  111 files, 432 tests, all passing
```

## Conversion architecture

Two formats, two very different sources of truth. Do not force one mechanism on both.

**DOCX declares its structure completely.** On the Intel release-notes template the
heading styles and the generated contents page agree exactly at every depth
(11/54/63/30). That contents page is the authority, because heading paragraphs do not
contain their own numbers - Word renders those from the numbering definition, so
`paragraph.text` gives "Release Kit Summary" and never "1 Release Kit Summary". The
numbering exists literally only in the contents entries.

**PDF declares almost nothing.** The GCC user guide ships four level-one bookmarks for
twenty pages. The outline is authoritative where it exists and detected headings fill
in below it, using the whole font signature rather than size or weight alone.

**Layout dies early on the PDF path.** `convert_pdf_to_docx` reads span coordinates,
sorts blocks by them and discards them; DOCX is a flow format, so page boundaries and
positions cannot be recovered downstream. `pdf_layout.py` is the parallel path that
keeps them. It and `docx_structure.py` are **written, tested and wired to nothing** -
no screen consumes them yet.

**The frontend sanitizer drops what a faithful render is made of.**
`sanitizeHtmlForPreview` removes `<style>`, the `style` attribute and `svg`. The
fidelity view therefore renders in a sandboxed iframe rather than through
`PreviewCanvas`.

## Table of contents

Stored in `versions.toc_json` beside the content it describes, served as
`toc_items`, never scraped from rendered HTML. Every entry carries a real page number
and a stable `anchor_id` matching a heading id, so navigation is a direct lookup.

It is built at upload from the source file and rebuilt from the HTML on every edit,
carrying pages across on the anchor id. Anything that writes `versions.content` must
write the contents too, or a review will compare a baseline holding entries against a
candidate holding none and report them all as removed.

Word's generated contents page is navigation, not content, and is not emitted into the
body. Left there, each line becomes a phantom section anchored to a page number and a
regenerated page reads as hundreds of deletions.

## How to work here

Trace before changing, and measure on the real documents rather than on fixtures
built from assumption. Several beliefs that seemed obvious were wrong when measured:
numbering appeared absent until spans were joined with their x-gaps; the running
header was invisible to repeated-text detection because it names the current chapter;
re-detecting a table with the text strategy made it worse, not better.

Fix at the earliest stage where the information is still present. Symptoms surface in
the editor and the contents panel, but the causes have consistently been two layers
upstream in extraction.
