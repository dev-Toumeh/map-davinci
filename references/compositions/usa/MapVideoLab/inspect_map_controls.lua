-- Read-only inspection through individual tools and inputs.
local fus = fusion or fu
if not fus and resolve then fus = resolve:Fusion() end
local current = comp or (fus and fus:GetCurrentComp())
assert(current, "Open the map clip in Fusion first.")
local now = current:GetAttrs().COMPN_CurrentTime or 0
local function describe(value)
    if type(value) == "table" then
        local parts = {}
        for key, item in pairs(value) do
            if type(item) ~= "table" then parts[#parts + 1] = tostring(key) .. "=" .. tostring(item) end
            if #parts >= 8 then break end
        end
        return "{" .. table.concat(parts, ", ") .. "}"
    end
    local text = tostring(value)
    if #text > 180 then text = text:sub(1, 180) .. "..." end
    return text
end
print("=== BEGIN MAP CONTROLS ===")
print("Current frame: " .. now)
for _, name in ipairs({"Transform1", "Background2", "China2", "Text1", "Text3", "Text3_1"}) do
    local tool = current:FindTool(name)
    if tool then
        print("NODE " .. name .. " [" .. tostring(tool:GetAttrs().TOOLS_RegID) .. "]")
        for _, input in pairs(tool:GetInputList() or {}) do
            local attrs = input:GetAttrs()
            local id = attrs.INPS_ID
            local kind = attrs.INPS_DataType
            if id and (kind == "Number" or kind == "Point" or kind == "Text") then
                local ok, value = pcall(function() return tool:GetInput(id, now) end)
                if ok then
                    print("  " .. id .. " = " .. describe(value))
                    local connectedOK, output = pcall(function() return input:GetConnectedOutput() end)
                    if connectedOK and output then
                        local sourceOK, source = pcall(function() return output:GetTool() end)
                        if sourceOK and source then
                            print("    driven by " .. tostring(source:GetAttrs().TOOLS_Name))
                            local keysOK, keys = pcall(function() return source:GetKeyFrames() end)
                            if keysOK and type(keys) == "table" then
                                local times = {}
                                for frame in pairs(keys) do times[#times + 1] = frame end
                                table.sort(times, function(a, b) return tostring(a) < tostring(b) end)
                                print("    keyframes: " .. table.concat(times, ", "))
                            end
                        end
                    end
                end
            end
        end
    else
        print("NODE " .. name .. ": not found")
    end
end
print("=== END MAP CONTROLS ===")
