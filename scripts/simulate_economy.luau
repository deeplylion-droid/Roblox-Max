--!nonstrict
--[[
	Simulazione economica (GDD §5): verifica che
	1) il primo acquisto significativo (modulo da 180) arrivi in 3–5 minuti;
	2) il rendimento oltre la sesta creatura cali;
	3) il recupero dopo due raid non superi ~10 minuti per un giocatore medio;
	4) la riserva offline resti un piccolo bonus.
]]
local Config = require("./Config")
local Creatures = require("./Creatures")

local INTERVAL = Config.Production.BaseInterval

local function productionPerInterval(creatureIds)
	local prods = {}
	for _, id in ipairs(creatureIds) do
		table.insert(prods, Creatures.Get(id).Production)
	end
	table.sort(prods, function(a, b)
		return a > b
	end)
	local total = 0
	for i, p in ipairs(prods) do
		total += p * (Config.Production.DiminishingFactors[i] or (i > 12 and 0.2 or 1))
	end
	return total
end

local function perMinute(ids)
	return productionPerInterval(ids) * (60 / INTERVAL)
end

print("1) Nuovo giocatore: 1 Lumino (10 ✦ / 30 s) + ricompense di inizio sessione")
do
	local sparks = 0
	local t = 0 -- secondi
	local firstPurchase
	local bonusApplied = {}
	while t <= 15 * 60 do
		-- traguardo album 'Primo Sole' subito riscuotibile (+60), commissione 'ritiri 8' a 4 min (+50), 'raccolta 120' a 6 min (+60)
		if t >= 0 and not bonusApplied.album then
			sparks += 60
			bonusApplied.album = true
		end
		if t >= 8 * INTERVAL and not bonusApplied.ritiri then
			sparks += 50
			bonusApplied.ritiri = true
		end
		if t >= 12 * INTERVAL and not bonusApplied.raccolta then
			sparks += 60
			bonusApplied.raccolta = true
		end
		if t > 0 and t % INTERVAL == 0 then
			sparks += productionPerInterval({ "sole_lumino" })
		end
		if not firstPurchase and sparks >= 180 then
			firstPurchase = t
		end
		t += INTERVAL
	end
	print(string.format("   primo modulo da 180 ✦ raggiungibile a %.1f min (obiettivo 3–5)  %s", firstPurchase / 60, (firstPurchase >= 150 and firstPurchase <= 330) and "✔" or "⚠"))
end

print("\n2) Rendimento marginale decrescente (✦/min)")
do
	local sets = {
		{ "sole_lumino" },
		{ "sole_lumino", "pioggia_gocciolo", "vento_brezzolo" },
		{ "sole_lumino", "pioggia_gocciolo", "vento_brezzolo", "aurora_velina", "sole_raggiolo", "pioggia_acquerella" },
		{ "sole_lumino", "pioggia_gocciolo", "vento_brezzolo", "aurora_velina", "sole_raggiolo", "pioggia_acquerella", "vento_alisea", "aurora_boreala" },
		{ "sole_lumino", "pioggia_gocciolo", "vento_brezzolo", "aurora_velina", "sole_raggiolo", "pioggia_acquerella", "vento_alisea", "aurora_boreala", "sole_meriggia", "pioggia_monsonia", "vento_zefirio", "aurora_australa" },
	}
	local prev
	for _, s in ipairs(sets) do
		local pm = perMinute(s)
		local raw = 0
		for _, id in ipairs(s) do
			raw += Creatures.Get(id).Production
		end
		raw = raw * (60 / INTERVAL)
		print(string.format("   %2d creature: %6.1f ✦/min (senza tetto sarebbero %6.1f, -%d%%)", #s, pm, raw, math.floor((1 - pm / raw) * 100 + 0.5)))
		prev = pm
	end
	local six = perMinute(sets[3])
	local twelve = perMinute(sets[5])
	print(string.format("   12 creature rendono %.2fx rispetto a 6 (senza tetto 2.9x)  %s", twelve / six, twelve / six < 2 and "✔" or "⚠"))
end

print("\n3) Recupero dopo due raid consecutivi (peggior caso: 25% delle esposte, due volte)")
do
	local profiles = {
		{ Name = "principiante (fascia 1)", Ids = { "sole_lumino", "pioggia_gocciolo" }, Exposed = 150, Tier = 1 },
		{ Name = "medio (fascia 2)", Ids = { "sole_lumino", "pioggia_gocciolo", "vento_brezzolo", "sole_raggiolo" }, Exposed = 400, Tier = 2 },
		{ Name = "avanzato (fascia 3)", Ids = { "sole_lumino", "pioggia_gocciolo", "vento_brezzolo", "sole_raggiolo", "aurora_boreala", "sole_meriggia" }, Exposed = 900, Tier = 3 },
		{ Name = "esperto (fascia 4)", Ids = { "sole_solstizia", "pioggia_diluvia", "vento_tramontana", "aurora_corona", "sole_meriggia", "pioggia_monsonia", "vento_zefirio", "aurora_australa" }, Exposed = 2000, Tier = 4 },
	}
	for _, p in ipairs(profiles) do
		local exposed = p.Exposed
		local lost = 0
		for _ = 1, 2 do
			local take = math.min(math.floor(exposed * Config.Raid.MaxTakeFraction), Config.Raid.TierTakeCaps[p.Tier])
			lost += take
			exposed -= take
		end
		local consolation = 2 * math.max(5, math.floor((lost / 2) * Config.Raid.DefenderConsolationFraction))
		local net = lost - consolation
		local minutes = net / perMinute(p.Ids)
		print(string.format("   %-24s esposte %4d → perse %3d, consolazione +%3d, recupero %.1f min  %s", p.Name, p.Exposed, lost, consolation, minutes, minutes <= 10 and "✔" or "⚠"))
	end
	print("   nota: dopo la prima perdita scatta lo scudo di 20 min, quindi due raid ravvicinati sono già il caso limite")
end

print("\n4) Riserva offline")
do
	local ids = { "sole_lumino", "pioggia_gocciolo", "vento_brezzolo", "sole_raggiolo" }
	local pm = perMinute(ids)
	for _, hours in ipairs({ 1, 2, 8, 24 }) do
		local minutes = math.min(hours * 60, Config.Production.OfflineCapMinutes)
		local gain = math.min(math.floor(pm * minutes * Config.Production.OfflineRateFraction), Config.Production.OfflineCapSparks)
		print(string.format("   %2d h offline → +%d ✦ (equivalenti a %.1f min di gioco attivo)", hours, gain, gain / pm))
	end
end

print("\n5) Tempi di progressione indicativi (giocatore medio, 4 creature, senza ricompense extra)")
do
	local pm = perMinute({ "sole_lumino", "pioggia_gocciolo", "vento_brezzolo", "sole_raggiolo" })
	print(string.format("   cassaforte L2 (250 ✦): %.1f min · L3 (600): %.1f min · espansione intermedia (1.200): %.1f min", 250 / pm, 600 / pm, 1200 / pm))
end
