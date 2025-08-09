from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Literal


ScriptConfigKey = Literal["ALL", "FROM_INTERACTIONS", "SAVED"]


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
    days_lookback: Optional[int] = None
    catalog_score_weights: Optional[List[float]] = None

    @classmethod
    def from_config_dict(
        cls, config_dict: Dict[str, Any], config_key: ScriptConfigKey
    ) -> "ScriptConfig":
        common_config = config_dict["COMMON"]
        script_config = config_dict[config_key]

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
            days_lookback=script_config.get("DAYS_LOOKBACK"),
            catalog_score_weights=script_config.get("CATALOG_SCORE_WEIGHTS"),
        )
