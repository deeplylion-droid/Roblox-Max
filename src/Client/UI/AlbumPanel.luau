--!nonstrict
-- Album delle famiglie meteo: creature, varianti, traguardi, maestria.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Creatures = require(Shared.Catalog.Creatures)
local Album = require(Shared.Catalog.Album)
local Net = require(Shared.Util.Net)
local CreatureModel = require(Shared.Models.CreatureModel)
local UI = require(script.Parent.UI)
local Toast = require(script.Parent.Toast)
local State = require(script.Parent.Parent.Controllers.State)

local AlbumPanel = {}
local C = UI.Colors
local panel, tabs, body
local current = "sole"

local function ownedCounts()
	local owned = State.Get("OwnedCreatureIds") or {}
	local byFamily, total = { sole = 0, pioggia = 0, vento = 0, aurora = 0 }, 0
	for id in pairs(owned) do
		local def = Creatures.Get(id)
		if def then
			byFamily[def.Family] += 1
			total += 1
		end
	end
	return byFamily, total, owned
end

local function renderFamily(family)
	body:ClearAllChildren()
	local scroll = UI.Scroll(body)
	UI.List(scroll, Enum.FillDirection.Vertical, 10)
	UI.Padding(scroll, 6)
	local byFamily, total, owned = ownedCounts()
	local info = Creatures.FamilyInfo[family]
	UI.Label(scroll, string.format("%s · %s  —  " .. Strings.AlbumOwned, info.Name, info.Description, byFamily[family], 4), { Font = UI.Theme.FontBold, TextSize = 15, Size = UDim2.new(1, 0, 0, 24), LayoutOrder = 0, ZIndex = 13 })
	local grid = UI.Frame(scroll, { BackgroundTransparency = 1, Size = UDim2.new(1, 0, 0, 270), LayoutOrder = 1, ZIndex = 12 })
	UI.Grid(grid, UDim2.fromOffset(200, 260), 10)
	local variants = State.Get("UnlockedVariants") or {}
	for i, def in ipairs(Creatures.ByFamily[family]) do
		local has = owned[def.Id] == true
		local card = UI.Card(grid, { Size = UDim2.fromOffset(200, 260), LayoutOrder = i, BackgroundColor3 = has and C.PanelAlt or Color3.fromRGB(215, 222, 235) })
		local model = CreatureModel.Build(def.Id, "base", nil)
		if not has then
			for _, d in ipairs(model:GetDescendants()) do
				if d:IsA("BasePart") then
					d.Color = Color3.fromRGB(70, 80, 110)
					d.Material = Enum.Material.SmoothPlastic
				elseif d:IsA("PointLight") or d:IsA("ParticleEmitter") or d:IsA("Sparkles") then
					d:Destroy()
				end
			end
		end
		UI.Viewport(card, model, { Size = UDim2.new(1, -16, 0, 120), Position = UDim2.fromOffset(8, 8) })
		UI.Label(card, has and def.Name or (Strings.AlbumLocked .. " #" .. def.UnlockOrder), { Font = UI.Theme.Font, TextSize = 18, Size = UDim2.new(1, -16, 0, 24), Position = UDim2.fromOffset(8, 132), ZIndex = 13 })
		UI.Pill(card, Strings.Rarity[def.Rarity], C.Rarity[def.Rarity], { Position = UDim2.fromOffset(8, 158), Size = UDim2.fromOffset(90, 20) })
		UI.Label(card, has and def.Description or "Ottienila con un bozzolo " .. info.Name, { TextSize = 12, TextColor3 = C.TextMuted, Size = UDim2.new(1, -16, 0, 44), Position = UDim2.fromOffset(8, 182), ZIndex = 13, TextYAlignment = Enum.TextYAlignment.Top })
		-- varianti
		local vx = 8
		local unlocked = variants[def.Id] or {}
		for _, v in ipairs(def.Variants) do
			local isU = has and unlocked[v.Id]
			local dot = UI.Frame(card, { Size = UDim2.fromOffset(40, 20), Position = UDim2.fromOffset(vx, 230), BackgroundColor3 = isU and v.Color or Color3.fromRGB(190, 195, 210), ZIndex = 13 })
			UI.Corner(dot, UDim.new(1, 0))
			UI.Label(dot, isU and "" or "🔒", { Size = UDim2.fromScale(1, 1), TextSize = 10, TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 14 })
			vx += 46
		end
	end
	-- traguardi della famiglia + globali
	local claimed = (State.Get("Album") or { Claimed = {} }).Claimed
	local mlist = UI.Frame(scroll, { BackgroundTransparency = 1, Size = UDim2.new(1, 0, 0, 0), AutomaticSize = Enum.AutomaticSize.Y, LayoutOrder = 2, ZIndex = 12 })
	UI.List(mlist, Enum.FillDirection.Vertical, 6)
	UI.Label(mlist, "🏅 " .. Strings.AlbumMilestone .. " (famiglia e globali)", { Font = UI.Theme.FontBold, TextSize = 15, Size = UDim2.new(1, 0, 0, 24), LayoutOrder = 0, ZIndex = 13 })
	local order = 0
	for _, m in ipairs(Album.List) do
		if m.Family == family or m.Family == nil then
			order += 1
			local reached = m.Family and byFamily[family] >= m.Count or (not m.Family and total >= m.Count)
			local isClaimed = claimed[m.Id] == true
			local row = UI.Card(mlist, { Size = UDim2.new(1, -8, 0, 56), LayoutOrder = order, BackgroundColor3 = isClaimed and Color3.fromRGB(220, 245, 230) or C.PanelAlt })
			local rewards = {}
			if m.Reward.Fragments then
				table.insert(rewards, "💎 " .. m.Reward.Fragments)
			end
			if m.Reward.Tokens then
				table.insert(rewards, "🎨 " .. m.Reward.Tokens)
			end
			if m.Reward.Sparks then
				table.insert(rewards, "✦ " .. m.Reward.Sparks)
			end
			if m.Reward.Decoration then
				table.insert(rewards, "🌸 decorazione")
			end
			if m.Reward.Cosmetic then
				table.insert(rewards, "🏷 targhetta")
			end
			UI.Label(row, string.format("%s  <font color=\"#6a7a95\">(%d %s)</font>", m.Title, m.Count, m.Family and "creature" or "creature in totale"), { Font = UI.Theme.FontBold, TextSize = 15, Size = UDim2.new(1, -330, 0, 26), Position = UDim2.fromOffset(12, 6), ZIndex = 13 })
			UI.Label(row, table.concat(rewards, "   "), { TextSize = 13, TextColor3 = C.TextMuted, Size = UDim2.new(1, -330, 0, 20), Position = UDim2.fromOffset(12, 30), ZIndex = 13 })
			local b = UI.Button(row, isClaimed and "✔ Riscosso" or (reached and "🎁 Riscuoti" or "Non raggiunto"), function()
				if reached and not isClaimed then
					local ok, msg = Net.Invoke("ClaimAlbumMilestone", m.Id)
					if not ok then
						Toast.Show(msg or Strings.Error, "warning")
					end
				end
			end, { Size = UDim2.fromOffset(170, 40), Position = UDim2.new(1, -182, 0.5, -20), Color = isClaimed and C.TextMuted or (reached and C.Success or C.TextMuted), TextSize = 14 })
			b.ZIndex = 13
		end
	end
