"""Estimate a map camera's pan and zoom from a rendered reference video.

The scanner matches satellite features in sampled video frames to the saved
wide map. It deliberately returns a proposal; callers decide whether to use it.
"""
from __future__ import annotations

import math
from pathlib import Path


SAMPLE_SECONDS = 0.5
MAX_REFERENCE_SECONDS = 180
MAP_FEATURES = 3500


def _fit_image(image, cv2, max_width: int):
    height, width = image.shape[:2]
    if width <= max_width:
        return image
    return cv2.resize(image, (max_width, round(height * max_width / width)),
                      interpolation=cv2.INTER_AREA)


def _camera_from_homography(homography, frame_size: tuple[int, int],
                            map_size: tuple[int, int], cv2, np) -> tuple[float, float, float]:
    frame_width, frame_height = frame_size
    points = np.float32([
        [0, frame_height / 2], [frame_width / 2, frame_height / 2],
        [frame_width, frame_height / 2],
    ]).reshape(-1, 1, 2)
    left, center, right = cv2.perspectiveTransform(points, homography).reshape(-1, 2)
    map_width, map_height = map_size
    view_width = float(np.linalg.norm(right - left) / map_width)
    return float(center[0] / map_width), float(center[1] / map_height), view_width


def _inside_map(x: float, y: float, width: float, source_aspect: float,
                output_aspect: float, min_width: float, max_width: float) -> bool:
    height = width * source_aspect / output_aspect
    tolerance = .015
    return (all(math.isfinite(value) for value in (x, y, width)) and
            min_width - tolerance <= width <= max_width + tolerance and
            width / 2 - tolerance <= x <= 1 - width / 2 + tolerance and
            height / 2 - tolerance <= y <= 1 - height / 2 + tolerance)


def _clamp_camera(x: float, y: float, width: float, source_aspect: float,
                  output_aspect: float, min_width: float,
                  max_width: float) -> tuple[float, float, float]:
    width = min(max(width, min_width), max_width)
    height = width * source_aspect / output_aspect
    x = min(max(x, width / 2), 1 - width / 2)
    y = min(max(y, height / 2), 1 - height / 2)
    return x, y, width


def _camera_error(actual: dict, estimated: dict) -> float:
    return max(abs(actual["x"] - estimated["x"]) / .004,
               abs(actual["y"] - estimated["y"]) / .004,
               abs(math.log(actual["width"] / estimated["width"])) / .025)


def _simplify(samples: list[dict]) -> list[dict]:
    """Keep camera direction changes while reducing timeline clutter."""
    if len(samples) <= 2:
        return samples
    selected = {0, len(samples) - 1}
    pending = [(0, len(samples) - 1)]
    while pending:
        start, end = pending.pop()
        a, b = samples[start], samples[end]
        greatest, split = 0.0, None
        for index in range(start + 1, end):
            item = samples[index]
            fraction = (item["frame"] - a["frame"]) / (b["frame"] - a["frame"])
            estimated = {
                "x": a["x"] + (b["x"] - a["x"]) * fraction,
                "y": a["y"] + (b["y"] - a["y"]) * fraction,
                "width": a["width"] + (b["width"] - a["width"]) * fraction,
            }
            error = _camera_error(item, estimated)
            if error > greatest:
                greatest, split = error, index
        if greatest > 1 and split is not None:
            selected.add(split)
            pending.extend(((start, split), (split, end)))
    return [samples[index] for index in sorted(selected)]


def _gaps(samples: list[dict], interval: float) -> list[dict]:
    gaps = []
    start = None
    for sample in samples:
        if not sample["tracked"] and start is None:
            start = sample["time"]
        if sample["tracked"] and start is not None:
            gaps.append({"start": start, "end": sample["time"]})
            start = None
    if start is not None:
        gaps.append({"start": start, "end": samples[-1]["time"] + interval})
    return gaps


def _rapid_changes(samples: list[dict], interval: float) -> list[dict]:
    """Flag possible cuts without claiming every fast camera move is a cut."""
    changes = []
    previous = None
    for item in samples:
        if not item["tracked"]:
            previous = None
            continue
        if previous and item["time"] - previous["time"] <= interval * 1.5:
            dx = abs(item["center"]["x"] - previous["center"]["x"])
            dy = abs(item["center"]["y"] - previous["center"]["y"])
            ratio = item["view_width"] / previous["view_width"]
            if dx > .05 or dy > .05 or ratio > 1.5 or ratio < 1 / 1.5:
                changes.append({"start": previous["time"], "end": item["time"]})
        previous = item
    return changes


