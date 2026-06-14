import os
import json
import re
import shutil

def sanitize_filename(name):
    name = name.lower()
    name = re.sub(r'[^a-z0-9]+', '_', name)
    name = re.sub(r'_+', '_', name)
    return name.strip('_')

def categorize_and_rename(item):
    path = item['path']
    title = item['original_title'].lower()
    filename = item['filename'].lower()
    body = item['body_snippet'].lower()
    
    cat = "reference"
    info_type = "doc"
    
    # 1. Determine Category and Info Type
    if "adr/" in path.lower():
        cat = "appendix"
        info_type = "adr"
    elif any(kw in filename or kw in title for kw in ["readme", "install", "create", "setup", "introduction", "overview", "getting_started", "start"]):
        cat = "introduction"
        info_type = "overview"
    elif any(kw in filename or kw in title or kw in body[:50] for kw in ["changelog", "license", "terms", "code_of_conduct", "contributing", "security", "support", "history", "glossary", "faq", "deadcode", "package"]):
        cat = "appendix"
        info_type = "metadata"
    elif any(kw in filename or kw in title or kw in body[:50] for kw in ["guide", "tutorial", "how_to", "how-to", "example", "demo", "pattern", "workflow", "action", "step", "recipe"]):
        cat = "guide"
        info_type = "guide"
    elif any(kw in filename or kw in title or kw in body[:50] for kw in ["api", "reference", "config", "command", "prompt", "cli", "error", "message", "issue", "comment", "fallback", "linter"]):
        cat = "reference"
        if "prompt" in filename or "prompt" in title:
            info_type = "prompt"
        elif "error" in filename or "fallback" in filename:
            info_type = "error_message"
        elif "issue" in filename:
            info_type = "issue_template"
        elif "comment" in filename:
            info_type = "comment_template"
        elif "linter" in filename:
            info_type = "linter_rule"
        else:
            info_type = "reference"
    else:
        # fallback parsing body
        if "guide" in body or "tutorial" in body or "example" in body:
            cat = "guide"
            info_type = "guide"
        else:
            cat = "reference"
            info_type = "doc"
            
    # Refine specific known files
    if filename == "agents.md":
        cat = "introduction"
        info_type = "overview"
    if filename == "devguide.md":
        cat = "guide"
        info_type = "developer_guide"
    if filename == "skill.md":
        cat = "reference"
        info_type = "skill_definition"
        
    # 2. Build detailed content string
    # Extract keywords from title and filename
    raw_name = title if title else filename.replace('.md', '')
    if "adr-" in raw_name or re.match(r'^\d+-', raw_name):
        # keep adr name
        pass
    
    details = sanitize_filename(raw_name)
    
    # Ensure at least 3 keywords if possible
    words = details.split('_')
    if len(words) < 3:
        # try to extract from body
        extra = sanitize_filename(body[:30])
        extra_words = [w for w in extra.split('_') if len(w) > 3 and w not in words]
        words.extend(extra_words)
        details = "_".join(words[:5])
        
    # Final name
    # Project: gh_aw
    # Format: gh_aw_[category]_[details]_[info_type].md
    new_name = f"gh_aw_{cat}_{details}_{info_type}.md"
    new_name = re.sub(r'_+', '_', new_name)
    
    return cat, new_name

def main():
    cache_dir = r"C:\Synology Drive\2way-sync\work\rag-maker\.tmp\cache"
    meta_path = "metadata.json"
    
    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
        
    moves = []
    for item in metadata:
        old_path = item['path']
        if not os.path.exists(old_path):
            continue
            
        cat, new_name = categorize_and_rename(item)
        new_dir = os.path.join(cache_dir, cat)
        new_path = os.path.join(new_dir, new_name)
        
        moves.append((old_path, new_path, new_dir))
        
    # Execute moves
    count = 0
    for old_path, new_path, new_dir in moves:
        if not os.path.exists(new_dir):
            os.makedirs(new_dir, exist_ok=True)
            
        # Handle conflicts
        if os.path.exists(new_path) and old_path != new_path:
            base, ext = os.path.splitext(new_path)
            new_path = f"{base}_{count}{ext}"
            
        try:
            shutil.move(old_path, new_path)
            count += 1
        except Exception as e:
            print(f"Failed to move {old_path} to {new_path}: {e}")
            
    print(f"Successfully processed and moved {count} files.")
    
    # Clean up empty directories
    for root, dirs, files in os.walk(cache_dir, topdown=False):
        for d in dirs:
            dir_path = os.path.join(root, d)
            # Do not delete the 4 main category folders even if empty
            if d in ['introduction', 'reference', 'guide', 'appendix'] and root == cache_dir:
                continue
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
            except Exception:
                pass
                
    print("Cleanup complete.")

if __name__ == "__main__":
    main()
