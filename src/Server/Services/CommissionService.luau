--!nonstrict
--[[
	CommissionService: 3 commissioni giornaliere pescate da categorie diverse in modo
	deterministico (giorno + userId), una sostituzione gratuita, riscossione idempotente.
	Il progresso deriva dalle statistiche giornaliere (StatsService).
]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Commissions = require(Shared.Catalog.Commissions)
local Cosmetics = require(Shared.Catalog.Cosmetics)
local TimeUtil = require(Shared.Util.TimeUtil)
local TableUtil = require(Shared.Util.TableUtil)
local Net = require(Shared.Util.Net)

local Registry = require(script.Parent.Parent.Registry)
local EventBus = require(script.Parent.Parent.EventBus)
local Guard = require(script.Parent.Parent.Util.Guard)

local CommissionService = {}

local function pick(profile, player, excludeIds, rng)
	local tier = Registry.Get("EconomyService").Tier(profile)
	local categories = table.clone(Config.Commissions.Categories)
	TableUtil.Shuffle(categories, rng)
	local used = {}
	for _, c in ipairs(profile.Commissions.List) do
		used[c.Category] = true
	end
	for _, cat in ipairs(categories) do
		if not used[cat] then
			local pool = TableUtil.Filter(Commissions.ByCategory(cat, tier), function(t)
				return not excludeIds[t.Id]
			end)
			if #pool > 0 then
				local t = pool[rng:NextInteger(1, #pool)]
				return { Id = t.Id, Category = t.Category, Claimed = false }
			end
		end
	end
	return nil
end

local function ensureDaily(player, profile)
	local key = TimeUtil.DayKey()
	if profile.Commissions.DayKey == key and #profile.Commissions.List == Config.Commissions.DailyCount then
		return
	end
	profile.Commissions = { DayKey = key, List = {}, RerollsUsed = 0 }
	local rng = Random.new(TimeUtil.Hash(key .. ":" .. player.UserId))
	local exclude = {}
	for _ = 1, Config.Commissions.DailyCount do
		local c = pick(profile, player, exclude, rng)
		if c then
			exclude[c.Id] = true
			table.insert(profile.Commissions.List, c)
		end
	end
end

-- Vista inviata al client
function CommissionService.View(player, profile)
	ensureDaily(player, profile)
	local daily = Registry.Get("StatsService").Daily(profile)
	local list = {}
	for i, c in ipairs(profile.Commissions.List) do
		local t = Commissions.ById[c.Id]
		if t then
			local progress = math.min(daily[t.Stat] or 0, t.Target)
			table.insert(list, {
				Index = i,
				Id = t.Id,
				Category = t.Category,
				Text = Commissions.Describe(t),
				Progress = progress,
				Target = t.Target,
				Reward = t.Reward,
				Claimed = c.Claimed,
				Complete = progress >= t.Target,
			})
		end
	end
	return {
		DayKey = profile.Commissions.DayKey,
		List = list,
		RerollAvailable = profile.Commissions.RerollsUsed < Config.Commissions.FreeRerollsPerDay,
		SecondsToReset = TimeUtil.SecondsToNextDay(),
	}
end

function CommissionService.Claim(player, index)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return false, Strings.Error
	end
	ensureDaily(player, profile)
	index = Guard.Int(index, 1, #profile.Commissions.List)
	local c = index and profile.Commissions.List[index]
	if not c then
		return false, Strings.Error
	end
	if c.Claimed then
		return false, Strings.CommissionClaimed
	end
	local t = Commissions.ById[c.Id]
	local daily = Registry.Get("StatsService").Daily(profile)
	if (daily[t.Stat] or 0) < t.Target then
		return false, "Commissione non completata"
	end
	local ledgerId = "comm:" .. profile.Commissions.DayKey .. ":" .. index .. ":" .. c.Id
	if profile.Ledger[ledgerId] then
		c.Claimed = true
		return false, Strings.CommissionClaimed
	end
	profile.Ledger[ledgerId] = true
	c.Claimed = true
	local eco = Registry.Get("EconomyService")
	eco.GrantSafe(player, profile, t.Reward.Sparks or 0, "commission")
	eco.GrantFragments(player, profile, t.Reward.Fragments, "commission")
	eco.GrantTokens(player, profile, Config.StyleTokens.PerCommission, "commission")
	profile.Pass.Points += Cosmetics.Pass.PointsPerCommission
	EventBus.Fire("CommissionClaimed", player, c.Id)
	Registry.Get("PlayerService").Sync(player, "Commissions", "Pass", "Fragments", "StyleTokens")
	Registry.Get("PlayerService").Sound(player, "Success")
	Registry.Get("PlayerService").Toast(player, string.format("Commissione completata! +%d scintille, +%d frammenti, +%d gettoni", t.Reward.Sparks or 0, t.Reward.Fragments or 0, Config.StyleTokens.PerCommission), "success")
	return true
end

function CommissionService.Reroll(player, index)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return false, Strings.Error
	end
	ensureDaily(player, profile)
	if profile.Commissions.RerollsUsed >= Config.Commissions.FreeRerollsPerDay then
		return false, Strings.CommissionRerollUsed
	end
	index = Guard.Int(index, 1, #profile.Commissions.List)
	local c = index and profile.Commissions.List[index]
	if not c or c.Claimed then
		return false, Strings.Error
	end
	local exclude = {}
	for _, other in ipairs(profile.Commissions.List) do
		exclude[other.Id] = true
	end
	-- rimuove temporaneamente per liberare la categoria
	local removed = table.remove(profile.Commissions.List, index)
	local rng = Random.new(TimeUtil.Hash(profile.Commissions.DayKey .. ":reroll:" .. player.UserId .. ":" .. os.time()))
	local replacement = pick(profile, player, exclude, rng)
	if not replacement then
		-- nessuna categoria nuova: pesca nella stessa categoria
		local tier = Registry.Get("EconomyService").Tier(profile)
		local pool = TableUtil.Filter(Commissions.ByCategory(removed.Category, tier), function(t)
			return not exclude[t.Id]
		end)
		if #pool > 0 then
			local t = pool[rng:NextInteger(1, #pool)]
			replacement = { Id = t.Id, Category = t.Category, Claimed = false }
		end
	end
	if not replacement then
		table.insert(profile.Commissions.List, index, removed)
		return false, "Nessuna commissione alternativa disponibile"
	end
	table.insert(profile.Commissions.List, index, replacement)
	profile.Commissions.RerollsUsed += 1
	Registry.Get("PlayerService").Sync(player, "Commissions")
	return true
end

function CommissionService.Init()
	Net.Function("GetCommissions").OnServerInvoke = function(player)
		local profile = Registry.Get("DataService").Get(player)
		if not profile then
			return nil
		end
		return CommissionService.View(player, profile)
	end
	Net.Function("ClaimCommission").OnServerInvoke = CommissionService.Claim
	Net.Function("RerollCommission").OnServerInvoke = CommissionService.Reroll
end

function CommissionService.Start()
	EventBus.On("ProfileLoaded", function(player, profile)
		ensureDaily(player, profile)
	end)
	-- aggiorna la vista quando cambiano le statistiche (coalescente nel PlayerService)
	EventBus.On("StatDelta", function(player)
		Registry.Get("PlayerService").Sync(player, "Commissions")
	end)
	-- rinnovo a mezzanotte UTC
	task.spawn(function()
		while true do
			task.wait(30)
			for player, profile in pairs(Registry.Get("DataService").GetAll()) do
				if profile.Commissions.DayKey ~= TimeUtil.DayKey() then
					ensureDaily(player, profile)
					Registry.Get("PlayerService").Sync(player, "Commissions")
					Registry.Get("PlayerService").Toast(player, "Nuove commissioni disponibili!", "info")
				end
			end
		end
	end)
end

return CommissionService
