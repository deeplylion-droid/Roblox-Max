--!nonstrict
--[[
	Album delle famiglie meteo: traguardi permanenti per numero di creature possedute
	in ciascuna famiglia, più traguardi globali. Premi: frammenti, gettoni, decorazioni,
	targhette. Tutto idempotente lato server (ClaimedMilestones).
]]

export type Milestone = {
	Id: string,
	Family: string?, -- nil = globale
	Count: number, -- creature possedute (famiglia) o totali (globale)
	Title: string,
	Reward: { Fragments: number?, Tokens: number?, Decoration: string?, Cosmetic: string?, Sparks: number? },
}

local Album = {}
local list: { Milestone } = {}

local familyNames = { sole = "Sole", pioggia = "Pioggia", vento = "Vento", aurora = "Aurora" }
local familyDeco = { sole = "meridiana", pioggia = "fontanella", vento = "girandola", aurora = "arco_luce" }

for _, fam in ipairs({ "sole", "pioggia", "vento", "aurora" }) do
	table.insert(list, { Id = fam .. "_1", Family = fam, Count = 1, Title = "Primo " .. familyNames[fam], Reward = { Fragments = 3, Sparks = 60 } })
	table.insert(list, { Id = fam .. "_2", Family = fam, Count = 2, Title = "Coppia di " .. familyNames[fam], Reward = { Fragments = 5, Tokens = 10 } })
	table.insert(list, { Id = fam .. "_3", Family = fam, Count = 3, Title = "Trio di " .. familyNames[fam], Reward = { Fragments = 6, Decoration = familyDeco[fam] } })
	table.insert(list, { Id = fam .. "_4", Family = fam, Count = 4, Title = "Famiglia " .. familyNames[fam] .. " completa", Reward = { Fragments = 10, Tokens = 20, Cosmetic = "plate_collezionista" } })
end

table.insert(list, { Id = "global_4", Count = 4, Title = "Quattro stagioni", Reward = { Fragments = 4, Tokens = 10 } })
table.insert(list, { Id = "global_8", Count = 8, Title = "Metà cielo", Reward = { Fragments = 8, Decoration = "fontana_stelle" } })
table.insert(list, { Id = "global_12", Count = 12, Title = "Meteorologo provetto", Reward = { Fragments = 10, Tokens = 25 } })
table.insert(list, { Id = "global_16", Count = 16, Title = "Il cielo intero", Reward = { Fragments = 15, Tokens = 50, Decoration = "trono_nuvola" } })

Album.List = list
Album.ById = {}
for _, m in ipairs(list) do
	Album.ById[m.Id] = m
end

-- Maestria: tre tracce. Soglie in Config.Mastery.Tiers. Premi per tier.
Album.MasteryRewards = {
	Collection = {
		{ Title = "Apprendista del cielo", Fragments = 4 },
		{ Title = "Custode", Fragments = 6, Unlock = "AutoDeposit" },
		{ Title = "Giardiniere delle nuvole", Fragments = 8, Tokens = 15 },
		{ Title = "Maestro del vivaio", Fragments = 12, Tokens = 25 },
		{ Title = "Leggenda meteorologica", Fragments = 20, Tokens = 40 },
	},
	Raid = {
		{ Title = "Esploratore", Fragments = 3 },
		{ Title = "Acrobata", Fragments = 5, Tokens = 10 },
		{ Title = "Ombra tra le nuvole", Fragments = 8, Tokens = 15 },
		{ Title = "Danzatore del vento", Fragments = 12, Tokens = 25 },
		{ Title = "Leggenda delle incursioni", Fragments = 20, Tokens = 40 },
	},
	Defense = {
		{ Title = "Guardiano", Fragments = 3 },
		{ Title = "Architetto", Fragments = 5, Tokens = 10 },
		{ Title = "Stratega", Fragments = 8, Tokens = 15 },
		{ Title = "Custode supremo", Fragments = 12, Tokens = 25 },
		{ Title = "Leggenda della difesa", Fragments = 20, Tokens = 40 },
	},
}

function Album.TierFor(points, tiers)
	local tier = 0
	for i, threshold in ipairs(tiers) do
		if points >= threshold then
			tier = i
		end
	end
	return tier
end

return Album
