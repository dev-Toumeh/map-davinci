-- Read-only connection and image diagnostic.
local fus = fusion or fu
if not fus and resolve then fus = resolve:Fusion() end
local current = comp or (fus and fus:GetCurrentComp())
assert(current, "Open the map clip in Fusion first.")
local now = current:GetAttrs().COMPN_CurrentTime or 0
print("=== ZOOM PREVIEW CHECK (frame " .. now .. ") ===")
for _, name in ipairs({"MapVideoLab_ZoomPreview", "Transform1", "MediaOut1"}) do
    local tool = current:FindTool(name)
    if not tool then
        print(name .. ": NOT FOUND")
    else
        print(name .. ": " .. tostring(tool:GetAttrs().TOOLS_RegID))
        for _, input in pairs(tool:GetInputList() or {}) do
            local attrs = input:GetAttrs()
            if attrs.INPS_DataType == "Image" then
                local output = input:GetConnectedOutput()
                local source = output and output:GetTool()
                print("  " .. tostring(attrs.INPS_ID) .. " <- " .. (source and tostring(source:GetAttrs().TOOLS_Name) or "DISCONNECTED"))
            end
        end
        if name == "MapVideoLab_ZoomPreview" then
            print("  Size: " .. tostring(tool:GetInput("Size", now)))
            print("  Blend: " .. tostring(tool:GetInput("Blend", now)))
        end
        local output = tool:FindMainOutput(1)
        if output then
            local ok, image = pcall(function() return output:GetValue(now) end)
            print("  Image at current frame: " .. (ok and tostring(image) or "could not query: " .. tostring(image)))
        end
    end
end
print("=== END CHECK ===")
