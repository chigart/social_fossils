import re
from dataclasses import dataclass
from datetime import timedelta


DEFAULT_PAGE_SIZE = 50
# Increment when analytics response semantics change without a database revision change.
ANALYTICS_CACHE_VERSION = 22

ACTIVE_WINDOW_MONTHS = 6
ACTIVE_MINIMUM_TEXT_MESSAGES = 20
CLOSE_WINDOW_MONTHS = 12
CLOSE_MINIMUM_ANNUAL_TEXT_MESSAGES = 200

TELEGRAM_PLATFORM_ID = "telegram"
INSTAGRAM_PLATFORM_ID = "instagram"
FACEBOOK_PLATFORM_ID = "facebook"
VK_PLATFORM_ID = "vk"

MESSAGE_INSERT_BATCH_SIZE = 50

FACEBOOK_MESSAGE_FILE_PATTERN = re.compile(
    r"message(?:_(\d+))?\.json", re.IGNORECASE
)
FACEBOOK_USER_FOLDER_PATTERN = re.compile(r"^.+_(?P<user_id>\d+)$")
FACEBOOK_MAX_MESSAGE_FILE_BYTES = 4 * 1024 * 1024
FACEBOOK_MAX_MESSAGE_DATA_BYTES = 16 * 1024 * 1024
FACEBOOK_MAX_PROFILE_FILE_BYTES = 5 * 1024 * 1024

INSTAGRAM_MESSAGE_FILE_PATTERN = re.compile(
    r"message(?:_(\d+))?\.json", re.IGNORECASE
)
INSTAGRAM_MAX_MESSAGE_FILE_BYTES = 100 * 1024 * 1024
INSTAGRAM_MAX_MESSAGE_DATA_BYTES = 1024 * 1024 * 1024
INSTAGRAM_USER_FOLDER_PATTERN = re.compile(
    r"^(?P<username>.+)_(?P<user_id>\d+)$"
)

VK_MESSAGE_FILE_PATTERN = re.compile(
    r"messages(?P<offset>\d+)\.html", re.IGNORECASE
)
VK_MAX_MESSAGE_FILE_BYTES = 8 * 1024 * 1024
VK_MAX_MESSAGE_DATA_BYTES = 1024 * 1024 * 1024
VK_MAX_PROFILE_FILE_BYTES = 5 * 1024 * 1024
VK_OWNER_SENDER_LABELS = frozenset({"me", "you", "you (you)", "я", "вы"})
VK_MONTH_NUMBERS = {
    "января": 1,
    "янв": 1,
    "февраля": 2,
    "февраль": 2,
    "фев": 2,
    "марта": 3,
    "март": 3,
    "мар": 3,
    "апреля": 4,
    "апрель": 4,
    "апр": 4,
    "мая": 5,
    "май": 5,
    "июня": 6,
    "июнь": 6,
    "июн": 6,
    "июля": 7,
    "июль": 7,
    "июл": 7,
    "августа": 8,
    "август": 8,
    "авг": 8,
    "сентября": 9,
    "сентябрь": 9,
    "сен": 9,
    "сент": 9,
    "октября": 10,
    "октябрь": 10,
    "окт": 10,
    "ноября": 11,
    "ноябрь": 11,
    "ноя": 11,
    "нояб": 11,
    "декабря": 12,
    "декабрь": 12,
    "дек": 12,
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
}
VK_DATE_WITH_MONTH_PATTERN = re.compile(
    r"(?P<day>\d{1,2})\s+(?P<month>[^\W\d_]+)\s+"
    r"(?P<year>\d{4})\D{0,12}(?P<hour>\d{1,2}):(?P<minute>\d{2})"
    r"(?::(?P<second>\d{2}))?",
    re.IGNORECASE,
)
VK_NUMERIC_DATE_PATTERN = re.compile(
    r"(?P<day>\d{1,2})[./-](?P<month>\d{1,2})[./-](?P<year>\d{4})"
    r"\D{0,12}(?P<hour>\d{1,2}):(?P<minute>\d{2})"
    r"(?::(?P<second>\d{2}))?"
)

SUPPORTED_CHAT_TYPES = ("personal_chat", "private_group", "private_supergroup")
ORDINARY_MESSAGE_TYPE = "message"
SERVICE_MESSAGE_TYPE = "service"
RANKING_LIMIT = 10
CONVERSATION_GAP = timedelta(hours=12)
MINIMUM_REPLY_SAMPLES_FOR_AVERAGE = 3
WORD_PATTERN = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)
EMOJI_START_PATTERN = re.compile(
    r"[#*0-9\u2300-\u23ff\u2600-\u27bf\U0001F000-\U0001FAFF]"
)

