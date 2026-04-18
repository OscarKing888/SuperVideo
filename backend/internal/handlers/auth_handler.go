package handlers

import (
	"net/http"
	"strings"

	"supervideo-server/internal/models"
)

// HandleLogin authenticates a user and issues a session cookie.
func (a *App) HandleLogin(w http.ResponseWriter, r *http.Request) {
	var req models.LoginRequest
	if err := decodeJSON(r, &req); err != nil {
		a.respondError(w, http.StatusBadRequest, "invalid JSON body")
		return
	}

	user, session, err := a.UserService.Login(r.Context(), req.Username, req.Password)
	if err != nil {
		a.respondError(w, http.StatusUnauthorized, "invalid username or password")
		return
	}

	a.setSessionCookie(w, r, session)
	a.RespondJSON(w, http.StatusOK, map[string]interface{}{
		"authenticated": true,
		"user":          user,
	})
}

// HandleLogout invalidates the current user session.
func (a *App) HandleLogout(w http.ResponseWriter, r *http.Request) {
	if cookie, err := r.Cookie(a.Config.SessionName); err == nil && cookie.Value != "" {
		_ = a.UserService.Logout(r.Context(), cookie.Value)
	}
	a.clearSessionCookie(w, r)
	a.RespondJSON(w, http.StatusOK, map[string]bool{"ok": true})
}

// HandleMe returns the currently logged-in user, or {authenticated:false}.
func (a *App) HandleMe(w http.ResponseWriter, r *http.Request) {
	user := CurrentUser(r)
	if user == nil {
		a.RespondJSON(w, http.StatusOK, map[string]interface{}{"authenticated": false})
		return
	}
	a.RespondJSON(w, http.StatusOK, map[string]interface{}{
		"authenticated": true,
		"user":          user,
	})
}

// HandleRegister creates a new user account.
func (a *App) HandleRegister(w http.ResponseWriter, r *http.Request) {
	var req models.RegisterRequest
	if err := decodeJSON(r, &req); err != nil {
		a.respondError(w, http.StatusBadRequest, "invalid JSON body")
		return
	}
	if strings.TrimSpace(req.Username) == "" {
		a.respondError(w, http.StatusBadRequest, "username is required")
		return
	}

	user, session, err := a.UserService.Register(r.Context(), req)
	if err != nil {
		msg := err.Error()
		if strings.Contains(msg, "UNIQUE constraint") || strings.Contains(msg, "already") {
			a.respondError(w, http.StatusConflict, "username already in use")
			return
		}
		a.respondError(w, http.StatusBadRequest, msg)
		return
	}

	a.setSessionCookie(w, r, session)
	a.RespondJSON(w, http.StatusCreated, map[string]interface{}{
		"authenticated": true,
		"user":          user,
	})
}
