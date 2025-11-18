from abc import ABC, abstractmethod


class BaseChunkDB(ABC):
    @abstractmethod
    def save_bulk(self, chunks: list[dict], *args) -> bool:
        """
        청크들을 한번에 저장

        Notes:
            추상 클래스이므로 함수 본문은 없습니다. 구체적인 동작방식은 구현체에서 구현합니다.
        """
        pass

    @abstractmethod
    def get_by_file_uuid(self, file_uuid: str, *args) -> list[dict]:
        """
        파일 UUID를 기준으로 청크들을 조회

        Notes:
            추상 클래스이므로 함수 본문은 없습니다. 구체적인 동작방식은 구현체에서 구현합니다.
        """
        pass

    @abstractmethod
    def is_exist(self, file_uuid: str, *args) -> bool:
        """
        파일 UUID가 존재하는지 확인

        Notes:
            추상 클래스이므로 함수 본문은 없습니다. 구체적인 동작방식은 구현체에서 구현합니다.
        """
        pass
