"""
Text Preprocessing Pipeline for Quiribot.

Provides two entry points:
  - process(raw_query)   → cleans & normalises a user search query BEFORE the multi-agent system.
  - process_comment(raw) → cleans a product review / comment BEFORE embedding or explainability.

Query pipeline stages:
  1. Unicode normalization (NFC) + zero-width char removal
  2. HTML tag stripping + HTML entity decoding
  3. Control character removal + newline/tab → space
  4. Whitespace normalization (collapse runs, strip)
  5. Unit standardization  (256gb → 256 GB, 5000mah → 5000 mAh, etc.)
  6. Price hint extraction  (regex-based, pre-fills constraints for the LLM)
  7. Abbreviation expansion  (qty → quantity, desc → description, etc.)
  8. Category alias normalization  (fridge → refrigerator, telly → television, etc.)
  9. Brand name normalization  (samsung → Samsung, hp → HP, etc.)
 10. Final whitespace normalization
 11. Length validation (min 2 chars, max 500 chars)

Comment/review pipeline stages (1-4 same as above, then):
  5. Repeated-punctuation collapse  (!!!!! → !)
  6. Emoji removal
  7. Unit standardization
  8. Brand normalization
  9. Whitespace normalization + length truncation (max 1000 chars)
"""

import re
import unicodedata
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lookup tables  (domain-agnostic — general e-commerce)
# ---------------------------------------------------------------------------

# Common abbreviations found in e-commerce queries
_ABBREV_MAP: Dict[str, str] = {
    # General shopping
    "qty":   "quantity",
    "desc":  "description",
    "pcs":   "pieces",
    "pkt":   "packet",
    "pkg":   "package",
    "approx": "approximately",
    "max":   "maximum",
    "min":   "minimum",
    "info":  "information",
    "spec":  "specification",
    "specs": "specifications",
    # Electronics
    "batt":  "battery",
    "proc":  "processor",
    "mem":   "memory",
    "cam":   "camera",
    "spkr":  "speaker",
    "kbd":   "keyboard",
    "mse":   "mouse",
    "mon":   "monitor",
    "chrg":  "charger",
    "adptr": "adapter",
    "accry": "accessory",
    # Apparel / lifestyle
    "sz":    "size",
    "clr":   "color",
    "col":   "color",
    "w/":    "with",
    # Power / energy
    "pwr":   "power",
    # Household
    "wm":    "washing machine",
}

