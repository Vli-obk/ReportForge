from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database.session import get_db
from app.schemas.dataset import Dataset, DatasetCreate, DataRow
from app.models.dataset import Dataset as DatasetModel
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()


@router.get("", response_model=List[Dataset])
async def get_datasets(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all datasets for current user"""
    stmt = (
        select(DatasetModel)
        .where(DatasetModel.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{dataset_id}", response_model=Dataset)
async def get_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific dataset"""
    stmt = select(DatasetModel).where(
        DatasetModel.id == dataset_id,
        DatasetModel.user_id == current_user.id
    )
    dataset = (await db.execute(stmt)).scalar_one_or_none()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    return dataset


@router.get("/{dataset_id}/rows", response_model=List[DataRow])
async def get_dataset_rows(
    dataset_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get rows from a dataset"""
    # Verify dataset belongs to user
    dataset_stmt = select(DatasetModel).where(
        DatasetModel.id == dataset_id,
        DatasetModel.user_id == current_user.id
    )
    dataset = (await db.execute(dataset_stmt)).scalar_one_or_none()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    from app.models.data_row import DataRow as DataRowModel
    rows_stmt = (
        select(DataRowModel)
        .where(DataRowModel.dataset_id == dataset_id)
        .offset(skip)
        .limit(limit)
    )
    return (await db.execute(rows_stmt)).scalars().all()


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a dataset"""
    stmt = select(DatasetModel).where(
        DatasetModel.id == dataset_id,
        DatasetModel.user_id == current_user.id
    )
    dataset = (await db.execute(stmt)).scalar_one_or_none()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    await db.delete(dataset)
    await db.commit()
    
    return {"message": "Dataset deleted successfully"}
