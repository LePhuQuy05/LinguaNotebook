// ── Languages ─────────────────────────────────────────────────
export const SUPPORTED_LANGUAGES = [
  { code: "en", name: "English" },
  { code: "vi", name: "Tiếng Việt" },
  { code: "zh", name: "中文" },
  { code: "ja", name: "日本語" },
  { code: "ko", name: "한국어" },
  { code: "fr", name: "Français" },
  { code: "de", name: "Deutsch" },
  { code: "es", name: "Español" },
] as const;

export type LanguageCode = (typeof SUPPORTED_LANGUAGES)[number]["code"];

// ── Tiers ────────────────────────────────────────────────────
// All features are free per constitution v2.0.0
export const ALL_FEATURES_FREE = true;
export const MAX_PDF_SIZE_BYTES = 524_288_000; // 500MB
export const MAX_DAILY_ITEMS = 50;
export const MIN_DAILY_ITEMS = 5;

// ── SM-2 Defaults ────────────────────────────────────────────
export const SM2_INITIAL_EASE_FACTOR = 2.5;
export const SM2_MINIMUM_EASE_FACTOR = 1.3;
export const SM2_LEECH_THRESHOLD = 5; // consecutive failures
export const SM2_GRADUATION_THRESHOLD = 3; // first score >= 3

// ── Chunking ─────────────────────────────────────────────────
export const CHUNK_MIN_TOKENS = 50;
export const CHUNK_MAX_TOKENS = 500;
export const CHUNK_OVERLAP_SENTENCES = 1;

// ── TTS ──────────────────────────────────────────────────────
export const TTS_SUPPORTED_LANGUAGES: Record<string, string[]> = {
  en: ["en-US-Emma", "en-US-Eric"],
  vi: ["vi-VN-Nam", "vi-VN-Mai"],
  zh: ["zh-CN-Xiaoxiao", "zh-CN-Yunxi"],
  ja: ["ja-JP-Nanami", "ja-JP-Keita"],
  ko: ["ko-KR-SunHi", "ko-KR-InJoon"],
  fr: ["fr-FR-Denise", "fr-FR-Henri"],
  de: ["de-DE-Katja", "de-DE-Conrad"],
  es: ["es-ES-Elvira", "es-ES-Alvaro"],
};

// ── Downloadable Limits ─────────────────────────────────────
export const TTS_CACHE_MAX_BYTES_PER_USER = 5 * 1024 * 1024 * 1024; // 5GB
export const TTS_CACHE_TTL_DAYS = 30;
