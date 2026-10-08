--!nonstrict
-- Opzioni: audio, effetti ridotti, deposito automatico, privacy galleria, tutorial.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Strings = require(Shared.Strings)
local Net = require(Shared.Util.Net)
local UI = require(script.Parent.UI)
local Toast = require(script.Parent.Toast)
local State = require(script.Parent.Parent.Controllers.State)
local Audio = require(script.Parent.Parent.Controllers.Audio)

local SettingsPanel = {}
local C = UI.Colors
local panel, body
SettingsPanel.ReducedEffectsChanged = nil -- callback impostata da Main

local function render()
	body:ClearAllChildren()
	local scroll = UI.Scroll(body)
	UI.List(scroll, Enum.FillDirection.Vertical, 8)
	UI.Padding(scroll, 6)
	local s = State.Get("Settings") or {}
	local function toggle(key, text, order, extra)
		UI.Toggle(scroll, text, s[key], function(v)
			Net.Fire("SetSetting", key, v)
			if extra then
				extra(v)
			end
		end, order)
	end
	toggle("AudioEnabled", "🔊 " .. Strings.SettingsAudio, 1, function(v)
		Audio.SetEnabled(v)
	end)
	toggle("ReducedEffects", "🌫 " .. Strings.SettingsReducedFx, 2, function(v)
		if SettingsPanel.ReducedEffectsChanged then
			SettingsPanel.ReducedEffectsChanged(v)
		end
	end)
	if State.Get("AutoDepositUnlocked") then
		toggle("AutoDeposit", "🔒 " .. Strings.SettingsAutoDeposit, 3)
	else
		local row = UI.Card(scroll, { Size = UDim2.new(1, 0, 0, 56), LayoutOrder = 3 })
		UI.Label(row, "🔒 " .. Strings.SettingsAutoDeposit .. "  —  " .. Strings.SettingsAutoDepositLocked, { Size = UDim2.new(1, -20, 1, 0), Position = UDim2.fromOffset(14, 0), ZIndex = 13, TextColor3 = C.TextMuted })
	end
	toggle("HideProfile", "🙈 " .. Strings.SettingsHideProfile, 4)
	toggle("ShowName", "🏷 " .. Strings.SettingsShowName, 5)
	local tut = State.Get("Tutorial") or {}
	local b = UI.Button(scroll, "🎓 " .. Strings.SettingsReplayTutorial, function()
		local ok = Net.Invoke("TutorialAdvance", 0)
		if ok then
			panel:Close()
		end
	end, { Size = UDim2.new(1, 0, 0, 48), LayoutOrder = 6, Color = C.Info })
	b.ZIndex = 13
	if tut.Active then
		local sk = UI.Button(scroll, "⏭ " .. Strings.TutorialSkip .. (tut.CompletedOnce and "" or " (disponibile dalla seconda volta)"), function()
			local ok, msg = Net.Invoke("TutorialSkip")
			if not ok then
				Toast.Show(msg or Strings.Error, "warning")
			end
		end, { Size = UDim2.new(1, 0, 0, 48), LayoutOrder = 7, Color = tut.CompletedOnce and C.AccentDark or C.TextMuted })
		sk.ZIndex = 13
	end
	UI.Label(scroll, "Controlli: WASD/levetta per muoverti · E per interagire · F raccogli tutto · G deposita · B costruisci · R ruota · X modalità modifica · N incursione · C commissioni · V album · K bozzoli · L galleria · P negozio · O opzioni", { TextSize = 12, TextColor3 = C.TextMuted, Size = UDim2.new(1, 0, 0, 60), LayoutOrder = 8, ZIndex = 13 })
	local info = State.Get("ServerInfo")
	if info and info.Mock then
		UI.Label(scroll, "⚠ Modalità Studio senza DataStore: i progressi non vengono salvati. Attiva «Enable Studio Access to API Services».", { TextSize = 12, TextColor3 = C.Danger, Size = UDim2.new(1, 0, 0, 40), LayoutOrder = 9, ZIndex = 13 })
	end
end

function SettingsPanel.Init(screenGui)
	panel = UI.Panel(screenGui, "⚙ " .. Strings.SettingsTitle, UDim2.new(0.6, 0, 0.8, 0))
	body = UI.Frame(panel.Content, { BackgroundTransparency = 1, ZIndex = 12 })
	panel.OnOpen = render
	State.Observe("Settings", function(s)
		Audio.SetEnabled(s.AudioEnabled ~= false)
		if SettingsPanel.ReducedEffectsChanged then
			SettingsPanel.ReducedEffectsChanged(s.ReducedEffects == true)
		end
	end)
end

function SettingsPanel.Toggle()
	panel:Toggle()
end
function SettingsPanel.Open()
	panel:Open()
end
function SettingsPanel.Close()
	panel:Close()
end

return SettingsPanel
