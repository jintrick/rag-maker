---
name: rag-installer
description: Install or migrate a RAG knowledge base. Automatically maintains directory naming and requires user confirmation of the target path.
---

# rag-installer

Execute these steps in order to install a RAG knowledge base:

1. **Select Source**: Run `ragmaker-ask-dir` and capture the selected directory path as `SOURCE_PATH`.
2. **Select Destination Parent**: Run `ragmaker-ask-dir --initial-dir .` to select where the KB should be placed. Capture this as `DEST_PARENT`.
3. **Calculate Target Path**:
    - Identify the name of the source folder from `SOURCE_PATH` (e.g., if source is `C:/my-kb`, the name is `my-kb`).
    - The final target path is `DEST_PARENT / (source folder name)`. Capture this as `TARGET_PATH`.
4. **User Confirmation**:
    - Clearly inform the user: "Installing knowledge base from `SOURCE_PATH` to `TARGET_PATH`."
    - Wait for the user's explicit confirmation before proceeding.
5. **Install**: Run `ragmaker-install-kb --source SOURCE_PATH --target-kb-root TARGET_PATH`. (Add `--force` if the user agrees to overwrite an existing directory).
6. **Open**: Run `ragmaker-open-directory TARGET_PATH` to show the results.
