"""
Main script for PDF parsing, regeneration, and similarity evaluation
"""
from promtree import PromTree
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

USERNAME = os.getenv("MONGO_USERNAME")
PASSWORD = os.getenv("MONGO_PASSWORD")
HOST = os.getenv("MONGO_HOST")
PORT = int(os.getenv("MONGO_PORT"))

url = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/"

# PDF files to process
pdf_files = [
    "gpt-020-3m-sds.pdf",
    "000000001112_US_EN.pdf",
    "1658559.pdf",
    "44-1206-SDS11757.pdf"
]

# Output directory
output_dir = "evaluation_outputs"

# Create PromTree instance and connect to MongoDB
pt = PromTree()
pt.set_mongodb(url, "s307_db", "s307_collection")

# Execute complete workflow
pt.parse_all_pdfs(pdf_files)
pt.regenerate_all_pdfs(pdf_files, output_dir)
pt.eval(pdf_files, output_dir, dpi=100)

# Close connection
pt.close()
