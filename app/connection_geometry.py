"""Font-independent connection geometry in output pixels, then source coordinates."""
import math


def path_at(connection, t):
    a, b = connection['start'], connection['end']
    if connection['path_type'] != 'curved' or not connection.get('bend'):
        return (a['x'] + (b['x']-a['x'])*t, a['y'] + (b['y']-a['y'])*t)
    q, u = connection['bend'], 1-t
    return tuple(u*u*a[k]+2*u*t*q[k]+t*t*b[k] for k in ('x', 'y'))


def dash_segments(points, dash, gap):
    """Split a pixel-space polyline at exact dash/gap distances."""
    result, current, remaining, drawing = [], [points[0]], dash, True
    for a, b in zip(points, points[1:]):
        length = math.dist(a, b)
        if length < 1e-12:
            continue
        used = 0.0
        while used < length - 1e-10:
            step = min(remaining, length-used)
            used += step
            p = tuple(a[i]+(b[i]-a[i])*used/length for i in (0, 1))
            if drawing:
                current.append(p)
            remaining -= step
            if remaining < 1e-10:
                if drawing and len(current) > 1:
                    result.append(current)
                drawing = not drawing
                remaining = dash if drawing else gap
                current = [p] if drawing else []
    if drawing and len(current) > 1:
        result.append(current)
    return result


def ribbon(points, thickness):
    """A filled stroke with butt caps and bounded miter joins."""
    clean = [points[0]]
    for p in points[1:]:
        if math.dist(p, clean[-1]) > 1e-10:
            clean.append(p)
    if len(clean) < 2:
        return [points[0]] * 4
    normals = []
    for a, b in zip(clean, clean[1:]):
        length = math.dist(a, b)
        normals.append((-(b[1]-a[1])/length, (b[0]-a[0])/length))
    left, right = [], []
    for i, p in enumerate(clean):
        a, b = normals[max(0, i-1)], normals[min(i, len(normals)-1)]
        nx, ny = a[0]+b[0], a[1]+b[1]
        norm = math.hypot(nx, ny)
        nx, ny = (nx/norm, ny/norm) if norm > 1e-10 else b
        distance = min(thickness*5, thickness/2/max(.1, nx*b[0]+ny*b[1]))
        left.append((p[0]+nx*distance, p[1]+ny*distance))
        right.append((p[0]-nx*distance, p[1]-ny*distance))
    return left + list(reversed(right))


def connection_shapes(connection, frame, scale, width, height, output):
    """Return filled source-space polygons, including the traveling arrow.

    Style units refer to a 1080-pixel output short edge, shared with the UI.
    Geometry is built in pixel space to avoid aspect-ratio distortion.
    """
    t = max(0.0, min(1.0, (frame-connection['start_frame']) /
                         (connection['arrival_frame']-connection['start_frame'])))
    if connection['easing'] == 'smooth':
        t = t*t*(3-2*t)
    unit = min(output['width'], output['height'])/1080
    def pixel(p):
        return (p[0]*width*scale, p[1]*height*scale)
    steps = max(2, math.ceil(60*t))
    points = [pixel(path_at(connection, i/steps*t)) for i in range(steps+1)]
    paths = (dash_segments(points, connection['thickness']*5*unit,
                           connection['thickness']*4*unit)
             if connection['line_style'] == 'dashed' else [points])
    shapes = [ribbon(p, max(1, connection['thickness']*1.5)*unit) for p in paths]
    if connection['arrowhead']:
        tip = points[-1]
        previous = pixel(path_at(connection, max(0, t-.015)))
        angle = math.atan2(tip[1]-previous[1], tip[0]-previous[0])
        radius = connection['arrow_size']*.65*unit
        shapes.append([(tip[0]+math.cos(angle+a)*radius, tip[1]+math.sin(angle+a)*radius)
                       for a in (0, 2.5, -2.5)])
    return [[(x/(width*scale)-.5, .5-y/(height*scale)) for x, y in shape] for shape in shapes]


