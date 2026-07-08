from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    supabase_jwt_secret: str
    allowed_origins: str = "http://localhost:5173"

    forecast_horizon_months: int = 6
    lead_time_months: float = 1.0
    safety_stock_z: float = 1.65

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


settings = Settings()
