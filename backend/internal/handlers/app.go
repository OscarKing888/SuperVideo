package handlers

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"

	"supervideo-server/internal/config"
	"supervideo-server/internal/service"
)

// App holds all injected dependencies for HTTP handlers.
type App struct {
	Config        *config.Config
	UserService   *service.UserService
	UploadService *service.UploadService
	QueryService  *service.QueryService
	ClientAuth    *ClientAuthMiddleware
}

// NewApp constructs an App with all dependencies injected.
func NewApp(
	cfg *config.Config,
	userSvc *service.UserService,
	uploadSvc *service.UploadService,
	querySvc *service.QueryService,
	clientAuth *ClientAuthMiddleware,
) *App {
	return &App{
		Config:        cfg,
		UserService:   userSvc,
		UploadService: uploadSvc,
		QueryService:  querySvc,
		ClientAuth:    clientAuth,
	}
}

// RespondJSON writes a JSON response with the given status code.
func (a *App) RespondJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		_ = err
	}
}

// respondError writes a JSON error response.
func (a *App) respondError(w http.ResponseWriter, status int, msg string) {
	a.RespondJSON(w, status, map[string]string{"error": msg})
}

// respondServerError logs an internal error with context and returns a
// generic 500 response to the client (to avoid leaking internals).
func (a *App) respondServerError(w http.ResponseWriter, r *http.Request, context string, err error) {
	log.Printf("ERROR %s %s: %s: %v", r.Method, r.URL.Path, context, err)
	a.RespondJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal server error"})
}

// decodeJSON decodes the request body into v.
func decodeJSON(r *http.Request, v interface{}) error {
	return json.NewDecoder(r.Body).Decode(v)
}

// parseIntQuery extracts an integer query parameter with a default.
func parseIntQuery(r *http.Request, key string, defaultVal int) int {
	raw := r.URL.Query().Get(key)
	if raw == "" {
		return defaultVal
	}
	if v, err := strconv.Atoi(raw); err == nil && v >= 0 {
		return v
	}
	return defaultVal
}
