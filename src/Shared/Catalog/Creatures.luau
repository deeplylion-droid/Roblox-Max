--!nonstrict
--[[
	Catalogo dei 16 Nimbini: 4 famiglie × 4 creature.
	Ogni creatura ha produzione base (scintille per intervallo), rarità visuale,
	comportamento di animazione, specifiche visive procedurali e 4 varianti cromatiche.
	UnlockOrder definisce il percorso deterministico dei bozzoli (nessuna loot box).
]]

export type Variant = { Id: string, Name: string, Color: Color3, Unlock: { Kind: string, Value: any } }
export type Creature = {
	Id: string,
	Name: string,
	Family: string,
	Rarity: string,
	Production: number,
	UnlockOrder: number,
	Behavior: string, -- bob | hop | orbit | drift
	Description: string,
	Visual: { Color: Color3, Accent: Color3, Size: number, Shape: string, Glow: number },
	Variants: { Variant },
}

local function variants(base: Color3, a: Color3, b: Color3, c: Color3)
	return {
		{ Id = "base", Name = "Classica", Color = base, Unlock = { Kind = "default" } },
		{ Id = "alba", Name = "Alba", Color = a, Unlock = { Kind = "mastery", Track = "Collection", Tier = 1 } },
		{ Id = "crepuscolo", Name = "Crepuscolo", Color = b, Unlock = { Kind = "mastery", Track = "Raid", Tier = 2 } },
		{ Id = "tempesta", Name = "Tempesta", Color = c, Unlock = { Kind = "activity", Stat = "RaidsDefended", Value = 10 } },
	}
end

local C = {}

