export const PLATFORM_CONFIG = {
  telegram: {
    label: "Telegram",
    acceptedFileType: ".json,application/json",
    fileInputLabel: "Choose Telegram JSON files",
    instructions: "Choose a Telegram JSON export.",
  },
  instagram: {
    label: "Instagram",
    acceptedFileType: ".zip,application/zip",
    fileInputLabel: "Choose Instagram ZIP files",
    instructions:
      "Choose the downloaded Instagram ZIP archive with JSON selected as its export format.",
  },
} as const;

export type UploadPlatform = keyof typeof PLATFORM_CONFIG;
