package security

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"strings"

	"golang.org/x/crypto/bcrypt"
)

const (
	// MinPasswordLength is the minimum accepted length for passwords.
	MinPasswordLength = 6
	bcryptCost        = 12
)

// passwordAlphabet is the set of characters used for generated temporary
// passwords. "Similar-looking" chars (0/O, 1/l/I) are excluded.
const passwordAlphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"

// GenerateRandomPassword returns a cryptographically random password of the
// given length drawn from passwordAlphabet. length is clamped to MinPasswordLength.
func GenerateRandomPassword(length int) (string, error) {
	if length < MinPasswordLength {
		length = MinPasswordLength
	}
	buffer := make([]byte, length)
	randomBytes := make([]byte, length)
	if _, err := rand.Read(randomBytes); err != nil {
		return "", fmt.Errorf("generate random password: %w", err)
	}
	for i := range buffer {
		buffer[i] = passwordAlphabet[int(randomBytes[i])%len(passwordAlphabet)]
	}
	return string(buffer), nil
}

// ValidatePassword returns an error if the password fails basic policy.
func ValidatePassword(password string) error {
	if len(strings.TrimSpace(password)) < MinPasswordLength {
		return fmt.Errorf("password must be at least %d characters", MinPasswordLength)
	}
	return nil
}

// HashPassword returns a bcrypt hash of password using bcryptCost.
func HashPassword(password string) (string, error) {
	hashed, err := bcrypt.GenerateFromPassword([]byte(password), bcryptCost)
	if err != nil {
		return "", fmt.Errorf("hash password: %w", err)
	}
	return string(hashed), nil
}

// CheckPassword returns true if password matches hash (bcrypt).
func CheckPassword(hash, password string) bool {
	return bcrypt.CompareHashAndPassword([]byte(hash), []byte(password)) == nil
}

// GenerateAPIKey returns a cryptographically random hex string suitable for
// use as an API key (32 random bytes = 64 hex chars).
func GenerateAPIKey() (string, error) {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", fmt.Errorf("generate api key: %w", err)
	}
	return hex.EncodeToString(b), nil
}
