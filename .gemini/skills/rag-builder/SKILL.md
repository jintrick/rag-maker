---
name: rag-builder
description: Builds a RAG knowledge base from various sources (Web, GitHub, Local). Use when the user wants to create a knowledge base or "ingest" documentation.
---

# RAG Builder Skill

This skill guides the agent through the process of creating a RAG (Retrieval-Augmented Generation) knowledge base using the `rag-maker` toolset. It adheres to the architecture of separating the **Master Tool Catalog** (project root) and the **Document Catalog** (knowledge base root).

## Workflow

Follow these steps sequentially to build a knowledge base.

### 1. Source Identification & Initialization

1.  **Identify the Source**: Determine the input source (URL, GitHub repo, or local path).
2.  **Initialize Cache**: Prepare the temporary workspace using `ragmaker-init-cache`.
    ```bash
    ragmaker-init-cache
    ```
    *Note: This creates a temporary directory for raw data and metadata.*

### 2. Data Fetching & Processing

Choose the appropriate tool based on the source type.

**Option A: Web Source (http/https)**
1.  **Fetch HTML**: Use `ragmaker-http-fetch`.
    ```bash
    ragmaker-http-fetch --url <source_url> --base-url <base_url> --output-dir .tmp/cache/raw/
    ```
2.  **Convert to Markdown**: Use `ragmaker-html-to-markdown` to clean and convert fetched HTML.
    ```bash
    ragmaker-html-to-markdown --input-dir .tmp/cache/raw/ --output-dir .tmp/cache/md/
    ```

**Option B: GitHub Repository (github.com)**
*   Use `ragmaker-github-fetch`.
    ```bash
    ragmaker-github-fetch --repo-url <repo_url> --path-in-repo <path> --temp-dir .tmp/cache/md/
    ```

**Option C: Local Directory**
*   Use `ragmaker-file-sync`.
    ```bash
    ragmaker-file-sync --source-dir <local_path> --dest-dir .tmp/cache/md/
    ```

### 3. Document Catalog Construction

All metadata is stored in a temporary `discovery.json` which will become the **Document Catalog**.

1.  **Register Documents**: For each file in `.tmp/cache/md/`, use `ragmaker-entry-discovery` to add an entry.
    ```bash
    ragmaker-entry-discovery --discovery-path .tmp/cache/discovery.json --path <relative_path_to_file> --uri <source_uri>
    ```
2.  **Enrich Metadata (AI task)**:
    *   Read each document content using `ragmaker-read-file`.
    *   Generate a concise `title` and `summary`.
    *   Update the catalog using `ragmaker-enrich-discovery`.
    ```bash
    ragmaker-enrich-discovery --discovery-path .tmp/cache/discovery.json --updates '[{"path": "...", "title": "...", "summary": "..."}]'
    ```

### 4. Knowledge Base Deployment

1.  **Determine Destination**: Use `ragmaker-ask-dir` to let the user select or create a destination directory (`<KB_ROOT>`).
2.  **Initialize KB Structure**: Run `ragmaker-create-knowledge-base`.
    ```bash
    ragmaker-create-knowledge-base --kb-root "<KB_ROOT>"
    ```
3.  **Deploy Files**:
    *   Move processed markdown files: `.tmp/cache/md/` -> `<KB_ROOT>/cache/`
    *   Move the Document Catalog: `.tmp/cache/discovery.json` -> `<KB_ROOT>/discovery.json`
    *   Use `ragmaker-move-file` for these operations.

### 5. Finalization & Handover

1.  **Cleanup**: Run `ragmaker-cache-cleanup` to remove temporary files.
2.  **Verify**: Ensure `<KB_ROOT>/discovery.json` exists and contains only `documents` (no tool definitions).
3.  **Notify**: Inform the user that the knowledge base is ready at `<KB_ROOT>`.
4.  **Usage Instructions**: Remind the user they can now use the `/ask` command within that directory.
    ```bash
    gemini /ask "Your question about the documents"
    ```
5.  **Open Directory**: Optionally use `ragmaker-open-directory` to show the result to the user.