local list: { Creature } = {
	-- ─────────── SOLE ───────────
	{
		Id = "sole_lumino", Name = "Lumino", Family = "sole", Rarity = "comune", Production = 10, UnlockOrder = 1,
		Behavior = "bob", Description = "Una pallina di luce calda che ronza felice al sole.",
		Visual = { Color = Color3.fromRGB(255, 214, 102), Accent = Color3.fromRGB(255, 240, 180), Size = 2.2, Shape = "Ball", Glow = 0.6 },
		Variants = variants(Color3.fromRGB(255, 214, 102), Color3.fromRGB(255, 170, 120), Color3.fromRGB(240, 120, 90), Color3.fromRGB(255, 240, 200)),
	},
	{
		Id = "sole_raggiolo", Name = "Raggiolo", Family = "sole", Rarity = "insolito", Production = 13, UnlockOrder = 2,
		Behavior = "hop", Description = "Salta tra i fasci di luce e lascia scie dorate.",
		Visual = { Color = Color3.fromRGB(255, 184, 60), Accent = Color3.fromRGB(255, 230, 140), Size = 2.4, Shape = "Ball", Glow = 0.8 },
		Variants = variants(Color3.fromRGB(255, 184, 60), Color3.fromRGB(255, 150, 100), Color3.fromRGB(220, 110, 60), Color3.fromRGB(255, 250, 220)),
	},
	{
		Id = "sole_meriggia", Name = "Meriggia", Family = "sole", Rarity = "raro", Production = 16, UnlockOrder = 3,
		Behavior = "orbit", Description = "Orbita lenta come un piccolo mezzogiorno privato.",
		Visual = { Color = Color3.fromRGB(255, 160, 40), Accent = Color3.fromRGB(255, 220, 110), Size = 2.8, Shape = "Ball", Glow = 1.0 },
		Variants = variants(Color3.fromRGB(255, 160, 40), Color3.fromRGB(255, 120, 90), Color3.fromRGB(200, 90, 50), Color3.fromRGB(255, 235, 170)),
	},
	{
		Id = "sole_solstizia", Name = "Solstizia", Family = "sole", Rarity = "leggendario", Production = 20, UnlockOrder = 4,
		Behavior = "drift", Description = "Porta con sé il giorno più lungo dell'anno.",
		Visual = { Color = Color3.fromRGB(255, 140, 30), Accent = Color3.fromRGB(255, 250, 200), Size = 3.2, Shape = "Ball", Glow = 1.4 },
		Variants = variants(Color3.fromRGB(255, 140, 30), Color3.fromRGB(255, 100, 80), Color3.fromRGB(180, 70, 40), Color3.fromRGB(255, 255, 230)),
	},
	-- ─────────── PIOGGIA ───────────
	{
		Id = "pioggia_gocciolo", Name = "Gocciolo", Family = "pioggia", Rarity = "comune", Production = 10, UnlockOrder = 1,
		Behavior = "bob", Description = "Una goccia timida con un cappellino di nuvola.",
		Visual = { Color = Color3.fromRGB(110, 170, 250), Accent = Color3.fromRGB(230, 240, 255), Size = 2.2, Shape = "Ball", Glow = 0.4 },
		Variants = variants(Color3.fromRGB(110, 170, 250), Color3.fromRGB(150, 210, 255), Color3.fromRGB(70, 110, 200), Color3.fromRGB(60, 80, 140)),
	},
	{
		Id = "pioggia_acquerella", Name = "Acquerella", Family = "pioggia", Rarity = "insolito", Production = 13, UnlockOrder = 2,
		Behavior = "hop", Description = "Saltella e dipinge pozzanghere arcobaleno.",
		Visual = { Color = Color3.fromRGB(90, 150, 240), Accent = Color3.fromRGB(200, 230, 255), Size = 2.4, Shape = "Ball", Glow = 0.5 },
		Variants = variants(Color3.fromRGB(90, 150, 240), Color3.fromRGB(140, 200, 255), Color3.fromRGB(60, 100, 190), Color3.fromRGB(50, 70, 130)),
	},
	{
		Id = "pioggia_monsonia", Name = "Monsonia", Family = "pioggia", Rarity = "raro", Production = 16, UnlockOrder = 3,
		Behavior = "orbit", Description = "Gira in tondo trascinando una pioggerella gentile.",
		Visual = { Color = Color3.fromRGB(70, 130, 230), Accent = Color3.fromRGB(190, 220, 255), Size = 2.8, Shape = "Ball", Glow = 0.7 },
		Variants = variants(Color3.fromRGB(70, 130, 230), Color3.fromRGB(120, 190, 255), Color3.fromRGB(50, 90, 180), Color3.fromRGB(40, 60, 120)),
	},
	{
		Id = "pioggia_diluvia", Name = "Diluvia", Family = "pioggia", Rarity = "leggendario", Production = 20, UnlockOrder = 4,
		Behavior = "drift", Description = "La custode delle grandi piogge, calma e profonda.",
		Visual = { Color = Color3.fromRGB(50, 110, 220), Accent = Color3.fromRGB(220, 240, 255), Size = 3.2, Shape = "Ball", Glow = 1.0 },
		Variants = variants(Color3.fromRGB(50, 110, 220), Color3.fromRGB(110, 180, 255), Color3.fromRGB(40, 80, 170), Color3.fromRGB(30, 50, 110)),
	},
	-- ─────────── VENTO ───────────
	{
		Id = "vento_brezzolo", Name = "Brezzolo", Family = "vento", Rarity = "comune", Production = 10, UnlockOrder = 1,
		Behavior = "drift", Description = "Un soffio con gli occhi, sempre in movimento.",
		Visual = { Color = Color3.fromRGB(170, 240, 210), Accent = Color3.fromRGB(240, 255, 250), Size = 2.2, Shape = "Ball", Glow = 0.4 },
		Variants = variants(Color3.fromRGB(170, 240, 210), Color3.fromRGB(210, 255, 230), Color3.fromRGB(110, 190, 170), Color3.fromRGB(80, 130, 130)),
	},
	{
		Id = "vento_alisea", Name = "Alisea", Family = "vento", Rarity = "insolito", Production = 13, UnlockOrder = 2,
		Behavior = "orbit", Description = "Segue rotte invisibili come i venti dei marinai.",
		Visual = { Color = Color3.fromRGB(140, 230, 200), Accent = Color3.fromRGB(230, 255, 245), Size = 2.4, Shape = "Ball", Glow = 0.5 },
		Variants = variants(Color3.fromRGB(140, 230, 200), Color3.fromRGB(190, 250, 220), Color3.fromRGB(90, 170, 150), Color3.fromRGB(70, 110, 120)),
	},
	{
		Id = "vento_zefirio", Name = "Zefirio", Family = "vento", Rarity = "raro", Production = 16, UnlockOrder = 3,
		Behavior = "hop", Description = "Rimbalza leggero portando il profumo della primavera.",
		Visual = { Color = Color3.fromRGB(110, 220, 190), Accent = Color3.fromRGB(220, 255, 240), Size = 2.8, Shape = "Ball", Glow = 0.7 },
		Variants = variants(Color3.fromRGB(110, 220, 190), Color3.fromRGB(170, 245, 215), Color3.fromRGB(70, 160, 140), Color3.fromRGB(60, 100, 110)),
	},
	{
		Id = "vento_tramontana", Name = "Tramontana", Family = "vento", Rarity = "leggendario", Production = 20, UnlockOrder = 4,
		Behavior = "drift", Description = "Il vento del nord, fiero e cristallino.",
		Visual = { Color = Color3.fromRGB(80, 210, 180), Accent = Color3.fromRGB(240, 255, 255), Size = 3.2, Shape = "Ball", Glow = 1.0 },
		Variants = variants(Color3.fromRGB(80, 210, 180), Color3.fromRGB(150, 240, 210), Color3.fromRGB(50, 150, 130), Color3.fromRGB(50, 90, 100)),
	},
	-- ─────────── AURORA ───────────
	{
		Id = "aurora_velina", Name = "Velina", Family = "aurora", Rarity = "comune", Production = 10, UnlockOrder = 1,
		Behavior = "bob", Description = "Un velo di luce colorata che ondeggia piano.",
		Visual = { Color = Color3.fromRGB(200, 150, 255), Accent = Color3.fromRGB(150, 255, 220), Size = 2.2, Shape = "Ball", Glow = 0.8 },
		Variants = variants(Color3.fromRGB(200, 150, 255), Color3.fromRGB(255, 180, 230), Color3.fromRGB(140, 100, 220), Color3.fromRGB(90, 60, 160)),
	},
	{
		Id = "aurora_boreala", Name = "Boreala", Family = "aurora", Rarity = "insolito", Production = 13, UnlockOrder = 2,
		Behavior = "drift", Description = "Scivola come un nastro verde nel cielo notturno.",
		Visual = { Color = Color3.fromRGB(180, 130, 255), Accent = Color3.fromRGB(120, 255, 200), Size = 2.4, Shape = "Ball", Glow = 1.0 },
		Variants = variants(Color3.fromRGB(180, 130, 255), Color3.fromRGB(240, 170, 220), Color3.fromRGB(120, 90, 210), Color3.fromRGB(80, 50, 150)),
	},
	{
		Id = "aurora_australa", Name = "Australa", Family = "aurora", Rarity = "raro", Production = 16, UnlockOrder = 3,
		Behavior = "orbit", Description = "La gemella del sud, con riflessi rosa e turchese.",
		Visual = { Color = Color3.fromRGB(160, 110, 255), Accent = Color3.fromRGB(255, 160, 220), Size = 2.8, Shape = "Ball", Glow = 1.2 },
		Variants = variants(Color3.fromRGB(160, 110, 255), Color3.fromRGB(230, 160, 210), Color3.fromRGB(110, 80, 200), Color3.fromRGB(70, 40, 140)),
	},
	{
		Id = "aurora_corona", Name = "Corona", Family = "aurora", Rarity = "leggendario", Production = 20, UnlockOrder = 4,
		Behavior = "orbit", Description = "La corona dell'aurora: ogni colore del cielo in un solo essere.",
		Visual = { Color = Color3.fromRGB(140, 90, 255), Accent = Color3.fromRGB(255, 220, 140), Size = 3.2, Shape = "Ball", Glow = 1.6 },
		Variants = variants(Color3.fromRGB(140, 90, 255), Color3.fromRGB(220, 150, 200), Color3.fromRGB(100, 70, 190), Color3.fromRGB(60, 30, 130)),
	},
}

