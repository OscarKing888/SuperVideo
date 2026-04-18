package handlers

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"

	"supervideo-server/internal/models"
	"supervideo-server/internal/store"
)

// --- Context keys ---

// currentUserCtxKey is the unexported context key holding the currently
// authenticated user (populated by the session auth middleware).
type currentUserCtxKey struct{}

// currentClientCtxKey is the unexported context key holding the currently
// authenticated client (populated by the client auth middleware).
type currentClientCtxKey struct{}

// --- Security Headers ---

// SecurityHeaders adds common security headers to every response.
func (a *App) SecurityHeaders(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("X-Frame-Options", "DENY")
		w.Header().Set("X-XSS-Protection", "1; mode=block")
		w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
		next.ServeHTTP(w, r)
	})
}

// CORS adds permissive CORS headers suitable for a prototype API.
func (a *App) CORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
		w.Header().Set("Access-Control-Allow-Credentials", "true")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}

// --- Client Auth (API Key) ---

// ClientAuthMiddleware validates the X-API-Key header against the client store.
type ClientAuthMiddleware struct {
	clientStore *store.ClientStore
}

// NewClientAuthMiddleware constructs a ClientAuthMiddleware.
func NewClientAuthMiddleware(clientStore *store.ClientStore) *ClientAuthMiddleware {
	return &ClientAuthMiddleware{clientStore: clientStore}
}

// Middleware returns an http.Handler that validates the X-API-Key header.
func (m *ClientAuthMiddleware) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		apiKey := r.Header.Get("X-API-Key")
		if apiKey == "" {
			respondErrorStatic(w, http.StatusUnauthorized, "missing X-API-Key header")
			return
		}

		client, err := m.clientStore.GetByAPIKey(r.Context(), apiKey)
		if err != nil {
			respondErrorStatic(w, http.StatusUnauthorized, "invalid API key")
			return
		}

		r = r.WithContext(context.WithValue(r.Context(), currentClientCtxKey{}, client))
		next.ServeHTTP(w, r)
	})
}

// CurrentClient returns the client previously attached by the client auth middleware.
func CurrentClient(r *http.Request) *models.Client {
	client, _ := r.Context().Value(currentClientCtxKey{}).(*models.Client)
	return client
}

// --- Session Auth (Cookie) ---

// SessionAuthRequired gates the endpoint behind a valid user session cookie.
func (a *App) SessionAuthRequired(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		user := a.resolveUser(r)
		if user == nil {
			a.respondError(w, http.StatusUnauthorized, "authentication required")
			return
		}
		next.ServeHTTP(w, withUser(r, user))
	})
}

// SessionAuthOptional attempts to resolve the user from the session cookie
// but does not require it. Used by GET /api/auth/me.
func (a *App) SessionAuthOptional(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if user := a.resolveUser(r); user != nil {
			r = withUser(r, user)
		}
		next.ServeHTTP(w, r)
	})
}

// AdminRequired gates the endpoint behind a valid session + admin role.
func (a *App) AdminRequired(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		user := a.resolveUser(r)
		if user == nil {
			a.respondError(w, http.StatusUnauthorized, "authentication required")
			return
		}
		if user.Role != "admin" {
			a.respondError(w, http.StatusForbidden, "admin access required")
			return
		}
		next.ServeHTTP(w, withUser(r, user))
	})
}

// resolveUser loads the user attached to the request's session cookie,
// or nil if the cookie is missing/expired.
func (a *App) resolveUser(r *http.Request) *models.User {
	cookie, err := r.Cookie(a.Config.SessionName)
	if err != nil || cookie.Value == "" {
		return nil
	}
	user, err := a.UserService.GetBySessionToken(r.Context(), cookie.Value)
	if err != nil {
		return nil
	}
	return user
}

// CurrentUser returns the user previously attached by the auth middleware.
func CurrentUser(r *http.Request) *models.User {
	user, _ := r.Context().Value(currentUserCtxKey{}).(*models.User)
	return user
}

// withUser returns a request carrying the given user in its context.
func withUser(r *http.Request, user *models.User) *http.Request {
	return r.WithContext(context.WithValue(r.Context(), currentUserCtxKey{}, user))
}

// setSessionCookie writes the session cookie with secure defaults.
func (a *App) setSessionCookie(w http.ResponseWriter, r *http.Request, session *models.UserSession) {
	http.SetCookie(w, &http.Cookie{
		Name:     a.Config.SessionName,
		Value:    session.Token,
		Path:     "/",
		HttpOnly: true,
		SameSite: http.SameSiteStrictMode,
		Secure:   requestIsSecure(r),
		Expires:  session.ExpiresAt,
	})
}

// clearSessionCookie expires the session cookie on logout.
func (a *App) clearSessionCookie(w http.ResponseWriter, r *http.Request) {
	http.SetCookie(w, &http.Cookie{
		Name:     a.Config.SessionName,
		Value:    "",
		Path:     "/",
		HttpOnly: true,
		SameSite: http.SameSiteStrictMode,
		Secure:   requestIsSecure(r),
		MaxAge:   -1,
	})
}

// requestIsSecure returns true if the request was served over HTTPS.
func requestIsSecure(r *http.Request) bool {
	if r.TLS != nil {
		return true
	}
	return strings.EqualFold(r.Header.Get("X-Forwarded-Proto"), "https")
}

// respondErrorStatic writes a JSON error without needing an App receiver.
func respondErrorStatic(w http.ResponseWriter, status int, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]string{"error": msg})
}