MINIMUM_BALANCE_TEXT_LENGTH = 500
BALANCED_OWNER_SHARE_MINIMUM = 0.40
BALANCED_OWNER_SHARE_MAXIMUM = 0.60
STRONG_OWNER_SHARE_MINIMUM = 0.80
STRONG_CONTACT_OWNER_SHARE_MAXIMUM = 0.20

FORGOTTEN_RECENT_WINDOW_DAYS = 90
FORGOTTEN_INACTIVE_DAYS = 90
FORGOTTEN_MIN_HISTORICAL_MESSAGES = 20
FORGOTTEN_MIN_HISTORICAL_ACTIVE_DAYS = 5
FORGOTTEN_MIN_HISTORICAL_ACTIVE_MONTHS = 3
FORGOTTEN_MIN_BASELINE_SPAN_DAYS = 90
FORGOTTEN_DECLINE_THRESHOLD = 0.50
FORGOTTEN_RECENT_MONTH_DAYS = 30
FORGOTTEN_EVIDENCE_MESSAGE_CAP = 100
FORGOTTEN_SCORE_INACTIVITY_CAP_DAYS = 180
FORGOTTEN_SCORE_INACTIVITY_WEIGHT = 0.60
FORGOTTEN_SCORE_DECLINE_WEIGHT = 0.40
FORGOTTEN_MAX_LIMIT = 500

RUSSIAN_STOP_WORDS = frozenset(
    """
    а без более бы был была были было быть в вам вами вас весь во вот все
    всего всех вы где да даже для до его ее её если есть еще ещё же за и из
    или им ими их к как какая какие каким какими каких какой ко когда кого
    кому которая которые который которым которыми которых которую которого
    которой которое кто куда ли либо меня мне много может можно мой моя мои
    моё мною мной мы на над надо нам нами нас наш наша наши наше нашего нашей
    нашим нашими наших не него нее неё ней нем нему нет нету ни них ничего
    но ну о об
    один одна одни одно одного одной одном одному одними одних он она они
    оно от потому после по при про с сам сама сами само своего своей своим
    своими своих себе себя сейчас со такой такая такие
    такое такого такой таким такими таких там те тем тех то того той только
    том тому тот та те тебе тебя тобой тобою три тут ты у уже хотя чего чей
    чья чьё чьи чем через
    что чтобы чём эта эти это этого этой этом этому эту я
    ведь впрочем вообще дескать итак как-либо мол откуда отсюда разве равно
    будто словно уж хоть лишь едва чуть почти будто бы
    """.split()
)

ENGLISH_STOP_WORDS = frozenset(
    """
    1 2 3 4 5 6 7 8 9
    a about above after again against all am an and any are as at attachment be because
    been before being below between both but by can cannot com could did do does
    doing down during each few for from further had has have having he her
    here hers herself him himself his how http https i if in into is it its itself just
    me more most my myself no nor not of off on once only or other ought our
    ours ourselves out over own same she should so some such than that the
    their theirs them themselves then there these they this those through to
    too under until up very was we were what when where which while who whom
    why with would you your yours yourself yourselves
    after all although always among amongst another anywhere anyhow anyone
    anything anyway anyways around back became become becomes becoming beside
    besides beyond bill call co computer con couldnt cry de describe detail
    done due eg eight either eleven else elsewhere empty enough etc even ever
    every everyone everything everywhere except few fifteen fifty fill find
    fire first five former formerly forty found four front full get give go
    hadnt hasnt havent hence herein hereby herein hereupon however hundred ie
    inc indeed interest instead keep last latter latterly least less liked ltd many
    may meanwhile message mill mine moreover mostly move much must name neither never
    nevertheless next nine ninety nobody none noone nothing nowhere now
    nowhere often other others otherwise our ours outside part per perhaps
    please put rather re reacted ru same see seem seemed seeming seems sent serious several
    seventeen seventy six sixty somehow someone something sometime sometimes
    somewhere still thence thereafter thereby therefore therein thereof
    thereupon thirty three throughout thru thus top toward towards twelve
    twenty two un under unless unlike unlikely upon used using us utm various v via vk
    watch well whatever whenever wherever whether whoever whole whose within without
    wont www youtube
    ain't aren't couldn't didn't doesn't don't hadn't hasn't haven't isn't
    mightn't mustn't needn't shouldn't wasn't weren't wouldn't
    """.split()
)
STOP_WORDS = RUSSIAN_STOP_WORDS | ENGLISH_STOP_WORDS


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
        importer="app.importers.telegram_importer:import_telegram_export",
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
        importer="app.importers.instagram_importer:import_instagram_export",
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
        importer="app.importers.facebook_importer:import_facebook_export",
    ),
    VK_PLATFORM_ID: PlatformConfig(
        label="VK",
        file_extensions=(".zip",),
        accepted_file_types=".zip,application/zip",
        file_input_label="Choose VK ZIP files",
        instructions="Choose the downloaded VK ZIP export with message history.",
        importer="app.importers.vk_importer:import_vk_export",
    ),
}
