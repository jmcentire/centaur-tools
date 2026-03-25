from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/centaur"
    github_client_id: str = ""
    github_client_secret: str = ""
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_days: int = 30
    gemini_api_key: str = ""
    frontend_url: str = "https://centaur.tools"
    proximity_threshold: float = 0.75
    prior_art_vote_threshold: int = 5

    model_config = {"env_prefix": "CENTAUR_"}


settings = Settings()
