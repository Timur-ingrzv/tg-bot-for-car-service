from aiogram.filters.command import Filter
from aiogram import types
from enum import Enum


class UserStatus(Enum):
    ADMIN = "administration"
    CLIENT = "client"
    UNAUTHORIZED_USER = "unauthorized"


class IsAdminFilter(Filter):
    async def __call__(self, message: types.Message, user_status: UserStatus) -> bool:
        return user_status == UserStatus.ADMIN


class IsAuthorizedFilter(Filter):
    async def __call__(self, message: types.Message, user_status: UserStatus) -> bool:
        return user_status == UserStatus.CLIENT


class IsUnauthorized(Filter):
    async def __call__(self, message: types.Message, user_status: UserStatus) -> bool:
        return user_status == UserStatus.UNAUTHORIZED_USER