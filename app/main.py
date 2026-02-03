from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from datetime import timedelta
from .database import init_db
from .routers import (
	sabbath_school_router,
	worship_service_router,
	youth_service_router,
	wednesday_service_router,
)
from .auth import oauth, create_access_token
from .config import settings

# Initialize FastAPI app
app = FastAPI(
	title="Boletin Service API",
	description="API for managing church service bulletins with Google OAuth authentication",
	version="1.0.0",
)

# Initialize database
@app.on_event("startup")
def startup_event():
	init_db()


# Include routers
app.include_router(sabbath_school_router)
app.include_router(worship_service_router)
app.include_router(youth_service_router)
app.include_router(wednesday_service_router)


# Authentication routes
@app.get("/")
def root():
	"""Root endpoint with API information"""
	return {
		"message": "Welcome to Boletin Service API",
		"docs": "/docs",
		"login": "/auth/login"
	}


@app.get("/auth/login")
async def login(request: Request):
	"""Initiate Google OAuth login"""
	redirect_uri = settings.GOOGLE_REDIRECT_URI
	return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback")
async def auth_callback(request: Request):
	"""Handle Google OAuth callback"""
	try:
		token = await oauth.google.authorize_access_token(request)
		user = token.get('userinfo')
        
		if user:
			# Create access token
			access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
			access_token = create_access_token(
				data={"sub": user['email']}, expires_delta=access_token_expires
			)
            
			return JSONResponse({
				"access_token": access_token,
				"token_type": "bearer",
				"user": {
					"email": user.get('email'),
					"name": user.get('name'),
				}
			})
		else:
			return JSONResponse(
				{"detail": "Authentication failed"},
				status_code=400
			)
	except Exception as e:
		return JSONResponse(
			{"detail": f"Authentication error: {str(e)}"},
			status_code=400
		)


@app.get("/auth/logout")
def logout():
	"""Logout endpoint (client should delete token)"""
	return {"message": "Logged out successfully. Please delete your access token."}


@app.get("/health")
def health():
	"""Simple health check endpoint for orchestration and load balancers."""
	return {"status": "ok"}


if __name__ == "__main__":
	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=8000)