def connection_tools(connection, width, height, duration, pos_y, layer_number, camera, output):
    """Native animated MultiPoly masks, with no font or text-layout dependency."""
    import re
    base = 'Link_' + re.sub(r'[^A-Za-z0-9_]', '_', connection['id'])
    start = connection['start_frame']
    stop = connection['disappearance_frame']
    stop = duration+1 if stop is None else stop
    samples, index = [], 0
    for frame in range(start, stop):
        while index < len(camera)-1 and camera[index+1]['frame'] <= frame:
            index += 1
        shapes = connection_shapes(connection, frame, camera[index]['zoom'], width, height, output)
        samples.append((frame, shapes))
    slots = max((len(shapes) for _, shapes in samples), default=0)
    inputs, definitions, splines = [], [], []
    for slot in range(slots):
        name = f'{base}_Shape{slot+1}'
        entries, previous = [], None
        for frame, shapes in samples:
            shape = shapes[slot] if slot < len(shapes) else [(0.0, 0.0)]*3
            # Per-frame shape keys allow dashes to appear/disappear as zoom changes.
            points = ', '.join('{ Linear = true, X = %.12g, Y = %.12g, LX = 0, LY = 0, RX = 0, RY = 0 }' % p for p in shape)
            value = f'Polyline {{ Closed = true, Points = {{ {points} }} }}'
            if value != previous:
                # Keep the end of a hold before a change to avoid interpolating across it.
                if previous is not None and frame > last_frame+1:
                    entries.append(f'[{frame-1}] = {{ 0, Flags = {{ Linear = true, LockedY = true }}, Value = {previous} }}')
                entries.append(f'[{frame}] = {{ 0, Flags = {{ Linear = true, LockedY = true }}, Value = {value} }}')
                previous, last_frame = value, frame
        splines.append(f'{name} = BezierSpline {{ KeyFrames = {{ {", ".join(entries)} }} }},')
        inputs.append(f'["PolyMask{slot+1}.Level"] = Input {{ Value = 1 }}, '
                      f'["PolyMask{slot+1}.Polyline"] = Input {{ SourceOp = "{name}", Source = "Value" }},')
        definitions.append(f'PolyMask{slot+1} = PolyMaskInputs {{ DrawMode = "InsertAndModify" }},')
    color = connection['color'].lstrip('#')
    r, g, b = [int(color[i:i+2], 16)/255 for i in (0, 2, 4)]
    order = ', '.join(str(i+1) for i in range(slots))
    tools = f'''
        {base}_Mask = MultiPoly {{ Inputs = {{
            MaskWidth = Input {{ Value = {width} }}, MaskHeight = Input {{ Value = {height} }},
            PixelAspect = Input {{ Value = {{ 1, 1 }} }}, UseFrameFormatSettings = Input {{ Value = 0 }},
            ClippingMode = Input {{ Value = FuID {{ "None" }} }},
            PolyOrder = Input {{ Value = ScriptVal {{ {{ [0] = {order} }} }} }},
            {''.join(inputs)}
        }}, {''.join(definitions)} ViewInfo = OperatorInfo {{ Pos = {{ -400, {pos_y} }} }} }},
        {base}_Line = Background {{ NameSet = true, Inputs = {{
            EffectMask = Input {{ SourceOp = "{base}_Mask", Source = "Mask" }},
            GlobalOut = Input {{ Value = {duration} }}, Width = Input {{ Value = {width} }}, Height = Input {{ Value = {height} }},
            UseFrameFormatSettings = Input {{ Value = 0 }},
            TopLeftRed = Input {{ Value = {r} }}, TopLeftGreen = Input {{ Value = {g} }}, TopLeftBlue = Input {{ Value = {b} }},
            TopLeftAlpha = Input {{ Expression = "iif(time >= {start} and time < {stop}, 1, 0)" }}
        }}, ViewInfo = OperatorInfo {{ Pos = {{ -180, {pos_y} }} }} }},
        {''.join(splines)}
'''
    layer = f'["Layer{layer_number}.Foreground"] = Input {{ SourceOp = "{base}_Line", Source = "Output" }},'
    return tools, layer
