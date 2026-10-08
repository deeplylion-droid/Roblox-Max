--!nonstrict
--[[
	Moduli di difesa. Tre categorie: ostacolo, distrazione, firma.
	Footprint = celle relative {dx,dz}; Solid = celle che bloccano il cammino
	(usate dal validatore per garantire un percorso completabile).
	Le "Alternatives" sono varianti tattiche (non muri di statistiche).
]]

export type Alternative = { Id: string, Name: string, Description: string, Params: { [string]: any }, Unlock: { Kind: string, Track: string?, Tier: number? } }
export type Module = {
	Id: string,
	Name: string,
	Category: string, -- ostacolo | distrazione | firma
	Energy: number,
	Difficulty: number, -- peso per la stima difficoltà (1..5)
	Footprint: { { number } },
	Solid: boolean,
	Description: string,
	Unlock: { Kind: string, Cost: number?, Track: string?, Tier: number? },
	Color: Color3,
	Params: { [string]: any },
	Alternatives: { Alternative },
}

local D = {}

local list: { Module } = {
	-- ───────── OSTACOLI ─────────
	{
		Id = "corrente", Name = "Corrente d'aria", Category = "ostacolo", Energy = 20, Difficulty = 1.5,
		Footprint = { { 0, 0 }, { -1, 0 }, { 1, 0 } }, Solid = false,
		Description = "Una lama di vento spinge l'incursore di lato. Telegrafata da foglie e particelle.",
		Unlock = { Kind = "default" }, Color = Color3.fromRGB(170, 235, 215),
		Params = { Push = 55, Pulse = false },
		Alternatives = {
			{ Id = "raffica", Name = "Raffica pulsante", Description = "Si attiva a intermittenza ma spinge più forte: premia il tempismo.", Params = { Push = 95, Pulse = true, PulsePeriod = 2.4 }, Unlock = { Kind = "mastery", Track = "Defense", Tier = 1 } },
			{ Id = "ascensionale", Name = "Corrente ascensionale", Description = "Solleva verso l'alto invece di spingere di lato: lo slancio gioca brutti scherzi.", Params = { Push = 70, Up = true }, Unlock = { Kind = "mastery", Track = "Defense", Tier = 2 } },
		},
	},
	{
		Id = "piattaforma", Name = "Piattaforma mobile", Category = "ostacolo", Energy = 25, Difficulty = 2,
		Footprint = { { 0, 0 }, { 0, -1 }, { 0, 1 } }, Solid = false,
		Description = "Apre un vuoto tra le nuvole attraversabile solo su una piattaforma in movimento.",
		Unlock = { Kind = "sparks", Cost = 180 }, Color = Color3.fromRGB(255, 220, 150),
		Params = { Period = 3.2, Width = 1 },
		Alternatives = {
			{ Id = "lenta_larga", Name = "Piattaforma lenta e larga", Description = "Più facile da prendere ma lentissima: costa tempo prezioso.", Params = { Period = 5.5, Width = 1.6 }, Unlock = { Kind = "mastery", Track = "Defense", Tier = 1 } },
			{ Id = "doppia", Name = "Coppia sfasata", Description = "Due piattaforme piccole in controfase: serve ritmo.", Params = { Period = 2.6, Width = 0.7, Double = true }, Unlock = { Kind = "mastery", Track = "Defense", Tier = 3 } },
		},
	},
	{
		Id = "sentinella", Name = "Sentinella luminosa", Category = "ostacolo", Energy = 30, Difficulty = 3,
		Footprint = { { 0, 0 } }, Solid = true,
		Description = "Un faro rotante: chi finisce nel cono di luce torna al checkpoint.",
		Unlock = { Kind = "sparks", Cost = 320 }, Color = Color3.fromRGB(255, 250, 200),
		Params = { Radius = 9, Arc = 50, Speed = 55 },
		Alternatives = {
			{ Id = "ampia", Name = "Sentinella ampia", Description = "Più lenta ma con un cono molto più largo.", Params = { Radius = 11, Arc = 90, Speed = 32 }, Unlock = { Kind = "mastery", Track = "Defense", Tier = 1 } },
			{ Id = "nervosa", Name = "Sentinella nervosa", Description = "Cono stretto che cambia direzione all'improvviso.", Params = { Radius = 9, Arc = 35, Speed = 80, Erratic = true }, Unlock = { Kind = "mastery", Track = "Defense", Tier = 2 } },
		},
	},
	{
		Id = "muro_nube", Name = "Muro di nubi", Category = "ostacolo", Energy = 15, Difficulty = 1,
		Footprint = { { 0, 0 }, { 1, 0 } }, Solid = true,
		Description = "Una nuvola compatta che blocca il passaggio e allunga il percorso.",
		Unlock = { Kind = "default" }, Color = Color3.fromRGB(235, 240, 255),
		Params = {},
		Alternatives = {
			{ Id = "lungo", Name = "Muraglia", Description = "Tre celle di nuvola: deviazioni più lunghe, stessa energia.", Params = { Long = true }, Unlock = { Kind = "mastery", Track = "Defense", Tier = 2 } },
		},
	},
	-- ───────── DISTRAZIONI ─────────
	{
		Id = "faro", Name = "Faro distrattore", Category = "distrazione", Energy = 15, Difficulty = 1,
		Footprint = { { 0, 0 } }, Solid = false,
		Description = "Brilla come una pozza di scintille: chi lo tocca resta abbagliato per qualche secondo.",
		Unlock = { Kind = "sparks", Cost = 150 }, Color = Color3.fromRGB(255, 200, 90),
		Params = { Dazzle = 3.5 },
		Alternatives = {},
	},
	{
		Id = "nebbia", Name = "Banco di nebbia", Category = "distrazione", Energy = 20, Difficulty = 1.5,
		Footprint = { { 0, 0 }, { 1, 0 }, { 0, 1 }, { 1, 1 } }, Solid = false,
		Description = "Riduce la visibilità: le sentinelle vicine diventano difficili da leggere.",
		Unlock = { Kind = "sparks", Cost = 220 }, Color = Color3.fromRGB(215, 225, 240),
		Params = {},
		Alternatives = {},
	},
	{
		Id = "scivolo", Name = "Prato di rugiada", Category = "distrazione", Energy = 15, Difficulty = 1,
		Footprint = { { 0, 0 }, { 1, 0 } }, Solid = false,
		Description = "Erba bagnata e scivolosa: il controllo del personaggio diventa impreciso.",
		Unlock = { Kind = "sparks", Cost = 150 }, Color = Color3.fromRGB(160, 230, 170),
		Params = { Friction = 0.05 },
		Alternatives = {},
	},
	-- ───────── MODULI FIRMA ─────────
	{
		Id = "cupola", Name = "Cupola prismatica", Category = "firma", Energy = 30, Difficulty = 2.5,
		Footprint = { { 0, 0 } }, Solid = false,
		Description = "Solleva la pozza su un piedistallo raggiungibile solo saltando sui trampolini di luce.",
		Unlock = { Kind = "mastery", Track = "Defense", Tier = 1 }, Color = Color3.fromRGB(220, 180, 255),
		Params = { Height = 7 },
		Alternatives = {},
	},
	{
		Id = "campana", Name = "Campana del vento", Category = "firma", Energy = 25, Difficulty = 2,
		Footprint = { { 0, 0 } }, Solid = false,
		Description = "A metà del tempo suona e inverte tutte le correnti d'aria del vivaio.",
		Unlock = { Kind = "mastery", Track = "Defense", Tier = 2 }, Color = Color3.fromRGB(255, 230, 170),
		Params = { TriggerFraction = 0.5 },
		Alternatives = {},
	},
	{
		Id = "arcobaleno", Name = "Ponte arcobaleno", Category = "firma", Energy = 35, Difficulty = 3,
		Footprint = { { 0, 0 }, { 0, 1 }, { 0, 2 } }, Solid = false,
		Description = "Un ponte che appare e scompare a ritmo: l'unico passaggio sopra un vuoto di tre celle.",
		Unlock = { Kind = "mastery", Track = "Defense", Tier = 3 }, Color = Color3.fromRGB(255, 160, 220),
		Params = { Period = 4 },
		Alternatives = {},
	},
}

