--!nonstrict
--[[
	RaidService: incursioni asincrone istanziate.
	- Matchmaking per fascia, difficoltà del layout e tasso di successo recente; esclude
	  bersagli con scudo, con 2 perdite nella finestra di 30 minuti, protetti (nuovi) o
	  già colpiti di recente. Nessuna identità mostrata.
	- Arena: copia del layout difensivo del bersaglio; ostacoli simulati dal server
	  (sentinelle, piattaforme, campana, ponte, faro). Errori → checkpoint, mai combattimento.
	- Esiti verificati dal server: bottino ≤ 25% delle esposte e ≤ tetto di fascia; difensore
	  riceve bonus (sistema) o consolazione; proprietari offline ricevono tutto via inbox.
]]
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")

local Shared = ReplicatedStorage.Shared
local Config = require(Shared.Config)
local Strings = require(Shared.Strings)
local Creatures = require(Shared.Catalog.Creatures)
local Simulated = require(Shared.Catalog.SimulatedVivai)
local LayoutValidator = require(Shared.LayoutValidator)
local PlotBuilder = require(Shared.Models.PlotBuilder)
local ModuleModel = require(Shared.Models.ModuleModel)
local Net = require(Shared.Util.Net)
local TableUtil = require(Shared.Util.TableUtil)

local Registry = require(script.Parent.Parent.Registry)
local EventBus = require(script.Parent.Parent.EventBus)
local Guard = require(script.Parent.Parent.Util.Guard)
local Logger = require(script.Parent.Parent.Util.Logger)
local RateLimiter = require(script.Parent.Parent.Util.RateLimiter)
local PoolStore = require(script.Parent.PoolStore)
local ArenaPool = require(script.Parent.Parent.World.ArenaPool)

local RaidService = {}
local R = Config.Raid

local offered = {} -- player -> { [key] = targetInfo }
local active = {} -- player -> raid
local limiter = RateLimiter.new(6, 0.5)

local function data()
	return Registry.Get("DataService")
end
local function ps()
	return Registry.Get("PlayerService")
end
local function eco()
	return Registry.Get("EconomyService")
end
local function send(player, name, payload)
	if player.Parent then
		Net.Event("RaidEvent"):FireClient(player, name, payload or {})
	end
end

-- ───────────────────────── matchmaking ─────────────────────────

local function recentLossCount(lossTs, now)
	local n = 0
	for _, t in ipairs(lossTs or {}) do
		if now - t < R.LossWindowSeconds then
			n += 1
		end
	end
	return n
end

local function successRate(profile)
	local results = profile.Raid.RecentResults
	if #results == 0 then
		return 0.5
	end
	local s = 0
	for _, r in ipairs(results) do
		s += r
	end
	return s / #results
end

