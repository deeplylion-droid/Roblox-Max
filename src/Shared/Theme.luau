--!nonstrict
-- Palette e misure dell'interfaccia. Pastelli celesti, contrasto alto, testo sempre leggibile.
local Theme = {}

Theme.Colors = {
	Sky = Color3.fromRGB(176, 214, 255),
	SkyDeep = Color3.fromRGB(94, 143, 222),
	Panel = Color3.fromRGB(246, 250, 255),
	PanelAlt = Color3.fromRGB(228, 238, 252),
	PanelDark = Color3.fromRGB(36, 48, 78),
	Stroke = Color3.fromRGB(120, 160, 220),
	Text = Color3.fromRGB(32, 42, 68),
	TextMuted = Color3.fromRGB(96, 110, 140),
	TextOnDark = Color3.fromRGB(245, 249, 255),
	Accent = Color3.fromRGB(255, 196, 72), -- scintilla
	AccentDark = Color3.fromRGB(214, 150, 30),
	Success = Color3.fromRGB(84, 196, 128),
	Danger = Color3.fromRGB(236, 104, 104),
	Info = Color3.fromRGB(92, 160, 255),
	Fragment = Color3.fromRGB(144, 196, 255),
	Token = Color3.fromRGB(226, 142, 255),
	Shield = Color3.fromRGB(120, 220, 240),
	Family = {
		sole = Color3.fromRGB(255, 190, 70),
		pioggia = Color3.fromRGB(96, 160, 240),
		vento = Color3.fromRGB(150, 232, 200),
		aurora = Color3.fromRGB(196, 130, 255),
	},
	Rarity = {
		comune = Color3.fromRGB(170, 190, 215),
		insolito = Color3.fromRGB(100, 200, 140),
		raro = Color3.fromRGB(96, 150, 255),
		leggendario = Color3.fromRGB(255, 170, 80),
	},
}

Theme.Font = Enum.Font.FredokaOne
Theme.FontBody = Enum.Font.GothamMedium
Theme.FontBold = Enum.Font.GothamBold

Theme.Corner = UDim.new(0, 14)
Theme.CornerSmall = UDim.new(0, 8)
Theme.StrokeThickness = 2

Theme.TextSize = {
	Title = 28,
	Header = 22,
	Body = 18,
	Small = 15,
	Hud = 20,
}

Theme.ButtonHeight = 52 -- pulsanti grandi, mobile-first

return Theme
