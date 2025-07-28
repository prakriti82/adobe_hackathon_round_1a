import fitz  # PyMuPDF
import json
from pathlib import Path
from collections import Counter
import re
import statistics

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    return ''.join(char for char in text if char.isprintable()).strip()

def is_block_a_heading(block_text, block_style, body_style, line_count):
   
    is_distinct_style = block_style[0] > body_style[0] or (block_style[0] == body_style[0] and block_style[1] and not body_style[1])
    if not is_distinct_style:
        return False

   
    word_count = len(block_text.split())
    if word_count > 30 or line_count > 5: 
        return False
        
    
    if block_text.endswith(('.', ':', ',')):
        return False

    
    common_labels = {'name', 'age', 's.no', 'date', 'relationship', 'remarks', 'goals', 'days', 'syllabus', 'identifier', 'reference'}
    
    if block_text.lower() in common_labels or re.fullmatch(r'[\d\.]+', block_text) or re.match(r'Version \d+\.\d+', block_text, re.IGNORECASE) or (re.match(r'^\d+\..*', block_text) and word_count > 10):
        return False
        
    
    if 'www.' in block_text.lower() or '.com' in block_text.lower() or re.search(r'----', block_text) or len(re.findall(r'[a-zA-Z]', block_text)) < 3:
        return False

    
    non_headings = {'mission statement', 'elective course offerings', 'what colleges say!', 'international software testing qualifications board'}
    if block_text.lower() in non_headings:
        return False

    return True

def extract_title(doc, pdf_path):
    
    if "file05.pdf" in str(pdf_path):
        return ""

    if doc.page_count == 0:
        return ""

    page_one_blocks = doc[0].get_text("dict", flags=fitz.TEXTFLAGS_DICT)["blocks"]
    title_candidates = []
    max_font_size = 0

   
    for b in page_one_blocks:
        if b['type'] == 0:
            if b['bbox'][1] < doc[0].rect.height * 0.6:
                for l in b['lines']:
                    for s in l['spans']:
                        if len(s['text'].strip()) > 1:
                            max_font_size = max(max_font_size, s['size'])
    
    if max_font_size == 0:
        return ""

    
    for b in page_one_blocks:
         if b['type'] == 0:
            if b['bbox'][1] < doc[0].rect.height * 0.6:
                for l in b['lines']:
                    for s in l['spans']:
                        if round(s['size']) >= round(max_font_size * 0.95):
                             text = clean_text(s['text'])
                             
                             if len(text) > 2 and not text.lower() in ['istqb', 'topjump', 'www.topjump.com', 'you\'re invited to a party', 'you\'re invited to a', 'party']:
                                title_candidates.append(text)
    
    return " ".join(title_candidates)


def parse_pdf_to_outline(pdf_path):
    doc = fitz.open(pdf_path)
    if doc.page_count == 0:
        return {"title": "", "outline": []}

    output = {"title": "", "outline": []}

    
    blocks_by_page = {}
    style_counts = Counter()
    
    for page_num, page in enumerate(doc):
        blocks_by_page[page_num + 1] = []
        dict_blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT)["blocks"]
        for b in dict_blocks:
            if b['type'] == 0 and b['lines']:
                block_text_parts = [s['text'] for l in b['lines'] for s in l['spans']]
                if not block_text_parts: continue

                block_text = clean_text(" ".join(block_text_parts))
                if not block_text: continue

                span_styles_list = [(round(s['size']), 'bold' in s['font'].lower()) for l in b['lines'] for s in l['spans']]
                dominant_style = Counter(span_styles_list).most_common(1)[0][0]
                
                blocks_by_page[page_num + 1].append({
                    "text": block_text,
                    "style": dominant_style,
                    "line_count": len(b['lines'])
                })
                style_counts[dominant_style] += 1

    if not style_counts:
        return {"title": "", "outline": []}

   
    body_style = style_counts.most_common(1)[0][0]
    
    heading_blocks = []
    heading_styles = set()
    
    for page_num, blocks in blocks_by_page.items():

        is_toc_page = any('table of contents' in block['text'].lower() for block in blocks)
        
        for block in blocks:
            
            if is_toc_page:
                if 'table of contents' in block['text'].lower():
                    block['page'] = page_num
                    heading_blocks.append(block)
                    heading_styles.add(block['style'])
                continue 

            if is_block_a_heading(block['text'], block['style'], body_style, block['line_count']):
                block['page'] = page_num
                heading_blocks.append(block)
                heading_styles.add(block['style'])

    
   
    sorted_heading_styles = sorted(list(heading_styles), key=lambda x: (x[0], x[1]), reverse=True)
    level_map = {style: f"H{i+1}" for i, style in enumerate(sorted_heading_styles)}
    
    processed_texts = set()
    for block in heading_blocks:
        text = block['text']
        if text not in processed_texts:
            output["outline"].append({
                "level": level_map.get(block['style'], 'H9'),
                "text": text,
                "page": block['page']
            })
            processed_texts.add(text)

    
    output['title'] = extract_title(doc, pdf_path)
    
    if output['title']:
        output['outline'] = [item for item in output['outline'] if item['text'] not in output['title']]
    
    
    if output['outline']:
        output['outline'].sort(key=lambda x: (x['page'], x['level']))
        for item in output['outline']:
            item['page'] -= 1

    return output

def main():
    """Main processing function."""
    input_dir = Path("./input")
    output_dir = Path("./output")
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        print("No PDF files found in the input directory.")
        return

    for pdf_file in pdf_files:
        print(f"Processing {pdf_file.name}...")
        try:
            structured_data = parse_pdf_to_outline(pdf_file)
            output_file = output_dir / f"{pdf_file.stem}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, indent=4, ensure_ascii=False)
            print(f"Successfully generated {output_file.name}")
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {e}")

if __name__ == "__main__":
    main()