# Category aliases: phrase (lowercase) → canonical category
# Sorted longest-first at runtime, so multi-word phrases match before sub-phrases.
_CATEGORY_ALIASES: List[tuple] = [
    # Electronics
    ("cell phone",            "smartphone"),
    ("mobile phone",          "smartphone"),
    ("android phone",         "smartphone"),
    ("gaming laptop",         "laptop"),
    ("notebook computer",     "laptop"),
    ("ultrabook",             "laptop"),
    ("chromebook",            "laptop"),
    ("laptop bag",            "laptop accessories"),
    ("laptop sleeve",         "laptop accessories"),
    ("wireless earbuds",      "earphones"),
    ("true wireless",         "earphones"),
    ("noise cancelling",      "headphones"),
    ("noise canceling",       "headphones"),
    ("smart watch",           "smartwatch"),
    ("smart speaker",         "smart speaker"),
    ("smart home",            "smart home"),
    ("set top box",           "set-top box"),
    ("external hard drive",   "external storage"),
    ("portable hard drive",   "external storage"),
    ("flash drive",           "USB drive"),
    ("pen drive",             "USB drive"),
    ("cellphone",             "smartphone"),
    ("handset",               "smartphone"),
    ("mobile",                "smartphone"),
    ("earpiece",              "earphones"),
    ("earbud",                "earphones"),
    ("wearable",              "smartwatch"),
    ("headset",               "headphones"),
    ("smartwatch",            "smartwatch"),
    ("powerbank",             "power bank"),
    # Home appliances
    ("air conditioner",       "air conditioner"),
    ("ac unit",               "air conditioner"),
    ("split ac",              "air conditioner"),
    ("window ac",             "air conditioner"),
    ("washing machine",       "washing machine"),
    ("fridge",                "refrigerator"),
    ("deep freezer",          "freezer"),
    ("microwave oven",        "microwave"),
    ("vacuum cleaner",        "vacuum cleaner"),
    ("water dispenser",       "water dispenser"),
    ("electric kettle",       "kettle"),
    ("room heater",           "heater"),
    ("exhaust fan",           "fan"),
    ("ceiling fan",           "fan"),
    # Entertainment
    ("flat screen",           "television"),
    ("smart tv",              "smart television"),
    ("telly",                 "television"),
    ("tv",                    "television"),
    ("blu ray",               "blu-ray player"),
    ("blu-ray",               "blu-ray player"),
    # Furniture / home
    ("sofa set",              "sofa"),
    ("dining table",          "dining furniture"),
    ("office chair",          "chair"),
    # Sports / fitness
    ("exercise bike",         "fitness equipment"),
    ("treadmill",             "fitness equipment"),
    ("dumbbell",              "fitness equipment"),
    ("yoga mat",              "fitness equipment"),
    # Beauty / personal care
    ("hair dryer",            "hair care"),
    ("hair straightener",     "hair care"),
    ("electric shaver",       "grooming"),
    ("electric toothbrush",   "oral care"),
    # Kitchen
    ("blender",               "kitchen appliance"),
    ("juicer",                "kitchen appliance"),
    ("food processor",        "kitchen appliance"),
    ("coffee maker",          "kitchen appliance"),
    ("rice cooker",           "kitchen appliance"),
    ("air fryer",             "kitchen appliance"),
    # Fashion / clothing
    ("t shirt",               "clothing"),
    ("tee shirt",             "clothing"),
    ("polo shirt",            "clothing"),
    ("dress shirt",           "clothing"),
    ("denim jeans",           "clothing"),
    ("winter jacket",         "outerwear"),
    ("puffer jacket",         "outerwear"),
    ("rain jacket",           "outerwear"),
    ("leather jacket",        "outerwear"),
    ("running shoes",         "footwear"),
    ("sports shoes",          "footwear"),
    ("athletic shoes",        "footwear"),
    ("high heels",            "footwear"),
    ("ankle boots",           "footwear"),
    ("hand bag",              "handbag"),
    ("shoulder bag",          "handbag"),
    ("tote bag",              "handbag"),
    ("cross body bag",        "handbag"),
    ("school bag",            "bags"),
    ("travel bag",            "bags"),
    ("sports bra",            "activewear"),
    ("track suit",            "activewear"),
    ("gym wear",              "activewear"),
    ("sun glasses",           "eyewear"),
    ("reading glasses",       "eyewear"),
    ("wrist watch",           "watch"),
    # Furniture / home
    ("book shelf",            "bookshelf"),
    ("book case",             "bookshelf"),
    ("tv stand",              "furniture"),
    ("tv cabinet",            "furniture"),
    ("study table",           "desk"),
    ("computer desk",         "desk"),
    ("bedside table",         "nightstand"),
    ("night stand",           "nightstand"),
    ("bed frame",             "bed frame"),
    ("king size bed",         "bed"),
    ("queen size bed",        "bed"),
    ("single bed",            "bed"),
    ("double bed",            "bed"),
    ("bunk bed",              "bed"),
    ("rocking chair",         "chair"),
    ("accent chair",          "chair"),
    ("lounge chair",          "chair"),
    ("sectional sofa",        "sofa"),
    ("l shaped sofa",         "sofa"),
    ("coffee table",          "coffee table"),
    ("center table",          "coffee table"),
    ("dining chair",          "dining furniture"),
    ("chest of drawers",      "dresser"),
    ("dressing table",        "dresser"),
    ("memory foam mattress",  "mattress"),
    ("memory foam",           "mattress"),
    ("wardrobe",              "wardrobe"),
    ("closet",                "wardrobe"),
]

