local fu = bmd.scriptapp("Fusion")
if not fu then
    error("Fusion scripting connection is unavailable")
end

local comp = fu:GetCurrentComp()
if not comp then
    error("No active Fusion composition")
end

local attrs = comp:GetAttrs() or {}
print("COMP_NAME=" .. tostring(attrs.COMPS_Name or ""))

local prefixes = { "PAK", "IRN", "AFG", "IND" }
for _, prefix in ipairs(prefixes) do
    local tools = comp:GetToolList(false, prefix .. "_Border_Highlight_Control")
    local found = false
    for _, tool in pairs(tools or {}) do
        found = true
        local toolAttrs = tool:GetAttrs() or {}
        print(prefix .. "_CONTROL=" .. tostring(toolAttrs.TOOLS_Name or "found"))
        print(prefix .. "_ENABLED=" .. tostring(tool:GetInput("Enabled", comp.CurrentTime)))
        print(prefix .. "_POSITION=" .. tostring(tool:GetInput("Start_Position", comp.CurrentTime)))
        print(prefix .. "_LENGTH=" .. tostring(tool:GetInput("Segment_Length", comp.CurrentTime)))
    end
    if not found then
        print(prefix .. "_CONTROL=MISSING")
    end
end
