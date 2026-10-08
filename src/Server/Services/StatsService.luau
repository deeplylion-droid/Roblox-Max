--!nonstrict
--[[
	StatsService: contatori giornalieri/settimanali usati da commissioni, bozzoli e sfide
	settimanali. Converte gli eventi del bus in statistiche.
]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local TimeUtil = require(Shared.Util.TimeUtil)

local Registry = require(script.Parent.Parent.Registry)
local EventBus = require(script.Parent.Parent.EventBus)

local Stats = {}

local function ensureDay(profile)
	local key = TimeUtil.DayKey()
	if profile.DailyStats.DayKey ~= key then
		profile.DailyStats = { DayKey = key }
	end
	return profile.DailyStats
end

local function ensureWeek(profile)
	local w = TimeUtil.WeekIndex()
	if profile.WeeklyStats.WeekIndex ~= w then
		profile.WeeklyStats = { WeekIndex = w }
	end
	return profile.WeeklyStats
end

function Stats.Daily(profile)
	return ensureDay(profile)
end

function Stats.Weekly(profile)
	return ensureWeek(profile)
end

-- Incrementa una statistica giornaliera (e settimanale con prefisso "Weekly")
function Stats.Add(player, statName, delta)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return
	end
	delta = delta or 1
	local d = ensureDay(profile)
	d[statName] = (d[statName] or 0) + delta
	EventBus.Fire("StatDelta", player, statName, delta, d[statName])
end

function Stats.Max(player, statName, value)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return
	end
	local d = ensureDay(profile)
	if (d[statName] or 0) < value then
		d[statName] = value
		EventBus.Fire("StatDelta", player, statName, value, value)
	end
end

function Stats.AddWeekly(player, statName, delta)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return
	end
	local w = ensureWeek(profile)
	w[statName] = (w[statName] or 0) + (delta or 1)
	EventBus.Fire("WeeklyStatDelta", player, statName, w[statName])
end

function Stats.Init() end

function Stats.Start()
	EventBus.On("SparksCollected", function(player, amount, manual)
		Stats.Add(player, "Collected", amount)
		if manual then
			Stats.Add(player, "CollectActions", 1)
		end
	end)
	EventBus.On("SparksDeposited", function(player, amount)
		Stats.Add(player, "Deposited", amount)
		Stats.AddWeekly(player, "WeeklyDeposited", amount)
	end)
	EventBus.On("LayoutPublished", function(player, moduleCount)
		Stats.Add(player, "LayoutsPublished", 1)
		Stats.Max(player, "LayoutModulesMax", moduleCount)
		Stats.AddWeekly(player, "WeeklyLayouts", 1)
	end)
	EventBus.On("LayoutTested", function(player)
		Stats.Add(player, "LayoutTests", 1)
	end)
	EventBus.On("DecorationPlaced", function(player)
		Stats.Add(player, "DecorationsPlaced", 1)
	end)
	EventBus.On("CreaturePlaced", function(player, uid, moved)
		if moved then
			Stats.Add(player, "CreaturesMoved", 1)
		end
	end)
	EventBus.On("Visited", function(player)
		Stats.Add(player, "Visits", 1)
	end)
	EventBus.On("Liked", function(player)
		Stats.Add(player, "Likes", 1)
	end)
	EventBus.On("DemoVisited", function(player)
		Stats.Add(player, "DemoVisits", 1)
	end)
	EventBus.On("RaidCompleted", function(player, summary)
		if summary.Test then
			return
		end
		Stats.Add(player, "RaidsCompleted", 1)
		Stats.AddWeekly(player, "WeeklyRaids", 1)
		if summary.Success then
			Stats.Add(player, "RaidsWon", 1)
			if summary.Checkpoints == 0 then
				Stats.Add(player, "RaidsClean", 1)
			end
		end
	end)
	EventBus.On("CommissionClaimed", function(player)
		Stats.AddWeekly(player, "WeeklyCommissions", 1)
	end)
end

return Stats
