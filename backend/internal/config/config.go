package config

import (
	"os"
	"strconv"
)

// Config holds all environment-based configuration for the SuperVideo server.
type Config struct {
	Host         string
	Port         string
	DBPath       string
	Secret       string
	SessionName  string
	SessionHours int
}

// Load reads configuration from environment variables with sensible defaults.
// SV_SECRET is required and will cause a panic if not set.
func Load() *Config {
	secret := os.Getenv("SV_SECRET")
	if secret == "" {
		panic("SV_SECRET environment variable is required")
	}

	return &Config{
		Host:         getEnvOrDefault("SV_HOST", "localhost"),
		Port:         getEnvOrDefault("SV_PORT", "8080"),
		DBPath:       getEnvOrDefault("SV_DB_PATH", "./data/supervideo.db"),
		Secret:       secret,
		SessionName:  getEnvOrDefault("SV_SESSION_NAME", "sv_session"),
		SessionHours: getEnvAsIntOrDefault("SV_SESSION_HOURS", 24),
	}
}

func getEnvOrDefault(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func getEnvAsIntOrDefault(key string, def int) int {
	raw := os.Getenv(key)
	if raw == "" {
		return def
	}
	if v, err := strconv.Atoi(raw); err == nil && v > 0 {
		return v
	}
	return def
}
