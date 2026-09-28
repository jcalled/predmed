"""
PREDMED — Autenticação JWT
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db, Usuario

SECRET_KEY = os.getenv("SECRET_KEY", "predmed-secret-centelha-2026-ekclick")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> Usuario:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        email: str = payload.get("sub")
        if not email:
            raise exc
    except JWTError:
        raise exc

    user = db.query(Usuario).filter(Usuario.email == email, Usuario.ativo == True).first()
    if not user:
        raise exc
    return user


def require_sesa(user: Usuario = Depends(get_current_user)) -> Usuario:
    if user.role != "sesa":
        raise HTTPException(status_code=403, detail="Acesso restrito à SESA")
    return user

def require_gestor(user: Usuario = Depends(get_current_user)) -> Usuario:
    """SESA ou SMS — gestores do sistema público"""
    if user.role not in ("sesa", "sms"):
        raise HTTPException(status_code=403, detail="Acesso restrito a gestores (SESA ou SMS)")
    return user

def require_particular(user: Usuario = Depends(get_current_user)) -> Usuario:
    if user.role != "hospital_particular":
        raise HTTPException(status_code=403, detail="Acesso restrito a hospital particular")
    return user
