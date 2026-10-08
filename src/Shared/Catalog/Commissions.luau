--!nonstrict
--[[
	Modelli di commissioni giornaliere. Ogni giorno il server pesca 3 commissioni
	da categorie diverse. Nessuna richiede di sottrarre risorse ad altri:
	la categoria "incursione" accetta sempre anche i Vivai del Guardiano (simulati).
	Stat = nome della statistica giornaliera incrementata dal server.
]]

export type Template = {
	Id: string,
	Category: string,
	Text: string,
	Stat: string,
	Target: number,
	Reward: { Sparks: number?, Fragments: number?, Tokens: number? },
	MinTier: number?,
}

local list: { Template } = {
	-- raccolta
	{ Id = "raccolta_120", Category = "raccolta", Text = "Raccogli %d scintille", Stat = "Collected", Target = 120, Reward = { Sparks = 60, Fragments = 2 } },
	{ Id = "raccolta_300", Category = "raccolta", Text = "Raccogli %d scintille", Stat = "Collected", Target = 300, Reward = { Sparks = 120, Fragments = 3 }, MinTier = 2 },
	{ Id = "deposito_200", Category = "raccolta", Text = "Deposita %d scintille nella cassaforte", Stat = "Deposited", Target = 200, Reward = { Sparks = 80, Fragments = 2 } },
	{ Id = "deposito_500", Category = "raccolta", Text = "Deposita %d scintille nella cassaforte", Stat = "Deposited", Target = 500, Reward = { Sparks = 150, Fragments = 3 }, MinTier = 2 },
	{ Id = "ritiri_8", Category = "raccolta", Text = "Ritira le scintille da una creatura %d volte", Stat = "CollectActions", Target = 8, Reward = { Sparks = 50, Fragments = 2 } },
	-- costruzione
	{ Id = "pubblica_1", Category = "costruzione", Text = "Pubblica un layout difensivo valido", Stat = "LayoutsPublished", Target = 1, Reward = { Sparks = 70, Fragments = 2 } },
	{ Id = "prova_1", Category = "costruzione", Text = "Prova il tuo percorso difensivo %d volta", Stat = "LayoutTests", Target = 1, Reward = { Sparks = 50, Fragments = 2 } },
	{ Id = "moduli_3", Category = "costruzione", Text = "Pubblica un layout con almeno %d moduli", Stat = "LayoutModulesMax", Target = 3, Reward = { Sparks = 90, Fragments = 3 }, MinTier = 2 },
	{ Id = "decora_2", Category = "costruzione", Text = "Posiziona %d decorazioni", Stat = "DecorationsPlaced", Target = 2, Reward = { Sparks = 40, Fragments = 2 } },
	{ Id = "sposta_creatura", Category = "costruzione", Text = "Riordina il vivaio: sposta %d creature", Stat = "CreaturesMoved", Target = 2, Reward = { Sparks = 40, Fragments = 2 } },
	-- visita
	{ Id = "visita_2", Category = "visita", Text = "Visita %d vivai dalla galleria", Stat = "Visits", Target = 2, Reward = { Sparks = 60, Fragments = 2 } },
	{ Id = "like_1", Category = "visita", Text = "Lascia %d «mi piace» in galleria", Stat = "Likes", Target = 1, Reward = { Sparks = 40, Fragments = 2 } },
	{ Id = "demo_1", Category = "visita", Text = "Osserva il vivaio dimostrativo nell'hub", Stat = "DemoVisits", Target = 1, Reward = { Sparks = 30, Fragments = 1 } },
	-- incursione (sempre valida anche contro i Vivai del Guardiano)
	{ Id = "raid_1", Category = "incursione", Text = "Completa %d incursione (anche contro un Vivaio del Guardiano)", Stat = "RaidsCompleted", Target = 1, Reward = { Sparks = 80, Fragments = 3 } },
	{ Id = "raid_win_1", Category = "incursione", Text = "Supera %d incursione (anche simulata)", Stat = "RaidsWon", Target = 1, Reward = { Sparks = 100, Fragments = 3 }, MinTier = 2 },
	{ Id = "raid_2", Category = "incursione", Text = "Completa %d incursioni (anche simulate)", Stat = "RaidsCompleted", Target = 2, Reward = { Sparks = 120, Fragments = 4 }, MinTier = 2 },
	{ Id = "raid_clean", Category = "incursione", Text = "Supera un'incursione senza tornare al checkpoint", Stat = "RaidsClean", Target = 1, Reward = { Sparks = 110, Fragments = 4 }, MinTier = 3 },
}

local Commissions = { List = list, ById = {} }
for _, t in ipairs(list) do
	Commissions.ById[t.Id] = t
end

function Commissions.ByCategory(category, tier)
	local out = {}
	for _, t in ipairs(list) do
		if t.Category == category and (t.MinTier or 1) <= (tier or 1) then
			table.insert(out, t)
		end
	end
	return out
end

function Commissions.Describe(t: Template)
	if t.Text:find("%%d") then
		return string.format(t.Text, t.Target)
	end
	return t.Text
end

return Commissions
