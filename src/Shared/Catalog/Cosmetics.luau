--!nonstrict
--[[
	Cosmetici: skin del vivaio, cieli, scie di particelle, emote, targhette.
	Prezzo in gettoni stile (guadagnabili giocando). Opzionalmente un
	DeveloperProduct Robux per acquisto diretto (id in Config.Monetization).
	Nessun cosmetico ha effetti sul gameplay.
]]

export type Cosmetic = {
	Id: string,
	Name: string,
	Slot: string, -- skin | sky | trail | emote | nameplate
	TokenPrice: number?, -- nil = non acquistabile con gettoni (es. solo pass/fondatore)
	Description: string,
	Data: { [string]: any },
	Source: string?, -- "tokens" | "pass" | "founder" | "weekly" | "album"
}

local list: { Cosmetic } = {
	-- Skin del vivaio (materiale/colore della piattaforma)
	{ Id = "skin_prato", Name = "Prato di nuvola", Slot = "skin", TokenPrice = 0, Description = "La base classica: erba soffice sulle nuvole.", Data = { Material = "Grass", Color = Color3.fromRGB(128, 200, 120), Trim = Color3.fromRGB(240, 246, 255) }, Source = "default" },
	{ Id = "skin_sabbia", Name = "Spiaggia celeste", Slot = "skin", TokenPrice = 45, Description = "Sabbia dorata e bordi di schiuma.", Data = { Material = "Sand", Color = Color3.fromRGB(236, 214, 160), Trim = Color3.fromRGB(180, 230, 255) } },
	{ Id = "skin_cristallo", Name = "Giardino di cristallo", Slot = "skin", TokenPrice = 90, Description = "Pavimento lucido come vetro ghiacciato.", Data = { Material = "Glass", Color = Color3.fromRGB(190, 230, 255), Trim = Color3.fromRGB(255, 255, 255) } },
	{ Id = "skin_notte", Name = "Velluto notturno", Slot = "skin", TokenPrice = 90, Description = "Blu profondo con bordi che brillano.", Data = { Material = "Fabric", Color = Color3.fromRGB(60, 70, 120), Trim = Color3.fromRGB(200, 170, 255) } },
	-- Cieli
	{ Id = "sky_giorno", Name = "Cielo del mattino", Slot = "sky", TokenPrice = 0, Description = "Azzurro limpido e nuvole bianche.", Data = { ClockTime = 13.5, Ambient = Color3.fromRGB(143, 161, 199), Tint = Color3.fromRGB(255, 255, 255) }, Source = "default" },
	{ Id = "sky_tramonto", Name = "Tramonto pesca", Slot = "sky", TokenPrice = 60, Description = "Arancio tenue che sfuma nel rosa.", Data = { ClockTime = 17.6, Ambient = Color3.fromRGB(200, 150, 140), Tint = Color3.fromRGB(255, 220, 190) } },
	{ Id = "sky_aurora", Name = "Notte d'aurora", Slot = "sky", TokenPrice = 120, Description = "Cielo scuro attraversato da veli verdi e viola.", Data = { ClockTime = 1.5, Ambient = Color3.fromRGB(90, 110, 170), Tint = Color3.fromRGB(170, 200, 255) } },
	-- Scie di particelle leggere (sul personaggio)
	{ Id = "trail_nessuna", Name = "Nessuna scia", Slot = "trail", TokenPrice = 0, Description = "Niente effetti.", Data = {}, Source = "default" },
	{ Id = "trail_stelline", Name = "Scia di stelline", Slot = "trail", TokenPrice = 40, Description = "Piccole stelle dorate che si spengono piano.", Data = { Color = Color3.fromRGB(255, 220, 120), Rate = 6 } },
	{ Id = "trail_gocce", Name = "Scia di gocce", Slot = "trail", TokenPrice = 40, Description = "Goccioline azzurre leggere.", Data = { Color = Color3.fromRGB(140, 200, 255), Rate = 6 } },
	{ Id = "trail_petali", Name = "Scia di petali", Slot = "trail", TokenPrice = 75, Description = "Petali rosa trasportati dal vento.", Data = { Color = Color3.fromRGB(255, 170, 210), Rate = 8 } },
	-- Emote non invasive
	{ Id = "emote_saluto", Name = "Saluto", Slot = "emote", TokenPrice = 0, Description = "Un gesto amichevole.", Data = { Text = "👋" }, Source = "default" },
	{ Id = "emote_applauso", Name = "Applauso", Slot = "emote", TokenPrice = 30, Description = "Per un layout ben fatto.", Data = { Text = "👏" } },
	{ Id = "emote_stella", Name = "Stellina", Slot = "emote", TokenPrice = 30, Description = "Una stellina sopra la testa.", Data = { Text = "✨" } },
	-- Targhette
	{ Id = "plate_nessuna", Name = "Nessuna targhetta", Slot = "nameplate", TokenPrice = 0, Description = "", Data = {}, Source = "default" },
	{ Id = "plate_fondatore", Name = "Targhetta Fondatore", Slot = "nameplate", Description = "Per chi ha creduto nel vivaio dal primo giorno.", Data = { Text = "Fondatore", Color = Color3.fromRGB(255, 200, 90) }, Source = "founder" },
	{ Id = "plate_collezionista", Name = "Targhetta Collezionista", Slot = "nameplate", Description = "Album di una famiglia completato.", Data = { Text = "Collezionista", Color = Color3.fromRGB(150, 200, 255) }, Source = "album" },
	-- Premi del pass / tema settimanale
	{ Id = "skin_fondatore", Name = "Terrazza del Fondatore", Slot = "skin", Description = "Marmo bianco con venature dorate.", Data = { Material = "Marble", Color = Color3.fromRGB(240, 236, 225), Trim = Color3.fromRGB(255, 200, 90) }, Source = "founder" },
	{ Id = "trail_aurora", Name = "Scia d'aurora", Slot = "trail", Description = "Nastri di luce verde e viola.", Data = { Color = Color3.fromRGB(180, 140, 255), Rate = 10 }, Source = "pass" },
	{ Id = "sky_monsone", Name = "Cielo del monsone", Slot = "sky", Description = "Grigio perla con pioggia luminosa.", Data = { ClockTime = 15, Ambient = Color3.fromRGB(150, 160, 180), Tint = Color3.fromRGB(200, 210, 230) }, Source = "pass" },
	{ Id = "emote_pioggia", Name = "Pioggerella", Slot = "emote", Description = "Una nuvoletta che piove felice.", Data = { Text = "🌧️" }, Source = "pass" },
	{ Id = "skin_alisei", Name = "Terrazza degli alisei", Slot = "skin", Description = "Legno chiaro battuto dal vento.", Data = { Material = "WoodPlanks", Color = Color3.fromRGB(220, 200, 160), Trim = Color3.fromRGB(170, 240, 215) }, Source = "weekly" },
	{ Id = "plate_meteorologo", Name = "Targhetta Meteorologo", Slot = "nameplate", Description = "Sfida settimanale completata.", Data = { Text = "Meteorologo", Color = Color3.fromRGB(170, 240, 215) }, Source = "weekly" },
}

