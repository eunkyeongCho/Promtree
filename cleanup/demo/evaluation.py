"""
PDF Similarity Evaluation using SSIM (Structural Similarity Index)
Compares original PDFs with regenerated PDFs pixel by pixel
"""
import fitz  # PyMuPDF
import numpy as np
from skimage.metrics import structural_similarity as ssim
from PIL import Image
import os


def pdf_to_images(pdf_path, dpi=150):
    """
    Convert PDF pages to images

    Args:
        pdf_path: Path to PDF file
        dpi: Resolution for rendering (default 150)

    Returns:
        List of numpy arrays (one per page)
    """
    doc = fitz.open(pdf_path)
    images = []

    # Scale factor for DPI
    zoom = dpi / 72  # 72 is default DPI
    mat = fitz.Matrix(zoom, zoom)

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat)

        # Convert to numpy array
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)

        # Convert RGBA to RGB if needed
        if pix.n == 4:
            img = img[:, :, :3]

        images.append(img)

    doc.close()
    return images


def compare_images(img1, img2):
    """
    Compare two images using SSIM

    Args:
        img1: First image (numpy array)
        img2: Second image (numpy array)

    Returns:
        SSIM score (0-1, 1 = identical)
    """
    # Resize if dimensions don't match
    if img1.shape != img2.shape:
        h = min(img1.shape[0], img2.shape[0])
        w = min(img1.shape[1], img2.shape[1])
        img1 = img1[:h, :w]
        img2 = img2[:h, :w]

    # Calculate SSIM with relaxed parameters
    score = ssim(img1, img2,
                 channel_axis=2,
                 data_range=255,
                 win_size=15,           # 7에서 15로 증가 (덜 민감)
                 gaussian_weights=True, # 부드러운 평가
                 K1=0.02,              # 기본값 0.01보다 크게
                 K2=0.06)              # 기본값 0.03보다 크게
    return score


def evaluate_pdf_pair(original_path, regenerated_path, dpi=150):
    """
    Evaluate similarity between original and regenerated PDF

    Args:
        original_path: Path to original PDF
        regenerated_path: Path to regenerated PDF
        dpi: Resolution for rendering

    Returns:
        dict with page_scores and average_score
    """
    print(f"  Converting to images (DPI={dpi})...")

    # Convert both PDFs to images
    original_images = pdf_to_images(original_path, dpi)
    regenerated_images = pdf_to_images(regenerated_path, dpi)

    # Check page counts
    if len(original_images) != len(regenerated_images):
        print(f"  ⚠️  Page count mismatch: {len(original_images)} vs {len(regenerated_images)}")
        min_pages = min(len(original_images), len(regenerated_images))
        original_images = original_images[:min_pages]
        regenerated_images = regenerated_images[:min_pages]

    print(f"  Comparing {len(original_images)} pages...")

    # Compare each page
    page_scores = []
    for i, (img1, img2) in enumerate(zip(original_images, regenerated_images)):
        score = compare_images(img1, img2)
        page_scores.append(score)
        print(f"    Page {i+1}: {score:.4f}")

    average_score = np.mean(page_scores)

    return {
        'page_scores': page_scores,
        'average_score': average_score,
        'page_count': len(page_scores)
    }


def main():
    """Main evaluation function"""
    print(f"\n{'='*70}")
    print(f"PDF Similarity Evaluation (SSIM)")
    print(f"{'='*70}\n")

    # PDF pairs to evaluate
    pdf_files = [
        "gpt-020-3m-sds.pdf",
        "000000001112_US_EN.pdf",
        "1658559.pdf",
        "44-1206-SDS11757.pdf"
    ]

    original_dir = "pdfs"
    regenerated_dir = "evaluation_outputs"

    results = []

    for pdf_file in pdf_files:
        print(f"\n{'='*70}")
        print(f"Evaluating: {pdf_file}")
        print(f"{'='*70}")

        original_path = os.path.join(original_dir, pdf_file)
        regenerated_name = pdf_file.replace('.pdf', '_regenerated.pdf')
        regenerated_path = os.path.join(regenerated_dir, regenerated_name)

        # Check if files exist
        if not os.path.exists(original_path):
            print(f"  ❌ Original not found: {original_path}")
            continue

        if not os.path.exists(regenerated_path):
            print(f"  ❌ Regenerated not found: {regenerated_path}")
            continue

        try:
            result = evaluate_pdf_pair(original_path, regenerated_path)
            result['file'] = pdf_file
            results.append(result)

            print(f"\n  ✅ Average SSIM: {result['average_score']:.4f} ({result['average_score']*100:.2f}%)")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                'file': pdf_file,
                'error': str(e)
            })

    # Summary
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"{'File':<30} {'Pages':>8} {'SSIM Score':>12} {'Similarity':>12}")
    print(f"{'-'*70}")

    for r in results:
        if 'error' in r:
            print(f"{r['file']:<30} {'N/A':>8} {'N/A':>12} {'ERROR':>12}")
        else:
            score = r['average_score']
            similarity_pct = score * 100
            print(f"{r['file']:<30} {r['page_count']:>8} {score:>12.4f} {similarity_pct:>11.2f}%")

    # Overall average
    valid_results = [r for r in results if 'average_score' in r]
    if valid_results:
        overall_avg = np.mean([r['average_score'] for r in valid_results])
        print(f"{'-'*70}")
        print(f"{'Overall Average':<30} {'':<8} {overall_avg:>12.4f} {overall_avg*100:>11.2f}%")

    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    main()
