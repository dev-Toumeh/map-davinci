-- Adds a separate preview branch. Does not intentionally alter MediaOut.
local fus = fusion or fu
if not fus and resolve then fus = resolve:Fusion() end
local current = comp or (fus and fus:GetCurrentComp())
assert(current, "Open your map composition in Fusion first.")
local source = current:FindTool("Transform1")
assert(source, "Transform1 was not found in this composition.")
-- Capture output wiring in case AddTool performs automatic connection.
local outputs = {}
for _, tool in pairs(current:GetToolList(false) or {}) do
    if tool:GetAttrs().TOOLS_RegID == "MediaOut" then
        local input = tool:FindMainInput(1)
        if input then outputs[#outputs + 1] = {input = input, output = input:GetConnectedOutput()} end
    end
end
current:StartUndo("MapVideoLab: separate zoom preview")
local preview = current:FindTool("MapVideoLab_ZoomPreview")
local ok, err = pcall(function()
    preview = preview or current:AddTool("Transform", -4, -4)
    assert(preview, "Could not create a native Fusion Transform.")
    preview:SetAttrs({TOOLS_Name = "MapVideoLab_ZoomPreview"})
    local spline = current:BezierSpline()
    assert(spline, "Could not create zoom animation spline.")
    spline:SetKeyFrames({
        [0] = {1, Flags = {Linear = true}},
        [60] = {1.35, Flags = {Linear = true}}
    })
    preview.Size = spline
end)
for _, saved in ipairs(outputs) do
    saved.input:ConnectTo(saved.output)
end
current:EndUndo(true)
assert(ok, "Zoom setup failed: " .. tostring(err) .. ". Undo once to revert this attempt.")
print("Created MapVideoLab_ZoomPreview: scale 1.00 to 1.35 over frames 0-60.")
for _, frame in ipairs({0, 30, 60}) do
    print("  Scale at frame " .. frame .. ": " .. tostring(preview:GetInput("Size", frame)))
end
print("Connect Transform1's output square to this node's yellow image input manually.")
print("Then select MapVideoLab_ZoomPreview and press 1 or 2; scrub frames 0-60.")
print("Original camera animation was not edited.")
print("Undo once to remove this preview branch.")
