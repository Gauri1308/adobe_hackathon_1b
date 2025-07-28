import json
import sys
import os
from datetime import datetime
import PyPDF2
import re
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import nltk
import argparse
import warnings
warnings.filterwarnings("ignore")

class DocumentAnalyzer:
    def __init__(self):
        # Download NLTK data if needed
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
        
        # Load lightweight model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def extract_pdf_text(self, pdf_path):
        """Extract text from PDF with page tracking"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                pages = {}
                for i, page in enumerate(reader.pages, 1):
                    text = page.extract_text()
                    if text.strip():
                        pages[i] = text
                return {
                    'filename': os.path.basename(pdf_path),
                    'pages': pages
                }
        except Exception as e:
            print(f"Error reading {pdf_path}: {e}")
            return {'filename': os.path.basename(pdf_path), 'pages': {}}
    
    def segment_text(self, text, page_num):
        """Split text into sections"""
        # Simple paragraph-based segmentation
        paragraphs = text.split('\n\n')
        sections = []
        
        for i, para in enumerate(paragraphs):
            if len(para.strip()) > 100:  # Min length threshold
                sections.append({
                    'title': f'Section {i+1}',
                    'content': para.strip(),
                    'page': page_num
                })
        return sections
    
    def calculate_relevance(self, text, persona, job):
        """Calculate relevance score"""
        query = f"{persona} {job}"
        
        # Semantic similarity
        query_emb = self.model.encode([query])
        text_emb = self.model.encode([text])
        similarity = cosine_similarity(query_emb, text_emb)[0][0]
        
        # Keyword matching
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        keyword_score = len(query_words.intersection(text_words)) / len(query_words) if query_words else 0
        
        # Combined score
        return 0.7 * similarity + 0.3 * keyword_score
    
    def refine_text(self, text, max_length=400):
        """Summarize text content"""
        if len(text) <= max_length:
            return text
        
        sentences = nltk.sent_tokenize(text)
        if not sentences:
            return text[:max_length] + "..."
        
        # Take first and last sentences, fill middle
        result = [sentences[0]]
        remaining_length = max_length - len(sentences[0])
        
        for sentence in sentences[1:-1]:
            if len(' '.join(result + [sentence])) <= max_length - len(sentences[-1]):
                result.append(sentence)
        
        if len(sentences) > 1:
            result.append(sentences[-1])
        
        return ' '.join(result)
    
    def process(self, input_data):
        """Main processing function"""
        start_time = datetime.now()
        
        documents = input_data['documents']
        persona = input_data['persona']
        job = input_data['job_to_be_done']
        
        all_sections = []
        
        # Process each document
        for doc_path in documents:
            if not os.path.exists(doc_path):
                print(f"Warning: {doc_path} not found")
                continue
            
            doc_data = self.extract_pdf_text(doc_path)
            
            for page_num, page_text in doc_data['pages'].items():
                sections = self.segment_text(page_text, page_num)
                
                for section in sections:
                    relevance = self.calculate_relevance(section['content'], persona, job)
                    
                    all_sections.append({
                        'document': doc_data['filename'],
                        'page_number': page_num,
                        'section_title': section['title'],
                        'content': section['content'],
                        'relevance_score': relevance
                    })
        
        # Sort by relevance and take top 10
        all_sections.sort(key=lambda x: x['relevance_score'], reverse=True)
        top_sections = all_sections[:10]
        
        # Create output
        extracted_sections = []
        subsection_analysis = []
        
        for i, section in enumerate(top_sections, 1):
            extracted_sections.append({
                "document": section['document'],
                "page_number": section['page_number'],
                "section_title": section['section_title'],
                "importance_rank": i
            })
            
            refined_text = self.refine_text(section['content'])
            subsection_analysis.append({
                "document": section['document'],
                "section_title": section['section_title'],
                "refined_text": refined_text,
                "page_number": section['page_number']
            })
        
        return {
            "metadata": {
                "input_documents": [os.path.basename(doc) for doc in documents],
                "persona": persona,
                "job_to_be_done": job,
                "processing_timestamp": start_time.isoformat()
            },
            "extracted_sections": extracted_sections,
            "subsection_analysis": subsection_analysis
        }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Input JSON file')
    parser.add_argument('--output', required=True, help='Output JSON file')
    args = parser.parse_args()
    
    # Load input
    with open(args.input, 'r') as f:
        input_data = json.load(f)
    
    # Process
    analyzer = DocumentAnalyzer()
    result = analyzer.process(input_data)
    
    # Save output
    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"Processing complete. Output saved to {args.output}")

if __name__ == "__main__":
    main()
