--!nonstrict
--[[
	Config.luau
	Tutti i numeri di bilanciamento del gioco in un unico posto.
	I valori seguono l'"esempio numerico da testare" del GDD (sezione 5) e
	le regole anti-frustrazione (sezione 4.2). Sono pensati per essere
	ritoccati senza toccare la logica.
]]

local Config = {}

Config.GameName = "Il Vivaio delle Nuvole"
Config.DataVersion = 1
Config.DataStoreName = "VivaioProfili_v1"
Config.RaidPoolStoreName = "VivaioRaidPool_v1"
Config.RaidInboxStoreName = "VivaioRaidInbox_v1"
Config.GalleryStoreName = "VivaioGalleria_v1"

-- ───────────────────────────── Griglia e plot ─────────────────────────────
Config.Grid = {
	Size = 12, -- celle per lato
	CellSize = 4, -- studs per cella
	-- celle riservate al percorso di incursione (non edificabili)
	EntranceCells = { { x = 5, z = 0 }, { x = 6, z = 0 } },
	ExitCells = { { x = 5, z = 11 }, { x = 6, z = 11 } },
	PozzaCells = { { x = 5, z = 5 }, { x = 6, z = 5 }, { x = 5, z = 6 }, { x = 6, z = 6 } },
}

Config.Plots = {
	Count = 12,
	RingRadius = 300,
	PlatformSize = 64,
	Height = 0,
}

Config.Arenas = {
	Count = 8,
	Origin = Vector3.new(0, 420, 1500),
	Spacing = 220,
}

-- ───────────────────────────── Produzione ─────────────────────────────
Config.Production = {
	BaseInterval = 30, -- secondi (GDD: 10 scintille ogni 30 s)
	BufferIntervals = 6, -- la creatura accumula al massimo 6 intervalli non ritirati
	-- rendimento marginale decrescente oltre la sesta creatura (ordinate per produzione)
	DiminishingFactors = { [7] = 0.5, [8] = 0.5, [9] = 0.35, [10] = 0.35, [11] = 0.25, [12] = 0.25 },
	-- riserva offline: frazione della produzione normale, con tetto
	OfflineRateFraction = 0.25,
	OfflineCapMinutes = 120,
	OfflineCapSparks = 240,
	TickSeconds = 1,
}

-- ───────────────────────────── Cassaforte ─────────────────────────────
Config.Vault = {
	-- capienza per livello (livello 1 = base 300 dal GDD)
	Capacities = { 300, 600, 1200, 2400, 4800, 9000 },
	-- costo in scintille per salire al livello successivo (indice = livello di arrivo)
	UpgradeCosts = { [2] = 250, [3] = 600, [4] = 1200, [5] = 2400, [6] = 4500 },
}

Config.PlotSlots = {
	-- quante creature possono essere esposte per livello di espansione
	Capacities = { 6, 8, 10, 12 },
	UpgradeCosts = { [2] = 400, [3] = 1200, [4] = 2600 },
}

-- ───────────────────────────── Incursioni ─────────────────────────────
Config.Raid = {
	DurationSeconds = 90,
	MinPlausibleSeconds = 6, -- sotto questa durata il server rifiuta il successo
	MaxTakeFraction = 0.25, -- massimo 25% delle scintille esposte
	TierTakeCaps = { 90, 180, 320, 520, 800 }, -- tetto assoluto per fascia del bersaglio
	MaxLossesPerWindow = 2,
	LossWindowSeconds = 30 * 60,
	ShieldAfterLossSeconds = 20 * 60,
	NewPlayerShieldPlaytime = 2 * 60 * 60, -- 2 ore di gioco
	NewPlayerShieldMinVaultLevel = 2,
	RepeatTargetCooldown = 60 * 60, -- non riproporre lo stesso bersaglio per 1 ora
	ParticipationReward = 15,
	DefenderBonus = 45, -- bonus difesa finanziato dal sistema
	DefenderConsolationFraction = 0.2, -- consolazione in % di quanto perso
	SimulatedRewardFraction = 0.6,
	MasteryWin = 6,
	MasteryLoss = 2,
	MasteryDefend = 5,
	CandidateCount = 3,
	DazzleSeconds = 3.5, -- faro distrattore
	CheckpointRespawnDelay = 0.8,
	StartCountdown = 3,
	PoolBucketLimit = 120, -- bersagli per fascia conservati nel pool
	InboxLimit = 30,
	AttackerCooldownSeconds = 20,
}

-- fasce di progressione (in base alla cassaforte + numero creature)
Config.Tiers = {
	-- punteggio = livello cassaforte*2 + creature possedute
	Thresholds = { 0, 8, 14, 20, 28 },
}

-- ───────────────────────────── Difesa ─────────────────────────────
Config.Defense = {
	EnergyBudget = 100,
	MaxObstacles = 3,
	MaxDistractions = 2,
	MaxSignature = 1,
	TestIsFree = true,
}

-- ───────────────────────────── Commissioni ─────────────────────────────
Config.Commissions = {
	DailyCount = 3,
	FreeRerollsPerDay = 1,
	Categories = { "raccolta", "costruzione", "visita", "incursione" },
}

-- ───────────────────────────── Bozzoli ─────────────────────────────
Config.Cocoon = {
	FragmentCost = 8,
}

-- ───────────────────────────── Galleria / social ─────────────────────────────
Config.Gallery = {
	VisitRewardSparks = 20,
	VisitRewardsPerDay = 3,
	LikesPerDay = 5,
	ListLimit = 24,
}

-- ───────────────────────────── Maestria ─────────────────────────────
Config.Mastery = {
	Tiers = { 10, 30, 60, 100, 160 },
	CollectionPerCreature = 6,
	CollectionPerVariant = 4,
	DefensePerPublish = 2,
}

-- ───────────────────────────── Tutorial ─────────────────────────────
Config.Tutorial = {
	Steps = 5,
	FreeDecorationChoices = { "lanterna_nube", "cespuglio_stellato" },
}

-- ───────────────────────────── Economia / anti-exploit ─────────────────────────────
Config.Limits = {
	InteractDistance = 14,
	CollectAllDistance = 48,
	MaxRemoteCallsPerMinute = 240,
	AutosaveSeconds = 60,
	StateSyncMaxPerSecond = 10,
}

Config.StyleTokens = {
	PerCommission = 5,
	PerAlbumMilestone = 10,
	WeeklyChallenge = 25,
	PerMasteryTier = 15,
}

-- ───────────────────────────── Suoni (asset integrati Roblox, nessuna dipendenza esterna) ─────────────────────────────
Config.Sounds = {
	Collect = "rbxasset://sounds/electronicpingshort.wav",
	Deposit = "rbxasset://sounds/snap.wav",
	Click = "rbxasset://sounds/button.wav",
	Place = "rbxasset://sounds/switch.wav",
	Error = "rbxasset://sounds/uuhhh.mp3",
	Success = "rbxasset://sounds/victory.wav",
	Whoosh = "rbxasset://sounds/swoosh.wav",
	Splash = "rbxasset://sounds/impact_water.mp3",
	Sentinel = "rbxasset://sounds/flashbulb.wav",
	Chime = "rbxasset://sounds/bass.wav",
}

-- ID prodotti Robux (0 = disattivato, nessun pulsante mostrato). Da compilare nel Creator Dashboard.
Config.Monetization = {
	FounderGamePassId = 0,
	CosmeticPassGamePassId = 0,
	-- cosmeticId -> DeveloperProductId
	CosmeticProducts = {},
}

return Config
