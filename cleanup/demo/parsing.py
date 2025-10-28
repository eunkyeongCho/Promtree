from pymongo.errors import ConnectionFailure
from pymongo import MongoClient
from dotenv import load_dotenv
from typing import Dict, Any
from io import BytesIO
from PIL import Image
import pdfplumber
import os

class PromisingTree:
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        self.pdf_path = None
        self.pdf = None

    def _connect_mongodb(self, URL: str):
        """
        MongoDB에 연결하기 위한 내부 함수

        Args:
            URL: MongoDB 연결 URL
        """

        try:
            self.client = MongoClient(URL)
            self.client.admin.command('ping')
            print("Successfully connected to MongoDB!")

        except ConnectionFailure as e:
            print(f"MongoDB connection failed: {e}")

    def _create_db_and_collection(self, db: str, collection: str):
        """
        MongoDB에 DB와 Collection을 생성하기 위한 내부 함수

        Args:
            db: DB 이름
            collection: Collection 이름
        """

        self.db = self.client[db]
        self.collection = self.db[collection]

        print(f"DB: {db} and Collection: {collection} created successfully")
    
    def set_mongodb(self, URL: str, db: str, collection: str):
        """
        한번에 MongoDB에 연결하고 DB와 Collection을 생성하기 위한 함수

        Args:
            URL: MongoDB 연결 URL
            db: DB 이름
            collection: Collection 이름
        """

        self._connect_mongodb(URL)
        self._create_db_and_collection(db, collection)

    def insert_object(self, object: Dict[str, Any]):
        """
        MongoDB에 Object를 추가하기 위한 함수

        Args:
            object: 추가할 Object
        """

        result = self.collection.insert_one(object)

        print(f"Object inserted successfully!!\n ID: {result.inserted_id}")

    def search_object(self, filter: Dict[str, Any]):
        """
        MongoDB에서 Object를 조회하기 위한 함수

        Args:
            filter: 조회할 Object의 필터

        Returns:
            object: 조회된 Object
        """

        object = self.collection.find_one(filter)

        print(f"Object searched successfully!!")

        return object

    def set_pdf(self, pdf_path: str):
        """
        파일 경로를 등록하는 함수

        Args:
            pdf_path: 사용할 pdf의 경로        
        """
        self.pdf_path = pdf_path
        self.pdf = pdfplumber.open(pdf_path)

    def _get_root_object(self):
        """
        PDFPlumber를 사용하여 PDF 파일을 파싱하여 Root Object를 생성하는 내부 함수

        Returns:
            root_object: Root Object
        """

        # Root Object 생성
        root_object = {
            "file_name": self.pdf_path.split("/")[-1],
            "page_num": 0,
            "page_count": len(self.pdf.pages),
            "width": self.pdf.pages[0].width,
            "height": self.pdf.pages[0].height
        }

        return root_object

    def make_image_doc_serializable(self, page_num: int, img: dict) -> dict:
        """
        직렬화 되지 않는 이미지 정보 처리 + 이미지 저장 + url 추가

        Args:
            page_num: 페이지 번호
            img: 이미지 객체

        Returns:
            out: 직렬화된 이미지 객체
        """
        # 이미지 폴더 생성 (없으면 자동 생성)
        os.makedirs("images", exist_ok=True)

        # png 제작을 위한 이미지 정보 추출
        img_id = str(img['name'])
        img_data = img['stream'].get_data()    # 바이트
        img_info = img['stream'].attrs
        img_width = int(img_info['Width'])
        img_height = int(img_info['Height'])
        img_bits = int(img_info['BitsPerComponent'])

        img_colorspace = str(img_info['ColorSpace']).lstrip('/').upper()
        print(img_colorspace[:10])
        img_filter_raw = img_info.get('Filter')
        img_filters = (
            [] if img_filter_raw is None
            else ([str(x).lstrip('/').strip(" '\"").upper() for x in img_filter_raw]
                if isinstance(img_filter_raw, (list, tuple))
                else [str(img_filter_raw).lstrip('/').strip(" '\"").upper()])
        )
        has_jpeg_like = any(f in ('DCTDECODE', 'JPXDECODE') for f in img_filters)

        # 이미지 모드 설정
        if img_colorspace in ('RGB', 'DEVICERGB'):
            img_mode = 'RGB'
        elif img_colorspace in ('GRAY', 'DEVICEGRAY'):
            img_mode = '1' if img_bits == 1 else 'L'
        elif img_colorspace in ('CMYK', 'DEVICECMYK'):
            img_mode = 'CMYK'
        else:
            img_mode = 'RGB'
            
        img_size = (img_width, img_height)

        # filter별 이미지 처리
        if has_jpeg_like:
            print("jpeg 이미지 발견\n")
            try:
                pil_image = Image.open(BytesIO(img_data))
                pil_image = pil_image.convert('RGB')
                pil_image.save(f"images/{self.pdf_path.split("/")[-1]}_{page_num}_{img_id}.png")
                img_url = str(f"images/{self.pdf_path.split("/")[-1]}_{page_num}_{img_id}.png")
                print(f"{img_id} 이미지 저장 완료\n")
            except Exception as e:
                print(f"이미지 저장 오류: {e}")
                img_url = None
        else:
            print("그 외 이미지 발견\n")
            try:
                pil_image = Image.frombytes(img_mode, img_size, img_data)
                pil_image = pil_image.convert('RGB')
                pil_image.save(f"images/{self.pdf_path.split("/")[-1]}_{page_num}_{img_id}.png")
                img_url = str(f"images/{self.pdf_path.split("/")[-1]}_{page_num}_{img_id}.png")
                print(f"{img_id} 이미지 저장 완료\n")
            except Exception as e:
                print(f"이미지 저장 오류: {e}")
                img_url = None
            
        
        out = {k: v for k, v in img.items() if k != "stream"}  # stream 제거
        if "colorspace" in out:
            out["colorspace"] = [str(cs).lstrip("/") for cs in out["colorspace"]]
        if isinstance(out.get("srcsize"), tuple):
            out["srcsize"] = list(out["srcsize"])

        out['url'] = img_url
        return out


    def _get_page_objects(self, page_num: int) -> Dict[str, Any]:
        """
        원하는 페이지의 Page Object를 추출 및 전처리하는 내부 함수

        Args:
            page_num: 원하는 페이지 번호

        Returns:
            page_object: Page Object
        """

        page = self.pdf.pages[page_num - 1]

        # key 추출
        keys = list(page.objects.keys())

        image_objects = []
        if "image" in keys:
            previous_image_objects = page.images.copy()
            for image in previous_image_objects:
                new_image_object = self.make_image_doc_serializable(page_num, image)
                image_objects.append(new_image_object)

        # Page Object 생성
        page_object = {
            "file_name": self.pdf_path.split("/")[-1],
            "page_num": page_num,
            "keys": keys,
            **({"lines": page.lines} if "line" in keys else {}),
            **({"rects": page.rects} if "rect" in keys else {}),
            **({"chars": page.chars} if "char" in keys else {}),
            **({"curves": page.curves} if "curve" in keys else {}),
            **({"images": image_objects} if "image" in keys else {})
        }

        return page_object

    def pdfplumber_parsing(self):
        """
        PDFPlumber를 사용하여 PDF 파일을 파싱하는 함수
        """
        # Root Object 추출
        root_object = self._get_root_object()
        self.insert_object(root_object)

        # Page Object 추출
        for page_idx in range(len(self.pdf.pages)):
            page_object = self._get_page_objects(page_idx + 1)
            self.insert_object(page_object)
        
        print("PDF parsing completed successfully!!")


    def close(self):
        self.client.close()
        print("MongoDB connection closed successfully!!")
        self.pdf.close()
        print("PDF file closed successfully!!")



