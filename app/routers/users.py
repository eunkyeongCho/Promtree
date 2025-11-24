from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas.user import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserInfoResponse,
    UserSettingsUpdate
)
from app.models.user import User
from app.utils.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user_email
)

user_router = APIRouter()


@user_router.get("/help")
async def help():
    return {"message": [
        "사용가능한 api 목록은 다음과 같습니다.",
        "POST /users/register - 회원가입",
        "POST /users/login - 로그인",
        "POST /users/logout - 로그아웃",
        "DELETE /users/delete - 회원 탈퇴",
        "GET /users/info - 유저 정보 조회",
        "PATCH /users/settings - 유저 설정 변경"
    ]}


# 회원가입
@user_router.post("/register", response_model=TokenResponse)
async def register(request: UserRegisterRequest):
    # 이메일 중복 체크
    existing_user = await User.find_one(User.email == request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다."
        )

    # 비밀번호 해싱
    hashed_password = get_password_hash(request.password)

    # 사용자 생성
    user = User(
        email=request.email,
        username=request.username,
        hashed_password=hashed_password,
        theme="light",
        language="ko"
    )
    await user.insert()

    # JWT 토큰 생성
    access_token = create_access_token(data={"sub": user.email})

    return TokenResponse(access_token=access_token)


# 로그인
@user_router.post("/login", response_model=TokenResponse)
async def login(request: UserLoginRequest):
    # 사용자 찾기
    user = await User.find_one(User.email == request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다."
        )

    # 비밀번호 검증
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다."
        )

    # JWT 토큰 생성
    access_token = create_access_token(data={"sub": user.email})

    return TokenResponse(access_token=access_token)


@user_router.post(
    "/token",
    response_model=TokenResponse,
    summary="Swagger Authorize용 OAuth2 Password 로그인",
    tags=["User"]
)
async def login_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Swagger UI의 Authorize 버튼에서 직접 로그인할 수 있도록 OAuth2 Password Flow를 제공합니다.
    username 필드에는 이메일을 입력하세요.
    """
    user = await User.find_one(User.email == form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다."
        )

    access_token = create_access_token(data={"sub": user.email})
    return TokenResponse(access_token=access_token)


# 로그아웃
@user_router.post("/logout")
async def logout(current_user_email: str = Depends(get_current_user_email)):
    # JWT는 stateless이므로 클라이언트에서 토큰을 삭제하면 됨
    # 서버에서 할 작업은 없지만 인증 확인은 필요
    return {"success": True, "message": "로그아웃 성공"}


# 회원 탈퇴
@user_router.delete("/delete")
async def delete(current_user_email: str = Depends(get_current_user_email)):
    # 사용자 찾기
    user = await User.find_one(User.email == current_user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )

    # 사용자 삭제
    await user.delete()

    return {"success": True, "message": "회원 탈퇴 완료"}


# 유저 정보
@user_router.get("/info", response_model=UserInfoResponse)
async def user_info(current_user_email: str = Depends(get_current_user_email)):
    # 사용자 찾기
    user = await User.find_one(User.email == current_user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )

    return UserInfoResponse(
        username=user.username,
        theme=user.theme,
        language=user.language
    )


# 유저 세팅 변경
@user_router.patch("/settings")
async def user_setting(
    settings: UserSettingsUpdate,
    current_user_email: str = Depends(get_current_user_email)
):
    # 사용자 찾기
    user = await User.find_one(User.email == current_user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )

    # 설정 업데이트
    if settings.theme is not None:
        user.theme = settings.theme
    if settings.language is not None:
        user.language = settings.language

    await user.save()

    return {"success": True, "message": "설정이 업데이트되었습니다."}