D.List = list
D.ById = {}
for _, m in ipairs(list) do
	D.ById[m.Id] = m
end

function D.Get(id): Module?
	return D.ById[id]
end

function D.GetAlternative(moduleId, altId): Alternative?
	local m = D.ById[moduleId]
	if not m or not altId or altId == "base" then
		return nil
	end
	for _, a in ipairs(m.Alternatives) do
		if a.Id == altId then
			return a
		end
	end
	return nil
end

-- Footprint effettivo tenendo conto dell'alternativa (es. muraglia lunga)
function D.EffectiveFootprint(moduleId, altId)
	local m = D.ById[moduleId]
	if not m then
		return {}
	end
	if moduleId == "muro_nube" and altId == "lungo" then
		return { { 0, 0 }, { 1, 0 }, { -1, 0 } }
	end
	return m.Footprint
end

-- Parametri effettivi = base + alternativa
function D.EffectiveParams(moduleId, altId)
	local m = D.ById[moduleId]
	if not m then
		return {}
	end
	local out = table.clone(m.Params)
	local alt = D.GetAlternative(moduleId, altId)
	if alt then
		for k, v in pairs(alt.Params) do
			out[k] = v
		end
	end
	return out
end

D.CategoryNames = { ostacolo = "Ostacolo", distrazione = "Distrazione", firma = "Modulo firma" }

return D
