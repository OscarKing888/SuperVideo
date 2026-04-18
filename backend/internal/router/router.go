package router

import (
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"

	"supervideo-server/internal/handlers"
)

// New builds and returns the Chi router with all routes wired up.
func New(app *handlers.App) http.Handler {
	r := chi.NewRouter()

	// Global middleware chain
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(middleware.Compress(5))
	r.Use(middleware.Heartbeat("/ping"))
	r.Use(app.SecurityHeaders)
	r.Use(app.CORS)

	// Root health check
	r.Get("/", func(w http.ResponseWriter, r *http.Request) {
		app.RespondJSON(w, http.StatusOK, map[string]string{
			"service": "supervideo",
			"status":  "ok",
		})
	})

	// --- Client upload endpoint (API-key auth) ---
	r.With(app.ClientAuth.Middleware).Post("/api/v1/upload", app.HandleUpload)

	// --- Authenticated query endpoints (session auth) ---
	r.Group(func(r chi.Router) {
		r.Use(app.SessionAuthRequired)

		r.Get("/api/v1/videos", app.HandleListVideos)
		r.Get("/api/v1/videos/{id}", app.HandleGetVideo)
		r.Get("/api/v1/species", app.HandleSpeciesStats)
		r.Get("/api/v1/clients", app.HandleListClients)
	})

	// --- Auth endpoints ---
	r.Post("/api/auth/register", app.HandleRegister)
	r.Post("/api/auth/login", app.HandleLogin)
	r.With(app.SessionAuthOptional).Get("/api/auth/me", app.HandleMe)
	r.With(app.SessionAuthRequired).Post("/api/auth/logout", app.HandleLogout)

	// --- Admin endpoints (session auth + admin role) ---
	r.Group(func(r chi.Router) {
		r.Use(app.AdminRequired)

		r.Get("/api/admin/overview", app.HandleOverview)
		r.Get("/api/admin/clients", app.HandleListClients)
	})

	return r
}