local function maxTakeFor(exposed, tier)
	return math.min(math.floor(exposed * R.MaxTakeFraction), R.TierTakeCaps[math.clamp(tier, 1, #R.TierTakeCaps)])
end

local function simulatedTarget(sim)
	return {
		Key = sim.Key,
		Name = sim.Name,
		Tier = sim.Tier,
		Difficulty = LayoutValidator.DifficultyStars(LayoutValidator.Validate(sim.Layout, {}).Difficulty or 0),
		ExposedEstimate = sim.Exposed,
		MaxTake = math.floor(maxTakeFor(sim.Exposed, sim.Tier) * R.SimulatedRewardFraction),
		Simulated = true,
		ModuleCount = #sim.Layout.Modules,
		Snapshot = sim,
	}
end

function RaidService.RequestTargets(player)
	local profile = data().Get(player)
	if not profile then
		return nil
	end
	if not limiter:Allow(player.UserId .. ":targets") then
		return nil, Strings.TooFast
	end
	local now = os.time()
	local myTier = eco().Tier(profile)
	local rate = successRate(profile)
	local candidates = {}
	for tier = math.max(1, myTier - 1), math.min(#R.TierTakeCaps, myTier + 1) do
		for id, e in pairs(PoolStore.GetBucket(tier)) do
			local uid = tonumber(id)
			local ok = uid ~= player.UserId
				and (e.Updated or 0) > now - 7 * 86400
				and (e.ShieldUntil or 0) < now
				and not e.Protected
				and recentLossCount(e.LossTs, now) < R.MaxLossesPerWindow
				and (e.Exposed or 0) >= 40
				and (profile.Raid.RecentTargets["u_" .. id] or 0) < now - R.RepeatTargetCooldown
				and e.Layout ~= nil
			-- un proprietario online in questo server e in incursione/visita va bene comunque: la copia è istanziata
			if ok then
				-- punteggio: preferisci difficoltà adatta al tasso di successo e fascia vicina
				local stars = e.Stars or 1
				local desired = 1 + rate * 4 -- chi vince spesso vede layout più difficili
				local score = -math.abs(stars - desired) * 2 - math.abs(tier - myTier) * 1.5 + math.random() * 0.8
				table.insert(candidates, { Entry = e, Tier = tier, Score = score, UserId = uid })
			end
		end
	end
	table.sort(candidates, function(a, b)
		return a.Score > b.Score
	end)
	local list = {}
	local offer = {}
	for i = 1, math.min(#candidates, R.CandidateCount - 1) do
		local c = candidates[i]
		local e = c.Entry
		local t = {
			Key = "u_" .. c.UserId,
			Name = "Vivaio rivale · fascia " .. c.Tier, -- nessuna identità
			Tier = c.Tier,
			Difficulty = e.Stars or 1,
			ExposedEstimate = e.Exposed or 0,
			MaxTake = maxTakeFor(e.Exposed or 0, c.Tier),
			Simulated = false,
			ModuleCount = #((e.Layout and e.Layout.Modules) or {}),
		}
		table.insert(list, t)
		offer[t.Key] = { Info = t, Snapshot = e, Tier = c.Tier, UserId = c.UserId }
	end
	-- almeno un Vivaio del Guardiano, sempre
	local sims = Simulated.ForTier(myTier)
	TableUtil.Shuffle(sims)
	for i = 1, math.max(1, R.CandidateCount - #list) do
		local sim = sims[((i - 1) % #sims) + 1]
		if sim and not offer[sim.Key] then
			local t = simulatedTarget(sim)
			table.insert(list, t)
			offer[t.Key] = { Info = t, Snapshot = sim, Simulated = true }
		end
	end
	-- tutorial: proponi l'allenamento
	if profile.Tutorial.Active and profile.Tutorial.Step == 4 then
		local sim = Simulated.ByKey.sim_allenamento
		local t = simulatedTarget(sim)
		table.insert(list, 1, t)
		offer[t.Key] = { Info = t, Snapshot = sim, Simulated = true }
	end
	offered[player] = offer
	return { Targets = list, Cooldown = math.max(0, (profile.Raid.LastRaidAt + R.AttackerCooldownSeconds) - now) }
end

-- ───────────────────────── istanza ─────────────────────────

local function viewFromSnapshot(snapshot, simulated)
	local creatures = {}
	for i, c in ipairs(snapshot.Creatures or {}) do
		table.insert(creatures, { Uid = "r" .. i, Id = c.Id, Variant = c.Variant or "base", x = c.x, z = c.z, Buffer = 0 })
	end
	return {
		Creatures = creatures,
		Layout = snapshot.Layout or { Modules = {} },
		Decorations = snapshot.Decorations or {},
		Skin = snapshot.Skin or "skin_prato",
		Exposed = snapshot.Exposed or 0,
	}
end

local function setupRuntime(raid)
	local plot = raid.Plot
	local rt = { Sentinels = {}, Platforms = {}, Zones = {}, Faro = {}, Bridges = {}, Bell = nil }
	for _, model in ipairs(plot.Folders.Modules:GetChildren()) do
		local id = model:GetAttribute("ModuleId")
		local root = model.PrimaryPart
		if id == "sentinella" then
			local cone = model:FindFirstChild("Cone")
			local pillar = model:FindFirstChild("Pillar")
			if cone and pillar and root then
				table.insert(rt.Sentinels, {
					Model = model, Root = root, Cone = cone, Base = root.Position, Radius = cone:GetAttribute("Radius") or 9,
					Arc = cone:GetAttribute("Arc") or 50, Speed = cone:GetAttribute("Speed") or 55, Erratic = cone:GetAttribute("Erratic") == true,
					Offset = math.random() * 360,
				})
			end
		elseif id == "piattaforma" then
			for _, name in ipairs({ "Platform", "Platform2" }) do
				local p = model:FindFirstChild(name)
				if p and root then
					table.insert(rt.Platforms, { Part = p, Root = root, Period = p:GetAttribute("Period") or 3.2, Travel = p:GetAttribute("Travel") or 8, Phase = p:GetAttribute("Phase") or 0, LastPos = p.Position })
				end
			end
		elseif id == "corrente" then
			local zone = model:FindFirstChild("Zone")
			if zone then
				table.insert(rt.Zones, { Zone = zone, Pulse = zone:GetAttribute("Pulse") == true, Period = zone:GetAttribute("PulsePeriod") or 2.4 })
			end
		elseif id == "faro" and root then
			table.insert(rt.Faro, { Root = root, Radius = root:GetAttribute("TriggerRadius") or 3.2, Dazzle = root:GetAttribute("Dazzle") or 3.5 })
		elseif id == "arcobaleno" then
			local bridge = model:FindFirstChild("Bridge")
			if bridge then
				local stripes = {}
				for _, s in ipairs(model:GetChildren()) do
					if s:GetAttribute("BridgeVisual") then
						table.insert(stripes, s)
					end
				end
				table.insert(rt.Bridges, { Part = bridge, Stripes = stripes, Period = bridge:GetAttribute("Period") or 4 })
			end
		elseif id == "campana" and root then
			rt.Bell = { Root = root, Fraction = root:GetAttribute("TriggerFraction") or 0.5, Rung = false }
		end
	end
	raid.Runtime = rt
end

local function teleportToCheckpoint(raid, reason)
	local player = raid.Player
	local char = player.Character
	if char and char.PrimaryPart then
		char:PivotTo(raid.Checkpoint)
		local hrp = char.PrimaryPart
		hrp.AssemblyLinearVelocity = Vector3.zero
	end
	raid.Checkpoints += 1
	raid.LastTeleport = os.clock()
	send(player, "Checkpoint", { Reason = reason })
	ps().Sound(player, "Whoosh")
end

local function dazzle(raid, seconds)
	local player = raid.Player
	local char = player.Character
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	if not hum or raid.DazzledUntil > os.clock() then
		return
	end
	raid.DazzledUntil = os.clock() + seconds
	raid.DazzleCount += 1
	hum.WalkSpeed = 0
	hum.JumpPower = 0
	hum.UseJumpPower = true
	send(player, "Dazzled", { Seconds = seconds })
	ps().Sound(player, "Sentinel")
	task.delay(seconds, function()
		if active[player] == raid and hum.Parent then
			hum.WalkSpeed = 18
			hum.JumpPower = 50
		end
	end)
end

local function progressFraction(raid, hrp)
	local origin = raid.Slot.Origin
	local lp = origin:PointToObjectSpace(hrp.Position)
	-- da z=-32 (ingresso) a 0 (pozza) a +32 (uscita)
	if raid.Phase == 1 then
		return math.clamp((lp.Z + 32) / 32, 0, 1) * 0.5
	end
	return 0.5 + math.clamp(lp.Z / 32, 0, 1) * 0.5
end

local function step(raid, dt)
	local player = raid.Player
	local char = player.Character
	local hrp = char and char.PrimaryPart
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	local now = os.clock()
	if not hrp or not hum or hum.Health <= 0 then
		-- personaggio in respawn: tolleriamo fino a 12 s, poi consideriamo abbandono
		raid.MissingSince = raid.MissingSince or now
		if now - raid.MissingSince > 12 then
			return "abbandono"
		end
		return nil
	end
	raid.MissingSince = nil
	local t = now - raid.StartTime
	local rt = raid.Runtime
	local origin = raid.Slot.Origin

	if raid.Countdown then
		if t >= R.StartCountdown then
			raid.Countdown = false
			raid.StartTime = now
			send(player, "Go")
			t = 0
		else
			return nil
		end
	end

	if t >= raid.Duration then
		return "tempo"
	end

	-- caduta
	if hrp.Position.Y < origin.Y - 25 then
		raid.Falls += 1
		teleportToCheckpoint(raid, "caduta")
		return nil
	end

	-- anti-exploit leggero: spostamenti impossibili
	if raid.LastPos and now - raid.LastTeleport > 0.6 then
		local speed = (hrp.Position - raid.LastPos).Magnitude / math.max(dt, 1 / 60)
		if speed > 140 then
			raid.Anomalies += 1
			teleportToCheckpoint(raid, "anomalia")
			return nil
		end
	end
	raid.LastPos = hrp.Position

	-- sentinelle
	for _, s in ipairs(rt.Sentinels) do
		local angle = s.Offset + t * s.Speed
		if s.Erratic then
			angle += math.sin(t * 1.7) * 45
		end
		local baseCF = ModuleModel.OrientSentinel(s.Model, angle) or CFrame.new(s.Base)
		local rel = hrp.Position - s.Base
		local flat = Vector3.new(rel.X, 0, rel.Z)
		if flat.Magnitude <= s.Radius and rel.Y > -3 and rel.Y < 7 and raid.DazzledUntil < now and now - raid.LastTeleport > 0.8 then
			-- direzione del cono: -Z locale ruotata
			local coneDir = baseCF.LookVector
			local cosang = flat.Unit:Dot(coneDir)
			if cosang >= math.cos(math.rad(s.Arc / 2)) then
				raid.SentinelHits += 1
				send(player, "Spotted")
				teleportToCheckpoint(raid, "sentinella")
				return nil
			end
		end
	end

	-- piattaforme mobili (anchored + velocità per trasportare il personaggio)
	for _, p in ipairs(rt.Platforms) do
		local phase = (t / p.Period + p.Phase) * math.pi * 2
		local z = math.sin(phase) * (p.Travel / 2)
		local target = p.Root.CFrame * CFrame.new(0, 0.1, z)
		local newPos = target.Position
		p.Part.CFrame = CFrame.new(newPos) * (p.Root.CFrame - p.Root.CFrame.Position)
		p.Part.AssemblyLinearVelocity = (newPos - p.LastPos) / math.max(dt, 1 / 60)
		p.LastPos = newPos
	end

	-- correnti pulsanti
	for _, z in ipairs(rt.Zones) do
		if z.Pulse then
			local on = (t % z.Period) < z.Period * 0.55
			if z.Zone:GetAttribute("Active") ~= on then
				z.Zone:SetAttribute("Active", on)
			end
		end
	end

	-- campana del vento: inverte le correnti a metà tempo
	if rt.Bell and not rt.Bell.Rung and t >= raid.Duration * rt.Bell.Fraction then
		rt.Bell.Rung = true
		for _, z in ipairs(rt.Zones) do
			z.Zone:SetAttribute("Dir", -(z.Zone:GetAttribute("Dir") or 1))
		end
		send(player, "Bell")
		ps().Sound(player, "Chime")
	end

	-- ponte arcobaleno intermittente
	for _, b in ipairs(rt.Bridges) do
		local visible = (t % b.Period) < b.Period * 0.5
		if b.Part:GetAttribute("Visible") ~= visible then
			b.Part:SetAttribute("Visible", visible)
			b.Part.CanCollide = visible
			b.Part.Transparency = visible and 0.1 or 0.9
			for _, s in ipairs(b.Stripes) do
				s.Transparency = visible and 0.15 or 0.95
			end
		end
	end

	-- faro distrattore
	for _, f in ipairs(rt.Faro) do
		if raid.DazzledUntil < now and (hrp.Position - f.Root.Position).Magnitude <= f.Radius + 1.5 then
			dazzle(raid, f.Dazzle)
		end
	end

	-- obiettivi
	local plot = raid.Plot
	if raid.Phase == 1 then
		local rel = hrp.Position - plot.Pozza.Position
		if Vector3.new(rel.X, 0, rel.Z).Magnitude <= 4.6 and math.abs(rel.Y) < 7 then
			raid.Phase = 2
			raid.PozzaAt = t
			raid.Checkpoint = CFrame.new(plot.Pozza.Position + Vector3.new(0, 4, 0))
			plot.Pozza.Color = Color3.fromRGB(190, 200, 230)
			plot.PozzaEmitter.Enabled = false
			send(player, "Collected", { Amount = raid.Info.MaxTake })
			ps().Sound(player, "Collect")
		end
	else
		local rel = hrp.Position - plot.Exit.Position
		if Vector3.new(rel.X, 0, rel.Z).Magnitude <= 4 and rel.Y > -2 and rel.Y < 8 then
			return "successo"
		end
	end
	return nil
end

-- ───────────────────────── esiti ─────────────────────────

local function pushHistory(profile, entry)
	table.insert(profile.Raid.History, entry)
	TableUtil.Truncate(profile.Raid.History, 10)
end

-- Applica una perdita al difensore (online qui o tramite inbox già scaricata)
function RaidService.ApplyLoss(player, profile, item)
	if profile.Raid.AppliedInbox[item.RaidId] then
		return
	end
	profile.Raid.AppliedInbox[item.RaidId] = true
	table.insert(profile.Raid.AppliedInboxOrder, item.RaidId)
	while #profile.Raid.AppliedInboxOrder > 60 do
		local old = table.remove(profile.Raid.AppliedInboxOrder, 1)
		profile.Raid.AppliedInbox[old] = nil
	end
	local now = os.time()
	-- scudo o finestra già saturi (raid partiti da un'istantanea vecchia): la perdita decade
	if profile.Raid.ShieldUntil > now or recentLossCount(profile.Raid.LossTimestamps, now) >= R.MaxLossesPerWindow or Registry.Get("PlayerService").HasNewPlayerShield(profile) then
		return
	end
	local exposedNow = eco().ExposedTotal(profile)
	local amount = math.min(item.Amount or 0, math.floor(exposedNow * R.MaxTakeFraction))
	if amount <= 0 then
		return
	end
	eco().RemoveExposed(player, profile, amount)
	table.insert(profile.Raid.LossTimestamps, now)
	while #profile.Raid.LossTimestamps > 10 do
		table.remove(profile.Raid.LossTimestamps, 1)
	end
	profile.Raid.ShieldUntil = now + R.ShieldAfterLossSeconds
	profile.Raid.Lost += 1
	profile.Stats.RaidsLost += 1
	local consolation = math.max(5, math.floor(amount * R.DefenderConsolationFraction))
	eco().GrantSafe(player, profile, consolation, "consolation")
	pushHistory(profile, { Type = "lost", Time = now, Amount = amount, Consolation = consolation })
	EventBus.Fire("RaidLost", player, amount)
	ps().Sync(player, "Raid", "Stats")
	ps().Toast(player, string.format(Strings.RaidLostToast, amount, consolation), "warning")
	Logger.Audit("Raid", player, "loss_applied", string.format("raid=%s amount=%d", item.RaidId, amount))
	Registry.Get("GalleryService").MarkDirty(player)
end

function RaidService.ApplyDefend(player, profile, item)
	if profile.Raid.AppliedInbox[item.RaidId] then
		return
	end
	profile.Raid.AppliedInbox[item.RaidId] = true
	table.insert(profile.Raid.AppliedInboxOrder, item.RaidId)
	profile.Raid.Defended += 1
	profile.Stats.RaidsDefended += 1
	profile.Mastery.Defense += R.MasteryDefend
	eco().GrantSafe(player, profile, R.DefenderBonus, "defense_bonus")
	pushHistory(profile, { Type = "defended", Time = os.time(), Amount = R.DefenderBonus, Feedback = item.Feedback })
	EventBus.Fire("RaidDefended", player, R.DefenderBonus)
	Registry.Get("AlbumService").CheckMastery(player, profile)
	ps().Sync(player, "Raid", "Stats", "Mastery")
	ps().Toast(player, string.format(Strings.RaidDefendedToast, R.DefenderBonus), "success")
end

local function drainInbox(player, profile)
	local items = PoolStore.DrainInbox(player.UserId)
	for _, item in ipairs(items) do
		if item.Type == "loss" then
			RaidService.ApplyLoss(player, profile, item)
		elseif item.Type == "defend" then
			RaidService.ApplyDefend(player, profile, item)
		end
	end
end

local function notifyDefender(raid, success, take, feedback)
	local userId = raid.Offer.UserId
	if not userId then
		return
	end
	local raidId = raid.Id
	local item = { RaidId = raidId, Type = success and "loss" or "defend", Amount = take, Time = os.time(), Feedback = feedback }
	local victim = Players:GetPlayerByUserId(userId)
	local victimProfile = victim and data().Get(victim)
	if victimProfile then
		if success then
			RaidService.ApplyLoss(victim, victimProfile, item)
		else
			RaidService.ApplyDefend(victim, victimProfile, item)
		end
		return
	end
	PoolStore.PushInbox(userId, item)
	if success then
		-- aggiorna l'istantanea così il matchmaking rispetta scudo e finestra perdite
		PoolStore.ModifyEntry(userId, raid.Offer.Tier, function(e)
			e.Exposed = math.max(0, (e.Exposed or 0) - take)
			e.LossTs = e.LossTs or {}
			table.insert(e.LossTs, os.time())
			e.ShieldUntil = os.time() + R.ShieldAfterLossSeconds
		end)
	end
end

local function finish(raid, reason)
	local player = raid.Player
	if active[player] ~= raid then
		return
	end
	active[player] = nil
	raid.Ended = true
	local profile = data().Get(player)
	local now = os.clock()
	local duration = raid.Countdown and 0 or (now - raid.StartTime)
	local success = reason == "successo" and duration >= R.MinPlausibleSeconds and raid.Phase == 2 and raid.Anomalies < 3

	local feedback = {}
	if raid.SentinelHits > 0 then
		table.insert(feedback, string.format(Strings.RaidFeedbackSentinel, raid.SentinelHits))
	end
	if raid.Falls > 0 then
		table.insert(feedback, string.format(Strings.RaidFeedbackFall, raid.Falls))
	end
	if reason == "tempo" then
		local char = player.Character
		local frac = (char and char.PrimaryPart) and progressFraction(raid, char.PrimaryPart) or 0
		table.insert(feedback, string.format(Strings.RaidFeedbackTime, math.floor(frac * 100)))
	end
	if success and raid.Checkpoints == 0 then
		table.insert(feedback, Strings.RaidFeedbackClean)
	end

	local summary = {
		Success = success,
		Take = 0,
		Participation = 0,
		Mastery = 0,
		Feedback = feedback,
		Duration = math.floor(duration),
		Simulated = raid.Simulated,
		Test = raid.Test,
		Checkpoints = raid.Checkpoints,
		Reason = reason,
	}

	if profile and not raid.Test then
		local hum = player.Character and player.Character:FindFirstChildOfClass("Humanoid")
		if hum then
			hum.WalkSpeed = 18
			hum.JumpPower = 50
		end
		profile.Raid.Attempts += 1
		profile.Raid.LastRaidAt = os.time()
		table.insert(profile.Raid.RecentResults, success and 1 or 0)
		TableUtil.Truncate(profile.Raid.RecentResults, 10)
		if success then
			local take = raid.Info.MaxTake
			if raid.Simulated then
				take = math.floor(maxTakeFor(raid.Offer.Snapshot.Exposed, raid.Offer.Snapshot.Tier) * R.SimulatedRewardFraction)
			else
				-- ricalcola sull'istantanea più recente (il bersaglio potrebbe aver depositato)
				local fresh = PoolStore.FindByUserId(raid.Offer.UserId)
				local exposed = fresh and fresh.Exposed or raid.Offer.Snapshot.Exposed
				local victim = Players:GetPlayerByUserId(raid.Offer.UserId)
				local victimProfile = victim and data().Get(victim)
				if victimProfile then
					exposed = eco().ExposedTotal(victimProfile)
				end
				take = maxTakeFor(exposed, raid.Offer.Tier)
			end
			summary.Take = take
			summary.Mastery = R.MasteryWin
			profile.Raid.Successes += 1
			profile.Stats.RaidsWon += 1
			eco().GrantExposed(player, profile, take, raid.Simulated and "raid_sim" or "raid")
		else
			if duration >= 20 or raid.Phase == 2 then
				summary.Participation = R.ParticipationReward
				eco().GrantSafe(player, profile, R.ParticipationReward, "raid_participation")
			end
			summary.Mastery = R.MasteryLoss
		end
		if not raid.Simulated then
			profile.Raid.RecentTargets[raid.Offer.Key] = os.time()
			-- pulizia bersagli vecchi
			for k, t in pairs(profile.Raid.RecentTargets) do
				if os.time() - t > R.RepeatTargetCooldown then
					profile.Raid.RecentTargets[k] = nil
				end
			end
			notifyDefender(raid, success, summary.Take, feedback)
		end
		pushHistory(profile, { Type = success and "won" or "failed", Time = os.time(), Amount = summary.Take + summary.Participation, Stars = raid.Info.Difficulty, Simulated = raid.Simulated })
		Registry.Get("AlbumService").AddMastery(player, "Raid", summary.Mastery)
		ps().Sync(player, "Raid", "Stats", "Sparks")
		EventBus.Fire("RaidCompleted", player, summary)
		Logger.Audit("Raid", player, success and "success" or "fail", string.format("id=%s target=%s take=%d reason=%s dur=%d", raid.Id, raid.Info.Key, summary.Take, reason, summary.Duration))
	elseif profile and raid.Test then
		EventBus.Fire("LayoutTested", player)
		EventBus.Fire("RaidCompleted", player, summary)
	end

	send(player, "Summary", summary)
	ps().Sound(player, success and "Success" or "Error")
	Registry.Get("PlotService").SetLocation(player, "home")
	task.delay(0.3, function()
		if player.Parent then
			Registry.Get("PlotService").TeleportHome(player)
		end
	end)
	task.delay(2, function()
		ArenaPool.Release(raid.Slot)
	end)
end

-- ───────────────────────── avvio ─────────────────────────

local function begin(player, profile, offer, test)
	local slot = ArenaPool.Acquire(test and "test" or "raid")
	if not slot then
		return false, "Tutte le arene sono occupate, riprova tra poco"
	end
	local view = viewFromSnapshot(offer.Snapshot, offer.Simulated)
	local plot = PlotBuilder.Build(slot.Folder, slot.Origin, view, "raid")
	local raid = {
		Id = HttpService:GenerateGUID(false),
		Player = player,
		Slot = slot,
		Plot = plot,
		Offer = offer,
		Info = offer.Info,
		Simulated = offer.Simulated == true,
		Test = test == true,
		StartTime = os.clock(),
		Countdown = true,
		Duration = R.DurationSeconds,
		Phase = 1,
		Checkpoint = plot:EntranceCFrame(),
		Checkpoints = 0,
		Falls = 0,
		SentinelHits = 0,
		DazzleCount = 0,
		Anomalies = 0,
		DazzledUntil = 0,
		LastTeleport = os.clock(),
		LastPos = nil,
	}
	setupRuntime(raid)
	active[player] = raid
	Registry.Get("GalleryService").EndVisit(player)
	Registry.Get("PlotService").SetLocation(player, "raid")
	local char = player.Character
	if char and char.PrimaryPart then
		char:PivotTo(raid.Checkpoint)
		char.PrimaryPart.AssemblyLinearVelocity = Vector3.zero
	end
	send(player, "Start", {
		Duration = R.DurationSeconds,
		Countdown = R.StartCountdown,
		TargetName = offer.Info.Name,
		Simulated = raid.Simulated,
		Test = raid.Test,
		MaxTake = offer.Info.MaxTake,
		Difficulty = offer.Info.Difficulty,
	})
	ps().Sound(player, "Whoosh")
	return true
end

function RaidService.StartRaid(player, key)
	local profile = data().Get(player)
	if not profile then
		return false, Strings.Error
	end
	if active[player] then
		return false, "Sei già in un'incursione"
	end
	key = Guard.Str(key, 32)
	local offer = key and offered[player] and offered[player][key]
	if not offer then
		return false, "Bersaglio non più disponibile: aggiorna la lista"
	end
	local now = os.time()
	local remaining = (profile.Raid.LastRaidAt + R.AttackerCooldownSeconds) - now
	if remaining > 0 then
		return false, string.format(Strings.RaidCooldown, remaining)
	end
	if not offer.Simulated then
		-- ricontrolla lo stato fresco del bersaglio
		local fresh = PoolStore.FindByUserId(offer.UserId)
		if fresh then
			if (fresh.ShieldUntil or 0) > now or recentLossCount(fresh.LossTs, now) >= R.MaxLossesPerWindow or fresh.Protected then
				offered[player][key] = nil
				return false, "Questo vivaio è protetto al momento. Scegli un altro bersaglio."
			end
			offer.Snapshot = fresh
			offer.Info.ExposedEstimate = fresh.Exposed or 0
			offer.Info.MaxTake = maxTakeFor(fresh.Exposed or 0, offer.Tier)
		end
	end
	offered[player] = nil
	return begin(player, profile, offer, false)
end

function RaidService.StartTest(player)
	local profile = data().Get(player)
	if not profile then
		return false, Strings.Error
	end
	if active[player] then
		return false, "Sei già in un'incursione"
	end
	-- usa il layout in modifica se valido, altrimenti l'ultimo pubblicato
	local layout = profile.Layout
	local res = Registry.Get("DefenseService").Validate(profile, layout)
	if not res.Ok then
		layout = profile.LastValidLayout
		res = LayoutValidator.Validate(layout, {})
	end
	local snapshot = Registry.Get("GalleryService").BuildSnapshot(player, profile)
	snapshot.Layout = layout
	local info = {
		Key = "test",
		Name = Strings.RaidTestTitle,
		Tier = snapshot.Tier,
		Difficulty = LayoutValidator.DifficultyStars(res.Difficulty or 0),
		ExposedEstimate = snapshot.Exposed,
		MaxTake = 0,
		Simulated = true,
		ModuleCount = #(layout.Modules or {}),
	}
	return begin(player, profile, { Info = info, Snapshot = snapshot, Simulated = true, Test = true }, true)
end

function RaidService.Abort(player, reason)
	local raid = active[player]
	if raid then
		finish(raid, reason or "abbandono")
	end
end

function RaidService.IsInRaid(player)
	return active[player] ~= nil
end

function RaidService.Init()
	ArenaPool.Init()
	Net.Function("RequestRaidTargets").OnServerInvoke = RaidService.RequestTargets
	Net.Function("StartRaid").OnServerInvoke = function(player, key)
		if not limiter:Allow(player.UserId .. ":start", 2) then
			return false, Strings.TooFast
		end
		return RaidService.StartRaid(player, key)
	end
	Net.Event("RaidAbort").OnServerEvent:Connect(function(player)
		RaidService.Abort(player, "abbandono")
	end)
end

function RaidService.Start()
	RunService.Heartbeat:Connect(function(dt)
		for player, raid in pairs(active) do
			if not raid.Ended then
				local ok, result = pcall(step, raid, dt)
				if not ok then
					Logger.Warn("Raid", "Errore nello step:", result)
					finish(raid, "errore")
				elseif result then
					finish(raid, result)
				end
			end
		end
	end)
	Players.PlayerRemoving:Connect(function(player)
		local raid = active[player]
		if raid then
			finish(raid, "abbandono")
		end
		offered[player] = nil
	end)
	EventBus.On("ProfileLoaded", function(player, profile)
		task.delay(2, function()
			if player.Parent then
				drainInbox(player, profile)
			end
		end)
	end)
	-- controllo periodico della inbox per i giocatori online (esiti di raid subiti altrove)
	task.spawn(function()
		while true do
			task.wait(120)
			for player, profile in pairs(data().GetAll()) do
				task.spawn(drainInbox, player, profile)
				task.wait(0.5)
			end
		end
	end)
	-- la morte del personaggio durante un raid riporta al checkpoint (non termina il raid)
	Players.PlayerAdded:Connect(function(player)
		player.CharacterAdded:Connect(function(char)
			local raid = active[player]
			if raid then
				task.wait(0.3)
				if active[player] == raid then
					teleportToCheckpoint(raid, "respawn")
				end
			end
		end)
	end)
end

return RaidService
