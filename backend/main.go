package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"supervideo-server/internal/config"
	"supervideo-server/internal/database"
	"supervideo-server/internal/handlers"
	"supervideo-server/internal/router"
	"supervideo-server/internal/service"
	"supervideo-server/internal/store"
)

func main() {
	cfg := config.Load()

	// Open and configure SQLite
	db, err := database.Open(cfg.DBPath)
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	defer db.Close()

	// Run schema migrations (idempotent)
	if err := database.RunMigrations(db); err != nil {
		log.Fatalf("run migrations: %v", err)
	}
	// Seed the default admin user on first boot (idempotent)
	if err := database.SeedDefaults(db); err != nil {
		log.Fatalf("seed defaults: %v", err)
	}

	// Initialise stores (repository implementations)
	userStore := store.NewUserStore(db)
	sessionStore := store.NewSessionStore(db)
	clientStore := store.NewClientStore(db)
	videoStore := store.NewVideoStore(db)
	detectionStore := store.NewDetectionStore(db)
	classificationStore := store.NewClassificationStore(db)

	// Initialise transactor for atomic uploads
	transactor := store.NewSQLiteTransactor(db, videoStore, detectionStore, classificationStore)

	// Initialise services (business logic)
	userSvc := service.NewUserService(cfg, userStore, sessionStore)
	uploadSvc := service.NewUploadService(clientStore, transactor)
	querySvc := service.NewQueryService(videoStore, detectionStore, classificationStore, clientStore)

	// Build the HTTP application
	clientAuth := handlers.NewClientAuthMiddleware(clientStore)
	app := handlers.NewApp(cfg, userSvc, uploadSvc, querySvc, clientAuth)

	// Build router
	h := router.New(app)

	srv := &http.Server{
		Addr:         fmt.Sprintf("%s:%s", cfg.Host, cfg.Port),
		Handler:      h,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Start server in a goroutine so we can listen for shutdown signals.
	go func() {
		log.Printf("SuperVideo server starting on %s", srv.Addr)
		log.Printf("API: http://%s/", srv.Addr)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("server error: %v", err)
		}
	}()

	// Graceful shutdown on SIGINT / SIGTERM.
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf("server shutdown error: %v", err)
	}
	log.Println("server stopped")
}
