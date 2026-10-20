package main

import (
	"archive/zip"
	"bytes"
	"context"
	"encoding/json"
	"image"
	"image/color"
	"image/png"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func sample() (Config, map[string]Media) {
	return Config{Name: "Test", Aspect: "4:3", FPS: 24, Movement: 10, Items: []Item{{"a", 0, 5, "fill"}, {"b", 0, 2, "fit"}, {"c", 0, 5, "fill"}}}, map[string]Media{"a": {ID: "a", Kind: "video", Name: "a", Width: 768, Height: 576, Duration: 10}, "b": {ID: "b", Kind: "photo", Name: "b", Width: 600, Height: 900}, "c": {ID: "c", Kind: "video", Name: "c", Width: 1920, Height: 1080, Duration: 10}}
}
func TestSchedule(t *testing.T) {
	c, m := sample()
	s, e := schedule(c, m)
	if e != nil {
		t.Fatal(e)
	}
	if s.Frames != 288 {
		t.Fatal(s.Frames)
	}
	for i, row := range s.Sections {
		if row.EnterEnd-row.EnterStart != 10 {
			t.Fatal("entrance", i)
		}
		if i < len(s.Sections)-1 && row.ExitEnd-row.ExitStart != 10 {
			t.Fatal("exit", i)
		}
		if i > 0 && row.EnterStart != s.Sections[i-1].ExitStart {
			t.Fatal("handoff does not overlap")
		}
	}
	if s.Sections[0].EnterStart != 0 || s.Sections[0].EnterEnd != 10 {
		t.Fatal("first entrance")
	}
	if s.Sections[2].ExitStart != 288 {
		t.Fatal("last hold")
	}
	for _, aspect := range []string{"4:3", "16:9", "1:1", "9:16"} {
		c.Aspect = aspect
		s, e = schedule(c, m)
		if e != nil || s.CardWidth > 3264 || s.CardHeight > 1836 {
			t.Fatal(aspect, e)
		}
	}
	c.Items = []Item{{"a", 0, 5, "fill"}, {"b", 0, 2, "fit"}}
	s, e = schedule(c, m)
	if e != nil || s.Frames != 168 {
		t.Fatal("5+2 must equal seven seconds", e, s.Frames)
	}
	c.Items = c.Items[:1]
	s, e = schedule(c, m)
	if e != nil || len(s.Sections) != 1 {
		t.Fatal("single item", e)
	}
	c.Items = append(c.Items, Item{"c", 0, 5, "fill"}, Item{"b", 0, 2, "fit"}, Item{"a", 1, 2, "fill"})
	s, e = schedule(c, m)
	if e != nil || len(s.Sections) != 4 {
		t.Fatal("four items", e)
	}
}
func TestScheduleRejects(t *testing.T) {
	for _, test := range []string{"missing", "short", "range", "aspect", "fps", "negative"} {
		c, m := sample()
		switch test {
		case "missing":
			c.Items[0].MediaID = "unknown"
		case "short":
			c.Items[0].Duration = .1
		case "range":
			c.Items[0].Start = 8
		case "aspect":
			c.Aspect = "bad"
		case "fps":
			c.FPS = 0
		case "negative":
			c.Items[0].Start = -1
		}
		if _, e := schedule(c, m); e == nil {
			t.Fatal("accepted", test)
		}
	}
}
func TestNoRoundingDrift(t *testing.T) {
	c, m := sample()
	c.FPS = 29.97
	c.Items = nil
	for i := 0; i < 100; i++ {
		c.Items = append(c.Items, Item{"a", 0, 1.001, "fill"})
	}
	s, e := schedule(c, m)
	if e != nil {
		t.Fatal(e)
	}
	if s.Frames != 3000 {
		t.Fatal(s.Frames)
	}
}
func TestFusionSyntaxAndConnections(t *testing.T) {
	if _, e := exec.LookPath("luajit"); e != nil {
		t.Skip("LuaJIT not available")
	}
	c, m := sample()
	timeline, e := schedule(c, m)
	if e != nil {
		t.Fatal(e)
	}
	for i := range timeline.Sections {
		timeline.Sections[i].File = "media/item.png"
	}
	dir := t.TempDir()
	file := filepath.Join(dir, "test.setting")
	if e = os.WriteFile(file, []byte(buildSetting(timeline, dir)), 0600); e != nil {
		t.Fatal(e)
	}
	script := `local env=setmetatable({ordered=function() return function(t) return t end end},{__index=function(_,k) return function(t) t.__kind=k;return t end end});local f=assert(io.open(arg[1]));local chunk=assert(loadstring("return "..f:read("*a")));f:close();setfenv(chunk,env);local doc=chunk();local g=doc.Tools.Archive_Test;assert(g.__kind=="GroupOperator");local ts=g.Tools;for _,node in pairs(ts) do for _,input in pairs(node.Inputs or {}) do if type(input)=="table" and input.SourceOp then assert(ts[input.SourceOp],input.SourceOp) end end end;for _,input in pairs(g.Inputs) do assert(ts[input.SourceOp].Inputs[input.Source],input.Source) end;assert(ts.Canvas.Inputs.TopLeftAlpha.Value==0);assert(ts.Card1_Travel.KeyFrames[0][1]==.75);assert(ts.Card1_Travel.KeyFrames[10][1]==.5);assert(ts.Card2_Travel.KeyFrames[115][1]==.75);assert(ts.Card2_Travel.KeyFrames[125][1]==.5);assert(ts.Output.Inputs.LayerOrder.Value[0]==1);assert(ts.Output.Inputs.LayerOrder.Value[1]==2);assert(ts.Output.Inputs.LayerOrder.Value[2]==3);assert(ts.Output.Inputs.LayerOrder.Value[3]==nil);assert(ts.Card3_Travel.KeyFrames[288]==nil);assert(ts.Card1_Crop.Inputs.XSize.Value==2448);assert(ts.Card3_Resize.Inputs.YSize.Value==1836);assert(ts.Card2_Crop.Inputs.XOffset.Value<0);assert(ts.Film.Clips[1].Filename:match("film%-overlay.png$"));print("PASS: Lua syntax, links, native controls, 10-frame timing, exact layers, crop/fit, transparent canvas")`
	check := filepath.Join(dir, "check.lua")
	script = strings.ReplaceAll(script, "LayerOrder.Value[", "LayerOrder.Value[1][")
	os.WriteFile(check, []byte(strings.ReplaceAll(script, ";", ";\n")), 0600)
	out, e := exec.Command("luajit", check, file).CombinedOutput()
	if e != nil {
		t.Fatalf("%v\n%s", e, out)
	}
	t.Log(string(out))
}
func TestFilmAspects(t *testing.T) {
	for _, aspect := range []string{"4:3", "16:9", "1:1", "9:16"} {
		c, m := sample()
		c.Aspect = aspect
		s, e := schedule(c, m)
		if e != nil {
			t.Fatal(e)
		}
		dir := t.TempDir()
		if e = film(s, dir); e != nil {
			t.Fatal(e)
		}
		f, e := os.Open(filepath.Join(dir, "film-overlay.png"))
		if e != nil {
			t.Fatal(e)
		}
		im, e := png.Decode(f)
		f.Close()
		if e != nil {
			t.Fatal(e)
		}
		if im.Bounds().Dx() != s.CardWidth || im.Bounds().Dy() != s.CardHeight {
			t.Fatal("dimensions")
		}
		_, _, _, alpha := im.At(s.CardWidth/2, s.CardHeight/2).RGBA()
		if alpha != 0 {
			t.Fatal("center must remain transparent")
		}
	}
}
func testService(t *testing.T) *Service {
	t.Helper()
	dir := t.TempDir()
	return &Service{media: map[string]Media{}, jobs: map[string]*Job{}, packages: map[string]string{}, root: filepath.Join(dir, "exports"), defaultRoot: filepath.Join(dir, "exports"), runtime: dir, uploads: dir, back: "http://127.0.0.1:8787/", ctx: context.Background()}
}
func request(t *testing.T, s *Service, method, path string, body []byte, origin string) *httptest.ResponseRecorder {
	t.Helper()
	r := httptest.NewRequest(method, "http://127.0.0.1:8788"+path, bytes.NewReader(body))
	r.Header.Set("Content-Type", "application/json")
	if origin != "" {
		r.Header.Set("Origin", origin)
	}
	w := httptest.NewRecorder()
	s.handler().ServeHTTP(w, r)
	return w
}
func TestHTTPValidation(t *testing.T) {
	s := testService(t)
	if w := request(t, s, "GET", "/api/health", nil, ""); w.Code != 200 {
		t.Fatal(w.Code)
	}
	if w := request(t, s, "POST", "/api/generate", []byte(`{}`), "http://evil.example"); w.Code != 403 {
		t.Fatal(w.Code)
	}
	if w := request(t, s, "POST", "/api/generate", []byte(`{}`), ""); w.Code != 400 {
		t.Fatal(w.Code)
	}
	if w := request(t, s, "POST", "/api/settings", []byte(`{"path":"relative"}`), ""); w.Code != 400 {
		t.Fatal(w.Code)
	}
	if w := request(t, s, "GET", "/files/unknown/nope", nil, ""); w.Code != 404 {
		t.Fatal(w.Code)
	}
	if w := request(t, s, "POST", "/api/media?name=bad.exe", []byte("not media"), ""); w.Code != 400 {
		t.Fatal(w.Code)
	}
	data, _ := json.Marshal(map[string]any{"path": s.root})
	if w := request(t, s, "POST", "/api/settings", data, ""); w.Code != 200 {
		t.Fatal(w.Body.String())
	}
	if _, e := os.Stat(filepath.Join(s.runtime, "settings.json")); e != nil {
		t.Fatal(e)
	}
	outside := filepath.Join(s.runtime, "private.txt")
	os.WriteFile(outside, []byte("secret"), 0600)
	pkg := filepath.Join(s.root, "test")
	os.MkdirAll(pkg, 0755)
	os.Symlink(outside, filepath.Join(pkg, "escape"))
	s.packages["test"] = pkg
	if w := request(t, s, "GET", "/files/test/escape", nil, ""); w.Code != 403 {
		t.Fatal("symlink escape", w.Code)
	}
}
func TestGenerateMixedMedia(t *testing.T) {
	if testing.Short() {
		t.Skip("FFmpeg integration")
	}
	for _, bin := range []string{"ffmpeg", "ffprobe"} {
		if _, e := exec.LookPath(bin); e != nil {
			t.Skip(bin + " unavailable")
		}
	}
	ctx, cancel := timeoutContext()
	defer cancel()
	dir := t.TempDir()
	video := filepath.Join(dir, "source.mp4")
	if out, e := command(ctx, "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=768x576:rate=30", "-t", "3", "-c:v", "libx264", "-pix_fmt", "yuv420p", video); e != nil {
		t.Fatal(e, string(out))
	}
	photo := filepath.Join(dir, "photo.png")
	im := image.NewNRGBA(image.Rect(0, 0, 320, 500))
	for y := 0; y < 500; y++ {
		for x := 0; x < 320; x++ {
			im.SetNRGBA(x, y, color.NRGBA{230, 160, 40, 255})
		}
	}
	savePNG(photo, im)
	m, e := probe(ctx, video)
	if e != nil {
		t.Fatal(e)
	}
	m.ID = "a"
	m.Name = "A video"
	m.Path = video
	still, e := probe(ctx, photo)
	if e != nil {
		t.Fatal(e)
	}
	still.ID = "b"
	still.Name = "A photo"
	still.Path = photo
	c := Config{Name: "Integration", Aspect: "16:9", FPS: 24, Movement: 10, Items: []Item{{"a", .375, 1, "fill"}, {"b", 0, 1, "fit"}}}
	timeline, e := schedule(c, map[string]Media{"a": m, "b": still})
	if e != nil {
		t.Fatal(e)
	}
	result, e := generate(ctx, timeline, filepath.Join(dir, "output"), "testid", func(string, int) {})
	if e != nil {
		t.Fatal(e)
	}
	root := result["outputDir"].(string)
	file := filepath.Join(root, "media", "item-001.mp4")
	out, e := command(ctx, "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames,width,height,r_frame_rate", "-of", "json", file)
	if e != nil {
		t.Fatal(e)
	}
	var p struct {
		Streams []struct {
			Frames string `json:"nb_read_frames"`
			Width  int    `json:"width"`
			Height int    `json:"height"`
			FPS    string `json:"r_frame_rate"`
		} `json:"streams"`
	}
	json.Unmarshal(out, &p)
	if p.Streams[0].Frames != "24" || p.Streams[0].Width != 768 || p.Streams[0].Height != 576 || p.Streams[0].FPS != "24/1" {
		t.Fatal(string(out))
	}
	z, e := zip.OpenReader(filepath.Join(root, "package.zip"))
	if e != nil {
		t.Fatal(e)
	}
	defer z.Close()
	settings := 0
	for _, entry := range z.File {
		if !strings.HasPrefix(entry.Name, filepath.Base(root)+"/") {
			t.Fatal("wrong ZIP root", entry.Name)
		}
		if strings.HasSuffix(entry.Name, ".setting") {
			settings++
		}
		if strings.HasSuffix(entry.Name, "package.zip") {
			t.Fatal("recursive zip")
		}
	}
	if settings != 1 {
		t.Fatal("setting count", settings)
	}
	raw, _ := os.ReadFile(result["settingPath"].(string))
	if strings.Contains(string(raw), "MediaPool") {
		t.Fatal("project-specific link")
	}
	if !strings.Contains(string(raw), root) {
		t.Fatal("wrong loader paths")
	}
	// Endpoint includes no source audio and the exact selected duration.
	info, e := probe(ctx, file)
	if e != nil || info.Duration != 1 {
		t.Fatal(info, e)
	}
	t.Log("PASS: selected range, preserved resolution, 30→24fps, mixed photo/video, one editable setting, complete ZIP")
}
func TestUploadAndThumbnail(t *testing.T) {
	if testing.Short() {
		t.Skip("FFmpeg integration")
	}
	if _, e := exec.LookPath("ffmpeg"); e != nil {
		t.Skip(e)
	}
	s := testService(t)
	im := image.NewNRGBA(image.Rect(0, 0, 80, 60))
	var b bytes.Buffer
	png.Encode(&b, im)
	w := request(t, s, "POST", "/api/media?name=photo.png", b.Bytes(), "")
	if w.Code != http.StatusCreated {
		t.Fatal(w.Code, w.Body.String())
	}
	var m Media
	json.Unmarshal(w.Body.Bytes(), &m)
	if m.Kind != "photo" || m.Width != 80 {
		t.Fatal(m)
	}
	w = request(t, s, "GET", "/api/media/"+m.ID+"/thumbnail", nil, "")
	if w.Code != 200 {
		t.Fatal(w.Code, w.Body.String())
	}
	decoded, e := png.Decode(bytes.NewReader(w.Body.Bytes()))
	if e != nil || decoded.Bounds().Dx() != 320 {
		t.Fatal("thumbnail", e)
	}
}
func TestLuaEscaping(t *testing.T) {
	s := lua("a\"\\\nب")
	if strings.Contains(s, "\\u") || !strings.Contains(s, "\\010") {
		t.Fatal(s)
	}
}

func TestAlphaAndRotation(t *testing.T) {
	if testing.Short() {
		t.Skip("FFmpeg integration")
	}
	if _, e := exec.LookPath("ffmpeg"); e != nil {
		t.Skip(e)
	}
	ctx, cancel := timeoutContext()
	defer cancel()
	dir := t.TempDir()
	alpha := filepath.Join(dir, "alpha.mov")
	if _, e := command(ctx, "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=red@0.4:size=64x32:rate=24,format=argb", "-t", "1", "-c:v", "qtrle", alpha); e != nil {
		t.Fatal(e)
	}
	a, e := probe(ctx, alpha)
	if e != nil || !a.Alpha {
		t.Fatal("ARGB alpha detection", a, e)
	}
	a.Path = alpha
	dest := filepath.Join(dir, "alpha-cut.mov")
	if e = extract(ctx, Section{Item: Item{Start: .125, Duration: .5}, Media: a, ClipFrames: 12}, 24, dest); e != nil {
		t.Fatal(e)
	}
	out, e := command(ctx, "ffmpeg", "-v", "error", "-i", dest, "-frames:v", "1", "-vf", "alphaextract", "-pix_fmt", "gray", "-f", "rawvideo", "pipe:1")
	if e != nil {
		t.Fatal(e)
	}
	if len(out) != 64*32 || out[0] < 80 || out[0] > 120 {
		t.Fatal("alpha was lost", len(out))
	}
	src := filepath.Join(dir, "landscape.mp4")
	if _, e = command(ctx, "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=64x32:rate=24", "-t", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p", src); e != nil {
		t.Fatal(e)
	}
	rotated := filepath.Join(dir, "rotated.mp4")
	if _, e = command(ctx, "ffmpeg", "-v", "error", "-display_rotation", "90", "-i", src, "-c", "copy", rotated); e != nil {
		t.Fatal(e)
	}
	r, e := probe(ctx, rotated)
	if e != nil || r.Width != 32 || r.Height != 64 {
		t.Fatal("rotation probe", r, e)
	}
	r.Path = rotated
	cut := filepath.Join(dir, "rotation-cut.mp4")
	if e = extract(ctx, Section{Item: Item{Start: .125, Duration: .5}, Media: r, ClipFrames: 12}, 24, cut); e != nil {
		t.Fatal(e)
	}
	r, e = probe(ctx, cut)
	if e != nil || r.Width != 32 || r.Height != 64 {
		t.Fatal("rotation extraction", r, e)
	}
}
