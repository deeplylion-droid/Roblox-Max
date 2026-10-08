--!nonstrict
-- Commissioni del giorno + sfida del tema settimanale.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Strings = require(Shared.Strings)
local Themes = require(Shared.Catalog.Themes)
local Format = require(Shared.Util.Format)
local Net = require(Shared.Util.Net)
local UI = require(script.Parent.UI)
local Toast = require(script.Parent.Toast)
local State = require(script.Parent.Parent.Controllers.State)

local CommissionPanel = {}
local C = UI.Colors
local panel, list, resetLabel
local CATEGORY = { raccolta = { "✦", "Raccolta", C.Accent }, costruzione = { "🔨", "Costruzione", C.Info }, visita = { "🖼", "Visita", C.Token }, incursione = { "🌀", "Incursione", C.Danger } }

local function rewardText(r)
	local parts = {}
	if r.Sparks then
		table.insert(parts, "✦ " .. r.Sparks)
	end
	if r.Fragments then
		table.insert(parts, "💎 " .. r.Fragments)
	end
	table.insert(parts, "🎨 5")
	return table.concat(parts, "   ")
end

local function render()
	list:ClearAllChildren()
	UI.List(list, Enum.FillDirection.Vertical, 10)
	UI.Padding(list, 6)
	local data = State.Get("Commissions")
	if not data then
		return
	end
	for i, c in ipairs(data.List) do
		local cat = CATEGORY[c.Category] or { "•", c.Category, C.Info }
		local card = UI.Card(list, { Size = UDim2.new(1, -8, 0, 112), LayoutOrder = i })
		UI.Label(card, cat[1], { Size = UDim2.fromOffset(44, 44), Position = UDim2.fromOffset(10, 10), TextSize = 28, TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 13 })
		UI.Pill(card, cat[2], cat[3], { Position = UDim2.fromOffset(8, 58), Size = UDim2.fromOffset(90, 20) })
		UI.Label(card, c.Text, { Font = UI.Theme.Font, TextSize = 18, Size = UDim2.new(1, -340, 0, 26), Position = UDim2.fromOffset(110, 10), ZIndex = 13 })
		UI.Label(card, rewardText(c.Reward), { TextSize = 14, TextColor3 = C.TextMuted, Size = UDim2.new(1, -340, 0, 20), Position = UDim2.fromOffset(110, 38), ZIndex = 13 })
		local bar = UI.Progress(card, { Size = UDim2.new(1, -340, 0, 18), Position = UDim2.fromOffset(110, 66), FillColor = c.Complete and C.Success or C.Info })
		bar:Set(c.Progress, c.Target)
		if c.Claimed then
			local b = UI.Button(card, "✔ " .. Strings.CommissionClaimed, nil, { Size = UDim2.fromOffset(200, 44), Position = UDim2.new(1, -212, 0, 12), Color = C.TextMuted })
			b.ZIndex = 13
		elseif c.Complete then
			local b = UI.Button(card, "🎁 " .. Strings.CommissionClaim, function()
				local ok, msg = Net.Invoke("ClaimCommission", c.Index)
				if not ok then
					Toast.Show(msg or Strings.Error, "warning")
				end
			end, { Size = UDim2.fromOffset(200, 44), Position = UDim2.new(1, -212, 0, 12), Color = C.Success })
			b.ZIndex = 13
		else
			local b = UI.Button(card, data.RerollAvailable and ("↺ " .. Strings.CommissionReroll) or Strings.CommissionRerollUsed, function()
				if not data.RerollAvailable then
					return
				end
				local ok, msg = Net.Invoke("RerollCommission", c.Index)
				if not ok then
					Toast.Show(msg or Strings.Error, "warning")
				end
			end, { Size = UDim2.fromOffset(200, 44), Position = UDim2.new(1, -212, 0, 12), Color = data.RerollAvailable and C.Info or C.TextMuted, TextSize = 13 })
			b.ZIndex = 13
		end
		UI.Label(card, "Nessuna commissione richiede di colpire giocatori reali", { TextSize = 11, TextColor3 = C.TextMuted, Size = UDim2.fromOffset(200, 30), Position = UDim2.new(1, -212, 0, 62), ZIndex = 13, TextXAlignment = Enum.TextXAlignment.Center })
	end
	-- tema settimanale
	local info = State.Get("ServerInfo")
	local wp = info and info.WeeklyProgress
	local theme = info and Themes.ById[info.ThemeId]
	if theme and wp then
		local card = UI.Card(list, { Size = UDim2.new(1, -8, 0, 120), LayoutOrder = 50, BackgroundColor3 = Color3.fromRGB(235, 228, 255) })
		UI.Label(card, "🌤 " .. Strings.WeeklyTheme .. ": " .. theme.Name, { Font = UI.Theme.Font, TextSize = 18, Size = UDim2.new(1, -240, 0, 26), Position = UDim2.fromOffset(12, 8), ZIndex = 13 })
		UI.Label(card, theme.Description .. "\n" .. Strings.WeeklyChallenge .. ": " .. theme.Challenge.Text, { TextSize = 13, Size = UDim2.new(1, -240, 0, 44), Position = UDim2.fromOffset(12, 34), ZIndex = 13, TextYAlignment = Enum.TextYAlignment.Top })
		local bar = UI.Progress(card, { Size = UDim2.new(1, -240, 0, 18), Position = UDim2.fromOffset(12, 86), FillColor = C.Token })
		bar:Set(wp.Progress, wp.Target)
		local rewardLabel = theme.Challenge.Reward.Tokens and ("🎨 " .. theme.Challenge.Reward.Tokens) or "Cosmetico esclusivo"
		local b = UI.Button(card, wp.Claimed and "✔ Riscossa" or ((wp.Progress >= wp.Target) and ("🎁 Riscuoti " .. rewardLabel) or (rewardLabel .. " · " .. Format.Time(wp.SecondsToNextWeek))), function()
			if wp.Claimed or wp.Progress < wp.Target then
				return
			end
			local ok, msg = Net.Invoke("ClaimWeeklyChallenge")
			if not ok then
				Toast.Show(msg or Strings.Error, "warning")
			end
		end, { Size = UDim2.fromOffset(210, 44), Position = UDim2.new(1, -222, 0, 12), Color = (wp.Claimed and C.TextMuted) or ((wp.Progress >= wp.Target) and C.Success or C.Token), TextSize = 13 })
		b.ZIndex = 13
	end
	resetLabel.Text = string.format(Strings.CommissionReset, Format.Time(data.SecondsToReset or 0))
