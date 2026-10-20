package main

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"time"
)

type Job struct {
	State    string         `json:"state"`
	Message  string         `json:"message"`
	Progress int            `json:"progress"`
	Result   map[string]any `json:"result,omitempty"`
}
type Service struct {
	mu          sync.Mutex
	media       map[string]Media
	jobs        map[string]*Job
	packages    map[string]string
	root        string
	defaultRoot string
	runtime     string
	uploads     string
	back        string
	busy        bool
	ctx         context.Context
}

func token() string {
	b := make([]byte, 12)
	if _, e := rand.Read(b); e != nil {
		panic(e)
	}
	return hex.EncodeToString(b)
}
func respond(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}
func failure(w http.ResponseWriter, status int, err error) {
	respond(w, status, map[string]string{"error": err.Error()})
}
func decode(w http.ResponseWriter, r *http.Request, v any) error {
	if !strings.HasPrefix(r.Header.Get("Content-Type"), "application/json") {
		return fmt.Errorf("send application/json")
	}
	d := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1024*1024))
	d.DisallowUnknownFields()
	if e := d.Decode(v); e != nil {
		return e
	}
	var extra any
	if e := d.Decode(&extra); e != io.EOF {
		return fmt.Errorf("send one JSON object")
	}
	return nil
}
func localRequest(r *http.Request) bool {
	host, _, e := net.SplitHostPort(r.Host)
	if e != nil {
		return false
	}
	ip := net.ParseIP(host)
	if host != "localhost" && (ip == nil || !ip.IsLoopback()) {
		return false
	}
	if origin := r.Header.Get("Origin"); origin != "" {
		u, e := url.Parse(origin)
		if e != nil || u.Host != r.Host {
			return false
		}
	}
	return true
}
func (s *Service) handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/health", func(w http.ResponseWriter, r *http.Request) {
		respond(w, 200, map[string]any{"ok": true, "tool": "archive-carousel"})
	})
	mux.HandleFunc("GET /api/settings", func(w http.ResponseWriter, r *http.Request) {
		s.mu.Lock()
		defer s.mu.Unlock()
		respond(w, 200, map[string]any{"path": s.root, "defaultPath": s.defaultRoot, "back": s.back})
	})
	mux.HandleFunc("POST /api/settings", s.settings)
	mux.HandleFunc("POST /api/media", s.upload)
	mux.HandleFunc("GET /api/media/{id}/thumbnail", s.thumbnail)
	mux.HandleFunc("POST /api/generate", s.startJob)
	mux.HandleFunc("GET /api/jobs/{id}", func(w http.ResponseWriter, r *http.Request) {
		s.mu.Lock()
		defer s.mu.Unlock()
		j, ok := s.jobs[r.PathValue("id")]
		if !ok {
			http.NotFound(w, r)
			return
		}
		respond(w, 200, j)
	})
	mux.HandleFunc("GET /files/{package}/{file...}", s.file)
	web, _ := fs.Sub(resources, "web")
	mux.Handle("GET /", http.FileServer(http.FS(web)))
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("Referrer-Policy", "no-referrer")
		w.Header().Set("Content-Security-Policy", "default-src 'self'; img-src 'self' blob:; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
		if !localRequest(r) {
			failure(w, 403, fmt.Errorf("this tool accepts same-origin localhost requests only"))
			return
		}
		mux.ServeHTTP(w, r)
	})
}
func (s *Service) settings(w http.ResponseWriter, r *http.Request) {
	var c struct {
		Path       string `json:"path"`
		UseDefault bool   `json:"useDefault"`
	}
	if e := decode(w, r, &c); e != nil {
		failure(w, 400, e)
		return
	}
	target := strings.TrimSpace(c.Path)
	if c.UseDefault {
		target = s.defaultRoot
	}
	if target == "" {
		failure(w, 400, fmt.Errorf("choose an export folder"))
		return
	}
	if strings.HasPrefix(target, "~/") {
		home, e := os.UserHomeDir()
		if e != nil {
			failure(w, 400, e)
			return
		}
		target = filepath.Join(home, target[2:])
	}
	if !filepath.IsAbs(target) {
		failure(w, 400, fmt.Errorf("use an absolute folder path"))
		return
	}
	target = filepath.Clean(target)
	if e := os.MkdirAll(target, 0755); e != nil {
		failure(w, 400, e)
		return
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	temp := filepath.Join(s.runtime, "settings.json.tmp")
	if e := writeJSON(temp, map[string]string{"path": target}); e != nil {
		failure(w, 500, e)
		return
	}
	if e := os.Rename(temp, filepath.Join(s.runtime, "settings.json")); e != nil {
		failure(w, 500, e)
		return
	}
	s.root = target
	respond(w, 200, map[string]string{"path": target})
}
func (s *Service) upload(w http.ResponseWriter, r *http.Request) {
	name := filepath.Base(r.URL.Query().Get("name"))
	ext := strings.ToLower(filepath.Ext(name))
	if !strings.Contains("|.mp4|.mov|.mkv|.webm|.m4v|.avi|.png|.jpg|.jpeg|.webp|.tif|.tiff|.bmp|", "|"+ext+"|") || ext == "" {
		failure(w, 400, fmt.Errorf("choose MP4, MOV, MKV, WebM, AVI, PNG, JPEG, WebP, TIFF or BMP"))
		return
	}
	id := token()
	path := filepath.Join(s.uploads, id+ext)
	f, e := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if e != nil {
		failure(w, 500, e)
		return
	}
	n, e := io.Copy(f, http.MaxBytesReader(w, r.Body, 2*1024*1024*1024))
	closeErr := f.Close()
	if e == nil {
		e = closeErr
	}
	if e != nil || n == 0 {
		os.Remove(path)
		failure(w, 400, fmt.Errorf("upload failed or exceeds 2 GB; choose a smaller file"))
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 60*time.Second)
	defer cancel()
	m, e := probe(ctx, path)
	if e != nil {
		os.Remove(path)
		failure(w, 400, e)
		return
	}
	m.ID = id
	m.Name = name
	m.Path = path
	s.mu.Lock()
	s.media[id] = m
	s.mu.Unlock()
	respond(w, 201, m)
}
func (s *Service) thumbnail(w http.ResponseWriter, r *http.Request) {
	s.mu.Lock()
	m, ok := s.media[r.PathValue("id")]
	s.mu.Unlock()
	if !ok {
		http.NotFound(w, r)
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 30*time.Second)
	defer cancel()
	out, e := command(ctx, "ffmpeg", "-v", "error", "-nostdin", "-threads", "1", "-i", m.Path, "-frames:v", "1", "-vf", "scale=320:240:force_original_aspect_ratio=decrease", "-f", "image2pipe", "-vcodec", "png", "pipe:1")
	if e != nil {
		failure(w, 400, e)
		return
	}
	w.Header().Set("Content-Type", "image/png")
	w.Write(out)
}
func (s *Service) startJob(w http.ResponseWriter, r *http.Request) {
	var c Config
	if e := decode(w, r, &c); e != nil {
		failure(w, 400, e)
		return
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.busy {
		failure(w, 409, fmt.Errorf("an export is already running; wait for it to finish"))
		return
	}
	t, e := schedule(c, s.media)
	if e != nil {
		failure(w, 400, e)
		return
	}
	for _, exe := range []string{"ffmpeg", "ffprobe"} {
		if _, e = exec.LookPath(exe); e != nil {
			failure(w, 503, fmt.Errorf("install %s and restart the app", exe))
			return
		}
	}
	id := token()
	s.jobs[id] = &Job{State: "running", Message: "Starting", Progress: 0}
	s.busy = true
	root := s.root
	go func() {
		ctx, cancel := context.WithTimeout(s.ctx, 2*time.Hour)
		defer cancel()
		result, err := generate(ctx, t, root, id, func(msg string, p int) {
			s.mu.Lock()
			defer s.mu.Unlock()
			j := s.jobs[id]
			j.Message = msg
			j.Progress = p
		})
		s.mu.Lock()
		defer s.mu.Unlock()
		s.busy = false
		j := s.jobs[id]
		if err != nil {
			j.State = "error"
			j.Message = err.Error()
			return
		}
		j.State = "done"
		j.Message = "Fusion group ready"
		j.Progress = 100
		j.Result = result
		s.packages[result["package"].(string)] = result["outputDir"].(string)
	}()
	respond(w, 202, map[string]string{"jobId": id})
}
func (s *Service) file(w http.ResponseWriter, r *http.Request) {
	s.mu.Lock()
	root, ok := s.packages[r.PathValue("package")]
	s.mu.Unlock()
	if !ok {
		http.NotFound(w, r)
		return
	}
	target := filepath.Join(root, filepath.FromSlash(r.PathValue("file")))
	resolved, e := filepath.EvalSymlinks(target)
	if e != nil {
		http.NotFound(w, r)
		return
	}
	canonicalRoot, e := filepath.EvalSymlinks(root)
	if e != nil {
		http.NotFound(w, r)
		return
	}
	rel, e := filepath.Rel(canonicalRoot, resolved)
	if e != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		http.Error(w, "forbidden", 403)
		return
	}
	st, e := os.Stat(resolved)
	if e != nil || !st.Mode().IsRegular() {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=%q", filepath.Base(resolved)))
	http.ServeFile(w, r, resolved)
}
func main() {
	listen := flag.String("listen", "127.0.0.1:8788", "localhost address (port 0 selects a free port)")
	repo := flag.String("repo-root", "../../..", "workspace root")
	exports := flag.String("exports-root", "", "default carousel export folder")
	back := flag.String("back-url", "http://127.0.0.1:8787/", "map app URL")
	parent := flag.Int("parent-pid", 0, "exit when the owning app process exits")
	flag.Parse()
	host, _, e := net.SplitHostPort(*listen)
	if e != nil || net.ParseIP(host) == nil || !net.ParseIP(host).IsLoopback() {
		log.Fatal("listen must be a loopback IP address")
	}
	root, e := filepath.Abs(*repo)
	if e != nil {
		log.Fatal(e)
	}
	runtimeDir := filepath.Join(root, "app", "runtime", "archive-carousel")
	if e = os.MkdirAll(runtimeDir, 0700); e != nil {
		log.Fatal(e)
	}
	if *exports == "" {
		*exports = filepath.Join(root, "exports", "archive-carousels")
	}
	*exports, e = filepath.Abs(*exports)
	if e != nil {
		log.Fatal(e)
	}
	uploads, e := os.MkdirTemp(runtimeDir, "uploads-")
	if e != nil {
		log.Fatal(e)
	}
	defer os.RemoveAll(uploads)
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	s := &Service{media: map[string]Media{}, jobs: map[string]*Job{}, packages: map[string]string{}, root: *exports, defaultRoot: *exports, runtime: runtimeDir, uploads: uploads, back: *back, ctx: ctx}
	if raw, e := os.ReadFile(filepath.Join(runtimeDir, "settings.json")); e == nil {
		var c struct {
			Path string `json:"path"`
		}
		if json.Unmarshal(raw, &c) == nil && filepath.IsAbs(c.Path) {
			s.root = c.Path
		}
	}
	ln, e := net.Listen("tcp", *listen)
	if e != nil {
		log.Fatal(e)
	}
	server := &http.Server{Handler: s.handler(), ReadHeaderTimeout: 10 * time.Second, IdleTimeout: 60 * time.Second}
	// The parent reads this single readiness record, rather than assuming a fixed port.
	fmt.Printf("{\"url\":%q}\n", "http://"+ln.Addr().String())
	go func() {
		if e := server.Serve(ln); e != nil && e != http.ErrServerClosed {
			log.Print(e)
			stop()
		}
	}()
	if *parent > 0 {
		go func() {
			ticker := time.NewTicker(2 * time.Second)
			defer ticker.Stop()
			for {
				select {
				case <-ctx.Done():
					return
				case <-ticker.C:
					if os.Getppid() != *parent {
						stop()
						return
					}
				}
			}
		}()
	}
	<-ctx.Done()
	shutdown, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_ = server.Shutdown(shutdown)
}
