--!nonstrict
-- Notifiche brevi in alto al centro, con icona testuale per tipo (non solo colore).
local TweenService = game:GetService("TweenService")
local UI = require(script.Parent.UI)

local Toast = {}
local container
local ICONS = { info = "ℹ", success = "✔", warning = "⚠", error = "✖" }
local COLORS = { info = UI.Colors.Info, success = UI.Colors.Success, warning = UI.Colors.Accent, error = UI.Colors.Danger }

function Toast.Init(screenGui)
	container = UI.Frame(screenGui, { Name = "Toasts", BackgroundTransparency = 1, Size = UDim2.new(0, 460, 0, 300), Position = UDim2.new(0.5, 0, 0, 90), AnchorPoint = Vector2.new(0.5, 0), ZIndex = 50 })
	UI.List(container, Enum.FillDirection.Vertical, 6, Enum.HorizontalAlignment.Center)
end

function Toast.Show(message, kind)
	if not container then
		return
	end
	kind = kind or "info"
	local f = UI.Frame(container, { BackgroundColor3 = UI.Colors.PanelDark, Size = UDim2.new(1, 0, 0, 52), ZIndex = 51, BackgroundTransparency = 1 })
	UI.Corner(f)
	UI.Stroke(f, COLORS[kind] or UI.Colors.Info, 2)
	local icon = UI.Label(f, ICONS[kind] or "ℹ", { Size = UDim2.fromOffset(40, 52), Position = UDim2.fromOffset(10, 0), TextSize = 24, TextXAlignment = Enum.TextXAlignment.Center, TextColor3 = COLORS[kind], ZIndex = 52, TextTransparency = 1 })
	local label = UI.Label(f, message, { Size = UDim2.new(1, -64, 1, 0), Position = UDim2.fromOffset(54, 0), TextColor3 = UI.Colors.TextOnDark, TextSize = 16, ZIndex = 52, TextTransparency = 1 })
	TweenService:Create(f, TweenInfo.new(0.2), { BackgroundTransparency = 0.08 }):Play()
	TweenService:Create(label, TweenInfo.new(0.2), { TextTransparency = 0 }):Play()
	TweenService:Create(icon, TweenInfo.new(0.2), { TextTransparency = 0 }):Play()
	task.delay(math.clamp(2.5 + #message / 30, 3, 7), function()
		TweenService:Create(f, TweenInfo.new(0.3), { BackgroundTransparency = 1 }):Play()
		TweenService:Create(label, TweenInfo.new(0.3), { TextTransparency = 1 }):Play()
		TweenService:Create(icon, TweenInfo.new(0.3), { TextTransparency = 1 }):Play()
		task.wait(0.32)
		f:Destroy()
	end)
	-- massimo 4 toast visibili
	local children = container:GetChildren()
	local frames = {}
	for _, c in ipairs(children) do
		if c:IsA("Frame") then
			table.insert(frames, c)
		end
	end
	while #frames > 4 do
		local oldest = table.remove(frames, 1)
		if oldest then
			oldest:Destroy()
		end
	end
end

return Toast