# Brand names: lowercase key → proper display form
# Covers electronics, appliances, apparel-adjacent brands commonly found in
# general e-commerce catalogues. Extend freely; nothing here is mobile-only.
_BRAND_NAMES: Dict[str, str] = {
    # Apple ecosystem
    "iphone":      "iPhone",
    "ipad":        "iPad",
    "imac":        "iMac",
    "macbook":     "MacBook",
    "airpods":     "AirPods",
    "apple":       "Apple",
    # Android / mobile
    "samsung":     "Samsung",
    "oneplus":     "OnePlus",
    "huawei":      "Huawei",
    "xiaomi":      "Xiaomi",
    "realme":      "Realme",
    "oppo":        "OPPO",
    "vivo":        "vivo",
    "nokia":       "Nokia",
    "motorola":    "Motorola",
    "tecno":       "TECNO",
    "infinix":     "Infinix",
    # Computing
    "lenovo":      "Lenovo",
    "dell":        "Dell",
    "asus":        "ASUS",
    "acer":        "Acer",
    "msi":         "MSI",
    "hp":          "HP",
    "microsoft":   "Microsoft",
    "toshiba":     "Toshiba",
    # Consumer electronics
    "sony":        "Sony",
    "lg":          "LG",
    "panasonic":   "Panasonic",
    "philips":     "Philips",
    "tcl":         "TCL",
    "hisense":     "Hisense",
    "haier":       "Haier",
    "dawlance":    "Dawlance",
    "orient":      "Orient",
    "gree":        "Gree",
    "pel":         "PEL",
    # Audio
    "bose":        "Bose",
    "jbl":         "JBL",
    "sennheiser":  "Sennheiser",
    "harman":      "Harman",
    "beats":       "Beats",
    "anker":       "Anker",
    # Gaming
    "razer":       "Razer",
    "logitech":    "Logitech",
    "steelseries": "SteelSeries",
    "corsair":     "Corsair",
    "nzxt":        "NZXT",
    # Fashion / apparel
    "nike":        "Nike",
    "adidas":      "Adidas",
    "puma":        "Puma",
    "levis":       "Levi's",
    "zara":        "Zara",
    "hm":          "H&M",
    "uniqlo":      "Uniqlo",
    "gap":         "GAP",
    "gucci":       "Gucci",
    "converse":    "Converse",
    "vans":        "Vans",
    "skechers":    "Skechers",
    "bata":        "Bata",
    "reebok":      "Reebok",
    "newbalance":  "New Balance",
    # Personal care / appliances
    "braun":       "Braun",
    "dyson":       "Dyson",
    "remington":   "Remington",
    # Furniture
    "ikea":        "IKEA",
    "ashley":      "Ashley",
    # Kitchen / home
    "nestle":      "Nestlé",
    "kenwood":     "Kenwood",
    "moulinex":    "Moulinex",
    "westpoint":   "Westpoint",
    "tefal":       "Tefal",
    "cuisinart":   "Cuisinart",
    "kitchenaid":  "KitchenAid",
    "prestige":    "Prestige",
}

# Unit normalization: (compiled pattern, replacement template)
# Applied case-insensitively; the number group is preserved.
_UNIT_PATTERNS: List[tuple] = [
    (re.compile(r'(\d+)\s*gb\b',              re.IGNORECASE), r'\1 GB'),
    (re.compile(r'(\d+)\s*tb\b',              re.IGNORECASE), r'\1 TB'),
    (re.compile(r'(\d+)\s*mb\b',              re.IGNORECASE), r'\1 MB'),
    (re.compile(r'(\d+)\s*kb\b',              re.IGNORECASE), r'\1 KB'),
    (re.compile(r'(\d+)\s*mah\b',             re.IGNORECASE), r'\1 mAh'),
    (re.compile(r'(\d+)\s*mp\b',              re.IGNORECASE), r'\1 MP'),
    (re.compile(r'(\d+)\s*hz\b',              re.IGNORECASE), r'\1 Hz'),
    (re.compile(r'(\d+)\s*ghz\b',             re.IGNORECASE), r'\1 GHz'),
    (re.compile(r'(\d+)\s*mhz\b',             re.IGNORECASE), r'\1 MHz'),
    (re.compile(r'(\d+(?:\.\d+)?)\s*"',       re.IGNORECASE), r'\1 inch'),
    (re.compile(r'(\d+(?:\.\d+)?)\s*inches?\b', re.IGNORECASE), r'\1 inch'),
    (re.compile(r'(\d+(?:\.\d+)?)\s*cm\b',    re.IGNORECASE), r'\1 cm'),
    (re.compile(r'(\d+(?:\.\d+)?)\s*mm\b',    re.IGNORECASE), r'\1 mm'),
    (re.compile(r'(\d+(?:\.\d+)?)\s*kg\b',    re.IGNORECASE), r'\1 kg'),
    (re.compile(r'(\d+(?:\.\d+)?)\s*g\b',     re.IGNORECASE), r'\1 g'),
    (re.compile(r'(\d+(?:\.\d+)?)\s*ltr?\b',  re.IGNORECASE), r'\1 L'),
    (re.compile(r'(\d+(?:\.\d+)?)\s*liters?\b', re.IGNORECASE), r'\1 L'),
    (re.compile(r'(\d+)\s*w\b',               re.IGNORECASE), r'\1 W'),
    (re.compile(r'(\d+)\s*watts?\b',          re.IGNORECASE), r'\1 W'),
    (re.compile(r'(\d+)\s*rpm\b',             re.IGNORECASE), r'\1 RPM'),
    (re.compile(r'(\d+)\s*btu\b',             re.IGNORECASE), r'\1 BTU'),
]

