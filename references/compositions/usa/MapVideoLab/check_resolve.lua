-- Read-only diagnostic: run from Resolve's Console with Lua selected.
print("=== MapVideoLab: scripting check ===")
local app = resolve
if not app and bmd then app = bmd.scriptapp("Resolve") end
if app then
    print("Resolve: " .. tostring(app:GetVersionString()))
    local manager = app:GetProjectManager()
    local project = manager and manager:GetCurrentProject()
    print("Project: " .. (project and project:GetName() or "none open"))
else
    print("Resolve API unavailable in this console.")
end
local fus = fusion or fu
if not fus and app then fus = app:Fusion() end
local current = comp or (fus and fus:GetCurrentComp())
if current then
    print("Fusion composition accessible.")
    local count = 0
    for _, tool in pairs(current:GetToolList(false) or {}) do
        count = count + 1
        local attrs = tool:GetAttrs()
        print("  " .. tostring(attrs.TOOLS_Name) .. " [" .. tostring(attrs.TOOLS_RegID) .. "]")
    end
    print("Node count: " .. count)
else
    print("No Fusion composition open. Open a clip in the Fusion page and run again.")
end
print("Check complete. No project changes made.")
