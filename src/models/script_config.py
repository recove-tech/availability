from dataclasses import dataclass
from typing import Optional


@dataclass
class ScriptConfig:
    secrets_path: str
    log_dir: str
    use_proxy_alpha: float
    proxy_password_position: int

    num_items: int
    is_women_alpha: Optional[bool] = None
    sort_by_date_alpha: Optional[bool] = None
    run_every: Optional[int] = None
    num_neighbors: Optional[int] = None

    @classmethod
    def from_config_dict(
        cls, common_config: dict, script_config: dict
    ) -> "ScriptConfig":
        return cls(
            secrets_path=common_config["SECRETS_PATH"],
            log_dir=common_config["LOG_DIR"],
            use_proxy_alpha=common_config["USE_PROXY_ALPHA"],
            proxy_password_position=common_config["PROXY_PASSWORD_POSITION"],
            num_items=script_config["NUM_ITEMS"],
            is_women_alpha=script_config.get("IS_WOMEN_ALPHA"),
            sort_by_date_alpha=script_config.get("SORT_BY_DATE_ALPHA"),
            run_every=script_config.get("RUN_EVERY"),
            num_neighbors=script_config.get("NUM_NEIGHBORS"),
        )
