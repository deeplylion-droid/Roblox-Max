--!nonstrict
-- Test unitari dei moduli condivisi (eseguiti da scripts/run_tests.py con il CLI luau)
local Config = require("./Config")
local Creatures = require("./Creatures")
local Defenses = require("./Defenses")
local Validator = require("./LayoutValidator")
local GridUtil = require("./GridUtil")
local TableUtil = require("./TableUtil")
local TimeUtil = require("./TimeUtil")
local Format = require("./Format")
local Album = require("./Album")
local Cosmetics = require("./Cosmetics")
local Commissions = require("./Commissions")
local Simulated = require("./SimulatedVivai")
local DefaultData = require("./DefaultData")

local passed, failed = 0, 0
local function check(name, cond, detail)
	if cond then
		passed += 1
		print("  ✔ " .. name)
	else
		failed += 1
		print("  ✖ " .. name .. (detail and ("  → " .. tostring(detail)) or ""))
	end
end

print("Catalogo creature")
check("16 creature", #Creatures.List == 16, #Creatures.List)
for _, fam in ipairs(Creatures.Families) do
	check("famiglia " .. fam .. " ha 4 creature", #Creatures.ByFamily[fam] == 4)
	local orders = {}
	for _, c in ipairs(Creatures.ByFamily[fam]) do
		orders[c.UnlockOrder] = true
		check(c.Id .. " ha 4 varianti", #c.Variants == 4)
	end
	check("ordine di sblocco 1..4 in " .. fam, orders[1] and orders[2] and orders[3] and orders[4])
end
check("prossima mancante deterministica", Creatures.NextMissingInFamily("sole", { sole_lumino = true }).Id == "sole_raggiolo")
check("famiglia completa → nil", Creatures.NextMissingInFamily("sole", { sole_lumino = true, sole_raggiolo = true, sole_meriggia = true, sole_solstizia = true }) == nil)

print("Catalogo difese")
local cats = { ostacolo = 0, distrazione = 0, firma = 0 }
for _, m in ipairs(Defenses.List) do
	cats[m.Category] += 1
	check(m.Id .. " energia ≤ budget", m.Energy <= Config.Defense.EnergyBudget)
end
check("almeno 4 ostacoli, 3 distrazioni, 3 firme", cats.ostacolo >= 4 and cats.distrazione >= 3 and cats.firma >= 3)
check("muraglia ha footprint 3", #Defenses.EffectiveFootprint("muro_nube", "lungo") == 3)
check("parametri alternativa sovrascrivono", Defenses.EffectiveParams("sentinella", "ampia").Arc == 90)

print("Griglia")
check("rotazione footprint", (function()
	local r = GridUtil.RotateFootprint({ { 1, 0 } }, 1)
	return r[1][1] == 0 and r[1][2] == 1
end)())
check("celle riservate = 8", TableUtil.Count(GridUtil.ReservedSet()) == 8)
check("key/fromkey", (function()
	local x, z = GridUtil.FromKey(GridUtil.Key(3, 11))
	return x == 3 and z == 11
end)())

print("Validatore layout")
local unlockedAll = {}
for _, m in ipairs(Defenses.List) do
	unlockedAll[m.Id] = true
end
local r = Validator.Validate({ Modules = {} }, {})
check("layout vuoto valido con percorso", r.Ok and r.Path ~= nil and #r.Path > 0)
r = Validator.Validate({ Modules = { { Id = "corrente", x = 5, z = 3, Rot = 0 } } }, { UnlockedModules = unlockedAll })
check("corrente al centro valida", r.Ok, r.Reason)
check("energia conteggiata", r.Energy == 20)
r = Validator.Validate({ Modules = { { Id = "muro_nube", x = 5, z = 0, Rot = 0 } } }, {})
check("cella riservata rifiutata", not r.Ok and r.Reason:find("riservata") ~= nil, r.Reason)
r = Validator.Validate({ Modules = { { Id = "muro_nube", x = 11, z = 3, Rot = 0 } } }, {})
check("fuori griglia rifiutato", not r.Ok and r.Reason:find("griglia") ~= nil, r.Reason)
r = Validator.Validate({ Modules = { { Id = "corrente", x = 5, z = 3 }, { Id = "corrente", x = 6, z = 3 } } }, {})
check("sovrapposizione rifiutata", not r.Ok and r.Reason:find("sovrappone") ~= nil, r.Reason)
r = Validator.Validate({ Modules = { { Id = "sentinella", x = 2, z = 2 }, { Id = "sentinella", x = 8, z = 2 }, { Id = "sentinella", x = 2, z = 8 }, { Id = "sentinella", x = 8, z = 8 } } }, {})
check("4 ostacoli rifiutati", not r.Ok and r.Reason:find("ostacoli") ~= nil, r.Reason)
r = Validator.Validate({ Modules = { { Id = "sentinella", x = 2, z = 2 }, { Id = "sentinella", x = 8, z = 2 }, { Id = "sentinella", x = 2, z = 8 }, { Id = "nebbia", x = 8, z = 8 } } }, {})
check("oltre budget energia rifiutato (110)", not r.Ok and r.Reason:find("Energia") ~= nil, r.Reason)
r = Validator.Validate({ Modules = { { Id = "sentinella", x = 2, z = 2 } } }, { UnlockedModules = { corrente = true } })
check("modulo non sbloccato rifiutato", not r.Ok and r.Reason:find("sbloccato") ~= nil, r.Reason)
r = Validator.Validate({ Modules = { { Id = "corrente", x = 3, z = 3 } } }, { CreatureCells = { [GridUtil.Key(3, 3)] = true } })
check("sovrapposizione creatura rifiutata", not r.Ok and r.Reason:find("creatura") ~= nil, r.Reason)
r = Validator.Validate({ Modules = { { Id = "muro_nube", x = 3, z = 3, Alt = "lungo" } } }, { UnlockedAlternatives = {} })
check("alternativa non sbloccata rifiutata", not r.Ok, r.Reason)
r = Validator.Validate({ Modules = { { Id = "muro_nube", x = 3, z = 3, Alt = "lungo" } } }, { UnlockedAlternatives = { muro_nube = { lungo = true } } })
check("alternativa sbloccata accettata", r.Ok, r.Reason)
-- percorso: muro davanti all'ingresso costringe a deviare, resta valido
r = Validator.Validate({ Modules = { { Id = "muro_nube", x = 5, z = 1, Rot = 0 } } }, {})
check("deviazione trovata", r.Ok and #r.Path > 12, r.Reason)
check("stelle difficoltà in 1..5", Validator.DifficultyStars(0) == 1 and Validator.DifficultyStars(100) == 5)
for _, sim in ipairs(Simulated.List) do
	local res = Validator.Validate(sim.Layout, {})
	check("vivaio simulato valido: " .. sim.Key, res.Ok, res.Reason)
end

print("Economia e tempo")
check("capienza cassaforte base 300", Config.Vault.Capacities[1] == 300)
check("tetto 25%", Config.Raid.MaxTakeFraction == 0.25)
check("2 perdite / 30 min", Config.Raid.MaxLossesPerWindow == 2 and Config.Raid.LossWindowSeconds == 1800)
check("DayKey formato", TimeUtil.DayKey(0) == "1970-01-01")
check("WeekIndex monotono", TimeUtil.WeekIndex(1000000) <= TimeUtil.WeekIndex(2000000))
check("Hash deterministico", TimeUtil.Hash("abc") == TimeUtil.Hash("abc") and TimeUtil.Hash("abc") ~= TimeUtil.Hash("abd"))
check("Format.Number", Format.Number(1234) == "1.234" and Format.Number(12345) == "12.3k")
check("Format.Time", Format.Time(125) == "2:05")
check("Album.TierFor", Album.TierFor(35, Config.Mastery.Tiers) == 2 and Album.TierFor(0, Config.Mastery.Tiers) == 0)
check("Album 20 traguardi", #Album.List == 20)
for slot, id in pairs(Cosmetics.Defaults) do
	check("cosmetico default esiste: " .. slot, Cosmetics.Get(id) ~= nil and Cosmetics.Get(id).Slot == slot)
end
local d = DefaultData()
for slot, id in pairs(Cosmetics.Defaults) do
	check("default posseduto: " .. id, d.Cosmetics.Owned[id] == true)
end
local catsC = {}
for _, t in ipairs(Commissions.List) do
	catsC[t.Category] = true
end
check("commissioni in 4 categorie", catsC.raccolta and catsC.costruzione and catsC.visita and catsC.incursione)
check("categoria incursione accetta simulati", (function()
	for _, t in ipairs(Commissions.ByCategory("incursione", 5)) do
		if not t.Text:find("simulat") and not t.Text:find("Guardiano") and not t.Text:find("checkpoint") then
			return false
		end
	end
	return true
end)())
check("Reconcile aggiunge chiavi mancanti", (function()
	local t = { a = 1, nested = { x = 1 } }
	TableUtil.Reconcile(t, { a = 5, b = 2, nested = { x = 9, y = 3 } })
	return t.a == 1 and t.b == 2 and t.nested.x == 1 and t.nested.y == 3
end)())

print(string.format("\nRisultato: %d superati, %d falliti", passed, failed))
if failed > 0 then
	error("Test falliti")
end
