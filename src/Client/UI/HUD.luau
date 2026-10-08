--!nonstrict
--[[
	HUD: espone sempre le quattro informazioni richieste dal GDD (scintille da depositare,
	cassaforte, protezione, prossimo obiettivo), valute secondarie, menu principale con
	pulsanti grandi e azioni contestuali (Raccogli tutto / Deposita tutto).
]]
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Themes = require(Shared.Catalog.Themes)
local Commissions = require(Shared.Catalog.Commissions)
local LayoutValidator = require(Shared.LayoutValidator)
local Format = require(Shared.Util.Format)
local Net = require(Shared.Util.Net)
local UI = require(script.Parent.UI)
local State = require(script.Parent.Parent.Controllers.State)

local HUD = {}
local C = UI.Colors
local player = Players.LocalPlayer
local root, cards, menuButtons, contextFrame, currencyLabel, themeLabel, homeButton
local callbacks: any = {}

local MENU = {
	{ Id = "build", Icon = "🔨", Label = Strings.MenuBuild, Key = Enum.KeyCode.B },
	{ Id = "raid", Icon = "🌀", Label = Strings.MenuRaid, Key = Enum.KeyCode.N },
	{ Id = "board", Icon = "📋", Label = Strings.MenuCommissions, Key = Enum.KeyCode.C },
	{ Id = "album", Icon = "📖", Label = Strings.MenuAlbum, Key = Enum.KeyCode.V },
	{ Id = "cocoon", Icon = "🥚", Label = Strings.MenuCocoon, Key = Enum.KeyCode.K },
	{ Id = "gallery", Icon = "🖼", Label = Strings.MenuGallery, Key = Enum.KeyCode.L },
	{ Id = "shop", Icon = "🛍", Label = Strings.MenuShop, Key = Enum.KeyCode.P },
	{ Id = "settings", Icon = "⚙", Label = Strings.MenuSettings, Key = Enum.KeyCode.O },
}

local function infoCard(parent, icon, title, order, color)
	local card = UI.Frame(parent, { BackgroundColor3 = C.Panel, Size = UDim2.new(0.25, -8, 1, 0), LayoutOrder = order, ZIndex = 5, BackgroundTransparency = 0.05 })
	UI.Corner(card)
	UI.Stroke(card, color, 2, 0.2)
	UI.Label(card, icon, { Size = UDim2.fromOffset(40, 40), Position = UDim2.fromOffset(8, 10), TextSize = 26, TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 6 })
	UI.Label(card, title, { Size = UDim2.new(1, -56, 0, 18), Position = UDim2.fromOffset(50, 6), TextSize = 12, TextColor3 = C.TextMuted, Font = UI.Theme.FontBold, ZIndex = 6 })
	local value = UI.Label(card, "—", { Size = UDim2.new(1, -56, 0, 30), Position = UDim2.fromOffset(50, 24), TextSize = 19, Font = UI.Theme.Font, ZIndex = 6, TextTruncate = Enum.TextTruncate.AtEnd, TextWrapped = false })
	return { Frame = card, Value = value }
end

