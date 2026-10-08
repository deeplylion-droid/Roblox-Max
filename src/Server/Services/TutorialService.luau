--!nonstrict
--[[
	TutorialService: 5 passi (posiziona, raccogli+deposita, difesa, incursione guidata,
	decorazione gratuita). Avanza osservando gli eventi di gioco. Saltabile solo dopo la prima
	volta (GDD §7). Ricompense idempotenti.
]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Net = require(Shared.Util.Net)

local Registry = require(script.Parent.Parent.Registry)
local EventBus = require(script.Parent.Parent.EventBus)
local Guard = require(script.Parent.Parent.Util.Guard)

local TutorialService = {}

local function setStep(player, profile, step)
	profile.Tutorial.Step = step
	EventBus.Fire("TutorialStep", player, step)
	Registry.Get("AnalyticsService").Funnel(player, "tutorial", step)
	Registry.Get("PlayerService").Sync(player, "Tutorial")
	Net.Event("TutorialStep"):FireClient(player, step, profile.Tutorial.Active)
end

local function complete(player, profile)
	profile.Tutorial.Active = false
	profile.Tutorial.CompletedOnce = true
	profile.Tutorial.Step = Config.Tutorial.Steps + 1
	EventBus.Fire("TutorialCompleted", player)
	Registry.Get("AnalyticsService").Log(player, "tutorial_complete", profile.Stats.PlayTime)
	Registry.Get("PlayerService").Sync(player, "Tutorial")
	Registry.Get("PlayerService").Toast(player, Strings.TutorialDone, "success")
	Net.Event("TutorialStep"):FireClient(player, profile.Tutorial.Step, false)
end

local function advanceIf(player, step)
	local profile = Registry.Get("DataService").Get(player)
	if not profile or not profile.Tutorial.Active then
		return
	end
	if profile.Tutorial.Step == step then
		setStep(player, profile, step + 1)
	end
end

-- Passo 5: scelta di una decorazione gratuita
function TutorialService.ChooseDecoration(player, decoId)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return false, Strings.Error
	end
	decoId = Guard.Str(decoId, 32)
	if not decoId or not table.find(Config.Tutorial.FreeDecorationChoices, decoId) then
		return false, Strings.Error
	end
	if profile.Tutorial.Step ~= 5 or not profile.Tutorial.Active then
		return false, Strings.Error
	end
	if not profile.Ledger["tutorial_deco"] then
		profile.Ledger["tutorial_deco"] = true
		Registry.Get("EconomyService").GrantDecoration(player, profile, decoId)
		Registry.Get("PlayerService").Toast(player, "Decorazione ottenuta! Posizionala da Costruisci → Decorazioni", "success")
	end
	complete(player, profile)
	return true
end

function TutorialService.Skip(player)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return false, Strings.Error
	end
	if not profile.Tutorial.CompletedOnce then
		return false, "Il tutorial si può saltare dalla seconda volta"
	end
	profile.Tutorial.Active = false
	profile.Tutorial.Step = Config.Tutorial.Steps + 1
	Registry.Get("PlayerService").Sync(player, "Tutorial")
	Net.Event("TutorialStep"):FireClient(player, profile.Tutorial.Step, false)
	return true
end

function TutorialService.Replay(player)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return false
	end
	profile.Tutorial.Active = true
	setStep(player, profile, 1)
	return true
end

function TutorialService.Init()
	Net.Function("TutorialAdvance").OnServerInvoke = function(player, step, payload)
		step = Guard.Int(step, 0, Config.Tutorial.Steps)
		if step == 5 then
			return TutorialService.ChooseDecoration(player, payload)
		end
		if step == 0 then
			return TutorialService.Replay(player)
		end
		return false, Strings.Error
	end
	Net.Function("TutorialSkip").OnServerInvoke = TutorialService.Skip
end

function TutorialService.Start()
	EventBus.On("ProfileLoaded", function(player, profile)
		if profile.Tutorial.Active then
			task.delay(1, function()
				if player.Parent then
					Net.Event("TutorialStep"):FireClient(player, profile.Tutorial.Step, true)
				end
			end)
		end
	end)
	EventBus.On("CreaturePlaced", function(player)
		advanceIf(player, 1)
	end)
	EventBus.On("SparksDeposited", function(player)
		advanceIf(player, 2)
	end)
	EventBus.On("LayoutPublished", function(player, count)
		if count >= 1 then
			advanceIf(player, 3)
		end
	end)
	EventBus.On("RaidCompleted", function(player, summary)
		advanceIf(player, 4)
	end)
end

return TutorialService
