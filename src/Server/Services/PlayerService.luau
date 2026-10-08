--!nonstrict
--[[
	PlayerService: sincronizzazione dello stato verso il client (sezioni del profilo,
	coalescenza degli aggiornamenti), toast, suoni, tempo di gioco, remoti di base.
]]
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Net = require(Shared.Util.Net)
local Guard = require(script.Parent.Parent.Util.Guard)
local Registry = require(script.Parent.Parent.Registry)
local EventBus = require(script.Parent.Parent.EventBus)

local PlayerService = {}

local dirty = {} -- player -> { key = true }
local ready = {} -- player -> true quando il client ha chiesto lo stato
local lastSync = {}

-- Sezioni del profilo replicate al client (il resto resta privato al server)
local SYNC_KEYS = {
	"Sparks", "Fragments", "StyleTokens", "PlotLevel", "Creatures", "OwnedCreatureIds", "UnlockedVariants",
	"Layout", "LastValidLayout", "UnlockedModules", "UnlockedAlternatives", "ModuleAlternative", "Decorations",
	"Cosmetics", "Pass", "Founder", "Commissions", "Album", "Mastery", "AutoDepositUnlocked", "Cocoon",
	"Gallery", "Stats", "Settings", "Tutorial", "WeeklyChallengeClaimed",
}
local SYNC_SET = {}
for _, k in ipairs(SYNC_KEYS) do
	SYNC_SET[k] = true
end

local function sanitizedRaid(profile)
	local r = profile.Raid
	return {
		ShieldUntil = r.ShieldUntil,
		Attempts = r.Attempts,
		Successes = r.Successes,
		Defended = r.Defended,
		Lost = r.Lost,
		History = r.History,
		LastRaidAt = r.LastRaidAt,
		NewPlayerShield = PlayerService.HasNewPlayerShield(profile),
	}
end

function PlayerService.HasNewPlayerShield(profile)
	return profile.Stats.PlayTime < Config.Raid.NewPlayerShieldPlaytime and profile.Sparks.VaultLevel < Config.Raid.NewPlayerShieldMinVaultLevel
end

function PlayerService.BuildState(player, profile)
	local state = {}
	for _, k in ipairs(SYNC_KEYS) do
		state[k] = profile[k]
	end
	state.Raid = sanitizedRaid(profile)
	state.Commissions = Registry.Get("CommissionService").View(player, profile)
	state.ServerInfo = {
		Mock = Registry.Get("DataService").IsMock(),
		ThemeId = Registry.Get("ThemeService").CurrentThemeId(),
		WeeklyProgress = Registry.Get("ThemeService").Progress(profile),
	}
	return state
end

-- Segna sezioni da inviare; l'invio è coalescente (max N al secondo)
function PlayerService.Sync(player, ...)
	if not player or not player.Parent then
		return
	end
	local set = dirty[player]
	if not set then
		set = {}
		dirty[player] = set
	end
	for _, k in ipairs({ ... }) do
		set[k] = true
	end
end

function PlayerService.SyncAll(player)
	PlayerService.Sync(player, table.unpack(SYNC_KEYS))
	PlayerService.Sync(player, "Raid", "Commissions")
end

local function flush(player)
	local set = dirty[player]
	if not set or not ready[player] then
		return
	end
	dirty[player] = nil
	local profile = Registry.Get("DataService").Get(player)
	if not profile then
		return
	end
	local payload = {}
	for k in pairs(set) do
		if k == "Raid" then
			payload.Raid = sanitizedRaid(profile)
		elseif k == "Commissions" then
			payload.Commissions = Registry.Get("CommissionService").View(player, profile)
		elseif k == "ServerInfo" then
			payload.ServerInfo = {
				Mock = Registry.Get("DataService").IsMock(),
				ThemeId = Registry.Get("ThemeService").CurrentThemeId(),
				WeeklyProgress = Registry.Get("ThemeService").Progress(profile),
			}
		elseif SYNC_SET[k] then
			payload[k] = profile[k]
		end
	end
	Net.Event("StateSync"):FireClient(player, payload)
end

function PlayerService.Toast(player, message, kind)
	if player and player.Parent then
		Net.Event("Toast"):FireClient(player, message, kind or "info")
	end
end

function PlayerService.Sound(player, soundKey)
	if player and player.Parent then
		Net.Event("PlaySound"):FireClient(player, soundKey)
	end
end

function PlayerService.Init()
	Net.Function("GetState").OnServerInvoke = function(player)
		local profile = Registry.Get("DataService").WaitFor(player, 30)
		if not profile then
			return nil
		end
		ready[player] = true
		dirty[player] = nil
		return PlayerService.BuildState(player, profile)
	end

	Net.Event("ClientReady").OnServerEvent:Connect(function(player)
		ready[player] = true
	end)

	Net.Event("SetSetting").OnServerEvent:Connect(function(player, settingKey, value)
		local profile = Registry.Get("DataService").Get(player)
		if not profile then
			return
		end
		local k = Guard.Str(settingKey, 32)
		if not k or profile.Settings[k] == nil then
			return
		end
		local v = Guard.Bool(value)
		if v == nil then
			return
		end
		if k == "AutoDeposit" and v and not profile.AutoDepositUnlocked then
			return
		end
		profile.Settings[k] = v
		PlayerService.Sync(player, "Settings")
		if k == "HideProfile" or k == "ShowName" then
			Registry.Get("GalleryService").MarkDirty(player)
		end
	end)
end

function PlayerService.Start()
	-- Flush coalescente
	local acc = 0
	RunService.Heartbeat:Connect(function(dt)
		acc += dt
		if acc < 1 / Config.Limits.StateSyncMaxPerSecond then
			return
		end
		acc = 0
		for player in pairs(dirty) do
			if player.Parent then
				flush(player)
			else
				dirty[player] = nil
			end
		end
	end)

	-- Tempo di gioco
	task.spawn(function()
		while true do
			task.wait(10)
			for player, profile in pairs(Registry.Get("DataService").GetAll()) do
				profile.Stats.PlayTime += 10
			end
		end
	end)

	Players.PlayerRemoving:Connect(function(player)
		dirty[player] = nil
		ready[player] = nil
		lastSync[player] = nil
	end)

	EventBus.On("ProfileLoaded", function(player, profile)
		PlayerService.SyncAll(player)
	end)
end

return PlayerService