function HUD.Init(screenGui, cb)
	callbacks = cb or {}
	root = UI.Frame(screenGui, { Name = "HUD", BackgroundTransparency = 1, ZIndex = 5 })

	-- barra superiore con le 4 informazioni
	local top = UI.Frame(root, { Name = "Top", BackgroundTransparency = 1, Size = UDim2.new(1, -40, 0, 62), Position = UDim2.fromOffset(20, 12), ZIndex = 5 })
	UI.List(top, Enum.FillDirection.Horizontal, 8)
	cards = {
		Exposed = infoCard(top, "✦", Strings.HudExposed, 1, C.Accent),
		Vault = infoCard(top, "🔒", Strings.HudVault, 2, C.Info),
		Protection = infoCard(top, "🛡", Strings.HudProtection, 3, C.Shield),
		Goal = infoCard(top, "🎯", Strings.HudNextGoal, 4, C.Success),
	}

	-- valute secondarie + tema
	local sub = UI.Frame(root, { Name = "Sub", BackgroundColor3 = C.PanelDark, BackgroundTransparency = 0.25, Size = UDim2.new(0, 420, 0, 28), Position = UDim2.new(1, -20, 0, 80), AnchorPoint = Vector2.new(1, 0), ZIndex = 5 })
	UI.Corner(sub, UDim.new(1, 0))
	currencyLabel = UI.Label(sub, "", { Size = UDim2.new(0.5, 0, 1, 0), Position = UDim2.fromOffset(14, 0), TextSize = 14, TextColor3 = C.TextOnDark, Font = UI.Theme.FontBold, ZIndex = 6 })
	themeLabel = UI.Label(sub, "", { Size = UDim2.new(0.5, -14, 1, 0), Position = UDim2.fromScale(0.5, 0), TextSize = 13, TextColor3 = C.TextOnDark, TextXAlignment = Enum.TextXAlignment.Right, ZIndex = 6 })

	-- menu a sinistra
	local menu = UI.Frame(root, { Name = "Menu", BackgroundTransparency = 1, Size = UDim2.new(0, 150, 0, #MENU * 54), Position = UDim2.new(0, 16, 0.5, 0), AnchorPoint = Vector2.new(0, 0.5), ZIndex = 5 })
	UI.List(menu, Enum.FillDirection.Vertical, 6)
	menuButtons = {}
	for i, m in ipairs(MENU) do
		local b = UI.Button(menu, m.Icon .. "  " .. m.Label, function()
			if callbacks.OnMenu then
				callbacks.OnMenu(m.Id)
			end
		end, { Size = UDim2.new(1, 0, 0, 48), Color = C.PanelDark, LayoutOrder = i, TextSize = 16, Name = "Menu_" .. m.Id })
		b.TextXAlignment = Enum.TextXAlignment.Left
		UI.Padding(b, 0, 12, 0)
		b.ZIndex = 6
		b.BackgroundTransparency = 0.15
		menuButtons[m.Id] = b
	end

	-- azioni contestuali (in basso al centro)
	contextFrame = UI.Frame(root, { Name = "Context", BackgroundTransparency = 1, Size = UDim2.new(0, 420, 0, 56), Position = UDim2.new(0.5, 0, 1, -22), AnchorPoint = Vector2.new(0.5, 1), ZIndex = 5 })
	UI.List(contextFrame, Enum.FillDirection.Horizontal, 10, Enum.HorizontalAlignment.Center)
	local collectBtn = UI.Button(contextFrame, "✦ " .. Strings.CollectAll .. "  [F]", function()
		Net.Fire("CollectAll")
	end, { Size = UDim2.new(0.5, -5, 1, 0), Color = C.AccentDark, LayoutOrder = 1 })
	collectBtn.ZIndex = 6
	local depositBtn = UI.Button(contextFrame, "🔒 " .. Strings.DepositAll .. "  [G]", function()
		Net.Fire("DepositAll")
	end, { Size = UDim2.new(0.5, -5, 1, 0), Color = C.Info, LayoutOrder = 2 })
	depositBtn.ZIndex = 6

	homeButton = UI.Button(root, "🏠 " .. Strings.PromptHome, function()
		Net.Invoke("ReturnHome")
	end, { Size = UDim2.new(0, 260, 0, 48), Position = UDim2.new(0.5, 0, 1, -90), AnchorPoint = Vector2.new(0.5, 1), Color = C.Success, Visible = false })
	homeButton.ZIndex = 6

	-- scorciatoie tastiera
	UserInputService.InputBegan:Connect(function(input, processed)
		if processed then
			return
		end
		if input.KeyCode == Enum.KeyCode.F then
			Net.Fire("CollectAll")
		elseif input.KeyCode == Enum.KeyCode.G then
			Net.Fire("DepositAll")
		else
			for _, m in ipairs(MENU) do
				if input.KeyCode == m.Key and callbacks.OnMenu then
					callbacks.OnMenu(m.Id)
				end
			end
		end
	end)

	-- posizione del giocatore: a casa, hub, raid, visita
	local function onLocation()
		local loc = player:GetAttribute("Location") or "hub"
		contextFrame.Visible = loc == "home"
		homeButton.Visible = loc == "hub" or loc == "visit"
		menu.Visible = loc ~= "raid"
	end
	player:GetAttributeChangedSignal("Location"):Connect(onLocation)
	onLocation()

	HUD.Bind()
end

local function protectionText()
	local raid = State.Get("Raid")
	local now = os.time()
	if raid and raid.ShieldUntil and raid.ShieldUntil > now then
		return string.format(Strings.ProtectionShield, Format.Time(raid.ShieldUntil - now)), C.Shield
	end
	if raid and raid.NewPlayerShield then
		return Strings.ProtectionNewbie, C.Shield
	end
	local layout = State.Get("LastValidLayout")
	if layout and layout.Modules and #layout.Modules > 0 then
		local res = LayoutValidator.Validate(layout, {})
		local stars = LayoutValidator.DifficultyStars(res.Difficulty or 0)
		return string.format(Strings.ProtectionLevel, Format.Stars(stars, 5)), C.Text
	end
	return Strings.ProtectionNone, C.Danger
end

local function goalText()
	local tut = State.Get("Tutorial")
	if tut and tut.Active and tut.Step <= Config.Tutorial.Steps then
		return string.format("Tutorial %d/%d", tut.Step, Config.Tutorial.Steps)
	end
	local comm = State.Get("Commissions")
	if comm and comm.List then
		for _, c in ipairs(comm.List) do
			if c.Complete and not c.Claimed then
				return "Riscuoti: " .. c.Text
			end
		end
		for _, c in ipairs(comm.List) do
			if not c.Claimed then
				return string.format("%s (%d/%d)", c.Text, c.Progress, c.Target)
			end
		end
	end
	local cocoon = State.Get("Cocoon")
	if cocoon and cocoon.Active then
		return string.format("Bozzolo: %s (%d/%d)", cocoon.Active.GoalText, cocoon.Active.Progress, cocoon.Active.Target)
	end
	return "Esplora la galleria dei vivai"
end

function HUD.Refresh()
	if not State.IsReady then
		return
	end
	local sparks = State.Get("Sparks") or { Exposed = 0, Vault = 0, VaultLevel = 1 }
	local cap = Config.Vault.Capacities[sparks.VaultLevel] or 0
	cards.Exposed.Value.Text = Format.Number(sparks.Exposed)
	cards.Exposed.Value.TextColor3 = sparks.Exposed > 0 and C.AccentDark or C.Text
	cards.Vault.Value.Text = string.format("%s / %s", Format.Number(sparks.Vault), Format.Number(cap))
	cards.Vault.Value.TextColor3 = sparks.Vault >= cap and C.Danger or C.Text
	local pt, pc = protectionText()
	cards.Protection.Value.Text = pt
	cards.Protection.Value.TextColor3 = pc
	cards.Goal.Value.Text = goalText()
	currencyLabel.Text = string.format("💎 %d   🎨 %d", State.Get("Fragments") or 0, State.Get("StyleTokens") or 0)
	local info = State.Get("ServerInfo")
	if info and info.ThemeId then
		local theme = Themes.ById[info.ThemeId]
		themeLabel.Text = theme and ("🌤 " .. theme.Name) or ""
	end
end

function HUD.Bind()
	State.Changed:Connect(function()
		HUD.Refresh()
	end)
	State.OnReady(HUD.Refresh)
	-- timer scudo
	task.spawn(function()
		while true do
			task.wait(1)
			HUD.Refresh()
		end
	end)
end

function HUD.SetVisible(visible)
	if root then
		root.Visible = visible
	end
end

function HUD.CardPosition(name)
	local card = cards and cards[name]
	if card then
		return card.Frame.AbsolutePosition + card.Frame.AbsoluteSize / 2
	end
	return Vector2.new(200, 40)
end

local highlightStrokes = {}
function HUD.Highlight(menuId, on)
	local b = menuButtons and menuButtons[menuId]
	if not b then
		return
	end
	local stroke = highlightStrokes[menuId]
	if not stroke then
		stroke = UI.Stroke(b, C.Accent, 3, 1)
		highlightStrokes[menuId] = stroke
	end
	stroke.Transparency = on and 0 or 1
end

return HUD
