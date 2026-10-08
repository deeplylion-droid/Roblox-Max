--!nonstrict
--[[
	GalleryService: pubblicazione delle istantanee del vivaio nel pool condiviso, galleria
	con «mi piace» (senza effetti sulla produzione), visite (al plot online o a una copia
	istanziata se il proprietario è offline), ricompense di visita con tetto basso, codici layout.
]]
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Defenses = require(Shared.Catalog.Defenses)
local LayoutValidator = require(Shared.LayoutValidator)
local PlotBuilder = require(Shared.Models.PlotBuilder)
local TimeUtil = require(Shared.Util.TimeUtil)
local Net = require(Shared.Util.Net)

local Registry = require(script.Parent.Parent.Registry)
local EventBus = require(script.Parent.Parent.EventBus)
local Guard = require(script.Parent.Parent.Util.Guard)
local RateLimiter = require(script.Parent.Parent.Util.RateLimiter)
local PoolStore = require(script.Parent.PoolStore)
local ArenaPool = require(script.Parent.Parent.World.ArenaPool)

local Gallery = {}
local dirty = {} -- player -> timestamp della richiesta
local lastPublished = {} -- player -> tier
local visits = {} -- player -> { Slot, Plot, Key }
local limiter = RateLimiter.new(8, 1)

local ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

local function encodeCode(userId)
	local n = userId
	local s = ""
	repeat
		local d = n % 32
		s = ALPHABET:sub(d + 1, d + 1) .. s
		n = n // 32
	until n == 0
	return "NV-" .. s
end

local function decodeCode(code)
	code = code:upper():gsub("^NV%-", ""):gsub("[^0-9A-Z]", "")
	if #code == 0 then
		return nil
	end
	local n = 0
	for i = 1, #code do
		local idx = ALPHABET:find(code:sub(i, i), 1, true)
		if not idx then
			return nil
		end
		n = n * 32 + (idx - 1)
	end
	return n
end

Gallery.EncodeCode = encodeCode

-- Istantanea per il pool (niente dati privati; nome solo se consentito)
function Gallery.BuildSnapshot(player, profile)
	local eco = Registry.Get("EconomyService")
	local creatures = {}
	for _, c in pairs(profile.Creatures) do
		if c.x ~= nil then
			table.insert(creatures, { Id = c.Id, Variant = c.Variant or "base", x = c.x, z = c.z })
		end
	end
	local result = LayoutValidator.Validate(profile.LastValidLayout, {})
	local now = os.time()
	local recentLosses = {}
	for _, t in ipairs(profile.Raid.LossTimestamps) do
		if now - t < Config.Raid.LossWindowSeconds then
			table.insert(recentLosses, t)
		end
	end
	return {
		UserId = player.UserId,
		Name = profile.Settings.ShowName and player.DisplayName or nil,
		Tier = eco.Tier(profile),
		Updated = now,
		Published = profile.Gallery.Published and not profile.Settings.HideProfile,
		Hidden = profile.Settings.HideProfile,
		Layout = profile.LastValidLayout,
		LayoutVersion = profile.LayoutVersion,
		Difficulty = result.Difficulty or 0,
		Stars = LayoutValidator.DifficultyStars(result.Difficulty or 0),
		Exposed = eco.ExposedTotal(profile),
		ShieldUntil = profile.Raid.ShieldUntil,
		LossTs = recentLosses,
		Protected = Registry.Get("PlayerService").HasNewPlayerShield(profile),
		Creatures = creatures,
		Decorations = profile.Decorations.Placed,
		Skin = profile.Cosmetics.Equipped.skin,
		Nameplate = profile.Cosmetics.Equipped.nameplate,
		Likes = profile.Gallery.Likes,
		VaultLevel = profile.Sparks.VaultLevel,
		ShareCode = encodeCode(player.UserId),
	}
end

