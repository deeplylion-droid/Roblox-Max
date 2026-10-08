--!nonstrict
-- Bus di eventi interno del server: i servizi reagiscono senza dipendere l'uno dall'altro.
local Signal = require(game:GetService("ReplicatedStorage").Shared.Util.Signal)

local EventBus = { _signals = {} }

function EventBus.Get(name)
	local s = EventBus._signals[name]
	if not s then
		s = Signal.new()
		EventBus._signals[name] = s
	end
	return s
end

function EventBus.Fire(name, ...)
	EventBus.Get(name):Fire(...)
end

function EventBus.On(name, fn)
	return EventBus.Get(name):Connect(fn)
end

--[[
	Eventi usati:
	ProfileLoaded(player, profile)         ProfileReleasing(player, profile)
	SparksCollected(player, amount)        SparksDeposited(player, amount)
	SparksSpent(player, amount, reason)    CreaturePlaced(player, uid, moved)
	CreatureUnlocked(player, creatureId)   VariantUnlocked(player, creatureId, variantId)
	LayoutPublished(player, moduleCount)   LayoutTested(player)
	DecorationPlaced(player, decoId)       RaidCompleted(player, summary)
	RaidDefended(player, amount)           RaidLost(player, amount)
	Visited(player, key)                   Liked(player, key)
	DemoVisited(player)                    CommissionClaimed(player, templateId)
	AlbumMilestone(player, milestoneId)    MasteryTier(player, track, tier)
	TutorialStep(player, step)             TutorialCompleted(player)
	StatDelta(player, statName, delta)     ModuleUnlocked(player, moduleId)
]]

return EventBus
