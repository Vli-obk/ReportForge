from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.schemas.user import User, UserCreate, Token, UserSettings
from app.models.user import User as UserModel
from app.core.security import verify_password, get_password_hash, create_access_token
from app.api.deps import get_current_user


router = APIRouter()


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
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Login user and return access token"""
    print("--- LOGIN ATTEMPT ---", flush=True)
    print(f"Username: '{form_data.username}'", flush=True)
    print(f"Password: '{form_data.password}'", flush=True)

    result = await db.execute(select(UserModel).where(UserModel.email == form_data.username))
    user = result.scalars().first()
    print(f"User found: {user is not None}", flush=True)

    if user:
        pw_ok = verify_password(form_data.password, user.hashed_password)
        print(f"Password matches: {pw_ok}", flush=True)
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
