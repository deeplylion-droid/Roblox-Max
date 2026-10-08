--!nonstrict
--[[
	DataService: carica/salva i profili con lock di sessione, autosave, riconciliazione
	con il template, migrazioni e salvataggio alla chiusura del server.
	Salvataggi resilienti: retry con backoff, nessuna perdita silenziosa (se il
	caricamento fallisce il giocatore viene espulso con un messaggio, non gioca con dati vuoti).
]]
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local DefaultData = require(Shared.DefaultData)
local TableUtil = require(Shared.Util.TableUtil)
local Signal = require(Shared.Util.Signal)

local Store = require(script.Parent.Parent.Util.Store)
local Logger = require(script.Parent.Parent.Util.Logger)
local EventBus = require(script.Parent.Parent.EventBus)

local DataService = {}
DataService.ProfileLoaded = Signal.new()
DataService.ProfileReleasing = Signal.new()

local profiles = {} -- player -> profile
local loading = {} -- player -> true
local store
local LOCK_TIMEOUT = 120 -- secondi oltre i quali un lock è considerato orfano
local jobId = game.JobId ~= "" and game.JobId or "studio"

local function key(userId)
	return "p_" .. userId
end

-- Migrazioni tra versioni di dati
local migrations = {
	-- [1] = function(data) ... end,
}

local function migrate(data)
	local v = data.Version or 1
	while v < Config.DataVersion do
		local m = migrations[v]
		if m then
			m(data)
		end
		v += 1
		data.Version = v
	end
end

function DataService.Init()
	store = Store.new(Config.DataStoreName)
end

local function loadProfile(player)
	local userId = player.UserId
	local attempts = 0
	while attempts < 5 do
		attempts += 1
		local lockedElsewhere = false
		local ok, data = store:Update(key(userId), function(old)
			local now = os.time()
			if old and old.SessionLock and old.SessionLock.JobId ~= jobId and (now - (old.SessionLock.Time or 0)) < LOCK_TIMEOUT then
				lockedElsewhere = true
				return nil -- non modificare
			end
			local d = old or DefaultData()
			d.SessionLock = { JobId = jobId, Time = now }
			return d
		end)
		if not ok then
			Logger.Warn("Data", "Caricamento fallito per", player.Name, data)
			return nil, "Impossibile caricare i dati. Riprova tra poco."
		end
		if not lockedElsewhere and data then
			return data
		end
		Logger.Info("Data", "Profilo di", player.Name, "bloccato altrove, riprovo...")
		task.wait(3)
	end
	return nil, "I tuoi dati sono ancora in uso su un altro server. Riprova tra un minuto."
end

local function saveProfile(player, profile, release)
	profile.LastSeen = os.time()
	local snapshot = TableUtil.DeepCopy(profile)
	if release then
		snapshot.SessionLock = nil
	else
		snapshot.SessionLock = { JobId = jobId, Time = os.time() }
	end
	local ok, err = store:Update(key(player.UserId), function(old)
		-- Non sovrascrivere un profilo bloccato da un altro server (sicurezza extra)
		if old and old.SessionLock and old.SessionLock.JobId ~= jobId and (os.time() - (old.SessionLock.Time or 0)) < LOCK_TIMEOUT then
			return nil
		end
		return snapshot
	end)
	if not ok then
		Logger.Warn("Data", "Salvataggio fallito per", player.Name, err)
	end
	return ok
end

function DataService.OnPlayerAdded(player)
	loading[player] = true
	local profile, err = loadProfile(player)
	loading[player] = nil
	if not profile then
		player:Kick(err or "Errore dati")
		return
	end
	if not player.Parent then
		-- è uscito durante il caricamento: rilascia il lock
		saveProfile(player, profile, true)
		return
	end
	TableUtil.Reconcile(profile, DefaultData())
	migrate(profile)
	profile.Stats.Sessions += 1
	profiles[player] = profile
	Logger.Info("Data", "Profilo caricato per", player.Name, store:IsMock() and "(memoria)" or "")
	DataService.ProfileLoaded:Fire(player, profile)
	EventBus.Fire("ProfileLoaded", player, profile)
end

function DataService.OnPlayerRemoving(player)
	local profile = profiles[player]
	if not profile then
		return
	end
	DataService.ProfileReleasing:Fire(player, profile)
	EventBus.Fire("ProfileReleasing", player, profile)
	profiles[player] = nil
	saveProfile(player, profile, true)
end

function DataService.Get(player)
	return profiles[player]
end

function DataService.WaitFor(player, timeout)
	local t0 = os.clock()
	while not profiles[player] do
		if not player.Parent or (os.clock() - t0) > (timeout or 30) then
			return nil
		end
		task.wait(0.1)
	end
	return profiles[player]
end

function DataService.GetAll()
	return profiles
end

function DataService.Save(player)
	local profile = profiles[player]
	if profile then
		return saveProfile(player, profile, false)
	end
	return false
end

function DataService.IsMock()
	return store:IsMock()
end

function DataService.Start()
	Players.PlayerAdded:Connect(DataService.OnPlayerAdded)
	for _, p in ipairs(Players:GetPlayers()) do
		task.spawn(DataService.OnPlayerAdded, p)
	end
	Players.PlayerRemoving:Connect(DataService.OnPlayerRemoving)

	-- Autosave scaglionato
	task.spawn(function()
		while true do
			task.wait(Config.Limits.AutosaveSeconds)
			for player, profile in pairs(profiles) do
				task.spawn(saveProfile, player, profile, false)
				task.wait(0.5)
			end
		end
	end)

	game:BindToClose(function()
		if RunService:IsStudio() and store:IsMock() then
			return
		end
		local pending = 0
		for player, profile in pairs(profiles) do
			pending += 1
			task.spawn(function()
				DataService.ProfileReleasing:Fire(player, profile)
				saveProfile(player, profile, true)
				pending -= 1
			end)
		end
		local t0 = os.clock()
		while pending > 0 and os.clock() - t0 < 25 do
			task.wait(0.2)
		end
	end)
end

return DataService
