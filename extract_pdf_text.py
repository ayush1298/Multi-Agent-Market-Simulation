from pypdf import PdfReader
import sys
import os

pdf_path = "/Users/ayushmunot/Multi-Agent-Market-Simulation/Multi-Agent Simulation for Pricing and Hedging ina Dealer Market.pdf"
output_path = "paper_content.txt"

if not os.path.exists(pdf_path):
    print(f"Error: File not found at {pdf_path}")
    sys.exit(1)

try:
    reader = PdfReader(pdf_path)
    text = ""
    for i, page in enumerate(reader.pages):
        text += f"--- Page {i+1} ---\n"
        text += page.extract_text() + "\n"
    
    with open(output_path, "w") as f:
        f.write(text)
    print(f"Successfully extracted {len(text)} characters to {output_path}")
except Exception as e:
    print(f"Error extracting text: {e}")
