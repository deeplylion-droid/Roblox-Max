--!nonstrict
--[[
	CocoonService: ottenimento deterministico delle creature. Il giocatore sceglie una famiglia,
	vede in anteprima la creatura che otterrà (la prossima mancante) e l'obiettivo di sblocco,
	paga in frammenti e completa l'obiettivo giocando. Nessuna casualità, nessun doppione.
]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Creatures = require(Shared.Catalog.Creatures)
local TimeUtil = require(Shared.Util.TimeUtil)
local Net = require(Shared.Util.Net)

local Registry = require(script.Parent.Parent.Registry)
local EventBus = require(script.Parent.Parent.EventBus)
local Guard = require(script.Parent.Parent.Util.Guard)

local CocoonService = {}

-- Obiettivi possibili, scalati per ordine di sblocco (1..4) della creatura
local GOALS = {
	{ Id = "collect", Text = "Raccogli %d scintille", Event = "SparksCollected", Base = 250 },
	{ Id = "deposit", Text = "Deposita %d scintille", Event = "SparksDeposited", Base = 200 },
	{ Id = "commissions", Text = "Completa %d commissioni", Event = "CommissionClaimed", Base = 1, Step = 1 },
	{ Id = "raids", Text = "Completa %d incursioni (anche simulate)", Event = "RaidCompleted", Base = 1, Step = 1 },
}

local function goalFor(family, creature, userId)
	local rng = Random.new(TimeUtil.Hash(family .. creature.Id .. userId))
	local g = GOALS[rng:NextInteger(1, #GOALS)]
	local order = creature.UnlockOrder
	local target
	if g.Step then
		target = g.Base + (order - 1) * g.Step
	else
		target = math.floor(g.Base * (1 + (order - 1) * 0.6))
	end
	return { Id = g.Id, Text = string.format(g.Text, target), Target = target, Event = g.Event }
end

function CocoonService.Preview(player, family)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return nil
	end
	family = Guard.Str(family, 16)
	if not family or not Creatures.ByFamily[family] then
		return nil
	end
	local nextC = Creatures.NextMissingInFamily(family, profile.OwnedCreatureIds)
	if not nextC then
		return { Family = family, Complete = true }
	end
	local goal = goalFor(family, nextC, player.UserId)
	return {
		Family = family,
		CreatureId = nextC.Id,
		CreatureName = nextC.Name,
		Rarity = nextC.Rarity,
		Goal = goal,
		Cost = Config.Cocoon.FragmentCost,
		CanAfford = profile.Fragments >= Config.Cocoon.FragmentCost,
	}
end

function CocoonService.Begin(player, family)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return false, Strings.Error
	end
	if profile.Cocoon.Active then
		return false, "Hai già un bozzolo attivo"
	end
	local preview = CocoonService.Preview(player, family)
	if not preview or preview.Complete then
		return false, Strings.CocoonFamilyComplete
	end
	if profile.Fragments < Config.Cocoon.FragmentCost then
		return false, Strings.CocoonNoFragments
	end
	profile.Fragments -= Config.Cocoon.FragmentCost
	profile.Cocoon.Active = {
		Family = family,
		CreatureId = preview.CreatureId,
		GoalId = preview.Goal.Id,
		GoalText = preview.Goal.Text,
		Event = preview.Goal.Event,
		Target = preview.Goal.Target,
		Progress = 0,
		StartedAt = os.time(),
	}
	Registry.Get("PlayerService").Sync(player, "Cocoon", "Fragments")
	Registry.Get("PlayerService").Sound(player, "Chime")
	Registry.Get("PlayerService").Toast(player, string.format("Bozzolo %s avviato: %s", Strings.Family[family], preview.Goal.Text), "info")
	return true
end

local function progress(player, eventName, amount)
	local profile = Registry.Get("DataService").Get(player)
	local active = profile and profile.Cocoon.Active
	if not active or active.Event ~= eventName then
		return
	end
	active.Progress = math.min(active.Target, active.Progress + (amount or 1))
	if active.Progress >= active.Target then
		local creatureId = active.CreatureId
		profile.Cocoon.Active = nil
		profile.Cocoon.Completed += 1
		-- se nel frattempo la creatura è stata ottenuta altrove, passa alla successiva mancante
		if profile.OwnedCreatureIds[creatureId] then
			local nextC = Creatures.NextMissingInFamily(active.Family, profile.OwnedCreatureIds)
			creatureId = nextC and nextC.Id or nil
		end
		if creatureId then
			Registry.Get("EconomyService").GrantCreature(player, profile, creatureId, true)
			local def = Creatures.Get(creatureId)
			Registry.Get("PlayerService").Sound(player, "Success")
			Registry.Get("PlayerService").Toast(player, string.format(Strings.CocoonComplete, def.Name), "success")
			Net.Event("RaidEvent"):FireClient(player, "CocoonHatched", { CreatureId = creatureId })
		end
	end
	Registry.Get("PlayerService").Sync(player, "Cocoon")
end

function CocoonService.Init()
	Net.Function("GetCocoonPreview").OnServerInvoke = CocoonService.Preview
	Net.Function("StartCocoon").OnServerInvoke = CocoonService.Begin
end

function CocoonService.Start()
	EventBus.On("SparksCollected", function(player, amount)
		progress(player, "SparksCollected", amount)
	end)
	EventBus.On("SparksDeposited", function(player, amount)
		progress(player, "SparksDeposited", amount)
	end)
	EventBus.On("CommissionClaimed", function(player)
		progress(player, "CommissionClaimed", 1)
	end)
	EventBus.On("RaidCompleted", function(player, summary)
		if not summary.Test then
			progress(player, "RaidCompleted", 1)
		end
	end)
end

return CocoonService
