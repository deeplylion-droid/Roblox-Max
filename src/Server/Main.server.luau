--!nonstrict
--[[
	Main (server): costruisce il mondo, registra e avvia i servizi.
	Ordine: Init di tutti (collega i remoti), poi Start di tutti (loop e connessioni agli eventi).
]]
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage.Shared
local Net = require(Shared.Util.Net)
local Config = require(Shared.Config)

local Registry = require(script.Parent.Registry)
local Logger = require(script.Parent.Util.Logger)
local WorldBuilder = require(script.Parent.World.WorldBuilder)
local MeshLibrary = require(script.Parent.World.MeshLibrary)

Net.Event("StateSync") -- crea la cartella dei remoti

-- mesh ad alta qualità (asset glTF caricati via Open Cloud); fallback alle primitive se mancanti
MeshLibrary.Preload(25)
WorldBuilder.Build()

local servicesFolder = script.Parent.Services
local ORDER = {
	"DataService", "PlayerService", "StatsService", "PoolStore", "EconomyService", "PlotService", "DefenseService",
	"CommissionService", "AlbumService", "CocoonService", "GalleryService", "RaidService", "ShopService",
	"TutorialService", "ThemeService", "AnalyticsService",
}

local services = {}
for _, name in ipairs(ORDER) do
	local module = servicesFolder:FindFirstChild(name)
	assert(module, "Servizio mancante: " .. name)
	local service = require(module)
	services[name] = service
	Registry.Register(name, service)
end

for _, name in ipairs(ORDER) do
	local s = services[name]
	if s.Init then
		local ok, err = pcall(s.Init)
		if not ok then
			Logger.Warn("Main", "Init fallita per", name, err)
		end
	end
end
-- DataService per ultimo: i profili già presenti (Studio) devono trovare tutti i listener pronti
local START_ORDER = table.clone(ORDER)
table.remove(START_ORDER, table.find(START_ORDER, "DataService"))
table.insert(START_ORDER, "DataService")
for _, name in ipairs(START_ORDER) do
	local s = services[name]
	if s.Start then
		local ok, err = pcall(s.Start)
		if not ok then
			Logger.Warn("Main", "Start fallito per", name, err)
		end
	end
end

Logger.Info("Main", Config.GameName .. " · server avviato")
