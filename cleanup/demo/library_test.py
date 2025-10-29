from dotenv import load_dotenv
import promtree
import pyplum
import os


load_dotenv()

USERNAME = os.getenv("MONGO_USERNAME")
PASSWORD = os.getenv("MONGO_PASSWORD")
HOST = os.getenv("MONGO_HOST")
PORT = int(os.getenv("MONGO_PORT"))

# --------------------------
# MongoDB 연결
url = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/"

# PDF Parsing & MongoDB Insertion
pt = promtree.PromTree()
pt.set_mongodb(url, "s307_db", "s307_collection")

print("\n PDF Parsing & MongoDB Insertion Started... \n")
print("*"*50)

print("\n")

pt.insert_root_object(pyplum.get_root_object)
pt.insert_page_object(pyplum.get_page_objects)

print("\n")
print("*"*50)
print(f"PDF Parsing & MongoDB Insertion Completed!")

print("*"*50)
print("Searching Objects...")
print("*"*50)
print("\n")


# MongoDB Search
gpt_020_3m_sds_p0 = pt.search_object({"file_name": "gpt-020-3m-sds.pdf", "page_num": 0})
print("gpt_020_3m_sds_page_0\n")
print("keys: ", gpt_020_3m_sds_p0.keys())
print("file_name: ", gpt_020_3m_sds_p0["file_name"])

print("\n")

gpt_020_3m_sds_p1 = pt.search_object({"file_name": "gpt-020-3m-sds.pdf", "page_num": 1})
print("gpt_020_3m_sds_page_1\n")
print("keys: ", gpt_020_3m_sds_p1.keys())
print("file_name: ", gpt_020_3m_sds_p1["file_name"])

print("\n")

SDS11757 = pt.search_object({"file_name": "44-1206-SDS11757.pdf", "page_num": 0})
print("SDS11757_page_0\n")
print("keys: ", SDS11757.keys())
print("file_name: ", SDS11757["file_name"])

print("\n")

SDS11757_p6 = pt.search_object({"file_name": "44-1206-SDS11757.pdf", "page_num": 6})
print("SDS11757_page_6\n")
print("keys: ", SDS11757_p6.keys())
print("file_name: ", SDS11757_p6["file_name"])
print("images count: ", len(SDS11757_p6["images"]))

print("\n")

pt.close()