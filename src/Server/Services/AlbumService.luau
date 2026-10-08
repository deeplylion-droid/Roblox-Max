--!nonstrict
--[[
	AlbumService: traguardi dell'album (per famiglia e globali), tre tracce di maestria
	(Collezione, Incursione, Difesa) con tier, sblocco varianti cromatiche e deposito automatico.
	Tutte le ricompense sono idempotenti (Album.Claimed / Mastery.ClaimedTiers).
]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Album = require(Shared.Catalog.Album)
local Creatures = require(Shared.Catalog.Creatures)
local Cosmetics = require(Shared.Catalog.Cosmetics)
local Net = require(Shared.Util.Net)

local Registry = require(script.Parent.Parent.Registry)
local EventBus = require(script.Parent.Parent.EventBus)
local Guard = require(script.Parent.Parent.Util.Guard)

local AlbumService = {}

local function ownedCounts(profile)
	local byFamily = { sole = 0, pioggia = 0, vento = 0, aurora = 0 }
	local total = 0
	for id in pairs(profile.OwnedCreatureIds) do
		local def = Creatures.Get(id)
		if def then
			byFamily[def.Family] += 1
			total += 1
		end
	end
	return byFamily, total
end

function AlbumService.IsMilestoneReached(profile, m)
	local byFamily, total = ownedCounts(profile)
	if m.Family then
		return byFamily[m.Family] >= m.Count
	end
	return total >= m.Count
end

local function grantReward(player, profile, reward, reason)
	local eco = Registry.Get("EconomyService")
	eco.GrantFragments(player, profile, reward.Fragments, reason)
	eco.GrantTokens(player, profile, reward.Tokens, reason)
	eco.GrantSafe(player, profile, reward.Sparks or 0, reason)
	if reward.Decoration then
		eco.GrantDecoration(player, profile, reward.Decoration)
	end
	if reward.Cosmetic then
		Registry.Get("ShopService").GrantCosmetic(player, profile, reward.Cosmetic, reason)
	end
end

function AlbumService.ClaimMilestone(player, milestoneId)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return false, Strings.Error
	end
	milestoneId = Guard.Str(milestoneId, 32)
	local m = milestoneId and Album.ById[milestoneId]
	if not m then
		return false, Strings.Error
	end
	if profile.Album.Claimed[milestoneId] then
		return false, "Già riscosso"
	end
	if not AlbumService.IsMilestoneReached(profile, m) then
		return false, "Traguardo non raggiunto"
	end
	profile.Album.Claimed[milestoneId] = true
	grantReward(player, profile, m.Reward, "album:" .. milestoneId)
	profile.Pass.Points += Cosmetics.Pass.PointsPerAlbumMilestone
	profile.StyleTokens += Config.StyleTokens.PerAlbumMilestone
	EventBus.Fire("AlbumMilestone", player, milestoneId)
	Registry.Get("PlayerService").Sync(player, "Album", "Pass", "StyleTokens", "Decorations", "Cosmetics")
	Registry.Get("PlayerService").Sound(player, "Success")
	Registry.Get("PlayerService").Toast(player, "Traguardo dell'album: " .. m.Title, "success")
	return true
end

-- ───────────────────────── maestria ─────────────────────────

local function unlockVariantsForTier(player, profile, track, tier)
	for _, c in ipairs(Creatures.List) do
		if profile.OwnedCreatureIds[c.Id] then
			for _, v in ipairs(c.Variants) do
				if v.Unlock.Kind == "mastery" and v.Unlock.Track == track and v.Unlock.Tier <= tier then
					profile.UnlockedVariants[c.Id] = profile.UnlockedVariants[c.Id] or { base = true }
					if not profile.UnlockedVariants[c.Id][v.Id] then
						profile.UnlockedVariants[c.Id][v.Id] = true
						profile.Mastery.Collection += Config.Mastery.CollectionPerVariant
						EventBus.Fire("VariantUnlocked", player, c.Id, v.Id)
						Registry.Get("PlayerService").Toast(player, string.format(Strings.NewVariant, c.Name, v.Name), "success")
					end
				end
			end
		end
	end
end

local function unlockActivityVariants(player, profile)
	for _, c in ipairs(Creatures.List) do
		if profile.OwnedCreatureIds[c.Id] then
			for _, v in ipairs(c.Variants) do
				if v.Unlock.Kind == "activity" and (profile.Stats[v.Unlock.Stat] or 0) >= v.Unlock.Value then
					profile.UnlockedVariants[c.Id] = profile.UnlockedVariants[c.Id] or { base = true }
					if not profile.UnlockedVariants[c.Id][v.Id] then
						profile.UnlockedVariants[c.Id][v.Id] = true
						profile.Mastery.Collection += Config.Mastery.CollectionPerVariant
						EventBus.Fire("VariantUnlocked", player, c.Id, v.Id)
						Registry.Get("PlayerService").Toast(player, string.format(Strings.NewVariant, c.Name, v.Name), "success")
					end
				end
			end
		end
	end
end

-- Controlla se una traccia ha raggiunto un nuovo tier e assegna i premi (idempotente)
function AlbumService.CheckMastery(player, profile)
	local changed = false
	for _, track in ipairs({ "Collection", "Raid", "Defense" }) do
		local tier = Album.TierFor(profile.Mastery[track], Config.Mastery.Tiers)
		local claimed = profile.Mastery.ClaimedTiers[track] or 0
		while claimed < tier do
			claimed += 1
			profile.Mastery.ClaimedTiers[track] = claimed
			local reward = Album.MasteryRewards[track][claimed]
			if reward then
				Registry.Get("EconomyService").GrantFragments(player, profile, reward.Fragments, "mastery")
				Registry.Get("EconomyService").GrantTokens(player, profile, (reward.Tokens or 0) + Config.StyleTokens.PerMasteryTier, "mastery")
				if reward.Unlock == "AutoDeposit" then
					profile.AutoDepositUnlocked = true
					Registry.Get("PlayerService").Toast(player, "Deposito automatico sbloccato! Attivalo dalle Opzioni.", "success")
				end
				Registry.Get("PlayerService").Toast(player, string.format("Maestria %s · Tier %d: %s", Strings["Mastery" .. track] or track, claimed, reward.Title), "success")
			end
			unlockVariantsForTier(player, profile, track, claimed)
			EventBus.Fire("MasteryTier", player, track, claimed)
			changed = true
		end
	end
	if changed then
		Registry.Get("PlayerService").Sync(player, "Mastery", "AutoDepositUnlocked", "UnlockedVariants")
	end
end

function AlbumService.AddMastery(player, track, points)
	local profile = Registry.Get("DataService").Get(player)
	if not profile or points <= 0 then
		return
	end
	profile.Mastery[track] += points
	Registry.Get("PlayerService").Sync(player, "Mastery")
	AlbumService.CheckMastery(player, profile)
end

-- Vista (per il client): traguardi con stato
function AlbumService.View(profile)
	local out = {}
	for _, m in ipairs(Album.List) do
		table.insert(out, { Id = m.Id, Family = m.Family, Count = m.Count, Title = m.Title, Reward = m.Reward, Reached = AlbumService.IsMilestoneReached(profile, m), Claimed = profile.Album.Claimed[m.Id] == true })
	end
	return out
end

function AlbumService.Init()
	Net.Function("ClaimAlbumMilestone").OnServerInvoke = AlbumService.ClaimMilestone
end

function AlbumService.Start()
	EventBus.On("CreatureUnlocked", function(player, creatureId)
		local profile = Registry.Get("DataService").Get(player)
		if not profile then
			return
		end
		profile.Mastery.Collection += Config.Mastery.CollectionPerCreature
		-- varianti già meritate per i tier raggiunti
		for _, track in ipairs({ "Collection", "Raid", "Defense" }) do
			unlockVariantsForTier(player, profile, track, profile.Mastery.ClaimedTiers[track] or 0)
		end
		unlockActivityVariants(player, profile)
		AlbumService.CheckMastery(player, profile)
		Registry.Get("PlayerService").Sync(player, "Mastery", "UnlockedVariants", "Album")
		-- notifica traguardi raggiunti
		for _, m in ipairs(Album.List) do
			if not profile.Album.Claimed[m.Id] and AlbumService.IsMilestoneReached(profile, m) then
				Registry.Get("PlayerService").Toast(player, "Traguardo raggiunto: " .. m.Title .. " (riscuoti nell'Album)", "info")
			end
		end
	end)
	EventBus.On("RaidDefended", function(player)
		local profile = Registry.Get("DataService").Get(player)
		if profile then
			unlockActivityVariants(player, profile)
			Registry.Get("PlayerService").Sync(player, "UnlockedVariants")
		end
	end)
	EventBus.On("ProfileLoaded", function(player, profile)
		AlbumService.CheckMastery(player, profile)
		unlockActivityVariants(player, profile)
	end)
end

return AlbumService
