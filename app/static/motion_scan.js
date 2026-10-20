"use strict";

// This script runs after animation.html and shares its editor state.
(() => {
  const choice = document.getElementById("motionvideochoice");
  const video = document.getElementById("motionreference");
  const compare = document.getElementById("motioncompare");
  const scanButton = document.getElementById("motionscan");
  const applyButton = document.getElementById("motionapply");
  const discardButton = document.getElementById("motiondiscard");
  const review = document.getElementById("motionreview");
  const body = document.getElementById("motionbody");
  const filename = document.getElementById("motionfilename");
  const toggle = document.getElementById("motiontoggle");
  const uploadButton = document.getElementById("motionupload");
  const uploadInput = document.getElementById("motionuploadfile");
  let previous = null;
  let scanning = false;
  let uploading = false;
  let visible = false;
  let videoCount = 0;
  let videoVersion = 0;
  let videoFollowing = false;
  let lastEditorFrame = -1;

  function controls() {
    choice.disabled = scanning || uploading || !videoCount;
    scanButton.disabled = scanning || uploading || !visible || !choice.value || !anim;
    applyButton.disabled = !previous || scanning;
    discardButton.disabled = !previous || scanning;
    toggle.disabled = scanning || uploading || !videoCount;
    toggle.textContent = visible ? "Hide" : "Show";
    uploadButton.disabled = scanning || uploading;
    for (const id of ["save", "fusion", "format", "fps", "duration"]) {
      document.getElementById(id).disabled = !!previous || scanning;
    }
  }

  function chooseVideo() {
    if (previous) discardPreview();
    filename.textContent = choice.value || "No reference video";
    body.classList.toggle("hidden", !visible);
    if (!visible || !choice.value) {
      video.pause();
      compare.classList.add("hidden");
      video.removeAttribute("src");
      video.load();
    } else {
      video.src = `/exports/${encodeURIComponent(pkg)}/videos/${encodeURIComponent(choice.value)}?v=${videoVersion}`;
      compare.classList.remove("hidden");
      video.load();
    }
    lastEditorFrame = -1;
    controls();
    if (anim) render();
  }

  async function loadVideos({preferredName = null, forceVisible = false} = {}) {
    previous = null;
    motionPreviewActive = false;
    scanning = false;
    visible = false;
    videoCount = 0;
    choice.textContent = "";
    controls();
    const packageName = pkg;
    try {
      const response = await fetch(`/api/animation/${encodeURIComponent(packageName)}/reference-videos`);
      const data = await response.json();
      if (!response.ok || data.error) throw Error(data.error || "Could not list videos");
      if (pkg !== packageName) return;
      choice.textContent = "";
      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = "Choose a video";
      choice.append(placeholder);
      for (const item of data.videos) {
        const option = document.createElement("option");
        option.value = item.name;
        option.textContent = item.name;
        choice.append(option);
      }
      videoCount = data.videos.length;
      const hasDefault = data.videos.some(item => item.name === "reference.mp4");
      visible = forceVisible || (hasDefault && localStorage.getItem(`map-video-editor:hide-reference:${pkg}`) !== "1");
      choice.value = preferredName && data.videos.some(item => item.name === preferredName)
        ? preferredName : hasDefault ? "reference.mp4" : "";
      review.textContent = data.videos.length
        ? "Scan a video to preview its pan and zoom as editable camera keyframes."
        : "Upload reference.mp4 to compare and scan its movement.";
      chooseVideo();
    } catch (error) {
      choice.textContent = "";
      videoCount = 0;
      visible = false;
      review.textContent = error.message;
      chooseVideo();
    }
  }

  function toggleVideo() {
    if (scanning || uploading) return;
    if (previous) discardPreview();
    visible = !visible;
    if (visible && !choice.value && videoCount) choice.selectedIndex = 1;
    localStorage.setItem(`map-video-editor:hide-reference:${pkg}`, visible ? "0" : "1");
    chooseVideo();
  }

  async function uploadVideo() {
    const file = uploadInput.files?.[0];
    if (!file) return;
    if (!/\.mp4$/i.test(file.name)) {
      status("Choose an MP4 reference video.", "err");
      uploadInput.value = "";
      return;
    }
    const packageName = pkg;
    uploading = true;
    controls();
    status(`Uploading ${file.name} as reference.mp4…`);
    try {
      const response = await fetch(`/api/animation/${encodeURIComponent(packageName)}/reference-video`, {
        method: "POST", headers: {"Content-Type": "video/mp4"}, body: file,
      });
      const data = await response.json();
      if (!response.ok || data.error) throw Error(data.error || "Reference upload failed");
      if (pkg !== packageName) return;
      if (previous) discardPreview();
      videoVersion = Date.now();
      localStorage.removeItem(`map-video-editor:hide-reference:${pkg}`);
      await loadVideos({preferredName: data.name, forceVisible: true});
      status(`${file.name} uploaded as reference.mp4.`, "ok");
    } catch (error) {
      status("Reference upload failed: " + error.message, "err");
    } finally {
      uploading = false;
      uploadInput.value = "";
      controls();
    }
  }

  function discardPreview() {
    if (!previous) return;
    anim.keyframes = previous.keyframes;
    document.getElementById("duration").value = previous.duration;
    frame = Math.min(previous.frame, total() - 1);
    selected = null;
    previous = null;
    motionPreviewActive = false;
    controls();
    setView(evaluate(frame));
    render();
    review.textContent = "Movement preview discarded. The previous camera keys are restored.";
    status("Movement preview discarded.", "ok");
  }

  async function scanVideo() {
    if (!choice.value || scanning) return;
    if (previous) discardPreview();
    const packageName = pkg;
    const videoName = choice.value;
    scanning = true;
    controls();
    review.textContent = "Matching map landmarks in the reference video…";
    status("Scanning reference movement…", "ok");
    try {
      const response = await fetch(`/api/animation/${encodeURIComponent(packageName)}/scan-motion`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          video: videoName,
          output: {...output(), fps: Number(document.getElementById("fps").value)},
        }),
      });
      const data = await response.json();
      if (!response.ok || data.error) throw Error(data.error || "Movement scan failed");
      if (pkg !== packageName || choice.value !== videoName) return;
      previous = {
        keyframes: anim.keyframes.map(key => ({...key, center: {...key.center}})),
        duration: document.getElementById("duration").value,
        frame,
      };
      motionPreviewActive = true;
      anim.keyframes = data.keyframes;
      document.getElementById("duration").value =
        (data.duration_frames / Number(document.getElementById("fps").value)).toFixed(3);
      frame = 0;
      selected = null;
      video.pause();
      video.currentTime = 0;
      setView(evaluate(0));
      render();
      const gapText = data.gaps.length
        ? ` Review low-confidence sections at ${data.gaps.map(g => `${g.start.toFixed(1)}–${g.end.toFixed(1)}s`).join(", ")}.`
        : " No low-confidence sections found.";
      const changeText = data.rapid_changes?.length
        ? ` Check rapid changes at ${data.rapid_changes.map(g => `${g.start.toFixed(1)}–${g.end.toFixed(1)}s`).join(", ")}.`
        : "";
      review.textContent = `${data.tracked_count}/${data.samples.length} samples tracked; ` +
        `${data.keyframes.length} proposed keys.${gapText}${changeText} Save and Fusion are paused until Apply or Discard.`;
      status("Movement preview ready. Scrub the reference and map, then Apply or Discard.", "ok");
    } catch (error) {
      review.textContent = error.message;
      status("Movement scan failed: " + error.message, "err");
    } finally {
      scanning = false;
      controls();
    }
  }

  function applyPreview() {
    if (!previous) return;
    previous = null;
    motionPreviewActive = false;
    controls();
    review.textContent = "Movement applied to the editable shot. Use Save shot to keep it.";
    status("Movement applied as a draft — Save shot to keep it.", "ok");
  }

  function followReference() {
    if (video.paused || !anim || !choice.value) return;
    videoFollowing = true;
    frame = Math.min(total() - 1, Math.round(video.currentTime * Number(document.getElementById("fps").value)));
    selected = null;
    setView(evaluate(frame));
    render();
    videoFollowing = false;
    requestAnimationFrame(followReference);
  }

  function syncReference() {
    if (anim && choice.value && video.paused && !videoFollowing &&
        frame !== lastEditorFrame && video.readyState >= 1) {
      const time = Math.min(video.duration || Infinity,
                            frame / Number(document.getElementById("fps").value));
      if (Math.abs(video.currentTime - time) > .08) video.currentTime = time;
      lastEditorFrame = frame;
    }
    requestAnimationFrame(syncReference);
  }

  choice.addEventListener("change", chooseVideo);
  toggle.addEventListener("click", toggleVideo);
  uploadButton.addEventListener("click", () => uploadInput.click());
  uploadInput.addEventListener("change", uploadVideo);
  scanButton.addEventListener("click", scanVideo);
  applyButton.addEventListener("click", applyPreview);
  discardButton.addEventListener("click", discardPreview);
  video.addEventListener("play", () => {
    if (playing) document.getElementById("play").click();
    requestAnimationFrame(followReference);
  });
  video.addEventListener("seeked", () => {
    if (video.paused && anim && choice.value) {
      videoFollowing = true;
      frame = Math.min(total() - 1, Math.round(video.currentTime * Number(document.getElementById("fps").value)));
      selected = null;
      setView(evaluate(frame));
      render();
      videoFollowing = false;
      lastEditorFrame = frame;
    }
  });
  window.addEventListener("motion-package-loaded", loadVideos);
  requestAnimationFrame(syncReference);
})();