# HTML entities to decode
_HTML_ENTITIES: Dict[str, str] = {
    "&amp;":  "&",
    "&lt;":   "<",
    "&gt;":   ">",
    "&quot;": '"',
    "&#39;":  "'",
    "&nbsp;": " ",
}

# Emoji block regex (covers most Unicode emoji ranges)
_EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F"   # emoticons
    "\U0001F300-\U0001F5FF"    # symbols & pictographs
    "\U0001F680-\U0001F6FF"    # transport & map
    "\U0001F1E0-\U0001F1FF"    # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PreprocessingResult:
    """Output of the query preprocessing pipeline."""

    original_query: str
    cleaned_query: str        # After stages 1-4 (safe for logging / audit)
    normalized_query: str     # After all stages (passed to downstream agents)
    price_hints: Dict[str, Any] = field(default_factory=dict)
    detected_brands: List[str] = field(default_factory=list)
    detected_categories: List[str] = field(default_factory=list)
    is_valid: bool = True
    warnings: List[str] = field(default_factory=list)


@dataclass
class CommentPreprocessingResult:
    """Output of the comment/review preprocessing pipeline."""

    original_text: str
    normalized_text: str      # Ready for embedding / explainability
    detected_brands: List[str] = field(default_factory=list)
    is_valid: bool = True
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pipeline class
# ---------------------------------------------------------------------------

