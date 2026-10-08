--!nonstrict
-- Vivaio dimostrativo: spiega cosa mostra e come leggere un layout.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Strings = require(Shared.Strings)
local Simulated = require(Shared.Catalog.SimulatedVivai)
local Defenses = require(Shared.Catalog.Defenses)
local Creatures = require(Shared.Catalog.Creatures)
local UI = require(script.Parent.UI)

local DemoPanel = {}
local panel

function DemoPanel.Init(screenGui)
	panel = UI.Panel(screenGui, "🏝 " .. Strings.PromptDemo, UDim2.new(0.6, 0, 0.7, 0))
	local content = panel.Content
	local scroll = UI.Scroll(content)
	UI.List(scroll, Enum.FillDirection.Vertical, 8)
	UI.Padding(scroll, 6)
	local demo = Simulated.ByKey.sim_faro
	UI.Label(scroll, "Questo vivaio mostra come si legge un layout: l'incursore entra dall'INGRESSO, raggiunge la pozza al centro ed esce dall'USCITA. Ogni layout deve lasciare almeno un percorso completabile.", { TextSize = 15, Size = UDim2.new(1, 0, 0, 70), LayoutOrder = 1, ZIndex = 13 })
	UI.Label(scroll, "Moduli esposti", { Font = UI.Theme.Font, TextSize = 18, Size = UDim2.new(1, 0, 0, 26), LayoutOrder = 2, ZIndex = 13 })
	for i, m in ipairs(demo.Layout.Modules) do
		local def = Defenses.Get(m.Id)
		if def then
			UI.Label(scroll, string.format("• <b>%s</b> (%s, ⚡%d): %s", def.Name, Defenses.CategoryNames[def.Category], def.Energy, def.Description), { TextSize = 14, Size = UDim2.new(1, 0, 0, 44), LayoutOrder = 10 + i, ZIndex = 13 })
		end
	end
	UI.Label(scroll, "Creature in mostra", { Font = UI.Theme.Font, TextSize = 18, Size = UDim2.new(1, 0, 0, 26), LayoutOrder = 30, ZIndex = 13 })
	for i, c in ipairs(demo.Creatures) do
		local def = Creatures.Get(c.Id)
		if def then
			UI.Label(scroll, string.format("• <b>%s</b> · %s · %s — %s", def.Name, Strings.Family[def.Family], Strings.Rarity[def.Rarity], def.Description), { TextSize = 14, Size = UDim2.new(1, 0, 0, 40), LayoutOrder = 30 + i, ZIndex = 13 })
		end
	end
	UI.Label(scroll, "Suggerimento: nel tuo vivaio apri Costruisci → Difese, posiziona un modulo e usa «Prova il percorso» per testarlo gratis.", { TextSize = 14, TextColor3 = UI.Colors.TextMuted, Size = UDim2.new(1, 0, 0, 44), LayoutOrder = 60, ZIndex = 13 })
end

function DemoPanel.Open()
	panel:Open()
end
function DemoPanel.Close()
	panel:Close()
end

return DemoPanel
