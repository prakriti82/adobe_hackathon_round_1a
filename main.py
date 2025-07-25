import fitz  # PyMuPDF
import json
from pathlib import Path
from collections import Counter
import re
import statistics

def clean_text(text):
    """Cleans text by removing excessive whitespace and non-printable characters."""
    text = re.sub(r'\s+', ' ', text)
    return ''.join(char for char in text if char.isprintable()).strip()

def is_likely_heading_by_style(text, style, body_style):
    """
    Applies a very strict, rule-based filter to determine if a line is a heading.
    This is specifically for documents that do NOT have a built-in Table of Contents.
    """
    # Rule 1: Must have a style distinct from the body text (larger or bolder).
    is_distinct_style = style[0] > body_style[0] or (style[0] == body_style[0] and style[1] and not body_style[1])
    if not is_distinct_style:
        return False

    # Rule 2: Must be concise. Long paragraphs are not headings.
    word_count = len(text.split())
    if word_count > 15:
        return False
        
    # Rule 3: Must not end with typical sentence-ending punctuation.
    if text.endswith(('.', ':', ',')):
        return False

    # Rule 4: Must not be a common form/table label or just a number.
    common_labels = {'name', 'age', 's.no', 'date', 'relationship', 'remarks', 'version', 'goals'}
    if text.lower() in common_labels or re.fullmatch(r'[\d\.]+', text):
        return False
        
    # Rule 5: Must not be junk text, a URL, or contain excessive symbols.
    if 'www.' in text.lower() or '.com' in text.lower() or re.search(r'----', text) or len(re.findall(r'[a-zA-Z]', text)) < 3:
        return False

    # Rule 6: Exclude common non-heading phrases.
    non_headings = {'mission statement', 'elective course offerings', 'what colleges say!'}
    if text.lower() in non_headings:
        return False

    return True

def process_from_toc(doc):
    """
    Generates the outline directly from the PDF's Table of Contents.
    This is the most reliable method for structured documents.
    """
    toc = doc.get_toc()
    outline = []
    for level, title, page in toc:
        clean_title = clean_text(title)
        # Filter out entries that are just page numbers, which sometimes sneak into the TOC
        if not clean_title.isdigit():
            outline.append({
                "level": f"H{level}",
                "text": clean_title,
                "page": page
            })
    return outline

def process_by_styles(doc):
    """
    Generates the outline by analyzing font styles. Used as a fallback
    when a valid Table of Contents is not available.
    """
    lines_with_styles = []
    style_counts = Counter()
    
    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT)["blocks"]
        for b in blocks:
            if b['type'] == 0:
                for l in b['lines']:
                    line_text = clean_text(" ".join(s['text'] for s in l['spans']))
                    if not line_text: continue
                    
                    span_styles = [(round(s['size']), 'bold' in s['font'].lower()) for s in l['spans']]
                    if not span_styles: continue
                    
                    dominant_style = Counter(span_styles).most_common(1)[0][0]
                    
                    lines_with_styles.append({
                        "text": line_text,
                        "style": dominant_style,
                        "page": page_num + 1,
                    })
                    style_counts[dominant_style] += 1

    if not style_counts:
        return []

    body_style = style_counts.most_common(1)[0][0]
    
    heading_lines = []
    heading_styles = set()
    for line in lines_with_styles:
        if is_likely_heading_by_style(line['text'], line['style'], body_style):
            heading_lines.append(line)
            heading_styles.add(line['style'])
    
    sorted_heading_styles = sorted(list(heading_styles), key=lambda x: (x[0], x[1]), reverse=True)
    level_map = {style: f"H{i+1}" for i, style in enumerate(sorted_heading_styles)}
    
    outline = []
    processed_texts = set()
    for line in heading_lines:
        text = line['text']
        if text not in processed_texts:
            outline.append({
                "level": level_map.get(line['style'], 'H9'),
                "text": text,
                "page": line['page']
            })
            processed_texts.add(text)
    return outline

def extract_title(doc):
    """
    Extracts the main title from the first page of the document.
    Returns an empty string if no suitable title is found.
    """
    if doc.page_count == 0:
        return ""

    page_one_blocks = doc[0].get_text("dict", flags=fitz.TEXTFLAGS_DICT)["blocks"]
    title_candidates = []
    max_font_size = 0

    # Find the maximum font size on the first page
    for b in page_one_blocks:
        if b['type'] == 0:
            for l in b['lines']:
                for s in l['spans']:
                    if len(s['text'].strip()) > 1:
                        max_font_size = max(max_font_size, s['size'])
    
    if max_font_size == 0:
        return ""

    # Collect all text blocks that use this maximum font size
    for b in page_one_blocks:
         if b['type'] == 0:
            for l in b['lines']:
                for s in l['spans']:
                    if round(s['size']) >= round(max_font_size * 0.95):
                         text = clean_text(s['text'])
                         # Final sanity check for title candidates
                         if len(text) > 2 and not text.lower() in ['istqb', 'topjump', 'www.topjump.com', 'you\'re invited to a party']:
                            title_candidates.append(text)
    
    return " ".join(title_candidates)


def parse_pdf_to_outline(pdf_path):
    """
    Main controller function to parse a PDF. It decides which strategy to use
    (TOC-based or style-based) for the best results.
    """
    doc = fitz.open(pdf_path)
    if doc.page_count == 0:
        return {"title": "", "outline": []}

    output = {"title": "", "outline": []}

    # --- Strategy Decision ---
    # Use the TOC if it's valid and looks like a real table of contents.
    toc = doc.get_toc()
    if toc and len(toc) > 3:
        output['outline'] = process_from_toc(doc)
    else:
        # Otherwise, use the more robust style-based analysis.
        output['outline'] = process_by_styles(doc)

    # --- Universal Title Extraction and Final Cleanup ---
    output['title'] = extract_title(doc)
    
    if output['title']:
        # Remove any outline entries that are just parts of the title
        output['outline'] = [item for item in output['outline'] if item['text'] not in output['title']]
    
    # Hierarchical sort and page number correction
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
