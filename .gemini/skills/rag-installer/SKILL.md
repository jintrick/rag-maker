---
name: rag-installer
description: Install or migrate a RAG knowledge base. Automatically maintains directory naming and requires user confirmation of the target path.
---

# rag-installer

Execute these steps in order to install a RAG knowledge base:

1. **Select Source**: Run `ragmaker-ask-dir` and capture the selected directory path as `SOURCE_PATH`.
2. **Select Destination Parent**: Run `ragmaker-ask-dir --initial-dir .` to select the parent directory where the KB will be installed. Capture this as `DEST_PARENT`.
3. **User Confirmation**:
    - Inform the user: "Installing knowledge base from `SOURCE_PATH` to `DEST_PARENT`."
    - Note that a new directory with the same name as the source will be created inside `DEST_PARENT`.
    - Wait for the user's explicit confirmation before proceeding.
4. **Install**: Run `ragmaker-install-kb --source SOURCE_PATH --target-kb-root DEST_PARENT`. (Add `--force` if the user agrees to overwrite any existing directory).
5. **Open**: Parse the `target_kb_root` from the JSON output of the install command. Run `ragmaker-open-directory` with this path.
