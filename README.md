PDF Outline Extractor - Adobe Hackathon 2025(Challenge_1a)

🎯 **Project Overview**  

This project is the solution to the challenge_1a that  tackles the challenge of extracting structured outlines from PDF documents for Adobe's hackathon. Instead of simply reading PDFs, our solution intelligently parses documents to understand their hierarchical structure, extracting titles and headings (H1, H2, H3) in a clean, machine-readable format.

📋 **Problem Statement**  

Challenge: Extract structured outlines from PDF documents (up to 50 pages) that can serve as the foundation for advanced document processing and AI applications.
Input: PDF files
Output: Structured JSON with title and hierarchical headings

🛠️ **Solution Architecture**

Our solution employs a dual-strategy approach for maximum reliability:

**Strategy 1: Table of Contents (TOC) Based**

When: Document has a built-in Table of Contents
How: Directly extracts from PDF's TOC metadata
Advantage: Most accurate for properly structured documents

**Strategy 2: Style-Based Analysis**

When: No valid TOC available (fallback method)
How: Analyzes font sizes, weights, and formatting patterns
Features:

Intelligent body text detection
Rule-based heading identification
Style hierarchy mapping
Noise filtering (URLs, form labels, excessive symbols)



**Key Features**

Smart Title Extraction: Identifies main title from first page using largest font size
Hierarchical Processing: Maintains proper H1, H2, H3 level relationships
Robust Filtering: Eliminates false positives like form fields, URLs, and junk text
Page-Accurate Mapping: Precise page number tracking for each heading

**📁 Project Structure**

<img width="680" height="236" alt="image" src="https://github.com/user-attachments/assets/dda800f5-1424-4aaa-8982-a27543c6d0aa" />



**🔧 Technical Implementation**

Dependencies

PyMuPDF (fitz): PDF parsing and text extraction
Python 3.10: Runtime environment
Standard libraries: json, pathlib, collections, re, statistics

### 🔧 Core Functions

- `parse_pdf_to_outline()`: Main controller function  
- `process_from_toc()`: TOC-based extraction  
- `process_by_styles()`: Style-based analysis  
- `extract_title()`: Title identification  
- `is_likely_heading_by_style()`: Heading validation  
- `clean_text()`: Text preprocessing
  
**🐳 Docker Setup**

Build Image
bashdocker build --platform linux/amd64 -t pdf-outline-extractor:v1.0 .
Run Container
bashdocker run --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  --network none \
  pdf-outline-extractor:v1.0

**Steps to run this project**

Clone/Download this project
Place PDF files in the input/ directory
Build the Docker image:
docker build --platform linux/amd64 -t pdf-outline-extractor:v1.0 .

Run the extraction:
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none pdf-outline-extractor:v1.0

Check results in the output/ directory  
