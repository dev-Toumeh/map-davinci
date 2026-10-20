"use strict";
const element = id => document.getElementById(id);
let previewURL = null;
let settingPath = "";
let busy = false;
let savedFolder = "";
const busyControls = ["giffile", "groupname", "fps", "generate", "exportpath", "choosefolder", "savefolder", "defaultfolder"];

function setBusy(value) {
  busy = value;
  for (const id of busyControls) element(id).disabled = value;
}

function showFolder(data) {
  savedFolder = data.path;
  element("exportpath").value = data.path;
  element("destination").textContent = "Default: " + data.default_path + ". This affects future GIF exports only; existing packages stay in place.";
}

async function saveFolder(useDefault = false) {
  const response = await fetch("/api/gif/settings", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({path: element("exportpath").value, use_default: useDefault}),
  });
  const data = await response.json();
  if (!response.ok || data.error) throw new Error(data.error || "Could not save folder");
  showFolder(data);
  element("result").hidden = true;
}

function status(message, type = "") {
  element("status").textContent = message;
  element("status").className = type;
}

element("giffile").addEventListener("change", () => {
  if (previewURL) URL.revokeObjectURL(previewURL);
  element("previewwrap").hidden = true;
  element("result").hidden = true;
  status("");
  const file = element("giffile").files[0];
  if (!file) return;
  if (!/\.gif$/i.test(file.name) || file.size > 25 * 1024 * 1024) {
    status("Choose a GIF file up to 25 MB.", "error");
    element("giffile").value = "";
    return;
  }
  previewURL = URL.createObjectURL(file);
  element("preview").src = previewURL;
  element("previewwrap").hidden = false;
  element("groupname").value = file.name.replace(/\.gif$/i, "").slice(0, 64) || "GIFLoop";
});

element("gifform").addEventListener("submit", async event => {
  event.preventDefault();
  if (busy || !element("gifform").reportValidity()) return;
  const file = element("giffile").files[0];
  if (!file) return;
  const query = new URLSearchParams({name: element("groupname").value, fps: element("fps").value});
  setBusy(true);
  element("result").hidden = true;
  status("Uploading GIF and generating frames…");
  try {
    if (element("exportpath").value.trim() !== savedFolder) await saveFolder();
    const response = await fetch("/api/gif?" + query, {
      method: "POST", headers: {"Content-Type": "image/gif"}, body: file,
    });
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || "Conversion failed");
    settingPath = data.setting_path;
    element("settingdownload").href = data.setting_url;
    element("zipdownload").href = data.zip_url;
    element("settingpath").textContent = settingPath;
    element("details").textContent = `${data.frame_count} frames · ${data.width} × ${data.height} · ${(data.loop_ms / 1000).toFixed(3)} seconds per loop`;
    element("result").hidden = false;
    status("Saved to " + data.output_dir, "success");
  } catch (error) {
    status(error.message, "error");
  } finally {
    setBusy(false);
  }
});

element("copypath").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(settingPath);
    status("Setting path copied.", "success");
  } catch (_) {
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(element("settingpath"));
    selection.removeAllRanges();
    selection.addRange(range);
    status("Path selected. Press Command+C or Ctrl+C to copy it.");
  }
});

for (const [id, useDefault] of [["savefolder", false], ["defaultfolder", true]]) {
  element(id).addEventListener("click", async () => {
    if (busy) return;
    setBusy(true);
    try { await saveFolder(useDefault); status("GIF export folder saved.", "success"); }
    catch (error) { status(error.message, "error"); }
    finally { setBusy(false); }
  });
}

element("choosefolder").addEventListener("click", async () => {
  if (busy) return;
  setBusy(true);
  try {
    const response = await fetch("/api/settings/select-folder", {method: "POST", headers: {"Content-Type": "application/json"}, body: "{}"});
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || "Could not choose folder");
    if (!data.cancelled) {
      element("exportpath").value = data.path;
      await saveFolder();
      status("GIF export folder saved.", "success");
    }
  } catch (error) { status(error.message, "error"); }
  finally { setBusy(false); }
});

setBusy(true);
fetch("/api/gif/settings").then(async response => {
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Could not load settings");
  showFolder(data);
}).catch(error => {
  status(error.message, "error");
}).finally(() => setBusy(false));
