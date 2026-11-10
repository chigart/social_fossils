from dataclasses import dataclass


TELEGRAM_PLATFORM_ID = "telegram"
INSTAGRAM_PLATFORM_ID = "instagram"
FACEBOOK_PLATFORM_ID = "facebook"
VK_PLATFORM_ID = "vk"


@dataclass(frozen=True)
class PlatformConfig:
    label: str
    file_extensions: tuple[str, ...]
    accepted_file_types: str
    file_input_label: str
    instructions: str
    importer: str


PLATFORM_CONFIGS: dict[str, PlatformConfig] = {
    TELEGRAM_PLATFORM_ID: PlatformConfig(
        label="Telegram",
        file_extensions=(".json",),
        accepted_file_types=".json,application/json",
        file_input_label="Choose Telegram JSON files",
        instructions="Choose a Telegram JSON export.",
        importer="app.telegram_importer:import_telegram_export",
    ),
    INSTAGRAM_PLATFORM_ID: PlatformConfig(
        label="Instagram",
        file_extensions=(".zip",),
        accepted_file_types=".zip,application/zip",
        file_input_label="Choose Instagram ZIP files",
        instructions=(
            "Choose the downloaded Instagram ZIP archive with JSON selected "
            "as its export format."
        ),
        importer="app.instagram_importer:import_instagram_export",
    ),
    FACEBOOK_PLATFORM_ID: PlatformConfig(
        label="Facebook",
        file_extensions=(".zip",),
        accepted_file_types=".zip,application/zip",
        file_input_label="Choose Facebook ZIP files",
        instructions=(
            "Choose the downloaded Facebook ZIP archive with JSON selected "
            "as its export format."
        ),
        importer="app.facebook_importer:import_facebook_export",
    ),
    VK_PLATFORM_ID: PlatformConfig(
        label="VK",
        file_extensions=(".zip",),
        accepted_file_types=".zip,application/zip",
        file_input_label="Choose VK ZIP files",
        instructions="Choose the downloaded VK ZIP export with message history.",
        importer="app.vk_importer:import_vk_export",
    ),
}