def scan(video_path: Path, map_path: Path, native: dict, output: dict,
         sample_seconds: float = SAMPLE_SECONDS) -> dict:
    """Return editable camera keys and tracking diagnostics without saving."""
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Motion scanning needs OpenCV and NumPy in the app environment") from exc

    map_image = cv2.imread(str(map_path), cv2.IMREAD_COLOR)
    if map_image is None:
        raise ValueError("could not read the package's wide satellite image")
    map_image = _fit_image(map_image, cv2, 1920)
    map_height, map_width = map_image.shape[:2]
    detector = cv2.SIFT_create(nfeatures=MAP_FEATURES)
    map_keys, map_descriptors = detector.detectAndCompute(
        cv2.cvtColor(map_image, cv2.COLOR_BGR2GRAY), None)
    if map_descriptors is None or len(map_keys) < 20:
        raise ValueError("wide satellite image has too few trackable landmarks")

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError("could not open the reference video")
    try:
        video_fps = capture.get(cv2.CAP_PROP_FPS)
        video_frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        if not video_fps or not math.isfinite(video_fps) or video_frames < 2:
            raise ValueError("reference video has no usable frame rate or duration")
        duration = video_frames / video_fps
        if duration > MAX_REFERENCE_SECONDS:
            raise ValueError(f"reference video exceeds the {MAX_REFERENCE_SECONDS}s scan limit")
        target_fps = int(output["fps"])
        if not 1 <= target_fps <= 120:
            raise ValueError("shot FPS must be between 1 and 120")
        output_width, output_height = int(output["width"]), int(output["height"])
        if output_width <= 0 or output_height <= 0:
            raise ValueError("shot dimensions must be positive")
        source_aspect = int(native["width"]) / int(native["height"])
        output_aspect = output_width / output_height
        max_width = min(1.0, output_aspect / source_aspect)
        min_width = max_width / (float(native.get("wide_factor", 2)) * 16)
        duration_frames = max(2, math.ceil(duration * target_fps))
        if duration_frames > 36_000:
            raise ValueError("reference video exceeds the shot frame limit")
        timestamps = [index * sample_seconds for index in range(math.ceil(duration / sample_seconds))]
        last_time = max(0.0, (video_frames - 1) / video_fps)
        if not timestamps or last_time - timestamps[-1] > sample_seconds / 4:
            timestamps.append(last_time)
        matcher = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=80))
        samples = []
        accepted = []
        for timestamp in timestamps:
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ok, frame = capture.read()
            item = {"time": round(timestamp, 3), "tracked": False,
                    "inliers": 0, "confidence": 0.0}
            if not ok:
                samples.append(item)
                continue
            frame = _fit_image(frame, cv2, 540)
            frame_height, frame_width = frame.shape[:2]
            frame_keys, frame_descriptors = detector.detectAndCompute(
                cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), None)
            if frame_descriptors is None or len(frame_keys) < 12:
                samples.append(item)
                continue
            pairs = matcher.knnMatch(frame_descriptors, map_descriptors, k=2)
            good = [pair[0] for pair in pairs if len(pair) == 2 and
                    pair[0].distance < .7 * pair[1].distance]
            if len(good) < 12:
                samples.append(item)
                continue
            source = np.float32([frame_keys[match.queryIdx].pt for match in good])
            target = np.float32([map_keys[match.trainIdx].pt for match in good])
            homography, mask = cv2.findHomography(source, target, cv2.RANSAC, 5)
            if homography is None or mask is None:
                samples.append(item)
                continue
            inliers = int(mask.sum())
            item["inliers"] = inliers
            item["confidence"] = round(inliers / len(good), 3)
            if inliers < 10 or inliers / len(good) < .55:
                samples.append(item)
                continue
            x, y, width = _camera_from_homography(
                homography, (frame_width, frame_height), (map_width, map_height), cv2, np)
            if not _inside_map(x, y, width, source_aspect, output_aspect,
                               min_width, max_width):
                samples.append(item)
                continue
            x, y, width = _clamp_camera(x, y, width, source_aspect, output_aspect,
                                        min_width, max_width)
            frame_number = min(duration_frames - 1, round(timestamp * target_fps))
            item.update(tracked=True, center={"x": round(x, 6), "y": round(y, 6)},
                        view_width=round(width, 6), frame=frame_number)
            samples.append(item)
            accepted.append({"frame": frame_number, "x": x, "y": y, "width": width})
    finally:
        capture.release()

    if len(accepted) < 2 or len(accepted) / len(samples) < .35:
        raise ValueError("too little of the reference matches this package's satellite map")
    # Frame rounding can merge samples at low target FPS.
    unique = {item["frame"]: item for item in accepted}
    ordered = [unique[frame] for frame in sorted(unique)]
    first = ordered[0]
    if first["frame"] > 0:
        ordered.insert(0, {**first, "frame": 0})
    last = ordered[-1]
    if last["frame"] < duration_frames - 1:
        ordered.append({**last, "frame": duration_frames - 1})
    simplified = _simplify(ordered)
    keys = [{"frame": item["frame"],
             "center": {"x": round(item["x"], 6), "y": round(item["y"], 6)},
             "view_width": round(item["width"], 6), "easing": "linear"}
            for item in simplified]
    return {"duration_seconds": round(duration, 3), "duration_frames": duration_frames,
            "video_fps": round(video_fps, 3), "sample_seconds": sample_seconds,
            "samples": samples, "gaps": _gaps(samples, sample_seconds),
            "rapid_changes": _rapid_changes(samples, sample_seconds),
            "keyframes": keys, "tracked_count": len(accepted)}
