--!nonstrict
--[[
	BuildPanel: menu Costruisci con schede Creature / Difese / Decorazioni / Potenziamenti,
	barra energia, contatori slot, stato percorso, pubblicazione, prova, ripristino, codici.
	Più la toolbar flottante durante il posizionamento.
]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Creatures = require(Shared.Catalog.Creatures)
local Defenses = require(Shared.Catalog.Defenses)
local Decorations = require(Shared.Catalog.Decorations)
local Format = require(Shared.Util.Format)
local Net = require(Shared.Util.Net)
local CreatureModel = require(Shared.Models.CreatureModel)
local ModuleModel = require(Shared.Models.ModuleModel)
local DecorationModel = require(Shared.Models.DecorationModel)
local UI = require(script.Parent.UI)
local Toast = require(script.Parent.Toast)
local State = require(script.Parent.Parent.Controllers.State)
local Build = require(script.Parent.Parent.Controllers.BuildController)
local Audio = require(script.Parent.Parent.Controllers.Audio)

local BuildPanel = {}
local C = UI.Colors
local Players = game:GetService("Players")

local function playerAtHome()
	return Players.LocalPlayer:GetAttribute("Location") == "home"
end
local panel, tabs, body, statusBar, energyBar, slotsLabel, pathLabel
local toolbar, toolbarLabel, toolbarStatus
local currentTab = "creatures"

local function masteryTier(track)
	local m = State.Get("Mastery")
	if not m then
		return 0
	end
	local tier = 0
	for i, th in ipairs(Config.Mastery.Tiers) do
		if (m[track] or 0) >= th then
			tier = i
		end
	end
	return tier
end

local function refreshStatus(result)
	result = result or Build.Validate()
	energyBar:Set(result.Energy, Config.Defense.EnergyBudget, string.format(Strings.BuildEnergy, result.Energy, Config.Defense.EnergyBudget))
	local D = Config.Defense
	slotsLabel.Text = string.format(Strings.BuildSlots, result.Counts.ostacolo, D.MaxObstacles, result.Counts.distrazione, D.MaxDistractions, result.Counts.firma, D.MaxSignature)
	if result.Ok then
		pathLabel.Text = Strings.BuildPathOk .. (#Build.Layout.Modules > 0 and ("  ·  Difficoltà " .. Format.Stars(require(Shared.LayoutValidator).DifficultyStars(result.Difficulty), 5)) or "")
		pathLabel.TextColor3 = C.Success
	else
		pathLabel.Text = "✖ " .. (result.Reason or Strings.BuildPathBlocked)
		pathLabel.TextColor3 = C.Danger
	end
	if toolbarStatus then
		toolbarStatus.Text = pathLabel.Text .. "  ·  " .. string.format(Strings.BuildEnergy, result.Energy, Config.Defense.EnergyBudget)
		toolbarStatus.TextColor3 = pathLabel.TextColor3
	end
end

-- ───────────────────────── schede ─────────────────────────

local function renderCreatures()
	body:ClearAllChildren()
	local scroll = UI.Scroll(body)
	UI.Grid(scroll, UDim2.fromOffset(170, 250), 10)
	UI.Padding(scroll, 6)
	local creatures = State.Get("Creatures") or {}
	local placed, capacity = 0, Config.PlotSlots.Capacities[State.Get("PlotLevel") or 1]
	for _, c in pairs(creatures) do
		if c.x ~= nil then
			placed += 1
		end
	end
	local uids = {}
	for uid in pairs(creatures) do
		table.insert(uids, uid)
	end
	table.sort(uids)
	local order = 0
	for _, uid in ipairs(uids) do
		local c = creatures[uid]
		local def = Creatures.Get(c.Id)
		if def then
			order += 1
			local card = UI.Card(scroll, { Size = UDim2.fromOffset(170, 250), LayoutOrder = order })
			UI.Viewport(card, CreatureModel.Build(c.Id, c.Variant, nil), { Size = UDim2.new(1, -16, 0, 110), Position = UDim2.fromOffset(8, 8) })
			UI.Label(card, def.Name, { Font = UI.Theme.Font, TextSize = 18, Size = UDim2.new(1, -16, 0, 22), Position = UDim2.fromOffset(8, 122), ZIndex = 13 })
			UI.Pill(card, Strings.Rarity[def.Rarity], C.Rarity[def.Rarity], { Position = UDim2.fromOffset(8, 146), Size = UDim2.fromOffset(80, 20) })
			UI.Pill(card, Strings.Family[def.Family], C.Family[def.Family], { Position = UDim2.fromOffset(92, 146), Size = UDim2.fromOffset(70, 20) })
			UI.Label(card, string.format("✦ %d / %ds", def.Production, Config.Production.BaseInterval), { TextSize = 13, TextColor3 = C.TextMuted, Size = UDim2.new(1, -16, 0, 18), Position = UDim2.fromOffset(8, 168), ZIndex = 13 })
			if c.x ~= nil then
				local b = UI.Button(card, "Sposta", function()
					panel:Close()
					Build.Enter("creature", { Uid = uid })
				end, { Size = UDim2.new(0.5, -10, 0, 36), Position = UDim2.fromOffset(8, 206), Color = C.Info, TextSize = 14 })
				b.ZIndex = 13
				local r = UI.Button(card, "Ritira", function()
					Net.Invoke("RemoveCreature", uid)
				end, { Size = UDim2.new(0.5, -10, 0, 36), Position = UDim2.new(0.5, 2, 0, 206), Color = C.TextMuted, TextSize = 14 })
				r.ZIndex = 13
			else
				local full = placed >= capacity
				local b = UI.Button(card, full and "Vivaio pieno" or "Posiziona", function()
					if full then
						Toast.Show("Amplia il vivaio dalla scheda Potenziamenti", "warning")
						return
					end
					panel:Close()
					Build.Enter("creature", { Uid = uid })
				end, { Size = UDim2.new(1, -16, 0, 36), Position = UDim2.fromOffset(8, 206), Color = full and C.TextMuted or C.Success, TextSize = 14 })
				b.ZIndex = 13
			end
			-- varianti sbloccate
			local variants = (State.Get("UnlockedVariants") or {})[c.Id] or { base = true }
			local vx = 8
			for _, v in ipairs(def.Variants) do
				local unlocked = variants[v.Id] == true
				local dot = UI.Button(card, unlocked and "" or "🔒", function()
					if unlocked then
						Net.Invoke("SetVariant", uid, v.Id)
					end
				end, { Size = UDim2.fromOffset(28, 18), Position = UDim2.fromOffset(vx, 186), Color = unlocked and v.Color or Color3.fromRGB(200, 200, 210), TextSize = 10, Corner = UDim.new(1, 0) })
				dot.ZIndex = 13
				if c.Variant == v.Id then
					UI.Stroke(dot, C.Text, 2)
				end
				vx += 32
			end
		end
	end
	local info = UI.Label(scroll, string.format("Creature esposte: %d / %d · oltre la 6ª il rendimento cala", placed, capacity), { TextSize = 13, TextColor3 = C.TextMuted, Size = UDim2.fromOffset(340, 40), LayoutOrder = 999, ZIndex = 13 })
	info.TextWrapped = true
end

local function renderDefenses()
	body:ClearAllChildren()
	local scroll = UI.Scroll(body)
	UI.List(scroll, Enum.FillDirection.Vertical, 8)
	UI.Padding(scroll, 6)
	local unlocked = State.Get("UnlockedModules") or {}
	local unlockedAlts = State.Get("UnlockedAlternatives") or {}
	local chosenAlt = State.Get("ModuleAlternative") or {}
	local defenseTier = masteryTier("Defense")
	for i, def in ipairs(Defenses.List) do
		local isUnlocked = unlocked[def.Id] == true
		local card = UI.Card(scroll, { Size = UDim2.new(1, -8, 0, 150), LayoutOrder = i })
		UI.Viewport(card, ModuleModel.Build(def.Id, chosenAlt[def.Id], "home", nil), { Size = UDim2.fromOffset(130, 130), Position = UDim2.fromOffset(8, 10), Zoom = 1.0 })
		UI.Label(card, def.Name, { Font = UI.Theme.Font, TextSize = 20, Size = UDim2.new(1, -300, 0, 26), Position = UDim2.fromOffset(150, 8), ZIndex = 13 })
		UI.Pill(card, Defenses.CategoryNames[def.Category], def.Category == "ostacolo" and C.Info or (def.Category == "distrazione" and C.Token or C.Accent), { Position = UDim2.fromOffset(150, 36), Size = UDim2.fromOffset(110, 20) })
		UI.Label(card, string.format("⚡ %d energia · difficoltà %s", def.Energy, Format.Stars(math.clamp(math.floor(def.Difficulty + 0.5), 1, 5), 5)), { TextSize = 13, TextColor3 = C.TextMuted, Size = UDim2.new(1, -300, 0, 18), Position = UDim2.fromOffset(268, 37), ZIndex = 13 })
		UI.Label(card, def.Description, { TextSize = 14, Size = UDim2.new(1, -300, 0, 44), Position = UDim2.fromOffset(150, 60), ZIndex = 13, TextYAlignment = Enum.TextYAlignment.Top })
		-- alternative tattiche
		if #def.Alternatives > 0 then
			local ax = 150
			local function altButton(id, name, available)
				local b = UI.Button(card, (chosenAlt[def.Id] or "base") == id and ("● " .. name) or name, function()
					if not available then
						Toast.Show(Strings.BuildLocked, "warning")
						return
					end
					local ok, msg = Net.Invoke("SetModuleAlternative", def.Id, id)
					if not ok then
						Toast.Show(msg or Strings.Error, "warning")
					else
						renderDefenses()
					end
				end, { Size = UDim2.fromOffset(150, 28), Position = UDim2.fromOffset(ax, 110), Color = available and C.PanelDark or C.TextMuted, TextSize = 12, Corner = UDim.new(1, 0) })
				b.ZIndex = 13
				ax += 156
			end
			altButton("base", "Base", true)
			for _, alt in ipairs(def.Alternatives) do
				local avail = unlockedAlts[def.Id] and unlockedAlts[def.Id][alt.Id]
				altButton(alt.Id, alt.Name .. (avail and "" or (" (Difesa " .. alt.Unlock.Tier .. ")")), avail == true)
			end
		end
		local btn
		if isUnlocked then
			btn = UI.Button(card, "Posiziona", function()
				panel:Close()
				Build.Enter("module", { Id = def.Id, Alt = chosenAlt[def.Id] })
			end, { Size = UDim2.fromOffset(130, 44), Position = UDim2.new(1, -142, 0, 12), Color = C.Success })
		elseif def.Unlock.Kind == "sparks" then
			btn = UI.Button(card, string.format(Strings.BuildUnlockCost, def.Unlock.Cost), function()
				local ok, msg = Net.Invoke("UnlockModule", def.Id)
				if ok then
					renderDefenses()
				else
					Toast.Show(msg or Strings.Error, "warning")
				end
			end, { Size = UDim2.fromOffset(130, 44), Position = UDim2.new(1, -142, 0, 12), Color = C.AccentDark, TextSize = 14 })
		else
			btn = UI.Button(card, string.format("Maestria Difesa %d", def.Unlock.Tier or 1), nil, { Size = UDim2.fromOffset(130, 44), Position = UDim2.new(1, -142, 0, 12), Color = C.TextMuted, TextSize = 13 })
		end
		btn.ZIndex = 13
		UI.Label(card, string.format("Maestria Difesa attuale: %d", defenseTier), { TextSize = 12, TextColor3 = C.TextMuted, Size = UDim2.fromOffset(130, 30), Position = UDim2.new(1, -142, 0, 60), ZIndex = 13, TextXAlignment = Enum.TextXAlignment.Center })
	end
end

local function renderDecorations()
	body:ClearAllChildren()
	local scroll = UI.Scroll(body)
	UI.Grid(scroll, UDim2.fromOffset(170, 230), 10)
	UI.Padding(scroll, 6)
	local decos = State.Get("Decorations") or { Owned = {}, Placed = {} }
	local tokens = State.Get("StyleTokens") or 0
	local order = 0
	for _, def in ipairs(Decorations.List) do
		local owned = decos.Owned[def.Id] == true
		if owned or def.TokenPrice then
			order += 1
			local card = UI.Card(scroll, { Size = UDim2.fromOffset(170, 230), LayoutOrder = order })
			UI.Viewport(card, DecorationModel.Build(def.Id, nil, false), { Size = UDim2.new(1, -16, 0, 110), Position = UDim2.fromOffset(8, 8) })
			UI.Label(card, def.Name, { Font = UI.Theme.Font, TextSize = 17, Size = UDim2.new(1, -16, 0, 22), Position = UDim2.fromOffset(8, 122), ZIndex = 13 })
			UI.Label(card, def.Description, { TextSize = 12, TextColor3 = C.TextMuted, Size = UDim2.new(1, -16, 0, 40), Position = UDim2.fromOffset(8, 144), ZIndex = 13, TextYAlignment = Enum.TextYAlignment.Top })
			local b
			if owned then
				b = UI.Button(card, "Posiziona", function()
					panel:Close()
					Build.Enter("decoration", { Id = def.Id })
				end, { Size = UDim2.new(1, -16, 0, 36), Position = UDim2.fromOffset(8, 188), Color = C.Success, TextSize = 14 })
			else
				b = UI.Button(card, string.format("🎨 %d gettoni", def.TokenPrice), function()
					local ok, msg = Net.Invoke("BuyCosmetic", def.Id)
					if ok then
						renderDecorations()
					else
						Toast.Show(msg or Strings.Error, "warning")
					end
				end, { Size = UDim2.new(1, -16, 0, 36), Position = UDim2.fromOffset(8, 188), Color = tokens >= def.TokenPrice and C.Token or C.TextMuted, TextSize = 14 })
			end
			b.ZIndex = 13
		end
	end
	local placedInfo = UI.Label(scroll, string.format("Posizionate: %d / %d · tocca una decorazione nel vivaio (modalità modifica) per rimuoverla", #decos.Placed, Decorations.MaxPlaced), { TextSize = 13, TextColor3 = C.TextMuted, Size = UDim2.fromOffset(340, 60), LayoutOrder = 999, ZIndex = 13 })
	placedInfo.TextWrapped = true
end

local function renderUpgrades()
	body:ClearAllChildren()
	local scroll = UI.Scroll(body)
	UI.List(scroll, Enum.FillDirection.Vertical, 10)
	UI.Padding(scroll, 6)
	local sparks = State.Get("Sparks") or { Vault = 0, Exposed = 0, VaultLevel = 1 }
	local total = sparks.Vault + sparks.Exposed
	-- cassaforte
	local vcard = UI.Card(scroll, { Size = UDim2.new(1, -8, 0, 120), LayoutOrder = 1 })
	UI.Label(vcard, "🔒 Cassaforte", { Font = UI.Theme.Font, TextSize = 20, Size = UDim2.new(1, -16, 0, 26), Position = UDim2.fromOffset(12, 8), ZIndex = 13 })
	local nextLevel = sparks.VaultLevel + 1
	local vcost = Config.Vault.UpgradeCosts[nextLevel]
	UI.Label(vcard, string.format("Livello %d · capienza %s%s", sparks.VaultLevel, Format.Number(Config.Vault.Capacities[sparks.VaultLevel]), vcost and (" → " .. Format.Number(Config.Vault.Capacities[nextLevel])) or " (massimo)"), { TextSize = 15, Size = UDim2.new(1, -200, 0, 40), Position = UDim2.fromOffset(12, 40), ZIndex = 13 })
	UI.Label(vcard, "Le scintille depositate non possono essere sottratte.", { TextSize = 13, TextColor3 = C.TextMuted, Size = UDim2.new(1, -200, 0, 30), Position = UDim2.fromOffset(12, 82), ZIndex = 13 })
	if vcost then
		local b = UI.Button(vcard, string.format("Potenzia · %s ✦", Format.Number(vcost)), function()
			local ok, msg = Net.Invoke("UpgradeVault")
			if ok then
				renderUpgrades()
			else
				Toast.Show(msg or Strings.Error, "warning")
			end
		end, { Size = UDim2.fromOffset(180, 48), Position = UDim2.new(1, -192, 0.5, -24), Color = total >= vcost and C.AccentDark or C.TextMuted, TextSize = 15 })
		b.ZIndex = 13
	end
	-- espansione vivaio
	local pcard = UI.Card(scroll, { Size = UDim2.new(1, -8, 0, 120), LayoutOrder = 2 })
	local plotLevel = State.Get("PlotLevel") or 1
	local pnext = plotLevel + 1
	local pcost = Config.PlotSlots.UpgradeCosts[pnext]
	UI.Label(pcard, "🌿 Espansione del vivaio", { Font = UI.Theme.Font, TextSize = 20, Size = UDim2.new(1, -16, 0, 26), Position = UDim2.fromOffset(12, 8), ZIndex = 13 })
	UI.Label(pcard, string.format("Livello %d · %d creature esponibili%s", plotLevel, Config.PlotSlots.Capacities[plotLevel], pcost and (" → " .. Config.PlotSlots.Capacities[pnext]) or " (massimo)"), { TextSize = 15, Size = UDim2.new(1, -200, 0, 40), Position = UDim2.fromOffset(12, 40), ZIndex = 13 })
	UI.Label(pcard, "Oltre la sesta creatura il rendimento marginale cala: varietà, non quantità.", { TextSize = 13, TextColor3 = C.TextMuted, Size = UDim2.new(1, -200, 0, 30), Position = UDim2.fromOffset(12, 82), ZIndex = 13 })
	if pcost then
		local b = UI.Button(pcard, string.format("Amplia · %s ✦", Format.Number(pcost)), function()
			local ok, msg = Net.Invoke("UpgradePlot")
			if ok then
				renderUpgrades()
			else
				Toast.Show(msg or Strings.Error, "warning")
			end
		end, { Size = UDim2.fromOffset(180, 48), Position = UDim2.new(1, -192, 0.5, -24), Color = total >= pcost and C.AccentDark or C.TextMuted, TextSize = 15 })
		b.ZIndex = 13
	end
	-- importa codice layout
	local icard = UI.Card(scroll, { Size = UDim2.new(1, -8, 0, 110), LayoutOrder = 3 })
	UI.Label(icard, "🔗 Importa un layout dalla galleria", { Font = UI.Theme.Font, TextSize = 20, Size = UDim2.new(1, -16, 0, 26), Position = UDim2.fromOffset(12, 8), ZIndex = 13 })
	local box = UI.TextBox(icard, "Codice (es. NV-1A2B3)", { Size = UDim2.new(1, -220, 0, 44), Position = UDim2.fromOffset(12, 50) })
	local ib = UI.Button(icard, Strings.GalleryImport, function()
		local ok, res = Net.Invoke("ImportLayoutCode", box.Text)
		if ok and type(res) == "table" then
			Build.Start()
			Build.SetLayout(res.Layout)
			if #res.Missing > 0 then
				Toast.Show("Moduli da sbloccare: " .. table.concat(res.Missing, ", "), "warning")
			else
				Toast.Show("Layout importato nell'editor: pubblica per attivarlo", "success")
			end
			refreshStatus()
		else
			Toast.Show(type(res) == "string" and res or Strings.Error, "warning")
		end
	end, { Size = UDim2.fromOffset(190, 44), Position = UDim2.new(1, -202, 0, 50), Color = C.Info, TextSize = 15 })
	ib.ZIndex = 13
end

local renderers = { creatures = renderCreatures, defenses = renderDefenses, decorations = renderDecorations, upgrades = renderUpgrades }

-- ───────────────────────── toolbar di posizionamento ─────────────────────────

local function buildToolbar(screenGui)
	toolbar = UI.Frame(screenGui, { Name = "BuildToolbar", BackgroundColor3 = C.PanelDark, BackgroundTransparency = 0.1, Size = UDim2.new(0, 760, 0, 96), Position = UDim2.new(0.5, 0, 1, -16), AnchorPoint = Vector2.new(0.5, 1), Visible = false, ZIndex = 20 })
	UI.Corner(toolbar, UDim.new(0, 18))
	UI.Stroke(toolbar, C.Accent, 2)
	toolbarLabel = UI.Label(toolbar, "", { Size = UDim2.new(1, -24, 0, 22), Position = UDim2.fromOffset(14, 6), TextColor3 = C.TextOnDark, Font = UI.Theme.FontBold, TextSize = 15, ZIndex = 21 })
	toolbarStatus = UI.Label(toolbar, "", { Size = UDim2.new(1, -24, 0, 18), Position = UDim2.fromOffset(14, 26), TextColor3 = C.TextOnDark, TextSize = 13, ZIndex = 21 })
	local row = UI.Frame(toolbar, { BackgroundTransparency = 1, Size = UDim2.new(1, -24, 0, 42), Position = UDim2.fromOffset(12, 48), ZIndex = 21 })
	UI.List(row, Enum.FillDirection.Horizontal, 8)
	local function tb(text, fn, color, order)
		local b = UI.Button(row, text, fn, { Size = UDim2.new(0, 118, 1, 0), Color = color, LayoutOrder = order, TextSize = 14 })
		b.ZIndex = 22
		return b
	end
	tb("📋 Menu", function()
		panel:Open()
	end, C.Info, 1)
	tb("↻ " .. Strings.BuildRotate, function()
		Build.Rotate()
	end, C.PanelDark, 2)
	tb("✋ Modifica", function()
		Build.Enter("edit")
	end, C.PanelDark, 3)
	tb("✔ " .. Strings.BuildPublish, function()
		if Build.Publish() then
			Audio.Play("Success")
		end
	end, C.Success, 4)
	tb("▶ " .. Strings.BuildTest, function()
		local ok, msg = Net.Invoke("StartLayoutTest")
		if not ok then
			Toast.Show(msg or Strings.Error, "warning")
		else
			Build.Stop()
		end
	end, C.AccentDark, 5)
	tb("✕ Esci", function()
		Build.Stop()
	end, C.Danger, 6)
end

local function describeMode(mode, payload)
	if mode == "module" then
		local def = Defenses.Get(payload.Id)
		return "Posiziona: " .. (def and def.Name or payload.Id) .. "  ·  " .. Strings.BuildPlaceHint
	elseif mode == "creature" then
		local c = (State.Get("Creatures") or {})[payload.Uid]
		local def = c and Creatures.Get(c.Id)
		return "Posiziona: " .. (def and def.Name or "creatura") .. "  ·  tocca una cella libera"
	elseif mode == "decoration" then
		local def = Decorations.ById[payload.Id]
		return "Posiziona: " .. (def and def.Name or payload.Id) .. "  ·  " .. Strings.BuildPlaceHint
	end
	return "Modalità modifica: tocca un modulo per rimuoverlo, una creatura per spostarla, una decorazione per toglierla"
end

-- ───────────────────────── init ─────────────────────────

function BuildPanel.Init(screenGui)
	panel = UI.Panel(screenGui, "🔨 " .. Strings.BuildTitle)
	local content = panel.Content
	statusBar = UI.Frame(content, { BackgroundColor3 = C.PanelAlt, Size = UDim2.new(1, 0, 0, 74), ZIndex = 12 })
	UI.Corner(statusBar)
	energyBar = UI.Progress(statusBar, { Size = UDim2.new(0.45, -16, 0, 20), Position = UDim2.fromOffset(12, 10), FillColor = C.Accent })
	slotsLabel = UI.Label(statusBar, "", { Size = UDim2.new(0.55, -16, 0, 20), Position = UDim2.new(0.45, 8, 0, 10), TextSize = 13, ZIndex = 13 })
	pathLabel = UI.Label(statusBar, "", { Size = UDim2.new(0.6, -16, 0, 22), Position = UDim2.fromOffset(12, 40), TextSize = 14, Font = UI.Theme.FontBold, ZIndex = 13 })
	local actions = UI.Frame(statusBar, { BackgroundTransparency = 1, Size = UDim2.new(0.4, 0, 0, 30), Position = UDim2.new(0.6, 0, 0, 38), ZIndex = 13 })
	UI.List(actions, Enum.FillDirection.Horizontal, 6, Enum.HorizontalAlignment.Right)
	local function ab(text, fn, color, order)
		local b = UI.Button(actions, text, fn, { Size = UDim2.new(0, 112, 1, 0), Color = color, LayoutOrder = order, TextSize = 12, Corner = UI.Theme.CornerSmall })
		b.ZIndex = 14
	end
	ab(Strings.BuildPublish, function()
		Build.Start()
		if Build.Publish() then
			Audio.Play("Success")
			refreshStatus()
		end
	end, C.Success, 1)
	ab(Strings.BuildTest, function()
		local ok, msg = Net.Invoke("StartLayoutTest")
		if ok then
			panel:Close()
			Build.Stop()
		else
			Toast.Show(msg or Strings.Error, "warning")
		end
	end, C.AccentDark, 2)
	ab("Ripristina", function()
		Build.Start()
		Build.RestoreLastValid()
		refreshStatus()
	end, C.Info, 3)
	ab(Strings.BuildClear, function()
		Build.Start()
		Build.Clear()
		refreshStatus()
	end, C.Danger, 4)

	tabs = UI.Tabs(content, {
		{ Id = "creatures", Label = "🐣 " .. Strings.BuildCreatures },
		{ Id = "defenses", Label = "🛡 " .. Strings.BuildDefenses },
		{ Id = "decorations", Label = "🌸 " .. Strings.BuildDecor },
		{ Id = "upgrades", Label = "⬆ Potenziamenti" },
	}, function(name)
		currentTab = name
		renderers[name]()
	end, { Position = UDim2.fromOffset(0, 82) })
	body = UI.Frame(content, { BackgroundTransparency = 1, Size = UDim2.new(1, 0, 1, -136), Position = UDim2.fromOffset(0, 136), ZIndex = 12 })

	panel.OnOpen = function()
		if playerAtHome() then
			Build.Start()
		end
		tabs:Select(currentTab)
		refreshStatus()
	end

	buildToolbar(screenGui)
	Build.Toast = Toast.Show
	Build.Changed:Connect(function(result)
		refreshStatus(result)
	end)
	Build.ModeChanged:Connect(function(mode, payload)
		toolbar.Visible = mode ~= nil
		if mode then
			toolbarLabel.Text = describeMode(mode, payload)
			refreshStatus()
		end
	end)
	State.Changed:Connect(function(key)
		if panel.IsOpen and (key == "Creatures" or key == "UnlockedModules" or key == "Decorations" or key == "Sparks" or key == "PlotLevel" or key == "ModuleAlternative" or key == "StyleTokens" or key == "UnlockedVariants") then
			renderers[currentTab]()
		end
	end)
end

function BuildPanel.Open()
	if not playerAtHome() then
		Toast.Show("Torna nel tuo vivaio per costruire (pad HUB → Torna al tuo vivaio)", "warning")
	end
	panel:Open()
end

function BuildPanel.Close()
	panel:Close()
end

function BuildPanel.Toggle()
	if panel.IsOpen then
		panel:Close()
	else
		BuildPanel.Open()
	end
end

return BuildPanel
