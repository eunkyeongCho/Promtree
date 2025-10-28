"""
Coordinate-based PDF De-parser
Reads pdfplumber JSON data from MongoDB and recreates PDF with exact positioning
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pymongo import MongoClient
from dotenv import load_dotenv
import os


class CoordinateBasedDeParser:
    """
    PDF 재생성기: pdfplumber가 추출한 좌표 기반 JSON을 읽어서 PDF 재생성
    """

    def __init__(self, mongo_uri=None):
        """
        Initialize de-parser with MongoDB connection

        Args:
            mongo_uri: MongoDB connection string (optional, will use .env if not provided)
        """
        if mongo_uri is None:
            load_dotenv()
            username = os.getenv('MONGO_USERNAME')
            password = os.getenv('MONGO_PASSWORD')
            host = os.getenv('MONGO_HOST')
            port = int(os.getenv('MONGO_PORT'))
            mongo_uri = f'mongodb://{username}:{password}@{host}:{port}/'

        self.client = MongoClient(mongo_uri)
        self.db = self.client['s307_db']
        self.collection = self.db['s307_collection']

        # Initialize font mapping and registered font tracking
        self._setup_font_mapping()
        self.registered_fonts = {}  # Track already registered fonts

    def _setup_font_mapping(self):
        """
        Setup OS-aware font mapping for different font families
        Combines Windows font_mapping from unparser.ipynb with macOS/Linux support
        """
        import platform

        system = platform.system()

        # 기본 폰트 정의 (Fallback용 - Helvetica는 한글 미지원하므로 한글 폰트 사용)
        DEFAULT_FONT = 'MalgunGothic-Fallback'

        # OS별 폰트 매핑 설정
        if system == 'Windows':
            self.font_mapping = {
                'DotumChe': {
                    'normal': 'C:/Windows/Fonts/gulim.ttc',
                    'bold': 'C:/Windows/Fonts/malgunbd.ttf',
                },
                'Dotum': {
                    'normal': 'C:/Windows/Fonts/gulim.ttc',
                    'bold': 'C:/Windows/Fonts/malgunbd.ttf',
                },
                'Malgun': {
                    'normal': 'C:/Windows/Fonts/malgun.ttf',
                    'bold': 'C:/Windows/Fonts/malgunbd.ttf',
                },
            }
            default_font_path = 'C:/Windows/Fonts/malgun.ttf'

        elif system == 'Darwin':  # macOS
            # macOS 시스템 폰트 사용
            self.font_mapping = {
                'DotumChe': {
                    'normal': '/System/Library/Fonts/Supplemental/AppleGothic.ttf',
                    'bold': '/System/Library/Fonts/Supplemental/AppleGothic.ttf',
                },
                'Dotum': {
                    'normal': '/System/Library/Fonts/Supplemental/AppleGothic.ttf',
                    'bold': '/System/Library/Fonts/Supplemental/AppleGothic.ttf',
                },
                'Malgun': {
                    'normal': '/System/Library/Fonts/Supplemental/AppleGothic.ttf',
                    'bold': '/System/Library/Fonts/Supplemental/AppleGothic.ttf',
                },
            }
            default_font_path = '/System/Library/Fonts/Supplemental/AppleGothic.ttf'

        else:  # Linux
            self.font_mapping = {
                'DotumChe': {
                    'normal': '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
                    'bold': '/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf',
                },
                'Dotum': {
                    'normal': '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
                    'bold': '/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf',
                },
                'Malgun': {
                    'normal': '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
                    'bold': '/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf',
                },
            }
            default_font_path = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'

        # Register default fallback font
        try:
            pdfmetrics.registerFont(TTFont(DEFAULT_FONT, default_font_path))
            self.default_font = DEFAULT_FONT
            print(f"Default font registered: {DEFAULT_FONT} from {default_font_path} (OS: {system})")
        except Exception as e:
            # 폰트 등록 실패 시에도 DEFAULT_FONT 사용 (나중에 등록 시도)
            self.default_font = DEFAULT_FONT
            print(f"Warning: Failed to register {DEFAULT_FONT}, will retry on first use (OS: {system})")

    def register_font_from_db(self, fontname):
        """
        Register font dynamically based on DB fontname
        Analyzes fontname like "FAAAAH+DotumChe,Bold" and registers appropriate font file

        Args:
            fontname: Font name from PDF (e.g., "FAAAAH+DotumChe,Bold")

        Returns:
            Registered font name to use with ReportLab
        """
        # Already registered or no fontname
        if not fontname or fontname in self.registered_fonts:
            return self.registered_fonts.get(fontname, self.default_font)

        # Parse DB fontname
        # Example: "FAAAAH+DotumChe,Bold" -> base="DotumChe", is_bold=True
        parts = fontname.split('+')[-1]  # Remove subset prefix (e.g., "FAAAAH+")
        is_bold = 'Bold' in parts or 'bold' in parts
        base_font = parts.split(',')[0]  # Extract base font name

        # Find matching font file from mapping
        font_file = None
        for key in self.font_mapping:
            if key in base_font:
                if is_bold and 'bold' in self.font_mapping[key]:
                    font_file = self.font_mapping[key]['bold']
                else:
                    font_file = self.font_mapping[key]['normal']
                break

        # Try to register the font
        if font_file and os.path.exists(font_file):
            try:
                pdfmetrics.registerFont(TTFont(fontname, font_file))
                self.registered_fonts[fontname] = fontname
                return fontname
            except Exception as e:
                # Registration failed, use default
                self.registered_fonts[fontname] = self.default_font
                return self.default_font
        else:
            # Font file not found, use default
            self.registered_fonts[fontname] = self.default_font
            return self.default_font

    def _convert_y_coordinate(self, y, page_height):
        """
        Convert pdfplumber coordinate (top-origin) to reportlab coordinate (bottom-origin)

        pdfplumber: (0,0) is top-left
        reportlab: (0,0) is bottom-left

        Args:
            y: Y coordinate from pdfplumber
            page_height: Total page height

        Returns:
            Converted Y coordinate for reportlab
        """
        return page_height - y

    def _draw_chars(self, c, chars, page_height):
        """
        Draw text characters at exact coordinates

        Args:
            c: ReportLab canvas
            chars: List of character objects from pdfplumber
            page_height: Page height for coordinate conversion
        """
        for char in chars:
            text = char['text']
            x0 = char['x0']
            y0 = char['y0']  # PDF coordinate (bottom-up) - use directly!

            # Get font info
            fontname = char.get('fontname', None)
            font_size = char.get('size', 10)

            # Get color info
            non_stroking_color = char.get('non_stroking_color', None)
            stroking_color = char.get('stroking_color', None)

            try:
                # Set font - use register_font_from_db for better font matching
                if fontname:
                    font_to_use = self.register_font_from_db(fontname)
                    c.setFont(font_to_use, font_size)
                else:
                    c.setFont(self.default_font, font_size)

                # Set text fill color (non_stroking_color)
                if non_stroking_color is not None:
                    if isinstance(non_stroking_color, (tuple, list)):
                        if len(non_stroking_color) == 3:
                            c.setFillColorRGB(*non_stroking_color)
                        elif len(non_stroking_color) == 1:
                            c.setFillGray(non_stroking_color[0])
                    elif isinstance(non_stroking_color, (int, float)):
                        c.setFillGray(non_stroking_color)
                else:
                    # Default to black
                    c.setFillColorRGB(0, 0, 0)

                # Set text stroke color
                if stroking_color is not None:
                    if isinstance(stroking_color, (tuple, list)):
                        if len(stroking_color) == 3:
                            c.setStrokeColorRGB(*stroking_color)
                        elif len(stroking_color) == 1:
                            c.setStrokeGray(stroking_color[0])
                    elif isinstance(stroking_color, (int, float)):
                        c.setStrokeGray(stroking_color)

                # Draw text - use y0 directly (both PDF and reportlab use bottom-up coords)
                try:
                    c.drawString(x0, y0, text)
                except Exception as inner_e:
                    # 렌더링 실패 시 특수문자 대체 시도
                    # ∙ (U+2219) → · (U+00B7) 또는 • (U+2022)
                    fallback_text = text.replace('\u2219', '\u00B7').replace('\u2219', '\u2022')
                    try:
                        c.drawString(x0, y0, fallback_text)
                    except:
                        # 최종 실패 시 건너뛰기
                        continue

            except Exception as e:
                # Skip if rendering fails
                continue

    def _draw_lines(self, c, lines, page_height):
        """
        Draw lines at exact coordinates

        Args:
            c: ReportLab canvas
            lines: List of line objects from pdfplumber
            page_height: Page height for coordinate conversion
        """
        for line in lines:
            x0 = line['x0']
            x1 = line['x1']
            y0_pdf = line['y0']  # PDF coordinate (bottom-up)
            y1_pdf = line['y1']  # PDF coordinate (bottom-up)
            linewidth = line.get('linewidth', 1)
            stroke_color = line.get('stroking_color')

            # Convert PDF coordinates (bottom-up) to reportlab coordinates
            # PDF y-axis starts from bottom, reportlab also starts from bottom
            # So we can use y0_pdf and y1_pdf directly!
            y0_converted = y0_pdf
            y1_converted = y1_pdf

            # Set line properties
            c.setLineWidth(linewidth)

            if stroke_color is not None:
                if isinstance(stroke_color, (list, tuple)) and len(stroke_color) >= 3:
                    c.setStrokeColorRGB(stroke_color[0], stroke_color[1], stroke_color[2])
                elif isinstance(stroke_color, (int, float)):
                    c.setStrokeGray(stroke_color)

            # Draw line
            c.line(x0, y0_converted, x1, y1_converted)

    def _draw_rects(self, c, rects, page_height):
        """
        Draw rectangles at exact coordinates

        Args:
            c: ReportLab canvas
            rects: List of rect objects from pdfplumber
            page_height: Page height for coordinate conversion
        """
        for rect in rects:
            x0 = rect['x0']
            y0 = rect['y0']  # PDF coordinate (bottom-up) - use directly!
            width = rect['width']
            height = rect['height']
            linewidth = rect.get('linewidth', 1)
            stroke = rect.get('stroke', True)
            fill = rect.get('fill', False)
            stroke_color = rect.get('stroking_color')
            fill_color = rect.get('non_stroking_color')

            # Use y0 directly (both PDF and reportlab use bottom-up coordinates)
            y_bottom = y0

            # Set line properties
            c.setLineWidth(linewidth)

            # Set stroke color
            if stroke_color is not None:
                if isinstance(stroke_color, (list, tuple)) and len(stroke_color) >= 3:
                    c.setStrokeColorRGB(stroke_color[0], stroke_color[1], stroke_color[2])
                elif isinstance(stroke_color, (int, float)):
                    # Grayscale value
                    c.setStrokeGray(stroke_color)
                else:
                    c.setStrokeColorRGB(0, 0, 0)
            else:
                c.setStrokeColorRGB(0, 0, 0)

            # Set fill color
            if fill_color is not None:
                if isinstance(fill_color, (list, tuple)) and len(fill_color) >= 3:
                    c.setFillColorRGB(fill_color[0], fill_color[1], fill_color[2])
                elif isinstance(fill_color, (int, float)):
                    # Grayscale value
                    c.setFillGray(fill_color)
                else:
                    c.setFillColorRGB(1, 1, 1)
            else:
                c.setFillColorRGB(1, 1, 1)

            # Draw rectangle
            if fill and stroke:
                c.rect(x0, y_bottom, width, height, stroke=1, fill=1)
            elif fill:
                c.rect(x0, y_bottom, width, height, stroke=0, fill=1)
            elif stroke:
                c.rect(x0, y_bottom, width, height, stroke=1, fill=0)

    def _draw_images(self, c, images, page_height):
        """
        Draw images at exact coordinates

        Args:
            c: ReportLab canvas
            images: List of image objects from pdfplumber
            page_height: Page height for coordinate conversion
        """
        import base64
        import io
        from PIL import Image

        for img_data in images:
            x0 = img_data['x0']
            y0 = img_data['y0']  # PDF coordinate (bottom-up) - use directly!
            width = img_data['width']
            height = img_data['height']

            # Use y0 directly (both PDF and reportlab use bottom-up coordinates)
            y_bottom = y0

            # Try to load image from two sources:
            # 1. base64 encoded data (from parser.py)
            # 2. file path (from parsing.py)
            pil_image = None

            # Method 1: base64 image_data
            if 'image_data' in img_data:
                try:
                    image_bytes = base64.b64decode(img_data['image_data'])
                    pil_image = Image.open(io.BytesIO(image_bytes))
                except Exception as e:
                    print(f"Warning: Failed to decode base64 image: {e}")

            # Method 2: file path (url)
            elif 'url' in img_data and img_data['url']:
                try:
                    image_path = img_data['url']
                    if os.path.exists(image_path):
                        pil_image = Image.open(image_path)
                    else:
                        print(f"Warning: Image file not found: {image_path}")
                except Exception as e:
                    print(f"Warning: Failed to load image from {img_data.get('url')}: {e}")

            # Draw image if loaded successfully
            if pil_image:
                try:
                    c.drawInlineImage(pil_image, x0, y_bottom, width, height, preserveAspectRatio=False)
                except Exception as e:
                    print(f"Warning: Failed to draw image at ({x0}, {y_bottom}): {e}")

    def generate_pdf_from_mongodb(self, file_name, output_path):
        """
        Generate PDF from MongoDB data

        Args:
            file_name: Original PDF filename stored in MongoDB
            output_path: Path to save regenerated PDF
        """
        # Get root document to find page count and dimensions
        root_doc = self.collection.find_one({'file_name': file_name, 'page_num': 0})
        if not root_doc:
            raise ValueError(f"No root document found for {file_name}")

        page_count = root_doc['page_count']

        # Use original PDF dimensions from parsing.py
        if 'width' in root_doc and 'height' in root_doc:
            page_width = root_doc['width']
            page_height = root_doc['height']
        else:
            # Fallback to A4 if dimensions not found
            page_width, page_height = A4
            print("Warning: Page dimensions not found in root document, using A4")

        # Create PDF canvas with original page size
        c = canvas.Canvas(output_path, pagesize=(page_width, page_height))

        print(f"Regenerating PDF: {file_name}")
        print(f"Total pages: {page_count}")
        print(f"Page size: {page_width} x {page_height}")

        # Process each page
        for page_num in range(1, page_count + 1):
            print(f"Processing page {page_num}/{page_count}...")

            # Get page data from MongoDB
            page_doc = self.collection.find_one({'file_name': file_name, 'page_num': page_num})
            if not page_doc:
                print(f"Warning: Page {page_num} not found in database")
                continue

            # Draw in correct order: rects/lines first (background), then text (foreground)

            # Draw rects first (background)
            if 'rects' in page_doc:
                self._draw_rects(c, page_doc['rects'], page_height)

            # Draw lines
            if 'lines' in page_doc:
                self._draw_lines(c, page_doc['lines'], page_height)

            # Draw images (between rects/lines and text)
            if 'images' in page_doc and page_doc['images']:
                self._draw_images(c, page_doc['images'], page_height)

            # Draw characters on top
            if 'chars' in page_doc:
                self._draw_chars(c, page_doc['chars'], page_height)

            # Finish page
            c.showPage()

        # Save PDF
        c.save()
        print(f"PDF saved to: {output_path}")

    def close(self):
        """Close MongoDB connection"""
        self.client.close()


def main():
    """Main function for testing"""
    parser = CoordinateBasedDeParser()

    try:
        # Generate PDF from MongoDB data
        parser.generate_pdf_from_mongodb(
            file_name='gpt-020-3m-sds.pdf',
            output_path='reregenerated_output.pdf'
        )
    finally:
        parser.close()


if __name__ == '__main__':
    main()
