package models

// UploadVideo is a single video entry within an UploadRequest.
type UploadVideo struct {
	FileName   string  `json:"file_name"`
	FileHash   string  `json:"file_hash"`
	DurationMs *int    `json:"duration_ms,omitempty"`
	FrameCount *int    `json:"frame_count,omitempty"`
}

// UploadDetection is a single detection entry within an UploadRequest.
type UploadDetection struct {
	VideoIndex  int     `json:"video_index"`
	FrameNumber int     `json:"frame_number"`
	BBoxX       float64 `json:"bbox_x"`
	BBoxY       float64 `json:"bbox_y"`
	BBoxW       float64 `json:"bbox_w"`
	BBoxH       float64 `json:"bbox_h"`
	Confidence  float64 `json:"confidence"`
}

// UploadClassification is a single classification entry within an UploadRequest.
type UploadClassification struct {
	DetectionIndex int     `json:"detection_index"`
	SpeciesName    string  `json:"species_name"`
	SpeciesNameZh  string  `json:"species_name_zh,omitempty"`
	ScientificName string  `json:"scientific_name,omitempty"`
	Confidence     float64 `json:"confidence"`
	Rank           int     `json:"rank"`
}

// UploadRequest is the batch upload payload from a client machine.
// Videos, detections, and classifications are cross-referenced by index.
type UploadRequest struct {
	Videos          []UploadVideo          `json:"videos"`
	Detections      []UploadDetection      `json:"detections"`
	Classifications []UploadClassification `json:"classifications"`
}

// UploadResponse is returned after a successful batch upload.
type UploadResponse struct {
	VideosCreated          int      `json:"videos_created"`
	VideosSkipped          int      `json:"videos_skipped"`
	DetectionsCreated      int      `json:"detections_created"`
	ClassificationsCreated int      `json:"classifications_created"`
	VideoIDs               []string `json:"video_ids"`
}

// SpeciesStats holds aggregated statistics for a single species.
type SpeciesStats struct {
	SpeciesName    string  `json:"species_name"`
	SpeciesNameZh  string  `json:"species_name_zh,omitempty"`
	ScientificName string  `json:"scientific_name,omitempty"`
	Count          int     `json:"count"`
	AvgConfidence  float64 `json:"avg_confidence"`
}

// OverviewStats holds summary statistics for the admin dashboard.
type OverviewStats struct {
	TotalClients         int `json:"total_clients"`
	TotalVideos          int `json:"total_videos"`
	TotalDetections      int `json:"total_detections"`
	TotalClassifications int `json:"total_classifications"`
	UniqueSpecies        int `json:"unique_species"`
}

// ErrorResponse is a standard JSON error returned by the API.
type ErrorResponse struct {
	Error string `json:"error"`
}
