--!nonstrict
-- Incursioni: scelta del bersaglio, HUD durante il raid, riepilogo finale.
local TweenService = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Format = require(Shared.Util.Format)
local Net = require(Shared.Util.Net)
local UI = require(script.Parent.UI)
local Toast = require(script.Parent.Toast)
local State = require(script.Parent.Parent.Controllers.State)

local RaidPanel = {}
local C = UI.Colors
local panel, body, overlay, timerBar, objectiveLabel, titleLabel, flash, summaryPanel
local raidActive = false
local raidDuration, raidStart = 90, 0
local countdownLabel

local function render()
	body:ClearAllChildren()
	local scroll = UI.Scroll(body)
	UI.List(scroll, Enum.FillDirection.Vertical, 10)
	UI.Padding(scroll, 6)
	local loading = UI.Label(scroll, "Cerco vivai idonei…", { TextSize = 15, TextColor3 = C.TextMuted, Size = UDim2.new(1, 0, 0, 24), LayoutOrder = 0, ZIndex = 13 })
	task.spawn(function()
		local data, err = Net.Invoke("RequestRaidTargets")
		if not scroll.Parent then
			return
		end
		if type(data) ~= "table" then
			loading.Text = err or Strings.RaidNoTargets
			return
		end
		loading:Destroy()
		local raid = State.Get("Raid") or {}
		UI.Label(scroll, string.format("Incursioni: %d · riuscite: %d · difese respinte: %d", raid.Attempts or 0, raid.Successes or 0, raid.Defended or 0), { TextSize = 13, TextColor3 = C.TextMuted, Size = UDim2.new(1, 0, 0, 20), LayoutOrder = 0, ZIndex = 13 })
		UI.Label(scroll, "Regole: durata 90 s · massimo 25% delle scintille esposte · in caso di errore torni al checkpoint, nessun combattimento · chi difende non perde mai creature né scintille depositate.", { TextSize = 13, Size = UDim2.new(1, 0, 0, 40), LayoutOrder = 1, ZIndex = 13 })
		for i, t in ipairs(data.Targets) do
			local card = UI.Card(scroll, { Size = UDim2.new(1, -8, 0, 120), LayoutOrder = 10 + i, BackgroundColor3 = t.Simulated and Color3.fromRGB(230, 240, 255) or C.PanelAlt })
			UI.Label(card, (t.Simulated and "🤖 " or "🏝 ") .. t.Name, { Font = UI.Theme.Font, TextSize = 19, Size = UDim2.new(1, -220, 0, 26), Position = UDim2.fromOffset(12, 8), ZIndex = 13 })
			UI.Label(card, string.format("%s: %s   ·   🛡 %d moduli   ·   fascia %d", Strings.RaidDifficulty, Format.Stars(t.Difficulty, 5), t.ModuleCount, t.Tier), { TextSize = 14, Size = UDim2.new(1, -220, 0, 22), Position = UDim2.fromOffset(12, 36), ZIndex = 13 })
			UI.Label(card, string.format("%s: ~%s   ·   %s: ✦ %s", Strings.RaidExposed, Format.Number(t.ExposedEstimate), Strings.RaidReward, Format.Number(t.MaxTake)), { TextSize = 14, Size = UDim2.new(1, -220, 0, 22), Position = UDim2.fromOffset(12, 60), ZIndex = 13 })
			UI.Label(card, t.Simulated and Strings.RaidSimulatedNote or "Giocatore reale · identità non mostrata · il bottino va nelle tue scintille esposte", { TextSize = 12, TextColor3 = C.TextMuted, Size = UDim2.new(1, -220, 0, 22), Position = UDim2.fromOffset(12, 88), ZIndex = 13 })
			local b = UI.Button(card, "🌀 " .. Strings.RaidStart, function()
				local ok, msg = Net.Invoke("StartRaid", t.Key)
				if ok then
					panel:Close()
				else
					Toast.Show(msg or Strings.Error, "warning")
					render()
				end
			end, { Size = UDim2.fromOffset(190, 52), Position = UDim2.new(1, -202, 0.5, -26), Color = t.Simulated and C.Info or C.Danger })
			b.ZIndex = 13
		end
		if data.Cooldown and data.Cooldown > 0 then
			UI.Label(scroll, string.format(Strings.RaidCooldown, data.Cooldown), { TextSize = 13, TextColor3 = C.Danger, Size = UDim2.new(1, 0, 0, 20), LayoutOrder = 5, ZIndex = 13 })
		end
		local rb = UI.Button(scroll, "↻ " .. Strings.RaidRefresh, render, { Size = UDim2.new(1, -8, 0, 44), LayoutOrder = 50, Color = C.PanelDark, TextSize = 14 })
		rb.ZIndex = 13
		-- storico recente (senza identità)
		if raid.History and #raid.History > 0 then
			UI.Label(scroll, "Riepiloghi recenti", { Font = UI.Theme.FontBold, TextSize = 15, Size = UDim2.new(1, 0, 0, 24), LayoutOrder = 60, ZIndex = 13 })
			for i = #raid.History, math.max(1, #raid.History - 5), -1 do
				local h = raid.History[i]
				local text
				if h.Type == "won" then
					text = string.format("✔ Incursione riuscita · +%d ✦%s", h.Amount, h.Simulated and " (simulata)" or "")
				elseif h.Type == "failed" then
					text = string.format("✖ Incursione respinta · +%d ✦ partecipazione", h.Amount)
				elseif h.Type == "defended" then
					text = string.format("🛡 La tua difesa ha respinto un'incursione · bonus +%d ✦", h.Amount)
				else
					text = string.format("⚠ Hai subito un'incursione · -%d ✦ · consolazione +%d", h.Amount, h.Consolation or 0)
				end
				UI.Label(scroll, text, { TextSize = 13, Size = UDim2.new(1, 0, 0, 20), LayoutOrder = 60 + (#raid.History - i) + 1, ZIndex = 13 })
			end
		end
	end)
end

-- ───────────────────────── HUD in-raid ─────────────────────────

local function buildOverlay(screenGui)
	overlay = UI.Frame(screenGui, { Name = "RaidOverlay", BackgroundTransparency = 1, Visible = false, ZIndex = 30 })
	local top = UI.Frame(overlay, { BackgroundColor3 = C.PanelDark, BackgroundTransparency = 0.15, Size = UDim2.new(0, 560, 0, 84), Position = UDim2.new(0.5, 0, 0, 86), AnchorPoint = Vector2.new(0.5, 0), ZIndex = 31 })
	UI.Corner(top, UDim.new(0, 18))
	UI.Stroke(top, C.Danger, 2)
	titleLabel = UI.Label(top, "", { Size = UDim2.new(1, -24, 0, 24), Position = UDim2.fromOffset(12, 6), TextColor3 = C.TextOnDark, Font = UI.Theme.Font, TextSize = 18, ZIndex = 32 })
	objectiveLabel = UI.Label(top, "", { Size = UDim2.new(1, -24, 0, 22), Position = UDim2.fromOffset(12, 30), TextColor3 = C.Accent, Font = UI.Theme.FontBold, TextSize = 15, ZIndex = 32 })
	timerBar = UI.Progress(top, { Size = UDim2.new(1, -24, 0, 18), Position = UDim2.fromOffset(12, 58), FillColor = C.Success })
	timerBar.Frame.ZIndex = 32
	local abort = UI.Button(overlay, "✕ " .. Strings.PromptExitRaid, function()
		Net.Fire("RaidAbort")
	end, { Size = UDim2.fromOffset(220, 44), Position = UDim2.new(0.5, 0, 1, -20), AnchorPoint = Vector2.new(0.5, 1), Color = C.Danger, TextSize = 14 })
	abort.ZIndex = 32
	flash = UI.Frame(overlay, { BackgroundColor3 = Color3.new(1, 1, 1), BackgroundTransparency = 1, ZIndex = 29 })
	countdownLabel = UI.Label(overlay, "", { Size = UDim2.new(1, 0, 0, 120), Position = UDim2.new(0, 0, 0.35, 0), Font = UI.Theme.Font, TextSize = 96, TextColor3 = C.Accent, TextXAlignment = Enum.TextXAlignment.Center, ZIndex = 33, TextStrokeTransparency = 0.3 })
end

local function flashScreen(color, alpha, duration)
	flash.BackgroundColor3 = color
	flash.BackgroundTransparency = alpha
	TweenService:Create(flash, TweenInfo.new(duration or 0.6), { BackgroundTransparency = 1 }):Play()
end

local function showSummary(s)
	if summaryPanel then
		summaryPanel.Overlay:Destroy()
	end
	summaryPanel = UI.Panel(overlay.Parent, s.Success and ("✔ " .. Strings.RaidSuccess) or ("✖ " .. Strings.RaidFail), UDim2.new(0.5, 0, 0.6, 0))
	local content = summaryPanel.Content
	UI.List(content, Enum.FillDirection.Vertical, 8)
	UI.Padding(content, 8)
	local lines = {}
	if s.Test then
		table.insert(lines, Strings.RaidTestNote)
	end
	if s.Success then
		if not s.Test then
			table.insert(lines, string.format(Strings.RaidSummaryTake, s.Take) .. (s.Simulated and " (simulata, ricompensa ridotta)" or " → ora sono esposte: depositale!"))
		end
	else
		if s.Participation > 0 then
			table.insert(lines, string.format(Strings.RaidSummaryParticipation, s.Participation))
		end
	end
	if not s.Test then
		table.insert(lines, string.format(Strings.RaidSummaryMastery, s.Mastery))
	end
	table.insert(lines, string.format("Durata: %d s · checkpoint: %d", s.Duration, s.Checkpoints or 0))
	for _, f in ipairs(s.Feedback or {}) do
		table.insert(lines, "• " .. f)
	end
	for i, l in ipairs(lines) do
		UI.Label(content, l, { TextSize = 16, Size = UDim2.new(1, 0, 0, 26), LayoutOrder = i, ZIndex = 13 })
	end
	local b = UI.Button(content, Strings.Close, function()
		summaryPanel:Close()
	end, { Size = UDim2.new(1, 0, 0, 48), LayoutOrder = 99, Color = s.Success and C.Success or C.Info })
	b.ZIndex = 13
	summaryPanel:Open()
end

function RaidPanel.HandleEvent(name, payload)
	if name == "Start" then
		raidActive = true
		raidDuration = payload.Duration
		raidStart = os.clock() + (payload.Countdown or 0)
		overlay.Visible = true
		titleLabel.Text = string.format("%s · difficoltà %s%s", payload.TargetName, Format.Stars(payload.Difficulty or 1, 5), payload.Test and " · PROVA" or "")
		objectiveLabel.Text = Strings.RaidObjective1
		timerBar:Set(raidDuration, raidDuration, string.format(Strings.RaidTimer, raidDuration))
		-- conto alla rovescia
		task.spawn(function()
			for n = payload.Countdown or 3, 1, -1 do
				countdownLabel.Text = tostring(n)
				countdownLabel.TextTransparency = 0
				TweenService:Create(countdownLabel, TweenInfo.new(0.9), { TextTransparency = 1 }):Play()
				task.wait(1)
			end
			countdownLabel.Text = "VIA!"
			countdownLabel.TextTransparency = 0
			TweenService:Create(countdownLabel, TweenInfo.new(0.8), { TextTransparency = 1 }):Play()
		end)
	elseif name == "Go" then
		raidStart = os.clock()
	elseif name == "Collected" then
		objectiveLabel.Text = Strings.RaidObjective2
		flashScreen(C.Accent, 0.5, 0.5)
	elseif name == "Checkpoint" then
		flashScreen(C.Danger, 0.6, 0.5)
		Toast.Show(Strings.RaidCheckpoint .. (payload.Reason and (" (" .. payload.Reason .. ")") or ""), "warning")
	elseif name == "Spotted" then
		flashScreen(Color3.fromRGB(255, 250, 200), 0.3, 0.4)
	elseif name == "Dazzled" then
		flashScreen(Color3.new(1, 1, 1), 0.05, payload.Seconds or 3)
		Toast.Show(Strings.RaidDazzled, "warning")
	elseif name == "Bell" then
		Toast.Show("🔔 La campana del vento ha invertito le correnti!", "info")
	elseif name == "Summary" then
		raidActive = false
		overlay.Visible = false
		showSummary(payload)
	end
end

function RaidPanel.Init(screenGui)
	panel = UI.Panel(screenGui, "🌀 " .. Strings.RaidTitle)
	body = UI.Frame(panel.Content, { BackgroundTransparency = 1, ZIndex = 12 })
	panel.OnOpen = render
	buildOverlay(screenGui)
	task.spawn(function()
		while true do
			task.wait(0.1)
			if raidActive then
				local remaining = math.max(0, raidDuration - (os.clock() - raidStart))
				timerBar:Set(remaining, raidDuration, string.format(Strings.RaidTimer, math.ceil(remaining)))
				timerBar.Frame.Fill.BackgroundColor3 = remaining < 15 and C.Danger or (remaining < 40 and C.Accent or C.Success)
			end
		end
	end)
end

function RaidPanel.IsActive()
	return raidActive
end
function RaidPanel.Toggle()
	panel:Toggle()
end
function RaidPanel.Open()
	panel:Open()
end
function RaidPanel.Close()
	panel:Close()
end

return RaidPanel
