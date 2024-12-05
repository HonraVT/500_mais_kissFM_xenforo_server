import tomllib

FILE = "kiss_conf.toml"


class Config:
    DELAY: int
    ERROR_DELAY: int
    IS_DEMO: bool
    FORUM_URL: str
    COOKIE: str

    def __init__(self, file=FILE):
        try:
            with open(file, "rb") as f:
                data = tomllib.load(f)
                self.config_data = data
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file {FILE} not found.")

    def __getattr__(self, attr):
        try:
            return self.config_data[attr]
        except KeyError:
            raise AttributeError(f"'Config' object has no attribute '{attr}'")
