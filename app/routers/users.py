from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.core import supabase_admin
from app.core.auth import ADMIN, Principal, get_principal
from app.core.database import get_conn
from app.repositories import user_repo
from app.schemas.users import (
    AppUserSchema,
    MeSchema,
    UserAccessSchema,
    UserCreateSchema,
)

# /api/me — any user with a role
me_router = APIRouter()
# /api/users — admin only (enforced in main.py)
router = APIRouter()


@me_router.get("", response_model=MeSchema)
async def me(principal: Principal = Depends(get_principal)):
    return MeSchema(
        id=principal.id,
        email=principal.email,
        role=principal.role,
        categories=list(principal.categories),
    )


@router.get("", response_model=list[AppUserSchema])
async def list_users(conn: asyncpg.Connection = Depends(get_conn)):
    async with conn as c:
        return await user_repo.list_users(c)


@router.post(
    "", response_model=AppUserSchema, status_code=status.HTTP_201_CREATED
)
async def create_user(
    body: UserCreateSchema,
    conn: asyncpg.Connection = Depends(get_conn),
):
    created = await run_in_threadpool(
        supabase_admin.create_user, body.email, body.password
    )
    async with conn as c:
        await user_repo.set_access(c, created["id"], body.role, body.categories)
    return AppUserSchema(
        id=created["id"],
        email=created.get("email", body.email),
        created_at=created.get("created_at"),
        role=body.role,
        categories=body.categories,
    )


@router.put("/{user_id}", response_model=UserAccessSchema)
async def update_access(
    user_id: UUID,
    body: UserAccessSchema,
    principal: Principal = Depends(get_principal),
    conn: asyncpg.Connection = Depends(get_conn),
):
    if str(user_id) == principal.id and body.role != ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove your own admin role",
        )
    async with conn as c:
        if not await user_repo.user_exists(c, str(user_id)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        await user_repo.set_access(
            c, str(user_id), body.role, body.categories
        )
    return body


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    principal: Principal = Depends(get_principal),
):
    if str(user_id) == principal.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )
    # Role and category rows go with it via ON DELETE CASCADE.
    await run_in_threadpool(supabase_admin.delete_user, str(user_id))
