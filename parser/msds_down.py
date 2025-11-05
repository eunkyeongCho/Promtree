from pathlib import Path
import gdown
import zipfile



def msds_down() -> None:
    """
    Google Drive에서 MSDS Zip 파일 다운로드 & Unzip
    """

    gdown.download(url="https://drive.google.com/uc?id=1fFLoRCWg8lV-BKF5yfVGfS2tK8nq3Ufo", output="msds.zip", quiet=False)

    with zipfile.ZipFile("msds.zip", "r") as zip_ref:
        zip_ref.extractall()

    Path("msds.zip").unlink(missing_ok=True)

if __name__ == "__main__":
    msds_down()