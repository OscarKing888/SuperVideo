package handlers

import (
	"net/http"

	"supervideo-server/internal/models"
)

// HandleUpload processes a batch upload from a client machine.
// Requires ClientAuth middleware (X-API-Key header).
func (a *App) HandleUpload(w http.ResponseWriter, r *http.Request) {
	client := CurrentClient(r)
	if client == nil {
		a.respondError(w, http.StatusUnauthorized, "client authentication required")
		return
	}

	var req models.UploadRequest
	if err := decodeJSON(r, &req); err != nil {
		a.respondError(w, http.StatusBadRequest, "invalid JSON body")
		return
	}

	if len(req.Videos) == 0 {
		a.respondError(w, http.StatusBadRequest, "at least one video is required")
		return
	}

	resp, err := a.UploadService.ProcessUpload(r.Context(), client.ID, req)
	if err != nil {
		a.respondServerError(w, r, "process upload", err)
		return
	}

	a.RespondJSON(w, http.StatusOK, resp)
}
