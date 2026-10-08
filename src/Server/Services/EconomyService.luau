--!nonstrict
--[[
	EconomyService: produzione delle scintille, ritiro, deposito, deposito automatico,
	riserva offline, potenziamenti (cassaforte, espansione plot), sblocco moduli,
	posizionamento creature e decorazioni. Tutte le modifiche alle risorse passano da qui
	e sono verificate dal server.
]]
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Creatures = require(Shared.Catalog.Creatures)
local Defenses = require(Shared.Catalog.Defenses)
local Decorations = require(Shared.Catalog.Decorations)
local GridUtil = require(Shared.Util.GridUtil)
local Net = require(Shared.Util.Net)
local Format = require(Shared.Util.Format)

local Registry = require(script.Parent.Parent.Registry)
local EventBus = require(script.Parent.Parent.EventBus)
local Guard = require(script.Parent.Parent.Util.Guard)
local Logger = require(script.Parent.Parent.Util.Logger)
local RateLimiter = require(script.Parent.Parent.Util.RateLimiter)

local Economy = {}
local limiter = RateLimiter.new(12, 4)

local function data()
	return Registry.Get("DataService")
end
local function ps()
	return Registry.Get("PlayerService")
end
local function plots()
	return Registry.Get("PlotService")
end

-- ───────────────────────── helper economia ─────────────────────────

