package store

import (
	"context"
	"database/sql"
	"time"
)

// sqliteTimeFormat matches SQLite's datetime('now') output ("2006-01-02 15:04:05").
// Used when scanning TEXT-stored timestamps back into time.Time values.
const sqliteTimeFormat = "2006-01-02 15:04:05"

// parseTime parses a SQLite-formatted timestamp string. An empty string or
// an unparseable value yields a zero time.Time.
func parseTime(value string) time.Time {
	if value == "" {
		return time.Time{}
	}
	if t, err := time.Parse(sqliteTimeFormat, value); err == nil {
		return t.UTC()
	}
	if t, err := time.Parse(time.RFC3339, value); err == nil {
		return t.UTC()
	}
	return time.Time{}
}

// parseNullTime converts a sql.NullString holding a SQLite timestamp into
// a *time.Time. Invalid/zero values become nil.
func parseNullTime(value sql.NullString) *time.Time {
	if !value.Valid {
		return nil
	}
	t := parseTime(value.String)
	if t.IsZero() {
		return nil
	}
	return &t
}

// boolToInt converts a bool to SQLite's 0/1 integer bool convention.
func boolToInt(value bool) int {
	if value {
		return 1
	}
	return 0
}

// intToBool converts SQLite's 0/1 integer bool convention into a Go bool.
func intToBool(value int) bool {
	return value == 1
}

// DBTX is the minimal interface satisfied by both *sql.DB and *sql.Tx.
// Stores accept DBTX so they can operate either outside or inside a transaction.
type DBTX interface {
	ExecContext(ctx context.Context, query string, args ...interface{}) (sql.Result, error)
	QueryContext(ctx context.Context, query string, args ...interface{}) (*sql.Rows, error)
	QueryRowContext(ctx context.Context, query string, args ...interface{}) *sql.Row
}

// scanNullString converts a sql.NullString to a plain string (empty string if null).
func scanNullString(ns sql.NullString) string {
	if ns.Valid {
		return ns.String
	}
	return ""
}

// nullString converts an empty string to sql.NullString{Valid: false}.
func nullString(s string) sql.NullString {
	if s == "" {
		return sql.NullString{}
	}
	return sql.NullString{String: s, Valid: true}
}

// nullInt converts a *int to sql.NullInt64.
func nullInt(v *int) sql.NullInt64 {
	if v == nil {
		return sql.NullInt64{}
	}
	return sql.NullInt64{Int64: int64(*v), Valid: true}
}

// scanNullInt converts a sql.NullInt64 to a *int.
func scanNullInt(ni sql.NullInt64) *int {
	if !ni.Valid {
		return nil
	}
	v := int(ni.Int64)
	return &v
}