# 사용 예시
if __name__ == "__main__":
    # 환경 변수 로드
    load_dotenv()

    USERNAME = os.getenv("MONGO_USERNAME")
    PASSWORD = os.getenv("MONGO_PASSWORD")
    HOST = os.getenv("MONGO_HOST")
    PORT = int(os.getenv("MONGO_PORT"))

    # --------------------------
    # MongoDB 연결
    url = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/"
    
    pt = PromisingTree()

    pt.set_mongodb(url, "s307_db", "s307_collection")

    pt.set_pdf("gpt-020-3m-sds.pdf")

    pt.pdfplumber_parsing()

    page0_object = pt.search_object({"file_name": "gpt-020-3m-sds.pdf", "page_num": 0})
    
    print("\n--------------------------------")
    print("page0_object")
    print("--------------------------------")

    print(page0_object.keys())

    page1_object = pt.search_object({"file_name": "gpt-020-3m-sds.pdf", "page_num": 1})
    
    print("\n--------------------------------")
    print("page1_object")
    print("--------------------------------")

    print(page1_object.keys())

    page12_object = pt.search_object({"file_name": "gpt-020-3m-sds.pdf", "page_num": 12})
    
    print("\n--------------------------------")
    print("page12_object")
    print("--------------------------------")

    if page12_object:
        print(page12_object.keys())
    else:
        print("page12_object not found")

    pt.close()