function Economy.VaultCapacity(profile)
	return Config.Vault.Capacities[profile.Sparks.VaultLevel] or Config.Vault.Capacities[#Config.Vault.Capacities]
end

function Economy.PlotCapacity(profile)
	return Config.PlotSlots.Capacities[profile.PlotLevel] or Config.PlotSlots.Capacities[#Config.PlotSlots.Capacities]
end

-- Fascia di progressione (per matchmaking e commissioni)
function Economy.Tier(profile)
	local owned = 0
	for _ in pairs(profile.OwnedCreatureIds) do
		owned += 1
	end
	local score = profile.Sparks.VaultLevel * 2 + owned
	local tier = 1
	for i, th in ipairs(Config.Tiers.Thresholds) do
		if score >= th then
			tier = i
		end
	end
	return math.clamp(tier, 1, #Config.Raid.TierTakeCaps)
end

-- Spende scintille dalla cassaforte (prima) e poi dalle esposte. Ritorna ok.
function Economy.Spend(player, profile, amount, reason)
	local total = profile.Sparks.Vault + profile.Sparks.Exposed
	if amount > total then
		return false
	end
	local fromVault = math.min(profile.Sparks.Vault, amount)
	profile.Sparks.Vault -= fromVault
	profile.Sparks.Exposed -= (amount - fromVault)
	profile.Stats.TotalSpent += amount
	EventBus.Fire("SparksSpent", player, amount, reason)
	Logger.Audit("Economy", player, "spend", string.format("%d (%s)", amount, reason or "?"))
	ps().Sync(player, "Sparks")
	plots().RefreshSparks(player)
	return true
end

-- Aggiunge scintille al sicuro (ricompense di sistema): nella cassaforte, l'eccedenza va alle esposte
function Economy.GrantSafe(player, profile, amount, reason)
	if amount <= 0 then
		return
	end
	local cap = Economy.VaultCapacity(profile)
	local room = math.max(0, cap - profile.Sparks.Vault)
	local toVault = math.min(room, amount)
	profile.Sparks.Vault += toVault
	profile.Sparks.Exposed += (amount - toVault)
	Logger.Audit("Economy", player, "grant", string.format("%d (%s)", amount, reason or "?"))
	ps().Sync(player, "Sparks")
	plots().RefreshSparks(player)
end

function Economy.GrantExposed(player, profile, amount, reason)
	if amount <= 0 then
		return
	end
	profile.Sparks.Exposed += amount
	Logger.Audit("Economy", player, "grantExposed", string.format("%d (%s)", amount, reason or "?"))
	ps().Sync(player, "Sparks")
	plots().RefreshSparks(player)
end

function Economy.GrantFragments(player, profile, amount, reason)
	if amount and amount > 0 then
		profile.Fragments += amount
		ps().Sync(player, "Fragments")
		Logger.Audit("Economy", player, "fragments", string.format("+%d (%s)", amount, reason or "?"))
	end
end

function Economy.GrantTokens(player, profile, amount, reason)
	if amount and amount > 0 then
		profile.StyleTokens += amount
		ps().Sync(player, "StyleTokens")
		Logger.Audit("Economy", player, "tokens", string.format("+%d (%s)", amount, reason or "?"))
	end
end

-- Totale esposto (pool + buffer delle creature): è ciò che un'incursione può colpire
function Economy.ExposedTotal(profile)
	local total = profile.Sparks.Exposed
	for _, c in pairs(profile.Creatures) do
		if c.x ~= nil then
			total += (c.Buffer or 0)
		end
	end
	return total
end

-- Sottrae scintille esposte (incursione subita): prima dal pool, poi dai buffer
function Economy.RemoveExposed(player, profile, amount)
	local removed = math.min(profile.Sparks.Exposed, amount)
	profile.Sparks.Exposed -= removed
	local remaining = amount - removed
	if remaining > 0 then
		for uid, c in pairs(profile.Creatures) do
			if remaining <= 0 then
				break
			end
			if c.x ~= nil and (c.Buffer or 0) > 0 then
				local take = math.min(c.Buffer, remaining)
				c.Buffer -= take
				remaining -= take
				removed += take
				if player then
					plots().RefreshBuffer(player, uid)
				end
			end
		end
	end
	if player then
		ps().Sync(player, "Sparks", "Creatures")
		plots().RefreshSparks(player)
	end
	return removed
end

-- ───────────────────────── produzione ─────────────────────────

-- Fattori di rendimento marginale: ordina le creature esposte per produzione decrescente
local function productionFactors(profile)
	local placed = {}
	for uid, c in pairs(profile.Creatures) do
		if c.x ~= nil then
			local def = Creatures.Get(c.Id)
			if def then
				table.insert(placed, { Uid = uid, Prod = def.Production })
			end
		end
	end
	table.sort(placed, function(a, b)
		if a.Prod == b.Prod then
			return a.Uid < b.Uid
		end
		return a.Prod > b.Prod
	end)
	local factors = {}
	for i, e in ipairs(placed) do
		factors[e.Uid] = Config.Production.DiminishingFactors[i] or (i > 12 and 0.2 or 1)
	end
	return factors
end

function Economy.ProductionPerInterval(profile)
	local factors = productionFactors(profile)
	local total = 0
	for uid, c in pairs(profile.Creatures) do
		if c.x ~= nil then
			local def = Creatures.Get(c.Id)
			if def then
				total += def.Production * (factors[uid] or 1)
			end
		end
	end
	return total
end

local function tick(player, profile, now)
	local factors = productionFactors(profile)
	local changed = false
	for uid, c in pairs(profile.Creatures) do
		if c.x ~= nil then
			local def = Creatures.Get(c.Id)
			if def then
				c.LastTick = c.LastTick or now
				local interval = Config.Production.BaseInterval
				if now - c.LastTick >= interval then
					local n = math.floor((now - c.LastTick) / interval)
					c.LastTick += n * interval
					local maxBuffer = def.Production * Config.Production.BufferIntervals
					local gain = math.floor(def.Production * (factors[uid] or 1) * n + 0.5)
					local before = c.Buffer or 0
					c.Buffer = math.min(maxBuffer, before + gain)
					if c.Buffer ~= before then
						changed = true
						plots().RefreshBuffer(player, uid)
						-- deposito automatico: le scintille vanno dritte in cassaforte se c'è spazio
						if profile.Settings.AutoDeposit and profile.AutoDepositUnlocked then
							Economy.Collect(player, uid, true)
						end
					end
				end
			end
		end
	end
	if changed then
		ps().Sync(player, "Creatures")
	end
end

-- Riserva offline: al rientro, una frazione della produzione accumulata fino a un tetto
local function applyOfflineReserve(player, profile)
	local elapsed = os.time() - (profile.LastSeen or os.time())
	if elapsed < 60 then
		return
	end
	local minutes = math.min(elapsed / 60, Config.Production.OfflineCapMinutes)
	local perMinute = Economy.ProductionPerInterval(profile) * (60 / Config.Production.BaseInterval)
	local gain = math.floor(perMinute * minutes * Config.Production.OfflineRateFraction)
	gain = math.min(gain, Config.Production.OfflineCapSparks)
	if gain > 0 then
		-- distribuisce nei buffer delle creature (restano esposte: va ritirato e depositato)
		local placed = {}
		for uid, c in pairs(profile.Creatures) do
			if c.x ~= nil then
				table.insert(placed, uid)
			end
		end
		table.sort(placed)
		if #placed > 0 then
			local each = math.floor(gain / #placed)
			for _, uid in ipairs(placed) do
				local c = profile.Creatures[uid]
				local def = Creatures.Get(c.Id)
				local maxBuffer = def and def.Production * Config.Production.BufferIntervals or 60
				c.Buffer = math.min(maxBuffer, (c.Buffer or 0) + each)
			end
			ps().Toast(player, string.format("Bentornato! Le creature hanno messo da parte %d scintille per te.", gain), "success")
		end
	end
	for _, c in pairs(profile.Creatures) do
		c.LastTick = os.time()
	end
end

-- ───────────────────────── ritiro / deposito ─────────────────────────

function Economy.Collect(player, uid, silent)
	local profile = data().Get(player)
	if not profile then
		return false, Strings.Error
	end
	uid = Guard.Str(uid, 32)
	local c = uid and profile.Creatures[uid]
	if not c or c.x == nil then
		return false, Strings.Error
	end
	if not silent then
		if not limiter:Allow(player.UserId .. ":collect") then
			return false, Strings.TooFast
		end
		-- distanza: il giocatore deve essere vicino alla creatura
		local plot = plots().GetPlot(player)
		local model = plot and plot.CreatureModels[uid]
		if model and model.PrimaryPart and plots().DistanceTo(player, model.PrimaryPart.Position) > Config.Limits.InteractDistance then
			return false, "Troppo lontano"
		end
	end
	local amount = c.Buffer or 0
	if amount <= 0 then
		return false, "Nessuna scintilla da ritirare"
	end
	c.Buffer = 0
	local deposited = 0
	if profile.Settings.AutoDeposit and profile.AutoDepositUnlocked then
		local room = math.max(0, Economy.VaultCapacity(profile) - profile.Sparks.Vault)
		deposited = math.min(room, amount)
		profile.Sparks.Vault += deposited
		profile.Sparks.Exposed += amount - deposited
		if deposited > 0 then
			profile.Stats.TotalDeposited += deposited
			EventBus.Fire("SparksDeposited", player, deposited)
		end
	else
		profile.Sparks.Exposed += amount
	end
	profile.Stats.TotalCollected += amount
	if not profile.Stats.FirstActionAt then
		profile.Stats.FirstActionAt = os.time()
		Registry.Get("AnalyticsService").Log(player, "first_action", profile.Stats.PlayTime)
	end
	EventBus.Fire("SparksCollected", player, amount, not silent)
	plots().RefreshBuffer(player, uid)
	plots().RefreshSparks(player)
	ps().Sync(player, "Sparks", "Creatures", "Stats")
	if not silent then
		ps().Sound(player, "Collect")
		local plot = plots().GetPlot(player)
		local model = plot and plot.CreatureModels[uid]
		if model and model.PrimaryPart then
			Net.Event("SparkFx"):FireClient(player, model.PrimaryPart.Position, amount)
		end
	end
	return true, amount
end

function Economy.CollectAll(player)
	local profile = data().Get(player)
	if not profile then
		return false
	end
	if not limiter:Allow(player.UserId .. ":collectAll", 3) then
		return false, Strings.TooFast
	end
	if not plots().IsAtHome(player, Config.Limits.CollectAllDistance) then
		return false, "Devi essere nel tuo vivaio"
	end
	local total = 0
	for uid, c in pairs(profile.Creatures) do
		if c.x ~= nil and (c.Buffer or 0) > 0 then
			local ok, amount = Economy.Collect(player, uid, true)
			if ok then
				total += amount
			end
		end
	end
	if total > 0 then
		ps().Sound(player, "Collect")
		local plot = plots().GetPlot(player)
		if plot and plot.Pozza then
			Net.Event("SparkFx"):FireClient(player, plot.Pozza.Position, total)
		end
	end
	return true, total
end

function Economy.Deposit(player)
	local profile = data().Get(player)
	if not profile then
		return false, Strings.Error
	end
	if not limiter:Allow(player.UserId .. ":deposit") then
		return false, Strings.TooFast
	end
	local plot = plots().GetPlot(player)
	if not plot or not plot.Vault or plots().DistanceTo(player, plot.Vault.Position) > Config.Limits.InteractDistance + 4 then
		return false, "Avvicinati alla cassaforte"
	end
	local room = math.max(0, Economy.VaultCapacity(profile) - profile.Sparks.Vault)
	local amount = math.min(room, profile.Sparks.Exposed)
	if amount <= 0 then
		if profile.Sparks.Exposed > 0 then
			ps().Toast(player, Strings.VaultFull, "warning")
			return false, Strings.VaultFull
		end
		return false, "Nessuna scintilla da depositare"
	end
	profile.Sparks.Exposed -= amount
	profile.Sparks.Vault += amount
	profile.Stats.TotalDeposited += amount
	EventBus.Fire("SparksDeposited", player, amount)
	ps().Sync(player, "Sparks", "Stats")
	ps().Sound(player, "Deposit")
	plots().RefreshSparks(player)
	Net.Event("SparkFx"):FireClient(player, plot.Vault.Position, amount)
	if profile.Sparks.Exposed > 0 and room - amount <= 0 then
		ps().Toast(player, Strings.VaultFull, "warning")
	end
	return true, amount
end

-- ───────────────────────── potenziamenti ─────────────────────────

function Economy.UpgradeVault(player)
	local profile = data().Get(player)
	if not profile then
		return false, Strings.Error
	end
	local nextLevel = profile.Sparks.VaultLevel + 1
	local cost = Config.Vault.UpgradeCosts[nextLevel]
	if not cost then
		return false, "Cassaforte al massimo"
	end
	if not Economy.Spend(player, profile, cost, "vault_upgrade") then
		return false, Strings.NotEnoughSparks
	end
	profile.Sparks.VaultLevel = nextLevel
	ps().Sync(player, "Sparks")
	ps().Sound(player, "Success")
	ps().Toast(player, string.format("Cassaforte potenziata: capienza %s", Format.Number(Economy.VaultCapacity(profile))), "success")
	plots().RefreshSparks(player)
	Registry.Get("GalleryService").MarkDirty(player)
	return true
end

function Economy.UpgradePlot(player)
	local profile = data().Get(player)
	if not profile then
		return false, Strings.Error
	end
	local nextLevel = profile.PlotLevel + 1
	local cost = Config.PlotSlots.UpgradeCosts[nextLevel]
	if not cost then
		return false, "Vivaio già al massimo"
	end
	if not Economy.Spend(player, profile, cost, "plot_upgrade") then
		return false, Strings.NotEnoughSparks
	end
	profile.PlotLevel = nextLevel
	ps().Sync(player, "PlotLevel")
	ps().Sound(player, "Success")
	ps().Toast(player, string.format("Vivaio ampliato: %d creature esponibili", Economy.PlotCapacity(profile)), "success")
	return true
end

function Economy.UnlockModule(player, moduleId)
	local profile = data().Get(player)
	if not profile then
		return false, Strings.Error
	end
	moduleId = Guard.Str(moduleId, 32)
	local def = moduleId and Defenses.Get(moduleId)
	if not def then
		return false, Strings.Error
	end
	if profile.UnlockedModules[moduleId] then
		return false, "Già sbloccato"
	end
	if def.Unlock.Kind ~= "sparks" then
		return false, Strings.BuildLocked
	end
	if not Economy.Spend(player, profile, def.Unlock.Cost, "module_" .. moduleId) then
		return false, Strings.NotEnoughSparks
	end
	profile.UnlockedModules[moduleId] = true
	EventBus.Fire("ModuleUnlocked", player, moduleId)
	ps().Sync(player, "UnlockedModules")
	ps().Sound(player, "Success")
	ps().Toast(player, string.format(Strings.Unlocked, def.Name), "success")
	return true
end

-- ───────────────────────── creature ─────────────────────────

local function occupiedCells(profile, exceptUid)
	local set = {}
	for uid, c in pairs(profile.Creatures) do
		if c.x ~= nil and uid ~= exceptUid then
			set[GridUtil.Key(c.x, c.z)] = "creature"
		end
	end
	for _, d in ipairs(profile.Decorations.Placed) do
		set[GridUtil.Key(d.x, d.z)] = "deco"
	end
	for _, m in ipairs(profile.LastValidLayout.Modules or {}) do
		for _, cell in ipairs(GridUtil.ModuleCells(Defenses.EffectiveFootprint(m.Id, m.Alt), m.x, m.z, m.Rot or 0)) do
			set[GridUtil.Key(cell.x, cell.z)] = "module"
		end
	end
	for k in pairs(GridUtil.ReservedSet()) do
		set[k] = "reserved"
	end
	return set
end

function Economy.OccupiedCells(profile)
	return occupiedCells(profile, nil)
end

function Economy.PlaceCreature(player, uid, x, z)
	local profile = data().Get(player)
	if not profile then
		return false, Strings.Error
	end
	uid = Guard.Str(uid, 32)
	x = Guard.Int(x, 0, Config.Grid.Size - 1)
	z = Guard.Int(z, 0, Config.Grid.Size - 1)
	local c = uid and profile.Creatures[uid]
	if not c or not x or not z then
		return false, Strings.Error
	end
	local occupied = occupiedCells(profile, uid)
	if occupied[GridUtil.Key(x, z)] then
		return false, "Cella occupata"
	end
	local wasPlaced = c.x ~= nil
	if not wasPlaced then
		local placedCount = 0
		for _, other in pairs(profile.Creatures) do
			if other.x ~= nil then
				placedCount += 1
			end
		end
		if placedCount >= Economy.PlotCapacity(profile) then
			return false, "Spazio esaurito: amplia il vivaio"
		end
	end
	c.x, c.z = x, z
	c.LastTick = c.LastTick or os.time()
	EventBus.Fire("CreaturePlaced", player, uid, wasPlaced)
	plots().RefreshCreature(player, uid)
	ps().Sync(player, "Creatures")
	ps().Sound(player, "Place")
	Registry.Get("GalleryService").MarkDirty(player)
	return true
end

function Economy.RemoveCreature(player, uid)
	local profile = data().Get(player)
	if not profile then
		return false, Strings.Error
	end
	uid = Guard.Str(uid, 32)
	local c = uid and profile.Creatures[uid]
	if not c or c.x == nil then
		return false, Strings.Error
	end
	-- le scintille nel buffer vengono ritirate (restano esposte)
	if (c.Buffer or 0) > 0 then
		profile.Sparks.Exposed += c.Buffer
		profile.Stats.TotalCollected += c.Buffer
		c.Buffer = 0
	end
	c.x, c.z = nil, nil
	plots().RefreshCreature(player, uid)
	plots().RefreshSparks(player)
	ps().Sync(player, "Creatures", "Sparks")
	Registry.Get("GalleryService").MarkDirty(player)
	return true
end

-- Aggiunge una creatura al profilo (bozzolo, tutorial). Ritorna uid.
function Economy.GrantCreature(player, profile, creatureId, autoPlace)
	local def = Creatures.Get(creatureId)
	if not def then
		return nil
	end
	local uid = "c" .. profile.NextCreatureUid
	profile.NextCreatureUid += 1
	profile.Creatures[uid] = { Id = creatureId, Variant = "base", Buffer = 0, LastTick = os.time() }
	local first = not profile.OwnedCreatureIds[creatureId]
	profile.OwnedCreatureIds[creatureId] = true
	profile.UnlockedVariants[creatureId] = profile.UnlockedVariants[creatureId] or { base = true }
	if autoPlace then
		local occupied = occupiedCells(profile, nil)
		local placedCount = 0
		for _, other in pairs(profile.Creatures) do
			if other.x ~= nil then
				placedCount += 1
			end
		end
		if placedCount < Economy.PlotCapacity(profile) then
			-- cerca una cella libera a spirale partendo dagli angoli interni
			local candidates = { { 2, 2 }, { 9, 2 }, { 2, 9 }, { 9, 9 }, { 2, 5 }, { 9, 6 }, { 5, 2 }, { 6, 9 }, { 1, 7 }, { 10, 4 }, { 3, 4 }, { 8, 7 } }
			for _, cand in ipairs(candidates) do
				if not occupied[GridUtil.Key(cand[1], cand[2])] then
					profile.Creatures[uid].x = cand[1]
					profile.Creatures[uid].z = cand[2]
					break
				end
			end
			if profile.Creatures[uid].x == nil then
				for x = 0, Config.Grid.Size - 1 do
					for z = 0, Config.Grid.Size - 1 do
						if not occupied[GridUtil.Key(x, z)] and profile.Creatures[uid].x == nil then
							profile.Creatures[uid].x = x
							profile.Creatures[uid].z = z
						end
					end
				end
			end
		end
	end
	if first then
		EventBus.Fire("CreatureUnlocked", player, creatureId)
	end
	plots().RefreshCreature(player, uid)
	ps().Sync(player, "Creatures", "OwnedCreatureIds", "UnlockedVariants")
	Registry.Get("GalleryService").MarkDirty(player)
	return uid
end

function Economy.SetVariant(player, uid, variantId)
	local profile = data().Get(player)
	if not profile then
		return false
	end
	local c = profile.Creatures[uid]
	if not c then
		return false
	end
	local unlocked = profile.UnlockedVariants[c.Id]
	if not (unlocked and unlocked[variantId]) then
		return false, "Variante non sbloccata"
	end
	c.Variant = variantId
	plots().RefreshCreature(player, uid)
	ps().Sync(player, "Creatures")
	return true
end

-- ───────────────────────── decorazioni ─────────────────────────

function Economy.PlaceDecoration(player, decoId, x, z, rot)
	local profile = data().Get(player)
	if not profile then
		return false, Strings.Error
	end
	decoId = Guard.Str(decoId, 32)
	x = Guard.Int(x, 0, Config.Grid.Size - 1)
	z = Guard.Int(z, 0, Config.Grid.Size - 1)
	rot = Guard.Int(rot or 0, 0, 3) or 0
	if not decoId or not Decorations.ById[decoId] or not x or not z then
		return false, Strings.Error
	end
	if not profile.Decorations.Owned[decoId] then
		return false, "Decorazione non posseduta"
	end
	if #profile.Decorations.Placed >= Decorations.MaxPlaced then
		return false, "Troppe decorazioni (massimo " .. Decorations.MaxPlaced .. ")"
	end
	local occupied = occupiedCells(profile, nil)
	if occupied[GridUtil.Key(x, z)] then
		return false, "Cella occupata"
	end
	table.insert(profile.Decorations.Placed, { Id = decoId, x = x, z = z, Rot = rot })
	EventBus.Fire("DecorationPlaced", player, decoId)
	plots().RefreshDecorations(player)
	ps().Sync(player, "Decorations")
	ps().Sound(player, "Place")
	Registry.Get("GalleryService").MarkDirty(player)
	return true
end

function Economy.RemoveDecoration(player, index)
	local profile = data().Get(player)
	if not profile then
		return false, Strings.Error
	end
	index = Guard.Int(index, 1, #profile.Decorations.Placed)
	if not index then
		return false, Strings.Error
	end
	table.remove(profile.Decorations.Placed, index)
	plots().RefreshDecorations(player)
	ps().Sync(player, "Decorations")
	Registry.Get("GalleryService").MarkDirty(player)
	return true
end

function Economy.GrantDecoration(player, profile, decoId)
	if Decorations.ById[decoId] and not profile.Decorations.Owned[decoId] then
		profile.Decorations.Owned[decoId] = true
		ps().Sync(player, "Decorations")
		return true
	end
	return false
end

-- ───────────────────────── init ─────────────────────────

function Economy.Init()
	Net.Function("Collect").OnServerInvoke = function(player, uid)
		return Economy.Collect(player, uid, false)
	end
	Net.Function("Deposit").OnServerInvoke = Economy.Deposit
	Net.Event("CollectAll").OnServerEvent:Connect(function(player)
		local ok, msg = Economy.CollectAll(player)
		if not ok and msg then
			ps().Toast(player, msg, "warning")
		end
	end)
	Net.Event("DepositAll").OnServerEvent:Connect(function(player)
		Economy.Deposit(player)
	end)
	Net.Function("UpgradeVault").OnServerInvoke = Economy.UpgradeVault
	Net.Function("UpgradePlot").OnServerInvoke = Economy.UpgradePlot
	Net.Function("UnlockModule").OnServerInvoke = Economy.UnlockModule
	Net.Function("PlaceCreature").OnServerInvoke = function(player, uid, x, z)
		if not limiter:Allow(player.UserId .. ":place") then
			return false, Strings.TooFast
		end
		return Economy.PlaceCreature(player, uid, x, z)
	end
	Net.Function("RemoveCreature").OnServerInvoke = Economy.RemoveCreature
	Net.Function("SetVariant").OnServerInvoke = function(player, uid, variantId)
		uid = Guard.Str(uid, 32)
		variantId = Guard.Str(variantId, 32)
		if not uid or not variantId then
			return false, Strings.Error
		end
		return Economy.SetVariant(player, uid, variantId)
	end
	Net.Function("PlaceDecoration").OnServerInvoke = function(player, decoId, x, z, rot)
		if not limiter:Allow(player.UserId .. ":place") then
			return false, Strings.TooFast
		end
		return Economy.PlaceDecoration(player, decoId, x, z, rot)
	end
	Net.Function("RemoveDecoration").OnServerInvoke = Economy.RemoveDecoration
end

function Economy.Start()
	EventBus.On("ProfileLoaded", function(player, profile)
		-- creatura iniziale del tutorial (in inventario finché non la posiziona)
		local hasAny = next(profile.Creatures) ~= nil
		if not hasAny then
			Economy.GrantCreature(player, profile, Creatures.StarterCreatureId, false)
		end
		applyOfflineReserve(player, profile)
		ps().Sync(player, "Creatures", "Sparks")
	end)

	task.spawn(function()
		while true do
			task.wait(Config.Production.TickSeconds)
			local now = os.time()
			for player, profile in pairs(data().GetAll()) do
				tick(player, profile, now)
			end
		end
	end)
end

return Economy
