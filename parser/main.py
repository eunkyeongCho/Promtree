from msds_down import msds_down
from multi_parsing import process_pdf_folder


if __name__ == "__main__":
    msds_down()
    process_pdf_folder("msds", "output")