function Gallery.Publish(player)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return
	end
	if profile.Gallery.ShareCode == "" then
		profile.Gallery.ShareCode = encodeCode(player.UserId)
		Registry.Get("PlayerService").Sync(player, "Gallery")
	end
	-- un vivaio entra nel pool quando ha pubblicato almeno un layout (anche vuoto va bene) e non è protetto
	profile.Gallery.Published = profile.LayoutVersion > 0
	local snapshot = Gallery.BuildSnapshot(player, profile)
	local prevTier = lastPublished[player]
	if prevTier and prevTier ~= snapshot.Tier then
		PoolStore.Remove(player.UserId, prevTier)
	end
	lastPublished[player] = snapshot.Tier
	PoolStore.Upsert(snapshot)
	-- allinea i «mi piace» ricevuti mentre eravamo offline
	local entry = PoolStore.FindByUserId(player.UserId)
	if entry and (entry.Likes or 0) > profile.Gallery.Likes then
		profile.Gallery.Likes = entry.Likes
		Registry.Get("PlayerService").Sync(player, "Gallery")
	end
end

function Gallery.MarkDirty(player)
	dirty[player] = os.clock()
end

-- ───────────────────────── vista galleria ─────────────────────────

local function entryView(e, viewer, profile)
	local dayKey = TimeUtil.DayKey()
	local key = "u_" .. e.UserId
	return {
		Key = key,
		Name = e.Name or "Vivaio anonimo",
		Likes = e.Likes or 0,
		Stars = e.Stars or 1,
		Creatures = #(e.Creatures or {}),
		Modules = #((e.Layout and e.Layout.Modules) or {}),
		Skin = e.Skin,
		Nameplate = e.Nameplate,
		ShareCode = e.ShareCode or encodeCode(e.UserId),
		LikedByMe = profile.Gallery.LikesGiven[key] == dayKey,
		IsMine = e.UserId == viewer.UserId,
		Online = Players:GetPlayerByUserId(e.UserId) ~= nil,
	}
end

function Gallery.GetGallery(player)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return nil
	end
	if not limiter:Allow(player.UserId .. ":gallery") then
		return nil
	end
	local entries = PoolStore.AllEntries()
	-- giocatori online in questo server sempre aggiornati
	for other, otherProfile in pairs(Registry.Get("DataService").GetAll()) do
		if otherProfile.LayoutVersion > 0 then
			entries[tostring(other.UserId)] = Gallery.BuildSnapshot(other, otherProfile)
		end
	end
	local list = {}
	for _, e in pairs(entries) do
		if e.Published and not e.Hidden then
			table.insert(list, entryView(e, player, profile))
		end
	end
	table.sort(list, function(a, b)
		if a.Likes == b.Likes then
			return a.Name < b.Name
		end
		return a.Likes > b.Likes
	end)
	while #list > Config.Gallery.ListLimit do
		table.remove(list)
	end
	local dayKey = TimeUtil.DayKey()
	local visitsToday = (profile.Gallery.VisitDay == dayKey) and (profile.Gallery.VisitsToday or 0) or 0
	return { List = list, VisitsToday = visitsToday, VisitsMax = Config.Gallery.VisitRewardsPerDay, MyCode = encodeCode(player.UserId), Published = profile.Gallery.Published }
end

-- ───────────────────────── visite ─────────────────────────

local function parseKey(key)
	key = Guard.Str(key, 32)
	if not key then
		return nil
	end
	local id = key:match("^u_(%d+)$")
	return id and tonumber(id)
end

local function grantVisitReward(player, profile)
	local dayKey = TimeUtil.DayKey()
	if profile.Gallery.VisitDay ~= dayKey then
		profile.Gallery.VisitDay = dayKey
		profile.Gallery.VisitsToday = 0
	end
	if profile.Gallery.VisitsToday < Config.Gallery.VisitRewardsPerDay then
		profile.Gallery.VisitsToday += 1
		Registry.Get("EconomyService").GrantSafe(player, profile, Config.Gallery.VisitRewardSparks, "visit")
		Registry.Get("PlayerService").Toast(player, string.format(Strings.GalleryVisitReward, Config.Gallery.VisitRewardSparks, profile.Gallery.VisitsToday, Config.Gallery.VisitRewardsPerDay), "success")
		Registry.Get("PlayerService").Sync(player, "Gallery")
	end
