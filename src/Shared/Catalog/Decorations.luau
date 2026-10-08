--!nonstrict
-- Decorazioni: oggetti estetici posizionabili sulla griglia (non bloccano il percorso).
export type Decoration = { Id: string, Name: string, Description: string, Visual: { Kind: string, Color: Color3, Accent: Color3?, Height: number? }, Source: string }

local list: { Decoration } = {
	{ Id = "lanterna_nube", Name = "Lanterna di nube", Description = "Una lanterna che ondeggia con luce calda.", Visual = { Kind = "lantern", Color = Color3.fromRGB(255, 220, 150), Accent = Color3.fromRGB(120, 90, 60) }, Source = "tutorial" },
	{ Id = "cespuglio_stellato", Name = "Cespuglio stellato", Description = "Foglie azzurre punteggiate di stelline.", Visual = { Kind = "bush", Color = Color3.fromRGB(110, 190, 150), Accent = Color3.fromRGB(255, 240, 180) }, Source = "tutorial" },
	{ Id = "meridiana", Name = "Meridiana solare", Description = "Segna le ore con un'ombra di luce.", Visual = { Kind = "sundial", Color = Color3.fromRGB(240, 220, 170), Accent = Color3.fromRGB(255, 190, 70) }, Source = "album" },
	{ Id = "fontanella", Name = "Fontanella di pioggia", Description = "Zampilla goccioline azzurre.", Visual = { Kind = "fountain", Color = Color3.fromRGB(200, 220, 240), Accent = Color3.fromRGB(100, 170, 250) }, Source = "album" },
	{ Id = "girandola", Name = "Girandola del vento", Description = "Gira sempre, anche senza vento.", Visual = { Kind = "pinwheel", Color = Color3.fromRGB(250, 250, 255), Accent = Color3.fromRGB(150, 232, 200) }, Source = "album" },
	{ Id = "arco_luce", Name = "Arco di luce", Description = "Un piccolo arco d'aurora sopra il prato.", Visual = { Kind = "arch", Color = Color3.fromRGB(196, 130, 255), Accent = Color3.fromRGB(150, 255, 220) }, Source = "album" },
	{ Id = "fontana_stelle", Name = "Fontana di stelle", Description = "Stelline che salgono verso il cielo.", Visual = { Kind = "fountain", Color = Color3.fromRGB(240, 240, 255), Accent = Color3.fromRGB(255, 220, 120) }, Source = "album" },
	{ Id = "trono_nuvola", Name = "Trono di nuvola", Description = "Il posto d'onore di chi ha completato il cielo.", Visual = { Kind = "throne", Color = Color3.fromRGB(250, 250, 255), Accent = Color3.fromRGB(255, 200, 90) }, Source = "album" },
	{ Id = "panchina", Name = "Panchina di nube", Description = "Per osservare le creature in pace.", Visual = { Kind = "bench", Color = Color3.fromRGB(240, 244, 255), Accent = Color3.fromRGB(150, 180, 220) }, Source = "shop", TokenPrice = 20 },
	{ Id = "fiori_cielo", Name = "Fiori di cielo", Description = "Un'aiuola di fiori azzurri e rosa.", Visual = { Kind = "bush", Color = Color3.fromRGB(120, 200, 140), Accent = Color3.fromRGB(255, 170, 210) }, Source = "shop", TokenPrice = 20 },
}

local Decorations = { List = list, ById = {} }
for _, d in ipairs(list) do
	Decorations.ById[d.Id] = d
end

Decorations.MaxPlaced = 10 -- limite per performance su mobile

return Decorations
