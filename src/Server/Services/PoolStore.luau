--!nonstrict
--[[
	PoolStore: archivio condiviso tra server delle "istantanee" dei vivai pubblicati.
	Serve a: matchmaking asincrono delle incursioni (nessuna attesa che il proprietario sia online),
	galleria, codici layout. Include la "inbox" degli esiti di raid per i proprietari offline.
	Bucket per fascia: chiave "tier_<n>" -> { Entries = { [userId] = snapshot } }.
]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local Store = require(script.Parent.Parent.Util.Store)
local Logger = require(script.Parent.Parent.Util.Logger)

local PoolStore = {}
local poolStore, inboxStore
local cache = {} -- tier -> { Time, Entries }
local CACHE_SECONDS = 45

function PoolStore.Init()
	poolStore = Store.new(Config.RaidPoolStoreName)
	inboxStore = Store.new(Config.RaidInboxStoreName)
end

local function bucketKey(tier)
	return "tier_" .. tier
end

local function trim(entries)
	local list = {}
	for id, e in pairs(entries) do
		table.insert(list, { id = id, t = e.Updated or 0 })
	end
	if #list <= Config.Raid.PoolBucketLimit then
		return entries
	end
	table.sort(list, function(a, b)
		return a.t > b.t
	end)
	local keep = {}
	for i = 1, Config.Raid.PoolBucketLimit do
		keep[list[i].id] = entries[list[i].id]
	end
	return keep
end

function PoolStore.Upsert(snapshot)
	local key = bucketKey(snapshot.Tier)
	local id = tostring(snapshot.UserId)
	local ok, result = poolStore:Update(key, function(old)
		old = old or { Entries = {} }
		old.Entries = old.Entries or {}
		local existing = old.Entries[id]
		if existing then
			snapshot.Likes = math.max(existing.Likes or 0, snapshot.Likes or 0)
		end
		old.Entries[id] = snapshot
		old.Entries = trim(old.Entries)
		return old
	end)
	if ok then
		cache[snapshot.Tier] = { Time = os.clock(), Entries = result and result.Entries or {} }
	end
	return ok
end

function PoolStore.Remove(userId, tier)
	local id = tostring(userId)
	poolStore:Update(bucketKey(tier), function(old)
		if not old or not old.Entries or not old.Entries[id] then
			return nil
		end
		old.Entries[id] = nil
		return old
	end)
	if cache[tier] then
		cache[tier].Entries[id] = nil
	end
end

function PoolStore.GetBucket(tier, force)
	local c = cache[tier]
	if c and not force and os.clock() - c.Time < CACHE_SECONDS then
		return c.Entries
	end
	local ok, data = poolStore:Get(bucketKey(tier))
	local entries = (ok and data and data.Entries) or (c and c.Entries) or {}
	cache[tier] = { Time = os.clock(), Entries = entries }
	return entries
end

function PoolStore.AllEntries()
	local out = {}
	for tier = 1, #Config.Raid.TierTakeCaps do
		for id, e in pairs(PoolStore.GetBucket(tier)) do
			out[id] = e
		end
	end
	return out
end

function PoolStore.FindByUserId(userId)
	local id = tostring(userId)
	for tier = 1, #Config.Raid.TierTakeCaps do
		local e = PoolStore.GetBucket(tier)[id]
		if e then
			return e, tier
		end
	end
	return nil
end

-- Modifica atomica di una voce (es. dopo un raid riuscito contro un proprietario offline)
function PoolStore.ModifyEntry(userId, tier, fn)
	local id = tostring(userId)
	local ok, result = poolStore:Update(bucketKey(tier), function(old)
		if not old or not old.Entries or not old.Entries[id] then
			return nil
		end
		local e = old.Entries[id]
		fn(e)
		e.Updated = e.Updated or os.time()
		return old
	end)
	if ok and result and result.Entries then
		cache[tier] = { Time = os.clock(), Entries = result.Entries }
	end
	return ok
end

-- ───────────────────────── inbox esiti raid ─────────────────────────

function PoolStore.PushInbox(userId, item)
	local ok = inboxStore:Update("inbox_" .. userId, function(old)
		old = old or { Items = {} }
		table.insert(old.Items, item)
		while #old.Items > Config.Raid.InboxLimit do
			table.remove(old.Items, 1)
		end
		return old
	end)
	if not ok then
		Logger.Warn("Pool", "Inbox non aggiornata per", userId)
	end
	return ok
end

-- Preleva e svuota gli elementi (restituisce la lista)
function PoolStore.DrainInbox(userId)
	local drained = {}
	local ok = inboxStore:Update("inbox_" .. userId, function(old)
		if not old or not old.Items or #old.Items == 0 then
			return nil
		end
		drained = old.Items
		return { Items = {} }
	end)
	if not ok then
		return {}
	end
	return drained
end

function PoolStore.IsMock()
	return poolStore:IsMock()
end

return PoolStore