end

function Gallery.Visit(player, key)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return false, Strings.Error
	end
	if not limiter:Allow(player.UserId .. ":visit", 2) then
		return false, Strings.TooFast
	end
	local userId = parseKey(key)
	if not userId or userId == player.UserId then
		return false, Strings.Error
	end
	if Registry.Get("PlotService").Location(player) == "raid" then
		return false, "Sei in un'incursione"
	end
	Gallery.EndVisit(player)
	-- proprietario online qui: visita diretta al suo plot
	local owner, entry = Registry.Get("PlotService").FindByUserId(userId)
	if owner and entry then
		local ownerProfile = Registry.Get("DataService").Get(owner)
		if ownerProfile and ownerProfile.Settings.HideProfile then
			return false, Strings.GalleryHidden
		end
		local char = player.Character
		if char and char.PrimaryPart then
			char:PivotTo(entry.Plot:EntranceCFrame())
		end
		Registry.Get("PlotService").SetLocation(player, "visit")
		visits[player] = { Key = key, Live = true }
		EventBus.Fire("Visited", player, key)
		grantVisitReward(player, profile)
		return true
	end
	local snapshot = PoolStore.FindByUserId(userId)
	if not snapshot or snapshot.Hidden or not snapshot.Published then
		return false, Strings.GalleryHidden
	end
	local slot = ArenaPool.Acquire("visit")
	if not slot then
		return false, "Troppe visite in corso, riprova tra poco"
	end
	local creatures = {}
	for i, c in ipairs(snapshot.Creatures or {}) do
		table.insert(creatures, { Uid = "v" .. i, Id = c.Id, Variant = c.Variant, x = c.x, z = c.z, Buffer = 0 })
	end
	local plot = PlotBuilder.Build(slot.Folder, slot.Origin, {
		Creatures = creatures,
		Layout = snapshot.Layout,
		Decorations = snapshot.Decorations,
		Skin = snapshot.Skin,
		OwnerName = snapshot.Name or "Vivaio anonimo",
		Nameplate = snapshot.Nameplate ~= "plate_nessuna" and snapshot.Nameplate or nil,
		Exposed = snapshot.Exposed or 0,
		Vault = 0,
		VaultCap = Config.Vault.Capacities[snapshot.VaultLevel or 1],
	}, "visit")
	plot:SetVault(0, Config.Vault.Capacities[snapshot.VaultLevel or 1])
	if plot.VaultLabel then
		plot.VaultLabel.Text = "🔒 al sicuro"
	end
	local char = player.Character
	if char and char.PrimaryPart then
		char:PivotTo(plot:SpawnCFrame())
	end
	Registry.Get("PlotService").SetLocation(player, "visit")
	visits[player] = { Key = key, Slot = slot, Plot = plot }
	EventBus.Fire("Visited", player, key)
	grantVisitReward(player, profile)
	-- fine automatica dopo 4 minuti
	task.delay(240, function()
		local v = visits[player]
		if v and v.Slot == slot then
			Gallery.EndVisit(player)
			Registry.Get("PlotService").TeleportHome(player)
		end
	end)
	return true
end

function Gallery.EndVisit(player)
	local v = visits[player]
	if not v then
		return
	end
	visits[player] = nil
	if v.Slot then
		ArenaPool.Release(v.Slot)
	end
	if Registry.Get("PlotService").Location(player) == "visit" then
		Registry.Get("PlotService").SetLocation(player, "home")
	end
end

