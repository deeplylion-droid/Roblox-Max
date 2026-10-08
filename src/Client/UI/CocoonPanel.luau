--!nonstrict
-- Bozzoli: scelta deterministica della famiglia, anteprima esplicita del percorso di sblocco.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Creatures = require(Shared.Catalog.Creatures)
local Net = require(Shared.Util.Net)
local CreatureModel = require(Shared.Models.CreatureModel)
local UI = require(script.Parent.UI)
local Toast = require(script.Parent.Toast)
local State = require(script.Parent.Parent.Controllers.State)

local CocoonPanel = {}
local C = UI.Colors
local panel, body

local function render()
	body:ClearAllChildren()
	local scroll = UI.Scroll(body)
	UI.List(scroll, Enum.FillDirection.Vertical, 10)
	UI.Padding(scroll, 6)
	local cocoon = State.Get("Cocoon") or {}
	local fragments = State.Get("Fragments") or 0
	UI.Label(scroll, string.format("💎 Frammenti di cielo: %d  ·  " .. Strings.CocoonCost, fragments, Config.Cocoon.FragmentCost), { Font = UI.Theme.FontBold, TextSize = 15, Size = UDim2.new(1, 0, 0, 24), LayoutOrder = 0, ZIndex = 13 })
	if cocoon.Active then
		local a = cocoon.Active
		local def = Creatures.Get(a.CreatureId)
		local card = UI.Card(scroll, { Size = UDim2.new(1, -8, 0, 170), LayoutOrder = 1, BackgroundColor3 = Color3.fromRGB(255, 245, 225) })
		UI.Viewport(card, CreatureModel.Build(a.CreatureId, "base", nil), { Size = UDim2.fromOffset(150, 150), Position = UDim2.fromOffset(10, 10) })
		UI.Label(card, "🥚 " .. Strings.CocoonActive .. " · " .. Strings.Family[a.Family], { Font = UI.Theme.Font, TextSize = 20, Size = UDim2.new(1, -180, 0, 28), Position = UDim2.fromOffset(170, 10), ZIndex = 13 })
		UI.Label(card, string.format("Si schiuderà in: <b>%s</b> (%s)", def and def.Name or "?", Strings.Rarity[def and def.Rarity or "comune"]), { TextSize = 15, Size = UDim2.new(1, -180, 0, 24), Position = UDim2.fromOffset(170, 42), ZIndex = 13 })
		UI.Label(card, Strings.CocoonPath .. ": " .. a.GoalText, { TextSize = 15, Size = UDim2.new(1, -180, 0, 24), Position = UDim2.fromOffset(170, 68), ZIndex = 13 })
		local bar = UI.Progress(card, { Size = UDim2.new(1, -190, 0, 22), Position = UDim2.fromOffset(170, 100), FillColor = C.Accent })
		bar:Set(a.Progress, a.Target)
		UI.Label(card, "Continua a giocare: il progresso si aggiorna da solo.", { TextSize = 13, TextColor3 = C.TextMuted, Size = UDim2.new(1, -180, 0, 24), Position = UDim2.fromOffset(170, 130), ZIndex = 13 })
	end
	UI.Label(scroll, Strings.CocoonChoose .. " — vedrai prima quale creatura otterrai e cosa serve per sbloccarla. Nessuna casualità, nessun doppione.", { TextSize = 14, TextColor3 = C.TextMuted, Size = UDim2.new(1, 0, 0, 40), LayoutOrder = 2, ZIndex = 13 })
	local grid = UI.Frame(scroll, { BackgroundTransparency = 1, Size = UDim2.new(1, 0, 0, 300), LayoutOrder = 3, ZIndex = 12 })
	UI.Grid(grid, UDim2.new(0.25, -10, 0, 290), 10)
	for i, family in ipairs(Creatures.Families) do
		local info = Creatures.FamilyInfo[family]
		local card = UI.Card(grid, { LayoutOrder = i })
		UI.Gradient(card, Color3.new(1, 1, 1), C.Family[family], 90)
		UI.Label(card, Strings.Family[family], { Font = UI.Theme.Font, TextSize = 22, Size = UDim2.new(1, -16, 0, 30), Position = UDim2.fromOffset(8, 8), ZIndex = 13, TextXAlignment = Enum.TextXAlignment.Center })
		UI.Label(card, info.Description, { TextSize = 13, Size = UDim2.new(1, -16, 0, 36), Position = UDim2.fromOffset(8, 40), ZIndex = 13, TextXAlignment = Enum.TextXAlignment.Center })
		local preview = Net.Invoke("GetCocoonPreview", family)
		if type(preview) == "table" and not preview.Complete then
			UI.Viewport(card, CreatureModel.Build(preview.CreatureId, "base", nil), { Size = UDim2.new(1, -16, 0, 110), Position = UDim2.fromOffset(8, 80), BackgroundTransparency = 0.3 })
			UI.Label(card, string.format("<b>%s</b> · %s", preview.CreatureName, Strings.Rarity[preview.Rarity]), { TextSize = 14, Size = UDim2.new(1, -16, 0, 20), Position = UDim2.fromOffset(8, 194), ZIndex = 13, TextXAlignment = Enum.TextXAlignment.Center })
			UI.Label(card, "🎯 " .. preview.Goal.Text, { TextSize = 12, TextColor3 = C.TextMuted, Size = UDim2.new(1, -16, 0, 32), Position = UDim2.fromOffset(8, 214), ZIndex = 13, TextXAlignment = Enum.TextXAlignment.Center })
			local canStart = not cocoon.Active and preview.CanAfford
			local b = UI.Button(card, cocoon.Active and "Bozzolo in corso" or (preview.CanAfford and string.format("Avvia · 💎 %d", preview.Cost) or Strings.CocoonNoFragments), function()
				if not canStart then
					return
				end
				local ok, msg = Net.Invoke("StartCocoon", family)
				if ok then
					render()
				else
					Toast.Show(msg or Strings.Error, "warning")
				end
			end, { Size = UDim2.new(1, -16, 0, 38), Position = UDim2.fromOffset(8, 246), Color = canStart and C.Success or C.TextMuted, TextSize = 14 })
			b.ZIndex = 13
		else
			UI.Label(card, "✔ " .. Strings.CocoonFamilyComplete, { Font = UI.Theme.FontBold, TextSize = 16, Size = UDim2.new(1, -16, 0, 60), Position = UDim2.fromOffset(8, 120), ZIndex = 13, TextXAlignment = Enum.TextXAlignment.Center, TextColor3 = C.Success })
		end
	end
	UI.Label(scroll, "I frammenti si ottengono da commissioni, album e maestria. Non sono in vendita.", { TextSize = 13, TextColor3 = C.TextMuted, Size = UDim2.new(1, 0, 0, 24), LayoutOrder = 4, ZIndex = 13 })
end

function CocoonPanel.Init(screenGui)
	panel = UI.Panel(screenGui, "🥚 " .. Strings.CocoonTitle)
	body = UI.Frame(panel.Content, { BackgroundTransparency = 1, ZIndex = 12 })
	panel.OnOpen = render
	State.Changed:Connect(function(key)
		if panel.IsOpen and (key == "Cocoon" or key == "Fragments" or key == "OwnedCreatureIds") then
			render()
		end
	end)
end

function CocoonPanel.Toggle()
	panel:Toggle()
end
function CocoonPanel.Open()
	panel:Open()
end
function CocoonPanel.Close()
	panel:Close()
end

return CocoonPanel