local Cosmetics = { List = list, ById = {} }
for _, c in ipairs(list) do
	Cosmetics.ById[c.Id] = c
end

Cosmetics.Slots = { "skin", "sky", "trail", "emote", "nameplate" }
Cosmetics.SlotNames = { skin = "Skin del vivaio", sky = "Cielo", trail = "Scia", emote = "Emote", nameplate = "Targhetta" }

Cosmetics.Defaults = {
	skin = "skin_prato",
	sky = "sky_giorno",
	trail = "trail_nessuna",
	emote = "emote_saluto",
	nameplate = "plate_nessuna",
}

-- Pass delle Nuvole: percorso trasparente, solo premi estetici, visibile per intero.
-- Punti pass guadagnati con commissioni/attività. Premium = sblocca la corsia "Premium" (gamepass opzionale).
Cosmetics.Pass = {
	PointsPerCommission = 10,
	PointsPerRaid = 4,
	PointsPerAlbumMilestone = 15,
	Tiers = {
		{ Points = 20, Free = { Tokens = 10 }, Premium = { Cosmetic = "emote_pioggia" } },
		{ Points = 50, Free = { Tokens = 15 }, Premium = { Tokens = 20 } },
		{ Points = 90, Free = { Cosmetic = "trail_gocce" }, Premium = { Cosmetic = "sky_monsone" } },
		{ Points = 140, Free = { Tokens = 20 }, Premium = { Tokens = 30 } },
		{ Points = 200, Free = { Tokens = 25 }, Premium = { Cosmetic = "trail_aurora" } },
	},
}

Cosmetics.FounderBundle = { "plate_fondatore", "skin_fondatore" }

function Cosmetics.Get(id): Cosmetic?
	return Cosmetics.ById[id]
end

return Cosmetics