C.List = list
C.ById = {}
C.ByFamily = { sole = {}, pioggia = {}, vento = {}, aurora = {} }
for _, c in ipairs(list) do
	C.ById[c.Id] = c
	table.insert(C.ByFamily[c.Family], c)
end
for _, fam in pairs(C.ByFamily) do
	table.sort(fam, function(a, b)
		return a.UnlockOrder < b.UnlockOrder
	end)
end

C.Families = { "sole", "pioggia", "vento", "aurora" }
C.FamilyInfo = {
	sole = { Name = "Sole", Description = "Luce calda e scintille dorate.", Starter = "sole_lumino" },
	pioggia = { Name = "Pioggia", Description = "Gocce gentili e riflessi azzurri.", Starter = "pioggia_gocciolo" },
	vento = { Name = "Vento", Description = "Soffi leggeri e scie turchesi.", Starter = "vento_brezzolo" },
	aurora = { Name = "Aurora", Description = "Nastri di luce colorata.", Starter = "aurora_velina" },
}

-- Creatura di partenza del tutorial
C.StarterCreatureId = "sole_lumino"

function C.Get(id): Creature?
	return C.ById[id]
end

function C.GetVariant(creatureId, variantId): Variant?
	local c = C.ById[creatureId]
	if not c then
		return nil
	end
	for _, v in ipairs(c.Variants) do
		if v.Id == variantId then
			return v
		end
	end
	return nil
end

-- Prossima creatura mancante di una famiglia (percorso deterministico dei bozzoli)
function C.NextMissingInFamily(family, ownedSet)
	for _, c in ipairs(C.ByFamily[family] or {}) do
		if not ownedSet[c.Id] then
			return c
		end
	end
	return nil
end

return C