end

local function renderMastery()
	body:ClearAllChildren()
	local scroll = UI.Scroll(body)
	UI.List(scroll, Enum.FillDirection.Vertical, 12)
	UI.Padding(scroll, 6)
	local mastery = State.Get("Mastery") or { Collection = 0, Raid = 0, Defense = 0, ClaimedTiers = {} }
	local desc = {
		Collection = "Cresce con nuove creature e varianti. Tier II sblocca il deposito automatico.",
		Raid = "Cresce con ogni incursione (riuscita o no). Sblocca varianti Crepuscolo.",
		Defense = "Cresce con layout pubblicati e incursioni respinte. Sblocca alternative tattiche e moduli firma.",
	}
	for i, track in ipairs({ "Collection", "Raid", "Defense" }) do
		local points = mastery[track] or 0
		local tier = Album.TierFor(points, Config.Mastery.Tiers)
		local nextTh = Config.Mastery.Tiers[tier + 1]
		local card = UI.Card(scroll, { Size = UDim2.new(1, -8, 0, 150), LayoutOrder = i })
		local title = Album.MasteryRewards[track][tier] and Album.MasteryRewards[track][tier].Title or "—"
		UI.Label(card, string.format("%s · Tier %d  <font color=\"#6a7a95\">%s</font>", Strings["Mastery" .. track], tier, title), { Font = UI.Theme.Font, TextSize = 20, Size = UDim2.new(1, -24, 0, 28), Position = UDim2.fromOffset(12, 8), ZIndex = 13 })
		UI.Label(card, desc[track], { TextSize = 13, TextColor3 = C.TextMuted, Size = UDim2.new(1, -24, 0, 36), Position = UDim2.fromOffset(12, 36), ZIndex = 13, TextYAlignment = Enum.TextYAlignment.Top })
		local bar = UI.Progress(card, { Size = UDim2.new(1, -24, 0, 20), Position = UDim2.fromOffset(12, 76), FillColor = C.Info })
		if nextTh then
			bar:Set(points, nextTh, string.format("%d / %d punti al Tier %d", points, nextTh, tier + 1))
		else
			bar:Set(1, 1, "Maestria massima")
		end
		local nextReward = Album.MasteryRewards[track][tier + 1]
		UI.Label(card, nextReward and ("Prossimo: " .. nextReward.Title .. "  💎 " .. (nextReward.Fragments or 0) .. (nextReward.Tokens and ("  🎨 " .. nextReward.Tokens) or "") .. (nextReward.Unlock == "AutoDeposit" and "  + deposito automatico" or "")) or "", { TextSize = 13, Size = UDim2.new(1, -24, 0, 40), Position = UDim2.fromOffset(12, 102), ZIndex = 13 })
	end
	UI.Label(scroll, "La maestria dà identità e opzioni tattiche laterali, non vantaggi cumulativi.", { TextSize = 13, TextColor3 = C.TextMuted, Size = UDim2.new(1, 0, 0, 30), LayoutOrder = 10, ZIndex = 13 })
