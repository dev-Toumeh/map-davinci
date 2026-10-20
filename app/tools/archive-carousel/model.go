package main

import (
	"fmt"
	"math"
	"regexp"
)

type Media struct {
	ID       string  `json:"id"`
	Name     string  `json:"name"`
	Kind     string  `json:"kind"`
	Width    int     `json:"width"`
	Height   int     `json:"height"`
	Duration float64 `json:"duration"`
	FPS      float64 `json:"fps"`
	Frames   int     `json:"frames,omitempty"`
	Rotation float64 `json:"rotation,omitempty"`
	Alpha    bool    `json:"alpha"`
	Path     string  `json:"-"`
}
type Item struct {
	MediaID  string  `json:"mediaId"`
	Start    float64 `json:"start"`
	Duration float64 `json:"duration"`
	Fit      string  `json:"fit"`
}
type Config struct {
	Name     string  `json:"name"`
	Aspect   string  `json:"aspect"`
	FPS      float64 `json:"fps"`
	Movement int     `json:"movementFrames"`
	Items    []Item  `json:"items"`
}
type Section struct {
	Item
	Media      Media  `json:"media"`
	StartFrame int    `json:"startFrame"`
	EndFrame   int    `json:"endFrame"`
	EnterStart int    `json:"enterStart"`
	EnterEnd   int    `json:"enterEnd"`
	ExitStart  int    `json:"exitStart"`
	ExitEnd    int    `json:"exitEnd"`
	ClipFrames int    `json:"clipFrames"`
	File       string `json:"file"`
}
type Timeline struct {
	Config
	Frames     int       `json:"frames"`
	CardWidth  int       `json:"cardWidth"`
	CardHeight int       `json:"cardHeight"`
	Sections   []Section `json:"sections"`
}

var safeName = regexp.MustCompile(`[^A-Za-z0-9_]`)

func finite(n float64) bool { return !math.IsNaN(n) && !math.IsInf(n, 0) }
func schedule(c Config, media map[string]Media) (Timeline, error) {
	t := Timeline{Config: c}
	if !finite(c.FPS) || c.FPS < 1 || c.FPS > 120 {
		return t, fmt.Errorf("timeline FPS must be between 1 and 120")
	}
	if c.Movement < 1 || c.Movement > 240 {
		return t, fmt.Errorf("movement must be 1–240 frames")
	}
	if len(c.Items) == 0 {
		return t, fmt.Errorf("add at least one video or photo")
	}
	ratios := map[string]float64{"4:3": 4.0 / 3, "16:9": 16.0 / 9, "1:1": 1, "9:16": 9.0 / 16}
	ratio, ok := ratios[c.Aspect]
	if !ok {
		return t, fmt.Errorf("choose a supported card aspect ratio")
	}
	h := math.Min(2160*.85, 3840*.85/ratio)
	t.CardHeight = int(h/2) * 2
	t.CardWidth = int(h*ratio/2) * 2
	elapsed := 0.0
	for i, item := range c.Items {
		m, ok := media[item.MediaID]
		if !ok {
			return t, fmt.Errorf("item %d: upload a file first", i+1)
		}
		if !finite(item.Duration) || !finite(item.Start) || item.Duration <= 0 || item.Start < 0 {
			return t, fmt.Errorf("item %d: duration must be positive and source start cannot be negative", i+1)
		}
		if item.Fit != "fill" && item.Fit != "fit" {
			return t, fmt.Errorf("item %d: choose fill or fit", i+1)
		}
		if m.Kind == "video" && item.Start+item.Duration > m.Duration+1e-5 {
			return t, fmt.Errorf("item %d: selected range exceeds the %.3fs source video", i+1, m.Duration)
		}
		start := int(math.Round(elapsed * c.FPS))
		elapsed += item.Duration
		if elapsed > 86400 {
			return t, fmt.Errorf("carousel must not exceed 24 hours")
		}
		end := int(math.Round(elapsed * c.FPS))
		if end-start < 2*c.Movement {
			return t, fmt.Errorf("item %d: use at least %.3f seconds for %d-frame movements", i+1, float64(2*c.Movement)/c.FPS, c.Movement)
		}
		enter := start - c.Movement/2
		if i == 0 {
			enter = 0
		}
		t.Sections = append(t.Sections, Section{Item: item, Media: m, StartFrame: start, EndFrame: end, EnterStart: enter, EnterEnd: enter + c.Movement, ExitStart: end - c.Movement/2, ExitEnd: end - c.Movement/2 + c.Movement, ClipFrames: end - start})
	}
	t.Frames = int(math.Round(elapsed * c.FPS))
	last := &t.Sections[len(t.Sections)-1]
	last.ExitStart = t.Frames
	last.ExitEnd = t.Frames
	return t, nil
}