function Gallery.Like(player, key)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return false, Strings.Error
	end
	if not limiter:Allow(player.UserId .. ":like") then
		return false, Strings.TooFast
	end
	local userId = parseKey(key)
	if not userId or userId == player.UserId then
		return false, Strings.Error
	end
	local dayKey = TimeUtil.DayKey()
	if profile.Gallery.LikesGiven[key] == dayKey then
		return false, "Hai già messo «mi piace» oggi"
	end
	local given = 0
	for _, d in pairs(profile.Gallery.LikesGiven) do
		if d == dayKey then
			given += 1
		end
	end
	if given >= Config.Gallery.LikesPerDay then
		return false, "Limite giornaliero di «mi piace» raggiunto"
	end
	-- pulizia chiavi vecchie
	for k, d in pairs(profile.Gallery.LikesGiven) do
		if d ~= dayKey then
			profile.Gallery.LikesGiven[k] = nil
		end
	end
	profile.Gallery.LikesGiven[key] = dayKey
	local owner = Players:GetPlayerByUserId(userId)
	local ownerProfile = owner and Registry.Get("DataService").Get(owner)
	if ownerProfile then
		ownerProfile.Gallery.Likes += 1
		Registry.Get("PlayerService").Sync(owner, "Gallery")
		Registry.Get("PlayerService").Toast(owner, "Qualcuno ha apprezzato il tuo vivaio ♥", "info")
		Gallery.MarkDirty(owner)
	else
		local entry, tier = PoolStore.FindByUserId(userId)
		if entry then
			PoolStore.ModifyEntry(userId, tier, function(e)
				e.Likes = (e.Likes or 0) + 1
			end)
		end
	end
	EventBus.Fire("Liked", player, key)
	Registry.Get("PlayerService").Sync(player, "Gallery")
	return true
end

function Gallery.ImportCode(player, code)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return false, Strings.Error
	end
	code = Guard.Str(code, 24)
	local userId = code and decodeCode(code)
	if not userId then
		return false, "Codice non valido"
	end
	local layout
	local owner = Players:GetPlayerByUserId(userId)
	local ownerProfile = owner and Registry.Get("DataService").Get(owner)
	if ownerProfile then
		if ownerProfile.Settings.HideProfile then
			return false, Strings.GalleryHidden
		end
		layout = ownerProfile.LastValidLayout
	else
		local entry = PoolStore.FindByUserId(userId)
		if not entry or entry.Hidden then
			return false, "Nessun vivaio con questo codice"
		end
		layout = entry.Layout
	end
	local missing = {}
	for _, m in ipairs(layout.Modules or {}) do
		if not profile.UnlockedModules[m.Id] then
			local def = Defenses.Get(m.Id)
			table.insert(missing, def and def.Name or m.Id)
		end
	end
	return true, { Layout = layout, Missing = missing }
end

function Gallery.Init()
	Net.Function("GetGallery").OnServerInvoke = Gallery.GetGallery
	Net.Function("VisitVivaio").OnServerInvoke = Gallery.Visit
	Net.Function("LikeVivaio").OnServerInvoke = Gallery.Like
	Net.Function("ImportLayoutCode").OnServerInvoke = Gallery.ImportCode
end

function Gallery.Start()
	EventBus.On("ProfileLoaded", function(player, profile)
		task.delay(3, function()
			if player.Parent then
				Gallery.Publish(player)
			end
		end)
	end)
	EventBus.On("ProfileReleasing", function(player, profile)
		Gallery.EndVisit(player)
		-- ultima istantanea con dati freschi (scintille esposte, scudo)
		Gallery.Publish(player)
		lastPublished[player] = nil
		dirty[player] = nil
	end)
	-- pubblicazione differita delle modifiche + aggiornamento periodico
	task.spawn(function()
		while true do
			task.wait(5)
			local now = os.clock()
			for player, t in pairs(dirty) do
				if now - t >= 5 then
					dirty[player] = nil
					if player.Parent then
						task.spawn(Gallery.Publish, player)
					end
				end
			end
		end
	end)
	task.spawn(function()
		while true do
			task.wait(180)
			for player in pairs(Registry.Get("DataService").GetAll()) do
				Gallery.MarkDirty(player)
				task.wait(1)
			end
		end
	end)
end

return Gallery