end

function AlbumPanel.Init(screenGui)
	panel = UI.Panel(screenGui, "📖 " .. Strings.AlbumTitle)
	tabs = UI.Tabs(panel.Content, {
		{ Id = "sole", Label = "☀ Sole" }, { Id = "pioggia", Label = "🌧 Pioggia" }, { Id = "vento", Label = "🍃 Vento" }, { Id = "aurora", Label = "🌌 Aurora" }, { Id = "mastery", Label = "🏅 " .. Strings.AlbumMastery },
	}, function(name)
		current = name
		if name == "mastery" then
			renderMastery()
		else
			renderFamily(name)
		end
	end)
	body = UI.Frame(panel.Content, { BackgroundTransparency = 1, Size = UDim2.new(1, 0, 1, -54), Position = UDim2.fromOffset(0, 54), ZIndex = 12 })
	panel.OnOpen = function()
		tabs:Select(current)
	end
	State.Changed:Connect(function(key)
		if panel.IsOpen and (key == "OwnedCreatureIds" or key == "Album" or key == "Mastery" or key == "UnlockedVariants") then
			tabs:Select(current)
		end
	end)
end

function AlbumPanel.Toggle()
	panel:Toggle()
end
function AlbumPanel.Open()
	panel:Open()
end
function AlbumPanel.Close()
	panel:Close()
end

return AlbumPanel
