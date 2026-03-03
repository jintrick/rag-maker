#!/usr/bin/env python3
import logging
import sys
logging.disable(logging.CRITICAL)
import argparse
import json
import shutil
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Any

try:
    from ragmaker.io_utils import (
        handle_unexpected_error,
        handle_file_not_found_error,
        handle_value_error,
        print_json_stdout
    )
    from ragmaker.utils import safe_export, merge_catalog_data
except ImportError:
    sys.stderr.write("{\"status\": \"error\", \"message\": \"The 'ragmaker' package is not installed or not in the Python path.\"}\x0a")
    sys.exit(1)

logger = logging.getLogger(__name__)

def install_knowledge_base(source_roots: List[Path], target_root: Path, force: bool = False, merge: bool = False, flatten: bool = False):
    if merge or flatten: return _install_merged(source_roots, target_root, force)
    else:
        target_root.mkdir(parents=True, exist_ok=True)
        results = []
        for src in source_roots:
            sub = target_root / src.name
            results.append(_install_merged([src], sub, force))
        return {"status": "success", "installed_kbs": results}

def _install_merged(source_roots: List[Path], target_root: Path, force: bool = False) -> Dict[str, Any]:
    for src in source_roots:
        if not src.exists(): raise FileNotFoundError(str(src))
    if target_root.exists():
        if not target_root.is_dir(): raise NotADirectoryError(str(target_root))
        if not force and any(target_root.iterdir()): raise FileExistsError(str(target_root))
    
    target_root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target_root.parent) as tmp:
        work = Path(tmp) / "work"
        work.mkdir()
        if target_root.exists(): safe_export(target_root, work)
        t_cache = work / "cache"
        t_cache.mkdir(exist_ok=True)
        
        all_docs = []
        for src_root in source_roots:
            if (src_root / "cache").is_dir():
                s_cache, s_base = src_root / "cache", src_root
            elif src_root.name == "cache":
                s_cache, s_base = src_root, src_root.parent
            else:
                s_cache, s_base = src_root, src_root
            
            if s_cache.exists(): safe_export(s_cache, t_cache)
            
            s_cat = None
            loc = None
            for p, l in [(s_base/"catalog.json","root"),(s_base/"discovery.json","root"),(s_cache/"catalog.json","cache"),(s_cache/"discovery.json","cache")]:
                if p.exists():
                    s_cat, loc = p, l
                    break
            if not s_cat: continue
            
            data = json.load(open(s_cat, "r", encoding="utf-8"))
            for doc in data.get("documents", []):
                p_str = doc.get("path")
                if not p_str: continue
                abs_s = (s_base / p_str) if loc == "root" else (s_cache / p_str)
                abs_s = abs_s.resolve()
                try: rel = abs_s.relative_to(s_cache.resolve())
                except ValueError: rel = Path(p_str)
                
                parts = list(rel.parts)
                while parts and parts[0] == "cache": parts.pop(0)
                new_rel = Path("cache").joinpath(*parts)
                doc["path"] = new_rel.as_posix()
                all_docs.append(doc)
        
        source_paths_str = [str(p.resolve()) for p in source_roots]
        final = {
            "documents": all_docs,
            "metadata": {
                "generator": "ragmaker-install-kb",
                "sources": source_paths_str
            }
        }
        
        w_cat = work / "catalog.json"
        if w_cat.exists():
            try: 
                old = json.load(open(w_cat,"r", encoding="utf-8"))
                # Merge metadata sources safely
                old_sources = old.get("metadata", {}).get("sources", [])
                final = merge_catalog_data(old, final)
                merged_sources = list(dict.fromkeys(old_sources + source_paths_str))
                final.setdefault("metadata", {})["sources"] = merged_sources
            except Exception: pass
        json.dump(final, open(w_cat,"w",encoding="utf-8"), indent=2, ensure_ascii=False)
        
        if target_root.exists():
            bak = target_root.with_suffix(".bak")
            if bak.exists():
                if bak.is_dir(): shutil.rmtree(bak)
                else: bak.unlink()
            target_root.rename(bak)
            try: shutil.move(str(work), str(target_root))
            except Exception:
                if target_root.exists(): shutil.rmtree(target_root)
                try:
                    bak.rename(target_root)
                except Exception as e:
                    logger.critical(f"Failed to restore backup from {bak} to {target_root}. Data remains in {bak}.")
                    raise e
                raise
            if bak.exists(): shutil.rmtree(bak)
        else: shutil.move(str(work), str(target_root))
    return {"status": "success", "target_kb_root": str(target_root.resolve()), "document_count": len(all_docs)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, nargs="+")
    parser.add_argument("--target-kb-root", required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--merge", action="store_true")
    parser.add_argument("--flatten", action="store_true")
    try:
        args = parser.parse_args()
        res = install_knowledge_base([Path(p) for p in args.source], Path(args.target_kb_root), args.force, args.merge, args.flatten)
        print_json_stdout(res)
    except Exception as e:
        handle_unexpected_error(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
