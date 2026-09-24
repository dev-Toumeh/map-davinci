-- Exports a snapshot of the current composition without changing it.
local fus = fusion or fu
if not fus and resolve then fus = resolve:Fusion() end
local current = comp or (fus and fus:GetCurrentComp())
assert(current, "Open your map clip in the Fusion page first.")
local path = "/Users/naseemtoumeh/MapVideoLab/current_map_snapshot.lua"
local settings = current:CopySettings()
assert(settings, "Could not read the composition settings.")
-- Plain Lua serialization avoids optional Fusion writer helpers.
local active = {}
local function serialize(value, depth)
    local kind = type(value)
    if kind == "string" then return string.format("%q", value) end
    if kind == "number" or kind == "boolean" then return tostring(value) end
    if kind == "nil" then return "nil" end
    if kind ~= "table" then return string.format("%q", "<" .. kind .. ": " .. tostring(value) .. ">") end
    if active[value] then return '"<circular reference>"' end
    active[value] = true
    local indent = string.rep("  ", depth)
    local rows = {"{"}
    for key, item in pairs(value) do
        rows[#rows + 1] = indent .. "  [" .. serialize(key, depth + 1) .. "] = " .. serialize(item, depth + 1) .. ","
    end
    rows[#rows + 1] = indent .. "}"
    active[value] = nil
    return table.concat(rows, "\n")
end
local content = "-- Inspection snapshot; not a native Fusion settings file.\nreturn " .. serialize(settings, 0) .. "\n"
if not io or not io.open then
    print("File access unavailable; printing a focused inspection snapshot.")
    local focused = { CompositionAttributes = current:GetAttrs(), Tools = {} }
    local names = { "Transform1", "Background2", "China2", "Text1", "Text3", "Text3_1" }
    local toolSettings = settings.Tools or settings.tools
    if toolSettings then
        for _, name in ipairs(names) do
            focused.Tools[name] = toolSettings[name]
        end
    else
        print("Settings root keys:")
        for key, value in pairs(settings) do print(tostring(key) .. " : " .. type(value)) end
    end
    print("=== BEGIN MAP SNAPSHOT ===")
    print(serialize(focused, 0))
    print("=== END MAP SNAPSHOT ===")
    print("The open composition was not changed.")
    return
end
local file, err = io.open(path, "w")
assert(file, "Could not create snapshot: " .. tostring(err))
local written, writeErr = file:write(content)
file:close()
assert(written, "Could not write snapshot: " .. tostring(writeErr))
print("Exported composition snapshot to: " .. path)
print("The open composition was not changed.")
