from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.auth import create_token
from app.errors import AuthenticationError

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Mock auth for now
    if form_data.username == "admin" and form_data.password == "admin":
        token = create_token(subject="user-123", role="ADMINISTRATOR")
        return {"access_token": token, "token_type": "bearer"}
    raise AuthenticationError("Invalid credentials")
