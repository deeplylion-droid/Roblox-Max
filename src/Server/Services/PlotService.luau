--!nonstrict
--[[
	PlotService: assegna un'isola a ogni giocatore, costruisce il vivaio dai dati del profilo,
	gestisce teletrasporti (hub ↔ vivaio), caduta dal bordo e visite al vivaio di altri.
]]
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local Workspace = game:GetService("Workspace")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Cosmetics = require(Shared.Catalog.Cosmetics)
local PlotBuilder = require(Shared.Models.PlotBuilder)
local Net = require(Shared.Util.Net)

local WorldBuilder = require(script.Parent.Parent.World.WorldBuilder)
local Registry = require(script.Parent.Parent.Registry)
local EventBus = require(script.Parent.Parent.EventBus)
local Logger = require(script.Parent.Parent.Util.Logger)

local PlotService = {}

local plotsByPlayer = {} -- player -> { Index, Plot (PlotBuilder), Origin }
local freeIndices = {}
local playerLocation = {} -- player -> "home" | "hub" | "raid" | "visit"

function PlotService.BuildView(player, profile)
	local creatures = {}
	for uid, c in pairs(profile.Creatures) do
		if c.x ~= nil and c.z ~= nil then
			table.insert(creatures, { Uid = uid, Id = c.Id, Variant = c.Variant or "base", x = c.x, z = c.z, Buffer = c.Buffer or 0 })
		end
	end
	local equipped = profile.Cosmetics.Equipped
	return {
		Creatures = creatures,
		Layout = profile.LastValidLayout,
		Decorations = profile.Decorations.Placed,
		Skin = equipped.skin,
		OwnerName = profile.Settings.ShowName and player.DisplayName or nil,
		Nameplate = equipped.nameplate ~= "plate_nessuna" and equipped.nameplate or nil,
		Exposed = profile.Sparks.Exposed,
		Vault = profile.Sparks.Vault,
		VaultCap = Config.Vault.Capacities[profile.Sparks.VaultLevel] or Config.Vault.Capacities[#Config.Vault.Capacities],
	}
end

function PlotService.Get(player)
	return plotsByPlayer[player]
end

function PlotService.GetPlot(player)
	local e = plotsByPlayer[player]
	return e and e.Plot
end

function PlotService.Location(player)
	return playerLocation[player] or "hub"
end

function PlotService.SetLocation(player, loc)
	playerLocation[player] = loc
	player:SetAttribute("Location", loc)
end

local function teleport(player, cf)
	local char = player.Character
	if char and char.PrimaryPart then
		char:PivotTo(cf)
	end
end

function PlotService.TeleportHome(player)
	local e = plotsByPlayer[player]
	if not e then
		return false
	end
	teleport(player, e.Plot:SpawnCFrame())
	PlotService.SetLocation(player, "home")
	return true
end

function PlotService.TeleportHub(player)
	teleport(player, WorldBuilder.HubSpawnCFrame())
	PlotService.SetLocation(player, "hub")
end

-- È il giocatore fisicamente nel proprio vivaio (per "Raccogli tutto"/"Deposita")?
function PlotService.IsAtHome(player, maxDist)
	local e = plotsByPlayer[player]
	local char = player.Character
	if not e or not char or not char.PrimaryPart then
		return false
	end
	local d = (char.PrimaryPart.Position - e.Origin.Position)
	return math.abs(d.X) <= (maxDist or 48) and math.abs(d.Z) <= (maxDist or 48) and math.abs(d.Y) < 30
end

function PlotService.DistanceTo(player, position)
	local char = player.Character
	if not char or not char.PrimaryPart then
		return math.huge
	end
	return (char.PrimaryPart.Position - position).Magnitude
end

-- Collega i ProximityPrompt del vivaio (cassaforte e creature) al proprietario
local function wirePlot(player, plot)
	if plot.DepositPrompt then
		plot.DepositPrompt.Triggered:Connect(function(who)
			if who == player then
				Registry.Get("EconomyService").Deposit(player)
			end
		end)
	end
	local function wirePrompt(d)
		if d:IsA("ProximityPrompt") and d.Name == "CollectPrompt" then
			d.Triggered:Connect(function(who)
				if who == player then
					Registry.Get("EconomyService").Collect(player, d:GetAttribute("Uid"))
				end
			end)
		end
	end
	for _, d in ipairs(plot.Folders.Creatures:GetDescendants()) do
		wirePrompt(d)
	end
	plot.Folders.Creatures.DescendantAdded:Connect(wirePrompt)
end

local function assign(player, profile)
	local index = table.remove(freeIndices, 1)
	if not index then
		Logger.Warn("Plot", "Nessun plot libero per", player.Name)
		player:Kick("Server pieno, riprova tra poco.")
		return
	end
	local origin = WorldBuilder.PlotOrigin(index)
	local plot = PlotBuilder.Build(Workspace.Plots, origin, PlotService.BuildView(player, profile), "home")
	plot.Model.Name = "Plot_" .. index
	plot.Model:SetAttribute("OwnerUserId", player.UserId)
	plot.Model:SetAttribute("OwnerName", player.Name)
	plotsByPlayer[player] = { Index = index, Plot = plot, Origin = origin }
	player:SetAttribute("PlotIndex", index)

	wirePlot(player, plot)

	-- al primo spawn porta il giocatore sul suo vivaio
	local function onCharacter(char)
		char:WaitForChild("HumanoidRootPart", 5)
		task.wait(0.2)
		if plotsByPlayer[player] and playerLocation[player] ~= "raid" and playerLocation[player] ~= "visit" then
			PlotService.TeleportHome(player)
		end
	end
	player.CharacterAdded:Connect(onCharacter)
	if player.Character then
		task.spawn(onCharacter, player.Character)
	end
end

local function release(player)
	local e = plotsByPlayer[player]
	if e then
		e.Plot:Destroy()
		table.insert(freeIndices, e.Index)
		plotsByPlayer[player] = nil
	end
	playerLocation[player] = nil
end

-- Aggiornamenti incrementali chiamati dagli altri servizi
function PlotService.RefreshCreature(player, uid)
	local e = plotsByPlayer[player]
	local profile = Registry.Get("DataService").Get(player)
	if not e or not profile then
		return
	end
	local c = profile.Creatures[uid]
	if c and c.x ~= nil then
		e.Plot:AddCreature({ Uid = uid, Id = c.Id, Variant = c.Variant or "base", x = c.x, z = c.z, Buffer = c.Buffer or 0 })
	else
		e.Plot:RemoveCreature(uid)
	end
end

function PlotService.RefreshBuffer(player, uid)
	local e = plotsByPlayer[player]
	local profile = Registry.Get("DataService").Get(player)
	if not e or not profile then
		return
	end
	local c = profile.Creatures[uid]
	if c then
		e.Plot:SetCreatureBuffer(uid, c.Buffer or 0, c.Id)
	end
end

function PlotService.RefreshSparks(player)
	local e = plotsByPlayer[player]
	local profile = Registry.Get("DataService").Get(player)
	if not e or not profile then
		return
	end
	e.Plot:SetExposed(profile.Sparks.Exposed)
	e.Plot:SetVault(profile.Sparks.Vault, Config.Vault.Capacities[profile.Sparks.VaultLevel])
end

function PlotService.RefreshLayout(player)
	local e = plotsByPlayer[player]
	local profile = Registry.Get("DataService").Get(player)
	if not e or not profile then
		return
	end
	-- la cupola cambia la struttura della pozza: ricostruzione completa
	local hadCupola, hasCupola = false, false
	for _, m in ipairs(e.Plot.View.Layout.Modules or {}) do
		if m.Id == "cupola" then
			hadCupola = true
		end
	end
	for _, m in ipairs(profile.LastValidLayout.Modules or {}) do
		if m.Id == "cupola" then
			hasCupola = true
		end
	end
	if hadCupola ~= hasCupola then
		PlotService.Rebuild(player)
		return
	end
	e.Plot.View.Layout = profile.LastValidLayout
	e.Plot:RebuildModules(profile.LastValidLayout)
end

function PlotService.RefreshDecorations(player)
	local e = plotsByPlayer[player]
	local profile = Registry.Get("DataService").Get(player)
	if e and profile then
		e.Plot:RebuildDecorations(profile.Decorations.Placed)
	end
end

function PlotService.RefreshSkin(player)
	local e = plotsByPlayer[player]
	local profile = Registry.Get("DataService").Get(player)
	if e and profile then
		e.Plot:SetSkin(profile.Cosmetics.Equipped.skin)
	end
end

function PlotService.Rebuild(player)
	local e = plotsByPlayer[player]
	local profile = Registry.Get("DataService").Get(player)
	if not e or not profile then
		return
	end
	local wasHome = playerLocation[player] == "home"
	e.Plot:Destroy()
	local plot = PlotBuilder.Build(Workspace.Plots, e.Origin, PlotService.BuildView(player, profile), "home")
	plot.Model.Name = "Plot_" .. e.Index
	plot.Model:SetAttribute("OwnerUserId", player.UserId)
	e.Plot = plot
	wirePlot(player, plot)
	if wasHome then
		PlotService.TeleportHome(player)
	end
end

-- Trova il proprietario online di un plot dato lo userId
function PlotService.FindByUserId(userId)
	for player, e in pairs(plotsByPlayer) do
		if player.UserId == userId then
			return player, e
		end
	end
	return nil
end

function PlotService.Init()
	for i = 1, Config.Plots.Count do
		table.insert(freeIndices, i)
	end
	Net.Function("ReturnHome").OnServerInvoke = function(player)
		local loc = playerLocation[player]
		if loc == "raid" then
			Registry.Get("RaidService").Abort(player, "ritorno")
			return true
		end
		if loc == "visit" then
			Registry.Get("GalleryService").EndVisit(player)
		end
		return PlotService.TeleportHome(player)
	end
end

function PlotService.Start()
	EventBus.On("ProfileLoaded", function(player, profile)
		assign(player, profile)
	end)
	Players.PlayerRemoving:Connect(release)

	-- Prompt delle stazioni dell'hub e del pad verso l'hub nei plot
	Workspace.DescendantAdded:Connect(function(d)
		if d:IsA("ProximityPrompt") and d.Name == "StationPrompt" then
			d.Triggered:Connect(function(player)
				local station = d:GetAttribute("Station")
				if station == "home" then
					PlotService.TeleportHome(player)
				elseif station == "demo" then
					EventBus.Fire("DemoVisited", player)
					Net.Event("RaidEvent"):FireClient(player, "OpenPanel", { Panel = "demo" })
				else
					Net.Event("RaidEvent"):FireClient(player, "OpenPanel", { Panel = station })
				end
			end)
		end
	end)
	for _, d in ipairs(Workspace:GetDescendants()) do
		if d:IsA("ProximityPrompt") and d.Name == "StationPrompt" then
			d.Triggered:Connect(function(player)
				local station = d:GetAttribute("Station")
				if station == "home" then
					PlotService.TeleportHome(player)
				elseif station == "demo" then
					EventBus.Fire("DemoVisited", player)
					Net.Event("RaidEvent"):FireClient(player, "OpenPanel", { Panel = "demo" })
				else
					Net.Event("RaidEvent"):FireClient(player, "OpenPanel", { Panel = station })
				end
			end)
		end
	end

	-- Caduta dal bordo / pad verso l'hub
	local acc = 0
	RunService.Heartbeat:Connect(function(dt)
		acc += dt
		if acc < 0.25 then
			return
		end
		acc = 0
		for player, e in pairs(plotsByPlayer) do
			local char = player.Character
			local hrp = char and char.PrimaryPart
			if hrp then
				local loc = playerLocation[player]
				if loc ~= "raid" then
					if hrp.Position.Y < -60 then
						if loc == "home" then
							PlotService.TeleportHome(player)
						elseif loc == "visit" then
							Registry.Get("GalleryService").EndVisit(player)
							PlotService.TeleportHome(player)
						else
							PlotService.TeleportHub(player)
						end
					elseif loc == "home" and e.Plot.HubPad then
						local d = hrp.Position - e.Plot.HubPad.Position
						if math.abs(d.X) < 2.4 and math.abs(d.Z) < 2.4 and d.Y > 0 and d.Y < 6 then
							PlotService.TeleportHub(player)
						end
					end
				end
			end
		end
	end)
end

return PlotService