end

function CommissionPanel.Init(screenGui)
	panel = UI.Panel(screenGui, "📋 " .. Strings.CommissionsTitle, UDim2.new(0.8, 0, 0.8, 0))
	resetLabel = UI.Label(panel.Content, "", { TextSize = 14, TextColor3 = C.TextMuted, Size = UDim2.new(1, 0, 0, 22), ZIndex = 13, TextXAlignment = Enum.TextXAlignment.Right })
	list = UI.Scroll(panel.Content, { Size = UDim2.new(1, 0, 1, -26), Position = UDim2.fromOffset(0, 26) })
	panel.OnOpen = render
	State.Changed:Connect(function(key)
		if panel.IsOpen and (key == "Commissions" or key == "ServerInfo" or key == "WeeklyChallengeClaimed") then
			render()
		end
	end)
	task.spawn(function()
		while true do
			task.wait(30)
			if panel.IsOpen then
				local data = State.Get("Commissions")
				if data and data.SecondsToReset then
					data.SecondsToReset -= 30
					resetLabel.Text = string.format(Strings.CommissionReset, Format.Time(data.SecondsToReset))
				end
			end
		end
	end)
end

function CommissionPanel.Toggle()
	panel:Toggle()
end
function CommissionPanel.Open()
	panel:Open()
end
function CommissionPanel.Close()
	panel:Close()
end

return CommissionPanel
