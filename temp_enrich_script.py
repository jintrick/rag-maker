import json
import os

cache_dir = "C:\\Synology Drive\\2way-sync\\work\\rag-maker\\cache\\jules.google"
discovery_file = os.path.join(cache_dir, "discovery.json")

with open(discovery_file, 'r', encoding='utf-8') as f:
    discovery_data = json.load(f)

updated_documents = []
for doc_entry in discovery_data['documents']:
    html_path = doc_entry['path']
    md_path = html_path.replace('.html', '.md')
    full_md_path = os.path.join(cache_dir, md_path)

    title = ""
    summary = ""

    if os.path.exists(full_md_path):
        with open(full_md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            # Extract title (first heading)
            for line in lines:
                if line.startswith('# '):
                    title = line[2:].strip()
                    break
            if not title:
                title = os.path.basename(md_path).replace('.md', '').replace('_', ' ').title()

            # Extract summary (first paragraph)
            in_paragraph = False
            paragraph_lines = []
            for line in lines:
                if line.strip() and not line.startswith('#'):
                    paragraph_lines.append(line.strip())
                    in_paragraph = True
                elif in_paragraph:
                    break
            summary = ' '.join(paragraph_lines).strip()
            if not summary:
                summary = "このドキュメントには要約がありません。"

    doc_entry['path'] = md_path
    doc_entry['title'] = title
    doc_entry['summary'] = summary
    updated_documents.append(doc_entry)

discovery_data['documents'] = updated_documents

with open(discovery_file, 'w', encoding='utf-8') as f:
    json.dump(discovery_data, f, indent=2, ensure_ascii=False)

print("discovery.jsonのエンリッチが完了しました。")
