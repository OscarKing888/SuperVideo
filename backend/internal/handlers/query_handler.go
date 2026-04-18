package handlers

import (
	"net/http"

	"github.com/go-chi/chi/v5"
)

// HandleListVideos returns a paginated list of videos.
func (a *App) HandleListVideos(w http.ResponseWriter, r *http.Request) {
	limit := parseIntQuery(r, "limit", 50)
	offset := parseIntQuery(r, "offset", 0)

	videos, err := a.QueryService.ListVideos(r.Context(), limit, offset)
	if err != nil {
		a.respondServerError(w, r, "list videos", err)
		return
	}
	// Ensure non-nil slice for JSON encoding ([] instead of null)
	if videos == nil {
		a.RespondJSON(w, http.StatusOK, []struct{}{})
		return
	}
	a.RespondJSON(w, http.StatusOK, videos)
}

// HandleGetVideo returns a single video with its detections and classifications.
func (a *App) HandleGetVideo(w http.ResponseWriter, r *http.Request) {
	videoID := chi.URLParam(r, "id")
	if videoID == "" {
		a.respondError(w, http.StatusBadRequest, "video id is required")
		return
	}

	result, err := a.QueryService.GetVideo(r.Context(), videoID)
	if err != nil {
		a.respondServerError(w, r, "get video", err)
		return
	}
	a.RespondJSON(w, http.StatusOK, result)
}

// HandleSpeciesStats returns aggregated species statistics.
func (a *App) HandleSpeciesStats(w http.ResponseWriter, r *http.Request) {
	stats, err := a.QueryService.GetSpeciesStats(r.Context())
	if err != nil {
		a.respondServerError(w, r, "species stats", err)
		return
	}
	a.RespondJSON(w, http.StatusOK, stats)
}

// HandleListClients returns all registered client machines.
func (a *App) HandleListClients(w http.ResponseWriter, r *http.Request) {
	clients, err := a.QueryService.ListClients(r.Context())
	if err != nil {
		a.respondServerError(w, r, "list clients", err)
		return
	}
	a.RespondJSON(w, http.StatusOK, clients)
}

// HandleOverview returns summary statistics for the admin dashboard.
func (a *App) HandleOverview(w http.ResponseWriter, r *http.Request) {
	stats, err := a.QueryService.GetOverview(r.Context())
	if err != nil {
		a.respondServerError(w, r, "overview", err)
		return
	}
	a.RespondJSON(w, http.StatusOK, stats)
}
