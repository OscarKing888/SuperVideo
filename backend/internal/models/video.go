package models

import "time"

// Video represents a video file uploaded by a client.
type Video struct {
	ID         string    `json:"id"`
	ClientID   string    `json:"client_id"`
	FileName   string    `json:"file_name"`
	FileHash   string    `json:"file_hash,omitempty"`
	DurationMs *int      `json:"duration_ms,omitempty"`
	FrameCount *int      `json:"frame_count,omitempty"`
	UploadedAt time.Time `json:"uploaded_at"`
}

// Detection represents a bird detection within a video frame.
type Detection struct {
	ID          string  `json:"id"`
	VideoID     string  `json:"video_id"`
	FrameNumber int     `json:"frame_number"`
	BBoxX       float64 `json:"bbox_x"`
	BBoxY       float64 `json:"bbox_y"`
	BBoxW       float64 `json:"bbox_w"`
	BBoxH       float64 `json:"bbox_h"`
	Confidence  float64 `json:"confidence"`
}

// Classification represents a species classification for a detection.
type Classification struct {
	ID             string  `json:"id"`
	DetectionID    string  `json:"detection_id"`
	SpeciesName    string  `json:"species_name"`
	SpeciesNameZh  string  `json:"species_name_zh,omitempty"`
	ScientificName string  `json:"scientific_name,omitempty"`
	Confidence     float64 `json:"confidence"`
	Rank           int     `json:"rank"`
}
