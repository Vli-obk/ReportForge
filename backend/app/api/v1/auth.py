from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.schemas.user import User, UserCreate, Token, UserSettings
from app.models.user import User as UserModel
from app.core.security import verify_password, get_password_hash, create_access_token
from app.api.deps import get_current_user


router = APIRouter()


class LoginForm:
    def __init__(
        self,
        username: Annotated[str, Form()],
        password: Annotated[str, Form()],
        grant_type: Annotated[Optional[str], Form()] = None,
        scope: Annotated[str, Form()] = "",
        client_id: Annotated[Optional[str], Form()] = None,
        client_secret: Annotated[Optional[str], Form()] = None,
    ):
        self.username = username
        self.password = password
        self.grant_type = grant_type
        self.scopes = scope.split()
        self.client_id = client_id
        self.client_secret = client_secret


@router.post("/register", response_model=User)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    result = await db.execute(select(UserModel).where(UserModel.email == user_data.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    new_user = UserModel(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password)
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
async def login(
    form_data: LoginForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Login user and return access token"""
    result = await db.execute(select(UserModel).where(UserModel.email == form_data.username))
    user = result.scalars().first()

    if user:
        pw_ok = verify_password(form_data.password, user.hashed_password)
        if not pw_ok:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    access_token = create_access_token(data={"sub": str(user.id)})

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user


@router.put("/settings", response_model=User)
async def update_user_settings(
    settings_data: UserSettings,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user settings/preferences"""
    current_user.ocr_enabled = settings_data.ocr_enabled
    current_user.max_upload_size = settings_data.max_upload_size
    current_user.auto_process = settings_data.auto_process
    await db.commit()
    await db.refresh(current_user)
    return current_user
