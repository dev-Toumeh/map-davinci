package main

import (
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
)

// Fusion strings use Lua decimal escapes, not JSON's \u escapes.
func lua(s string) string {
	var b strings.Builder
	b.WriteByte('"')
	for _, r := range s {
		switch {
		case r == '"' || r == '\\':
			b.WriteByte('\\')
			b.WriteRune(r)
		case r < 32:
			fmt.Fprintf(&b, "\\%03d", r)
		default:
			b.WriteRune(r)
		}
	}
	b.WriteByte('"')
	return b.String()
}
func val(v any) string { return fmt.Sprintf("Input { Value = %v, },", v) }
func link(tool, output string) string {
	return fmt.Sprintf("Input { SourceOp = %s, Source = %s, },", lua(tool), lua(output))
}
func view(name string) string {
	row := 0
	_, _ = fmt.Sscanf(name, "Card%d_", &row)
	x := 0
	parts := strings.Split(name, "_")
	kind := parts[len(parts)-1]
	for k, v := range map[string]int{"Time": 180, "Resize": 360, "Crop": 540, "Base": 540, "Fit": 720, "Frame": 900} {
		if kind == k {
			x = v
		}
	}
	y := row * 180
	if kind == "Base" {
		y += 80
	}
	if name == "Film" {
		x = 900
		y = 0
	}
	return fmt.Sprintf("OperatorInfo { Pos = { %d, %d } },", x, y)
}
func loader(name, file string, frames int, photo bool) string {
	loop := 0
	if photo {
		loop = 1
		frames = 1
	}
	return fmt.Sprintf(`%s = Loader { NameSet = true, Clips = { Clip { ID = "Clip1", Filename = %s, StartFrame = 0, Length = %d, LengthSetManually = true, TrimIn = 0, TrimOut = %d, GlobalStart = 0, GlobalEnd = 10000000, ExtendFirst = 0, ExtendLast = 0, Loop = %d, }}, ViewInfo = %s },`, name, lua(file), frames, frames-1, loop, view(name))
}
func spline(name string, keys [][2]float64) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s = BezierSpline { NameSet = true, KeyFrames = {", name)
	for i, k := range keys {
		fmt.Fprintf(&b, "[%g] = { %g,", k[0], k[1])
		if i > 0 {
			fmt.Fprintf(&b, " LH = { %.9g, %g },", k[0]-(k[0]-keys[i-1][0])/3, k[1])
		}
		if i+1 < len(keys) {
			fmt.Fprintf(&b, " RH = { %.9g, %g },", k[0]+(keys[i+1][0]-k[0])/3, k[1])
		}
		b.WriteString(" },")
	}
	b.WriteString(" } },")
	return b.String()
}
func buildSetting(t Timeline, root string) string {
	var nodes, inputs, layers, order strings.Builder
	name := "Archive_" + safeName.ReplaceAllString(t.Name, "_")
	if len(name) > 64 {
		name = name[:64]
	}
	nodes.WriteString(fmt.Sprintf(`Canvas = Background { Inputs = { Width = %s Height = %s UseFrameFormatSettings = %s TopLeftAlpha = %s }, },`, val(3840), val(2160), val(0), val(0)))
	// The source's published closed curve: same points, with its hold point recentered.
	// Scale follows the reference so both travel endpoints stay beyond the UHD frame.
	nodes.WriteString(`Route = PublishPolyLine { Inputs = { Value = Input { Value = Polyline { Closed = true, Points = {
 { X = 0.100935828877005, Y = -0.267220902612827, LX = 0, LY = 0.122729944406843, RX = 0, RY = -0.122729944406843 },
 { X = 0.225935828877005, Y = -0.489443124835049, LX = -0.0690355937288492, LY = 0, RX = 0.0690355937288492, RY = 0 },
 { X = 0.350935828877005, Y = -0.267220902612827, LX = 0, LY = -0.122729944406843, RX = 0, RY = 0.122729944406843 },
 { X = 0.225935828877005, Y = -0.0449986803906044, LX = 0.0690355937288492, LY = 0, RX = -0.0690355937288492, RY = 0 }
 } }, }, }, },`)
	nodes.WriteString(loader("Film", filepath.Join(root, "assets", "film-overlay.png"), 1, true))
	for i, s := range t.Sections {
		p := fmt.Sprintf("Card%d", i+1)
		n := i + 1
		fmt.Fprintf(&order, "%d,", n)
		nodes.WriteString(loader(p+"_Media", filepath.Join(root, s.File), s.ClipFrames, s.Media.Kind == "photo"))
		expr := fmt.Sprintf("min(%d,max(0,time-%d))", s.ClipFrames-1, s.StartFrame)
		if s.Media.Kind == "photo" {
			expr = "0"
		}
		fmt.Fprintf(&nodes, `%s_Time = TimeStretcher { Inputs = { Input = %s SourceTime = Input { Expression = %s, }, }, ViewInfo = %s },`, p, link(p+"_Media", "Output"), lua(expr), view(p+"_Time"))
		scale := float64(t.CardWidth) / float64(s.Media.Width)
		other := float64(t.CardHeight) / float64(s.Media.Height)
		if s.Fit == "fill" && other > scale || s.Fit == "fit" && other < scale {
			scale = other
		}
		// Resize first, then crop/pad to exact card dimensions. Native inputs remain editable.
		rw := int(float64(s.Media.Width)*scale + .5)
		rh := int(float64(s.Media.Height)*scale + .5)
		fmt.Fprintf(&nodes, `%s_Resize = Resize { Inputs = { Input = %s XSize = %s YSize = %s KeepAspect = %s }, ViewInfo = %s },`, p, link(p+"_Time", "Output"), val(rw), val(rh), val(0), view(p+"_Resize"))
		fmt.Fprintf(&nodes, `%s_Crop = Crop { Inputs = { Input = %s XSize = %s YSize = %s XOffset = %s YOffset = %s }, ViewInfo = %s },`, p, link(p+"_Resize", "Output"), val(t.CardWidth), val(t.CardHeight), val((rw-t.CardWidth)/2), val((rh-t.CardHeight)/2), view(p+"_Crop"))
		fmt.Fprintf(&nodes, `%s_Base = Background { Inputs = { Width = %s Height = %s UseFrameFormatSettings = %s TopLeftAlpha = %s }, ViewInfo = %s },`, p, val(t.CardWidth), val(t.CardHeight), val(0), val(1), view(p+"_Base"))
		fmt.Fprintf(&nodes, `%s_Fit = Merge { Inputs = { Background = %s Foreground = %s }, ViewInfo = %s },`, p, link(p+"_Base", "Output"), link(p+"_Crop", "Output"), view(p+"_Fit"))
		fmt.Fprintf(&nodes, `%s_Frame = Merge { Inputs = { Background = %s Foreground = %s Blend = %s }, ViewInfo = %s },`, p, link(p+"_Fit", "Output"), link("Film", "Output"), val(.37), view(p+"_Frame"))
		keys := [][2]float64{{float64(s.EnterStart), .75}, {float64(s.EnterEnd), .5}}
		if i < len(t.Sections)-1 {
			keys = append(keys, [2]float64{float64(s.ExitStart), .5}, [2]float64{float64(s.ExitEnd), .25})
		}
		nodes.WriteString(spline(p+"_Travel", keys))
		fmt.Fprintf(&nodes, `%s_Path = PolyPath { Inputs = { Center = %s Size = %s Displacement = %s PolyLine = %s }, },`, p, val("{ -0.993232617767656, 1.63702570495558 }"), val(4.255), link(p+"_Travel", "Value"), link("Route", "Value"))
		end := s.ExitEnd
		if i == len(t.Sections)-1 {
			end = t.Frames
		}
		visible := fmt.Sprintf("iif(time>=%d and time<%d,1,0)", s.EnterStart, end)
		// Animate centers on UHD canvas, not on the small card's pixel domain.
		// MultiMerge interprets each layer's Center in canvas coordinates.
		fmt.Fprintf(&layers, `["Layer%d.Foreground"] = %s ["Layer%d.Center"] = %s ["Layer%d.Size"] = Input { Value = 1, }, ["Layer%d.Blend"] = Input { Expression = %s, }, LayerEnabled%d = Input { Value = 1, }, LayerName%d = Input { Value = %s, },`, n, link(p+"_Frame", "Output"), n, link(p+"_Path", "Position"), n, n, lua(visible), n, n, lua(s.Media.Name))
		fmt.Fprintf(&inputs, `%sSize = InstanceInput { SourceOp = "Output", Source = "Layer%d.Size", Name = %s, },`, p, n, lua(fmt.Sprintf("Card %d size", n)))
	}
	// Exported keys use a frame-zero timeline; usage instructions require placing it at comp start 0.
	fmt.Fprintf(&nodes, `Output = MultiMerge { Inputs = { Background = %s LayerOrder = Input { Value = ScriptVal { { [0] = %s } }, }, %s }, ViewInfo = OperatorInfo { Pos = { 900, 200 } }, },`, link("Canvas", "Output"), strings.TrimSuffix(order.String(), ","), layers.String())
	return fmt.Sprintf(`{ Tools = ordered() { %s = GroupOperator { NameSet = true, Inputs = ordered() { %s }, Outputs = { MainOutput1 = InstanceOutput { SourceOp = "Output", Source = "Output", }, }, ViewInfo = GroupInfo { Pos = { 0, 0 } }, Tools = ordered() { %s }, }, }, ActiveTool = %s, }`, name, inputs.String(), nodes.String(), strconv.Quote(name))
}
