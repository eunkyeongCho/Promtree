from pymongo.errors import ConnectionFailure
from pymongo import MongoClient
from typing import Dict, Any, Callable
import os


class PromTree:
    def __init__(self):
        self.__client = None
        self.__db = None
        self.__collection = None
        self.__storage_path = "storage"
        self.__pdfs_path = "pdfs"

        os.makedirs(self.__pdfs_path, exist_ok=True)
        os.makedirs(self.__storage_path, exist_ok=True)

    def _connect_mongodb(self, url: str) -> None:
        """
        MongoDB에 연결하기 위한 내부 함수

        Args:
            url: MongoDB 연결 URL
        """

        try:
            self.__client = MongoClient(url)
            self.__client.admin.command('ping')
            print("*"*50)
            print("Successfully connected to MongoDB!")
            print("*"*50)
            

        except ConnectionFailure as e:
            print(f"MongoDB connection failed: {e}")


    def _create_db_and_collection(self, db: str, collection: str) -> None:
        """
        MongoDB에 DB와 Collection을 생성하기 위한 내부 함수

        Args:
            db: Database 이름
            collection: Collection 이름
        """

        self.__db = self.__client[db]
        self.__collection = self.__db[collection]

        print(f" \n DB & Collection created successfully!!\n\n *** Database: {db} *** \n *** Collection: {collection} *** \n")

    

    def set_mongodb(self, url: str, db: str, collection: str) -> None:
        """
        한번에 MongoDB에 연결하고 DB와 Collection을 생성하기 위한 함수

        Args:
            url: MongoDB 연결 URL
            db: DB 이름
            collection: Collection 이름
        """

        self._connect_mongodb(url)
        self._create_db_and_collection(db, collection)


    def insert_root_object(self, root_object_callback: Callable) -> None:
        """
        MongoDB에 루트 객체를 추가하기 위한 함수

        Args:
            root_object_callback: 루트 객체 생성 콜백 함수
        """

        pdf_list = os.listdir(self.__pdfs_path)
        
        for pdf in pdf_list:
            pdf_full_path = os.path.join(self.__pdfs_path, pdf)
            root_object = root_object_callback(pdf_full_path) 
            filter = {"file_name": root_object["file_name"], "page_num": root_object["page_num"]}
            self.__collection.replace_one(filter, root_object, upsert=True)
            # print(f"File: {pdf} | Root object inserted successfully!!\n")
            print(f"***\"{pdf}\"*** \n File Parsing Started...\n")

    def insert_page_object(self, page_object_callback: Callable) -> None:
        """
        MongoDB에 페이지 객체를 추가하기 위한 함수

        Args:
            page_object_callback: 페이지 객체 생성 콜백 함수
        """

        pdf_list = os.listdir(self.__pdfs_path)

        for pdf in pdf_list:
            # 전체 경로를 전달하도록 수정
            pdf_full_path = os.path.join(self.__pdfs_path, pdf)
            page_objects = page_object_callback(pdf_full_path, self.__storage_path)
            
            for page_object in page_objects:
                filter = {"file_name": page_object["file_name"], "page_num": page_object["page_num"]}
                self.__collection.replace_one(filter, page_object, upsert=True)

            
            # print(f"File: {pdf} | Page object inserted successfully!!\n")

    def search_object(self, filter: Dict[str, Any]) -> Dict[str, Any]:
        """
        MongoDB에서 객체를 검색하기 위한 함수
        """
        return self.__collection.find_one(filter)

    def parse_all_pdfs(self, pdf_files: list = None) -> dict:
        """
        PDF 파일들을 파싱하여 MongoDB에 저장

        Args:
            pdf_files: 파싱할 PDF 파일 리스트 (None이면 pdfs 폴더 전체)

        Returns:
            결과 딕셔너리 (성공/실패 정보)
        """
        import time
        from pyplum import get_root_object, get_page_objects

        if pdf_files is None:
            pdf_files = [f for f in os.listdir(self.__pdfs_path) if f.endswith('.pdf')]

        print(f"\n{'='*70}")
        print(f"1단계: PDF 파싱 시작")
        print(f"{'='*70}\n")

        results = []

        for pdf_file in pdf_files:
            print(f"\n{'='*70}")
            print(f"Processing: {pdf_file}")
            print(f"{'='*70}")

            try:
                start_time = time.time()
                pdf_path = os.path.join(self.__pdfs_path, pdf_file)

                # Parse root object
                root_object = get_root_object(pdf_path)
                filter_root = {"file_name": root_object["file_name"], "page_num": root_object["page_num"]}
                self.__collection.replace_one(filter_root, root_object, upsert=True)

                # Parse page objects
                page_objects = get_page_objects(pdf_path, self.__storage_path)
                for page_object in page_objects:
                    filter_page = {"file_name": page_object["file_name"], "page_num": page_object["page_num"]}
                    self.__collection.replace_one(filter_page, page_object, upsert=True)

                elapsed = time.time() - start_time
                print(f"✅ Parsing completed in {elapsed:.2f}s")

                results.append({
                    'file': pdf_file,
                    'parse_time': elapsed,
                    'success': True
                })

            except Exception as e:
                print(f"❌ Error: {e}")
                results.append({
                    'file': pdf_file,
                    'success': False,
                    'error': str(e)
                })

        return {'parse_results': results}

    def regenerate_all_pdfs(self, pdf_files: list = None, output_dir: str = "evaluation_outputs") -> dict:
        """
        MongoDB 데이터로 PDF 재생성

        Args:
            pdf_files: 재생성할 PDF 파일 리스트 (None이면 전체)
            output_dir: 출력 디렉토리

        Returns:
            결과 딕셔너리
        """
        import time
        from de_parser import CoordinateBasedDeParser

        if pdf_files is None:
            pdf_files = [f for f in os.listdir(self.__pdfs_path) if f.endswith('.pdf')]

        os.makedirs(output_dir, exist_ok=True)

        print(f"\n{'='*70}")
        print(f"2단계: PDF 재생성 시작")
        print(f"{'='*70}\n")

        results = []

        for pdf_file in pdf_files:
            print(f"\n{'='*70}")
            print(f"Processing: {pdf_file}")
            print(f"{'='*70}")

            try:
                start_time = time.time()

                parser = CoordinateBasedDeParser()
                output_name = pdf_file.replace('.pdf', '_regenerated.pdf')
                output_path = os.path.join(output_dir, output_name)

                parser.generate_pdf_from_mongodb(
                    file_name=pdf_file,
                    output_path=output_path
                )
                parser.close()

                elapsed = time.time() - start_time

                # File size comparison
                original_path = os.path.join(self.__pdfs_path, pdf_file)
                if os.path.exists(original_path):
                    original_size = os.path.getsize(original_path) / 1024  # KB
                    regenerated_size = os.path.getsize(output_path) / 1024  # KB

                    results.append({
                        'file': pdf_file,
                        'original_size': original_size,
                        'regenerated_size': regenerated_size,
                        'regen_time': elapsed,
                        'success': True
                    })

                    print(f"✅ Regeneration completed in {elapsed:.2f}s")
                    print(f"   Original: {original_size:.1f} KB")
                    print(f"   Regenerated: {regenerated_size:.1f} KB")

            except Exception as e:
                print(f"❌ Error: {e}")
                results.append({
                    'file': pdf_file,
                    'success': False,
                    'error': str(e)
                })

        return {'regenerate_results': results}

    def eval(self, pdf_files: list = None, output_dir: str = "evaluation_outputs", dpi: int = 100) -> dict:
        """
        원본과 재생성된 PDF의 유사도 평가 (SSIM)

        Args:
            pdf_files: 평가할 PDF 파일 리스트
            output_dir: 재생성된 PDF가 있는 디렉토리
            dpi: 이미지 렌더링 해상도

        Returns:
            결과 딕셔너리
        """
        import fitz
        import numpy as np
        from skimage.metrics import structural_similarity as ssim

        if pdf_files is None:
            pdf_files = [f for f in os.listdir(self.__pdfs_path) if f.endswith('.pdf')]

        print(f"\n{'='*70}")
        print(f"3단계: 유사도 평가 시작 (SSIM)")
        print(f"{'='*70}\n")

        def pdf_to_images(pdf_path, dpi):
            doc = fitz.open(pdf_path)
            images = []
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)

            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=mat)
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                if pix.n == 4:
                    img = img[:, :, :3]
                images.append(img)

            doc.close()
            return images

        def compare_images(img1, img2):
            if img1.shape != img2.shape:
                h = min(img1.shape[0], img2.shape[0])
                w = min(img1.shape[1], img2.shape[1])
                img1 = img1[:h, :w]
                img2 = img2[:h, :w]

            score = ssim(img1, img2,
                         channel_axis=2,
                         data_range=255,
                         win_size=15,
                         gaussian_weights=True,
                         K1=0.02,
                         K2=0.06)
            return score

        results = []

        for pdf_file in pdf_files:
            print(f"\n{'='*70}")
            print(f"Evaluating: {pdf_file}")
            print(f"{'='*70}")

            original_path = os.path.join(self.__pdfs_path, pdf_file)
            regenerated_name = pdf_file.replace('.pdf', '_regenerated.pdf')
            regenerated_path = os.path.join(output_dir, regenerated_name)

            if not os.path.exists(original_path):
                print(f"  ❌ Original not found: {original_path}")
                continue

            if not os.path.exists(regenerated_path):
                print(f"  ❌ Regenerated not found: {regenerated_path}")
                continue

            try:
                print(f"  Converting to images (DPI={dpi})...")
                original_images = pdf_to_images(original_path, dpi)
                regenerated_images = pdf_to_images(regenerated_path, dpi)

                print(f"  Comparing {len(original_images)} pages...")

                page_scores = []
                for i, (img1, img2) in enumerate(zip(original_images, regenerated_images)):
                    score = compare_images(img1, img2)
                    page_scores.append(score)
                    print(f"    Page {i+1}: {score:.4f}")

                average_score = np.mean(page_scores)

                results.append({
                    'file': pdf_file,
                    'page_count': len(page_scores),
                    'average_score': average_score,
                    'page_scores': page_scores
                })

                print(f"\n  ✅ Average SSIM: {average_score:.4f} ({average_score*100:.2f}%)")

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

        return {'evaluation_results': results}


    def close(self):
        self.__client.close()

        print("*"*50)
        print("MongoDB connection closed successfully!!")
        print("*"*50)

