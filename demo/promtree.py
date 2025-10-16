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

    def eval(self):
        pass


    def close(self):
        self.__client.close()

        print("*"*50)
        print("MongoDB connection closed successfully!!")
        print("*"*50)