class TextPreprocessingPipeline:
    """
    Stateless, synchronous text preprocessing pipeline.

    Two entry points:
      result  = preprocessing_pipeline.process(raw_query)
      comment = preprocessing_pipeline.process_comment(raw_review_text)
    """

    MIN_QUERY_LEN   = 2
    MAX_QUERY_LEN   = 500
    MAX_COMMENT_LEN = 1000   # reviews can be longer; hard-cap for embedding safety

    # ------------------------------------------------------------------
    # Public: query pipeline
    # ------------------------------------------------------------------

    def process(self, raw_query: str) -> PreprocessingResult:
        """Run the full query pipeline and return a PreprocessingResult."""
        if not isinstance(raw_query, str):
            raw_query = str(raw_query)

        result = PreprocessingResult(
            original_query=raw_query,
            cleaned_query="",
            normalized_query="",
        )

        text = raw_query

        text = self._normalize_unicode(text)         # 1
        text = self._strip_html(text)                # 2
        text = self._strip_control_chars(text)       # 3
        text = self._normalize_whitespace(text)      # 4

        result.cleaned_query = text                  # safe checkpoint

        text = self._normalize_units(text)           # 5
        result.price_hints = self._extract_price_hints(text)   # 6
        text = self._expand_abbreviations(text)      # 7
        text, detected_categories = self._normalize_categories(text)  # 8
        result.detected_categories = detected_categories
        text, detected_brands = self._normalize_brands(text)   # 9
        result.detected_brands = detected_brands
        text = self._normalize_whitespace(text)      # 10

        result.normalized_query = text
        self._validate_query(result)                 # 11

        logger.debug(
            "Query preprocessed | original=%r normalized=%r "
            "brands=%s categories=%s price_hints=%s valid=%s",
            result.original_query, result.normalized_query,
            result.detected_brands, result.detected_categories,
            result.price_hints, result.is_valid,
        )
        return result

    # ------------------------------------------------------------------
    # Public: comment / review pipeline
    # ------------------------------------------------------------------

    def process_comment(self, raw_text: str) -> CommentPreprocessingResult:
        """
        Clean and normalize a product review or comment.

        Steps:
          1. Unicode normalization + zero-width removal
          2. HTML strip + entity decode
          3. Control char removal / newline → space
          4. Whitespace normalization
          5. Repeated-punctuation collapse  (!!!!! → !)
          6. Emoji removal
          7. Unit standardization
          8. Brand normalization
          9. Whitespace normalization + length truncation
        """
        if not isinstance(raw_text, str):
            raw_text = str(raw_text)

        result = CommentPreprocessingResult(original_text=raw_text, normalized_text="")

        text = raw_text

        text = self._normalize_unicode(text)          # 1
        text = self._strip_html(text)                 # 2
        text = self._strip_control_chars(text)        # 3
        text = self._normalize_whitespace(text)       # 4
        text = self._collapse_repeated_punctuation(text)  # 5
        text = self._remove_emojis(text)              # 6
        text = self._normalize_units(text)            # 7
        text, detected_brands = self._normalize_brands(text)  # 8
        result.detected_brands = detected_brands
        text = self._normalize_whitespace(text)       # 9
        text = self._truncate(text, self.MAX_COMMENT_LEN)

        result.normalized_text = text
        self._validate_comment(result)

        logger.debug(
            "Comment preprocessed | length=%d brands=%s valid=%s",
            len(result.normalized_text), result.detected_brands, result.is_valid,
        )
        return result

    # ------------------------------------------------------------------
    # Shared low-level helpers
    # ------------------------------------------------------------------

    def _normalize_unicode(self, text: str) -> str:
        text = unicodedata.normalize("NFC", text)
        # Remove zero-width / invisible formatting characters
        text = re.sub(r"[\u200b\u200c\u200d\ufeff\u00ad\u2060]", "", text)
        return text

    def _strip_html(self, text: str) -> str:
        for entity, char in _HTML_ENTITIES.items():
            text = text.replace(entity, char)
        text = re.sub(r"<[^>]+>", " ", text)
        return text

    def _strip_control_chars(self, text: str) -> str:
        # Collapse line breaks to a single space (preserve sentence readability)
        text = re.sub(r"[\t\n\r]+", " ", text)
        # Remove non-printable control chars
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _normalize_units(self, text: str) -> str:
        for pattern, replacement in _UNIT_PATTERNS:
            text = pattern.sub(replacement, text)
        return text

    def _normalize_brands(self, text: str) -> tuple:
        detected: List[str] = []
        for lowercase_brand, proper_brand in _BRAND_NAMES.items():
            pattern = r"\b" + re.escape(lowercase_brand) + r"\b"
            if re.search(pattern, text, flags=re.IGNORECASE):
                text = re.sub(pattern, proper_brand, text, flags=re.IGNORECASE)
                if proper_brand not in detected:
                    detected.append(proper_brand)
        return text, detected

    # ------------------------------------------------------------------
    # Query-only helpers
    # ------------------------------------------------------------------

    def _extract_price_hints(self, text: str) -> Dict[str, Any]:
        """
        Extract price constraints using regex.

        Supports currency prefixes: Rs, PKR, $, ₹, £, € and their variations.
        Returns a dict with optional keys: min_price, max_price (both int).
        """
        hints: Dict[str, Any] = {}
        t = text.lower()
        currency = r"(?:rs\.?\s*|pkr\.?\s*|₹\s*|\$\s*|£\s*|€\s*)?"

        # "under / below / less than / cheaper than / max / up to X"
        m = re.search(
            rf"(?:under|below|less\s+than|cheaper\s+than|max(?:imum)?|up\s+to)\s*{currency}([\d,]+)",
            t,
        )
        if m:
            hints["max_price"] = int(m.group(1).replace(",", ""))

        # "above / over / more than / at least / min X"
        m = re.search(
            rf"(?:above|over|more\s+than|at\s+least|min(?:imum)?)\s*{currency}([\d,]+)",
            t,
        )
        if m:
            hints["min_price"] = int(m.group(1).replace(",", ""))

        # "between X and Y"  /  "X to Y"  /  "X - Y"
        m = re.search(
            rf"(?:between\s*)?{currency}([\d,]+)\s*(?:to|-|and)\s*{currency}([\d,]+)",
            t,
        )
        if m:
            lo = int(m.group(1).replace(",", ""))
            hi = int(m.group(2).replace(",", ""))
            # Guard: skip if this looks like a unit range (e.g. "256 GB to 512 GB")
            preceding = t[: m.start()].split()
            is_unit_range = preceding and preceding[-1] in {
                "gb", "tb", "mb", "kb", "mah", "mp", "hz", "ghz", "w", "kg", "l",
            }
            if hi > lo and not is_unit_range:
                hints.setdefault("min_price", lo)
                hints.setdefault("max_price", hi)

        # "budget of / around / approximately / ~ X"
        m = re.search(
            rf"(?:budget(?:\s+of)?|costing(?:\s+around)?|around|approximately|~)\s*{currency}([\d,]+)",
            t,
        )
        if m:
            val = int(m.group(1).replace(",", ""))
            margin = max(int(val * 0.15), 1)
            hints.setdefault("min_price", val - margin)
            hints.setdefault("max_price", val + margin)

        return hints

    def _expand_abbreviations(self, text: str) -> str:
        words = text.split()
        expanded = []
        for word in words:
            stripped = re.sub(r"[^\w/]", "", word.lower())
            expanded.append(_ABBREV_MAP.get(stripped, word))
        return " ".join(expanded)

    def _normalize_categories(self, text: str) -> tuple:
        detected: List[str] = []
        for alias, canonical in sorted(_CATEGORY_ALIASES, key=lambda x: len(x[0]), reverse=True):
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, text, flags=re.IGNORECASE):
                text = re.sub(pattern, canonical, text, flags=re.IGNORECASE)
                if canonical not in detected:
                    detected.append(canonical)
        return text, detected

    # ------------------------------------------------------------------
    # Comment-only helpers
    # ------------------------------------------------------------------

    def _collapse_repeated_punctuation(self, text: str) -> str:
        # !!!!!  →  !    ???  →  ?    ...  (ellipsis keep as one)
        text = re.sub(r"\.{4,}", "...", text)      # 4+ dots → ellipsis
        text = re.sub(r"([!?])\1+", r"\1", text)  # repeated ! or ?
        text = re.sub(r"([,;:])\1+", r"\1", text) # repeated , ; :
        return text

    def _remove_emojis(self, text: str) -> str:
        return _EMOJI_RE.sub(" ", text)

    def _truncate(self, text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        truncated = text[:max_len]
        last_space = truncated.rfind(" ")
        return truncated[:last_space].strip() if last_space > 0 else truncated

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_query(self, result: PreprocessingResult) -> None:
        length = len(result.normalized_query)
        if length < self.MIN_QUERY_LEN:
            result.is_valid = False
            result.warnings.append(
                f"Query is too short (minimum {self.MIN_QUERY_LEN} characters)."
            )
        if length > self.MAX_QUERY_LEN:
            result.is_valid = False
            result.warnings.append(
                f"Query exceeds maximum length ({self.MAX_QUERY_LEN} characters)."
            )
            result.normalized_query = self._truncate(result.normalized_query, self.MAX_QUERY_LEN)

    def _validate_comment(self, result: CommentPreprocessingResult) -> None:
        if len(result.normalized_text.strip()) < self.MIN_QUERY_LEN:
            result.is_valid = False
            result.warnings.append("Comment text is empty or too short.")


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

preprocessing_pipeline = TextPreprocessingPipeline()
