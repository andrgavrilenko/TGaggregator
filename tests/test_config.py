from pathlib import Path

from tgaggerator.config import Settings


def test_empty_optional_int_env_is_ignored(tmp_path: Path) -> None:
    env_file = tmp_path / "test.env"
    env_file.write_text("TG_BOT_ALLOWED_CHAT_ID=\n", encoding="utf-8")

    settings = Settings(_env_file=str(env_file))

    assert settings.tg_bot_allowed_chat_id is None
