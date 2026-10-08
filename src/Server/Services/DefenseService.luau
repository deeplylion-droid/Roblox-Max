--!nonstrict
--[[
	DefenseService: salvataggio/pubblicazione dei layout (validazione server-side con il
	validatore condiviso), ultimo layout valido, alternative tattiche, prova locale gratuita.
]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Defenses = require(Shared.Catalog.Defenses)
local LayoutValidator = require(Shared.LayoutValidator)
local GridUtil = require(Shared.Util.GridUtil)
local TableUtil = require(Shared.Util.TableUtil)
local Net = require(Shared.Util.Net)

local Registry = require(script.Parent.Parent.Registry)
local EventBus = require(script.Parent.Parent.EventBus)
local Guard = require(script.Parent.Parent.Util.Guard)
local RateLimiter = require(script.Parent.Parent.Util.RateLimiter)
local Logger = require(script.Parent.Parent.Util.Logger)

local Defense = {}
local limiter = RateLimiter.new(6, 1)

local function context(profile)
	local creatureCells, decoCells = {}, {}
	for _, c in pairs(profile.Creatures) do
		if c.x ~= nil then
			creatureCells[GridUtil.Key(c.x, c.z)] = true
		end
	end
	for _, d in ipairs(profile.Decorations.Placed) do
		decoCells[GridUtil.Key(d.x, d.z)] = true
	end
	return {
		UnlockedModules = profile.UnlockedModules,
		UnlockedAlternatives = profile.UnlockedAlternatives,
		CreatureCells = creatureCells,
		DecorationCells = decoCells,
	}
end

-- Normalizza il layout ricevuto dal client (solo i campi attesi)
local function sanitize(layout)
	if type(layout) ~= "table" or type(layout.Modules) ~= "table" then
		return nil
	end
	local out = { Modules = {} }
	for i, m in ipairs(layout.Modules) do
		if i > 6 then
			break
		end
		if type(m) ~= "table" then
			return nil
		end
		local id = Guard.Str(m.Id, 32)
		local x = Guard.Int(m.x, 0, Config.Grid.Size - 1)
		local z = Guard.Int(m.z, 0, Config.Grid.Size - 1)
		local rot = Guard.Int(m.Rot or 0, 0, 3)
		local alt = m.Alt ~= nil and Guard.Str(m.Alt, 32) or nil
		if not id or not x or not z or rot == nil then
			return nil
		end
		table.insert(out.Modules, { Id = id, x = x, z = z, Rot = rot, Alt = alt })
	end
	return out
end

function Defense.Validate(profile, layout)
	return LayoutValidator.Validate(layout, context(profile))
end

function Defense.SaveLayout(player, layout)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return false, Strings.Error
	end
	if not limiter:Allow(player.UserId .. ":layout") then
		return false, Strings.TooFast
	end
	local clean = sanitize(layout)
	if not clean then
		return false, "Layout non valido"
	end
	-- applica le alternative scelte dal giocatore se il client non le specifica
	for _, m in ipairs(clean.Modules) do
		if m.Alt == nil and profile.ModuleAlternative[m.Id] then
			m.Alt = profile.ModuleAlternative[m.Id]
		end
	end
	local result = Defense.Validate(profile, clean)
	profile.Layout = clean
	if not result.Ok then
		Registry.Get("PlayerService").Sync(player, "Layout")
		Registry.Get("PlayerService").Toast(player, Strings.BuildKeptLast .. " (" .. (result.Reason or "") .. ")", "warning")
		return false, result.Reason
	end
	profile.LastValidLayout = TableUtil.DeepCopy(clean)
	profile.LayoutVersion += 1
	profile.Stats.LayoutsPublished += 1
	profile.Mastery.Defense += Config.Mastery.DefensePerPublish
	Registry.Get("PlotService").RefreshLayout(player)
	Registry.Get("PlayerService").Sync(player, "Layout", "LastValidLayout", "Stats", "Mastery")
	Registry.Get("PlayerService").Sound(player, "Success")
	Registry.Get("PlayerService").Toast(player, Strings.BuildPublished, "success")
	EventBus.Fire("LayoutPublished", player, #clean.Modules)
	Registry.Get("GalleryService").MarkDirty(player)
	Logger.Audit("Defense", player, "publish", string.format("%d moduli, energia %d", #clean.Modules, result.Energy))
	return true, { Energy = result.Energy, Difficulty = LayoutValidator.DifficultyStars(result.Difficulty) }
end

function Defense.SetAlternative(player, moduleId, altId)
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return false, Strings.Error
	end
	moduleId = Guard.Str(moduleId, 32)
	altId = Guard.Str(altId, 32)
	if not moduleId or not altId or not Defenses.Get(moduleId) then
		return false, Strings.Error
	end
	if altId ~= "base" then
		if not Defenses.GetAlternative(moduleId, altId) then
			return false, Strings.Error
		end
		local set = profile.UnlockedAlternatives[moduleId]
		if not (set and set[altId]) then
			return false, Strings.BuildLocked
		end
	end
	profile.ModuleAlternative[moduleId] = altId
	Registry.Get("PlayerService").Sync(player, "ModuleAlternative")
	return true
end

-- Sblocca alternative in base al tier di maestria Difesa
function Defense.UnlockAlternativesForTier(player, profile, tier)
	local newly = {}
	for _, m in ipairs(Defenses.List) do
		for _, alt in ipairs(m.Alternatives) do
			if alt.Unlock.Kind == "mastery" and alt.Unlock.Track == "Defense" and alt.Unlock.Tier <= tier then
				profile.UnlockedAlternatives[m.Id] = profile.UnlockedAlternatives[m.Id] or {}
				if not profile.UnlockedAlternatives[m.Id][alt.Id] then
					profile.UnlockedAlternatives[m.Id][alt.Id] = true
					table.insert(newly, m.Name .. " → " .. alt.Name)
				end
			end
		end
		if m.Unlock.Kind == "mastery" and m.Unlock.Track == "Defense" and m.Unlock.Tier <= tier and not profile.UnlockedModules[m.Id] then
			profile.UnlockedModules[m.Id] = true
			table.insert(newly, m.Name)
			EventBus.Fire("ModuleUnlocked", player, m.Id)
		end
	end
	if #newly > 0 then
		Registry.Get("PlayerService").Sync(player, "UnlockedAlternatives", "UnlockedModules")
		for _, n in ipairs(newly) do
			Registry.Get("PlayerService").Toast(player, string.format(Strings.Unlocked, n), "success")
		end
	end
end

function Defense.Init()
	Net.Function("SaveLayout").OnServerInvoke = Defense.SaveLayout
	Net.Function("SetModuleAlternative").OnServerInvoke = Defense.SetAlternative
	Net.Function("StartLayoutTest").OnServerInvoke = function(player)
		if not limiter:Allow(player.UserId .. ":test", 2) then
			return false, Strings.TooFast
		end
		return Registry.Get("RaidService").StartTest(player)
	end
end

function Defense.Start()
	EventBus.On("MasteryTier", function(player, track, tier)
		if track == "Defense" then
			local profile = Registry.Get("DataService").Get(player)
			if profile then
				Defense.UnlockAlternativesForTier(player, profile, tier)
			end
		end
	end)
	EventBus.On("ProfileLoaded", function(player, profile)
		local Album = require(Shared.Catalog.Album)
		local tier = Album.TierFor(profile.Mastery.Defense, Config.Mastery.Tiers)
		if tier > 0 then
			Defense.UnlockAlternativesForTier(player, profile, tier)
		end
	end)
end

return Defense
