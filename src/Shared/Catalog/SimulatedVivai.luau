--!nonstrict
--[[
	Vivai del Guardiano: bersagli simulati sempre disponibili. Servono per il tutorial,
	per le commissioni (nessuna richiede di colpire giocatori reali) e quando non ci sono
	bersagli idonei. Ricompensa ridotta (Config.Raid.SimulatedRewardFraction), nessuno perde nulla.
]]

local list = {
	{
		Key = "sim_allenamento", Name = "Vivaio del Guardiano · Allenamento", Tier = 1, Exposed = 160,
		Creatures = { { Id = "sole_lumino", x = 2, z = 3 }, { Id = "pioggia_gocciolo", x = 9, z = 8 } },
		Layout = { Modules = { { Id = "corrente", x = 5, z = 3, Rot = 0 } } },
		Tutorial = true,
	},
	{
		Key = "sim_brezza", Name = "Vivaio del Guardiano · Brezza", Tier = 1, Exposed = 220,
		Creatures = { { Id = "vento_brezzolo", x = 2, z = 2 }, { Id = "sole_lumino", x = 9, z = 3 }, { Id = "pioggia_gocciolo", x = 2, z = 9 } },
		Layout = { Modules = { { Id = "corrente", x = 5, z = 3, Rot = 0 }, { Id = "muro_nube", x = 4, z = 8, Rot = 0 } } },
	},
	{
		Key = "sim_faro", Name = "Vivaio del Guardiano · Faro", Tier = 2, Exposed = 380,
		Creatures = { { Id = "sole_raggiolo", x = 2, z = 2 }, { Id = "pioggia_acquerella", x = 9, z = 2 }, { Id = "vento_alisea", x = 2, z = 9 }, { Id = "aurora_velina", x = 9, z = 9 } },
		Layout = { Modules = { { Id = "sentinella", x = 3, z = 5, Rot = 0 }, { Id = "corrente", x = 6, z = 8, Rot = 0 }, { Id = "faro", x = 8, z = 5, Rot = 0 } } },
	},
	{
		Key = "sim_abisso", Name = "Vivaio del Guardiano · Abisso", Tier = 3, Exposed = 620,
		Creatures = { { Id = "sole_meriggia", x = 2, z = 2 }, { Id = "pioggia_monsonia", x = 9, z = 2 }, { Id = "vento_zefirio", x = 2, z = 9 }, { Id = "aurora_boreala", x = 9, z = 9 }, { Id = "sole_lumino", x = 1, z = 6 } },
		Layout = { Modules = { { Id = "piattaforma", x = 5, z = 2, Rot = 1 }, { Id = "sentinella", x = 8, z = 6, Rot = 0 }, { Id = "muro_nube", x = 3, z = 8, Rot = 0 }, { Id = "nebbia", x = 6, z = 7, Rot = 0 } } },
	},
	{
		Key = "sim_tempesta", Name = "Vivaio del Guardiano · Tempesta", Tier = 4, Exposed = 900,
		Creatures = { { Id = "sole_solstizia", x = 2, z = 2 }, { Id = "pioggia_diluvia", x = 9, z = 2 }, { Id = "vento_tramontana", x = 2, z = 9 }, { Id = "aurora_corona", x = 9, z = 9 }, { Id = "aurora_australa", x = 1, z = 6 }, { Id = "vento_alisea", x = 10, z = 6 } },
		-- energia: 30 + 20 + 25 + 25 = 100 (budget pieno)
		Layout = { Modules = { { Id = "sentinella", x = 4, z = 3, Rot = 0, Alt = "ampia" }, { Id = "corrente", x = 7, z = 8, Rot = 0, Alt = "raffica" }, { Id = "piattaforma", x = 6, z = 2, Rot = 1 }, { Id = "campana", x = 10, z = 10, Rot = 0 } } },
	},
}

local Simulated = { List = list, ByKey = {} }
for _, s in ipairs(list) do
	Simulated.ByKey[s.Key] = s
end

function Simulated.ForTier(tier)
	local out = {}
	for _, s in ipairs(list) do
		if not s.Tutorial and math.abs(s.Tier - tier) <= 1 then
			table.insert(out, s)
		end
	end
	if #out == 0 then
		table.insert(out, list[2])
	end
	return out
end

return Simulated
