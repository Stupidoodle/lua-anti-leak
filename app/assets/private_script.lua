local gui_reference = gui.Reference("Visuals", "Other", "Extra")
local gui_rainbow_enable = gui.Checkbox(gui_reference, "rainbow_trail_enable", "Rainbow Trail", false)
gui_rainbow_enable:SetDescription("Draws a rainbow trail between the backtrack positions.")
local gui_static_color = gui.ColorPicker(gui_rainbow_enable, "static_color", "", 255, 255, 255, 255)
local gui_dot_size = gui.Slider(gui_reference, "dot_size", "Dot Size", 0, 0, 10)
gui_dot_size:SetDescription("Size of the dots.")

local backtrack = false
local legitbot = false
local visibility_check = false

local local_player = nil
local player_positions = {}

local function drawing_hue(real_time)
    local r = math.floor(math.sin(real_time * 3) * 127 + 128);
    local g = math.floor(math.sin(real_time * 3 + 2) * 127 + 128);
    local b = math.floor(math.sin(real_time * 3 + 4) * 127 + 128);
    return r, g, b;
end

local function on_draw()
    legitbot = gui.GetValue("lbot.master")
    backtrack = legitbot and gui.GetValue("lbot.extra.backtrack") or gui.GetValue("rbot.aim.posadj.backtrack") and 200 or 0
    local_player = entities.GetLocalPlayer()  -- NOTE: We dont need to get the local_player every frame (could be optimised)
    visibility_check = gui.GetValue("esp.chams.enemy.occluded") == 0 and true or false
end

local function on_esp_draw(esp_builder)
    if esp_builder:GetEntity() == nil and local_player == nil then
        return
    end

    if not esp_builder:GetEntity():IsPlayer() then
        return
    end

    if backtrack == 0 then
        return
    end

    local player = esp_builder:GetEntity()

    if not local_player:IsAlive() or not player:IsAlive() then
        return
    end

    if local_player:GetIndex() == player:GetIndex() then  -- Is this even necissary?
        return
    end

    if local_player:GetTeamNumber() == player:GetTeamNumber() then
        return
    end

    local success, offset = pcall(function()
        return player:GetPropVector("m_vecViewOffset")
    end)
    if not success then
        return
    end

    local head_pos = player:GetAbsOrigin() + offset

    local last_w2sx, last_w2sy = nil, nil

    if not player_positions[player:GetIndex()] then
        player_positions[player:GetIndex()] = {}
    end

    table.insert(player_positions[player:GetIndex()], {head_pos, globals.RealTime()})

    for index, player_position in pairs(player_positions[player:GetIndex()]) do
        if globals.RealTime() - player_position[2] > backtrack / 1000 then
            table.remove(player_positions[player:GetIndex()], index)
        else
            local w2sx, w2sy = client.WorldToScreen(player_position[1])
            if w2sx and w2sy then
                visible = true
                if visibility_check then
                    local trace = engine.TraceLine(local_player:GetAbsOrigin() + local_player:GetPropVector("m_vecViewOffset"), player_position[1], MASK_SOLID)
                    if not trace or trace.fraction < 1 then
                        visible = false
                    else
                        visible = true
                    end
                end
                if last_w2sx and last_w2sy and visible then
                    if gui_rainbow_enable:GetValue() then
                        local r, g, b = drawing_hue(player_position[2])
                        gui_static_color:SetValue(r, g, b, 255)
                        draw.Color(r, g, b, 255)
                    else
                        gui_static_color:SetValue(255, 255, 255, 255)
                        draw.Color(gui_static_color:GetValue())
                    end
                    if gui_dot_size:GetValue() > 0 then
                        draw.FilledCircle( w2sx, w2sy, gui_dot_size:GetValue())
                    else
                        draw.Line(w2sx, w2sy, last_w2sx, last_w2sy)
                    end
                end
                last_w2sx, last_w2sy = w2sx, w2sy
            end
        end
    end
end

callbacks.Register("Draw", "draw_callback", on_draw)
callbacks.Register("DrawESP", "esp_draw_callback", on_esp_draw)