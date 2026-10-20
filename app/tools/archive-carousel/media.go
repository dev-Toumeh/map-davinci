package main

import (
	"archive/zip"
	"bytes"
	"context"
	"embed"
	"encoding/json"
	"fmt"
	"image"
	"image/color"
	"image/draw"
	"image/png"
	"io"
	"math"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

//go:embed assets/film.png web/*
var resources embed.FS

func command(ctx context.Context, exe string, args ...string) ([]byte, error) {
	cmd := exec.CommandContext(ctx, exe, args...)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	out, err := cmd.Output()
	if err != nil {
		msg := stderr.String()
		if len(msg) > 2000 {
			msg = msg[len(msg)-2000:]
		}
		return nil, fmt.Errorf("%s failed: %v %s", exe, err, msg)
	}
	return out, nil
}
func probe(ctx context.Context, path string) (Media, error) {
	out, err := command(ctx, "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path)
	if err != nil {
		return Media{}, err
	}
	var p struct {
		Streams []struct {
			Type     string            `json:"codec_type"`
			Width    int               `json:"width"`
			Height   int               `json:"height"`
			FPS      string            `json:"avg_frame_rate"`
			Frames   string            `json:"nb_frames"`
			Duration string            `json:"duration"`
			Pixel    string            `json:"pix_fmt"`
			Tags     map[string]string `json:"tags"`
			Side     []struct {
				Rotation float64 `json:"rotation"`
			} `json:"side_data_list"`
		} `json:"streams"`
		Format struct {
			Duration string `json:"duration"`
		} `json:"format"`
	}
	if err = json.Unmarshal(out, &p); err != nil {
		return Media{}, err
	}
	for _, s := range p.Streams {
		if s.Type != "video" {
			continue
		}
		m := Media{Width: s.Width, Height: s.Height, Kind: "video"}
		m.Frames, _ = strconv.Atoi(s.Frames)
		m.Duration, _ = strconv.ParseFloat(s.Duration, 64)
		if m.Duration <= 0 {
			m.Duration, _ = strconv.ParseFloat(p.Format.Duration, 64)
		}
		parts := strings.Split(s.FPS, "/")
		if len(parts) == 2 {
			a, _ := strconv.ParseFloat(parts[0], 64)
			b, _ := strconv.ParseFloat(parts[1], 64)
			if b > 0 {
				m.FPS = a / b
			}
		}
		rotation, _ := strconv.ParseFloat(s.Tags["rotate"], 64)
		for _, side := range s.Side {
			rotation = side.Rotation
		}
		m.Rotation = rotation
		if math.Mod(math.Abs(rotation), 180) > 45 {
			m.Width, m.Height = m.Height, m.Width
		}
		m.Alpha = strings.HasPrefix(s.Pixel, "yuva") || strings.HasPrefix(s.Pixel, "rgba") || strings.HasPrefix(s.Pixel, "bgra") || strings.HasPrefix(s.Pixel, "argb") || strings.HasPrefix(s.Pixel, "abgr") || strings.HasPrefix(s.Pixel, "ya") || strings.HasPrefix(s.Pixel, "gbrap") || s.Tags["alpha_mode"] == "1"
		ext := strings.ToLower(filepath.Ext(path))
		switch ext {
		case ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp":
			m.Kind = "photo"
			m.Duration = 0
		}
		if m.Width <= 0 || m.Height <= 0 || m.Width > 16384 || m.Height > 16384 {
			return m, fmt.Errorf("media dimensions must be between 1 and 16384 pixels")
		}
		if m.Kind == "video" && (!finite(m.Duration) || m.Duration <= 0) {
			return m, fmt.Errorf("video duration could not be read")
		}
		return m, nil
	}
	return Media{}, fmt.Errorf("file does not contain an image or video stream")
}

func savePNG(path string, img image.Image) error {
	f, e := os.Create(path)
	if e != nil {
		return e
	}
	e = png.Encode(f, img)
	closeErr := f.Close()
	if e != nil {
		return e
	}
	return closeErr
}

// Bilinear scaling keeps the film lettering proportional without extra Go dependencies.
func scaled(src image.Image, w, h int) *image.NRGBA {
	dst := image.NewNRGBA(image.Rect(0, 0, w, h))
	b := src.Bounds()
	for y := 0; y < h; y++ {
		sy := (float64(y)+.5)*float64(b.Dy())/float64(h) - .5
		sy = math.Max(0, math.Min(float64(b.Dy()-1), sy))
		y0 := int(sy)
		y1 := min(y0+1, b.Dy()-1)
		fy := sy - float64(y0)
		for x := 0; x < w; x++ {
			sx := (float64(x)+.5)*float64(b.Dx())/float64(w) - .5
			sx = math.Max(0, math.Min(float64(b.Dx()-1), sx))
			x0 := int(sx)
			x1 := min(x0+1, b.Dx()-1)
			fx := sx - float64(x0)
			samples := []color.NRGBA{color.NRGBAModel.Convert(src.At(b.Min.X+x0, b.Min.Y+y0)).(color.NRGBA), color.NRGBAModel.Convert(src.At(b.Min.X+x1, b.Min.Y+y0)).(color.NRGBA), color.NRGBAModel.Convert(src.At(b.Min.X+x0, b.Min.Y+y1)).(color.NRGBA), color.NRGBAModel.Convert(src.At(b.Min.X+x1, b.Min.Y+y1)).(color.NRGBA)}
			weights := []float64{(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy}
			var rgba [4]float64
			for i, c := range samples {
				a := float64(c.A) / 255
				rgba[0] += float64(c.R) * a * weights[i]
				rgba[1] += float64(c.G) * a * weights[i]
				rgba[2] += float64(c.B) * a * weights[i]
				rgba[3] += float64(c.A) * weights[i]
			}
			var c color.NRGBA
			c.A = uint8(math.Round(rgba[3]))
			if rgba[3] > 0 {
				c.R = uint8(math.Round(rgba[0] * 255 / rgba[3]))
				c.G = uint8(math.Round(rgba[1] * 255 / rgba[3]))
				c.B = uint8(math.Round(rgba[2] * 255 / rgba[3]))
			}
			dst.SetNRGBA(x, y, c)
		}
	}
	return dst
}
func film(t Timeline, dir string) error {
	raw, e := resources.ReadFile("assets/film.png")
	if e != nil {
		return e
	}
	if e = os.WriteFile(filepath.Join(dir, "film-original.png"), raw, 0644); e != nil {
		return e
	}
	im, e := png.Decode(bytes.NewReader(raw))
	if e != nil {
		return e
	}
	w, h := t.CardWidth, t.CardHeight
	var out image.Image
	if t.Aspect == "4:3" {
		out = scaled(im, w, h)
	} else {
		dst := image.NewNRGBA(image.Rect(0, 0, w, h))
		b := im.Bounds()
		stripH := int(float64(b.Dy()) * .15)
		targetH := int(float64(stripH) * float64(w) / float64(b.Dx()))
		top := im.(interface {
			SubImage(image.Rectangle) image.Image
		}).SubImage(image.Rect(0, 0, b.Dx(), stripH))
		bottom := im.(interface {
			SubImage(image.Rectangle) image.Image
		}).SubImage(image.Rect(0, b.Dy()-stripH, b.Dx(), b.Dy()))
		draw.Draw(dst, image.Rect(0, 0, w, targetH), scaled(top, w, targetH), image.Point{}, draw.Src)
		draw.Draw(dst, image.Rect(0, h-targetH, w, h), scaled(bottom, w, targetH), image.Point{}, draw.Src)
		out = dst
	}
	return savePNG(filepath.Join(dir, "film-overlay.png"), out)
}

func extract(ctx context.Context, s Section, fps float64, dest string) error {
	args := []string{"-v", "error", "-nostdin", "-threads", "2", "-y"}
	if s.Media.Kind == "video" {
		args = append(args, "-ss", fmt.Sprint(s.Start))
	}
	args = append(args, "-i", s.Media.Path, "-map", "0:v:0", "-an", "-sn", "-dn")
	if s.Media.Kind == "photo" {
		args = append(args, "-frames:v", "1", "-update", "1", dest)
		_, e := command(ctx, "ffmpeg", args...)
		return e
	}
	// Exact cuts and matching timeline FPS: no keyframe-seeking approximation or speed change.
	// Copy only complete clips already matching the selected FPS and frame count.
	if s.Start == 0 && s.Media.Rotation == 0 && s.Media.Frames == s.ClipFrames && math.Abs(s.Media.FPS-fps) < 1e-7 && math.Abs(s.Media.Duration-float64(s.ClipFrames)/fps) < 1e-6 && strings.EqualFold(filepath.Ext(s.Media.Path), filepath.Ext(dest)) {
		_, e := command(ctx, "ffmpeg", append(args, "-c:v", "copy", dest)...)
		return e
	}
	filter := fmt.Sprintf("fps=%g,tpad=stop_mode=clone:stop_duration=%g", fps, 2/fps)
	args = append(args, "-frames:v", strconv.Itoa(s.ClipFrames))
	if s.Media.Alpha {
		args = append(args, "-vf", filter, "-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le")
	} else {
		args = append(args, "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", "-vf", filter+",pad=ceil(iw/2)*2:ceil(ih/2)*2", "-movflags", "+faststart")
	}
	args = append(args, dest)
	_, e := command(ctx, "ffmpeg", args...)
	return e
}

func writeJSON(path string, v any) error {
	b, e := json.MarshalIndent(v, "", "  ")
	if e != nil {
		return e
	}
	return os.WriteFile(path, append(b, '\n'), 0644)
}
func zipFolder(dir, dest, prefix string) error {
	f, e := os.Create(dest)
	if e != nil {
		return e
	}
	z := zip.NewWriter(f)
	e = filepath.WalkDir(dir, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() || path == dest {
			return nil
		}
		rel, _ := filepath.Rel(dir, path)
		w, err := z.Create(filepath.ToSlash(filepath.Join(prefix, rel)))
		if err != nil {
			return err
		}
		in, err := os.Open(path)
		if err != nil {
			return err
		}
		defer in.Close()
		_, err = io.Copy(w, in)
		return err
	})
	ze := z.Close()
	fe := f.Close()
	if e != nil {
		return e
	}
	if ze != nil {
		return ze
	}
	return fe
}
func generate(ctx context.Context, t Timeline, root, id string, progress func(string, int)) (map[string]any, error) {
	if e := os.MkdirAll(root, 0755); e != nil {
		return nil, e
	}
	temp, e := os.MkdirTemp(root, ".carousel-")
	if e != nil {
		return nil, e
	}
	defer os.RemoveAll(temp)
	name := "Archive_" + safeName.ReplaceAllString(t.Name, "_")
	if len(name) > 64 {
		name = name[:64]
	}
	if name == "Archive_" {
		name = "Archive_Carousel"
	}
	final := filepath.Join(root, name+"_"+id)
	for _, d := range []string{"media", "assets"} {
		if e = os.MkdirAll(filepath.Join(temp, d), 0755); e != nil {
			return nil, e
		}
	}
	progress("Preparing film artwork", 3)
	if e = film(t, filepath.Join(temp, "assets")); e != nil {
		return nil, e
	}
	for i := range t.Sections {
		s := &t.Sections[i]
		ext := ".mp4"
		if s.Media.Kind == "photo" {
			ext = ".png"
		} else if s.Media.Alpha {
			ext = ".mov"
		}
		s.File = fmt.Sprintf("media/item-%03d%s", i+1, ext)
		progress(fmt.Sprintf("Extracting item %d of %d", i+1, len(t.Sections)), 5+i*80/len(t.Sections))
		if e = extract(ctx, *s, t.FPS, filepath.Join(temp, s.File)); e != nil {
			return nil, e
		}
		// Re-probe normalized orientation and dimensions (including even-sized codec padding).
		info, err := probe(ctx, filepath.Join(temp, s.File))
		if err != nil {
			return nil, err
		}
		if s.Media.Kind == "video" && info.Frames != s.ClipFrames {
			return nil, fmt.Errorf("item %d decoded to %d frames; expected %d", i+1, info.Frames, s.ClipFrames)
		}
		s.Media.Width = info.Width
		s.Media.Height = info.Height
	}
	setting := name + ".setting"
	if e = os.WriteFile(filepath.Join(temp, setting), []byte(buildSetting(t, final)), 0644); e != nil {
		return nil, e
	}
	if e = writeJSON(filepath.Join(temp, "carousel.json"), t); e != nil {
		return nil, e
	}
	instructions := fmt.Sprintf("Archive Carousel — %d frames, %g FPS, %0.3f seconds.\nDrag %s into Fusion. Use a composition whose global start is frame 0; set its end to %d and its FPS to %g.\nThe first entrance and every later entrance/exit last %d frames. Open the group to edit native nodes.\nKeep this folder in place: Loaders reference its absolute paths. If moved, relink the media and film Loaders inside the group.\nOutput is silent, 3840x2160, transparent outside the cards.\nSource media was cut accurately and transcoded to timeline FPS, without resizing (except codec-required even padding).\nNo Resolve preview has been performed automatically.\n", t.Frames, t.FPS, float64(t.Frames)/t.FPS, setting, t.Frames-1, t.FPS, t.Movement)
	if e = os.WriteFile(filepath.Join(temp, "USAGE.txt"), []byte(instructions), 0644); e != nil {
		return nil, e
	}
	progress("Packaging editable Fusion group", 92)
	// Build ZIP before publishing: failed jobs leave no half-finished public package.
	if e = zipFolder(temp, filepath.Join(temp, "package.zip"), filepath.Base(final)); e != nil {
		return nil, e
	}
	if e = os.Rename(temp, final); e != nil {
		return nil, e
	}
	return map[string]any{"outputDir": final, "settingPath": filepath.Join(final, setting), "settingFile": setting, "package": filepath.Base(final), "frames": t.Frames, "fps": t.FPS, "seconds": float64(t.Frames) / t.FPS}, nil
}
func timeoutContext() (context.Context, context.CancelFunc) {
	return context.WithTimeout(context.Background(), 2*time.Hour)
}
